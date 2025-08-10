# Cipher Backtest Library Documentation

Trading strategy backtesting framework supporting multiple concurrent sessions, complex exit strategies,
and multi-exchange data sources.

## Backtest Example

```python
import talib

from cipher import Cipher, Strategy, Session


class EMACrossoverStrategy(Strategy):
    def __init__(self, slow_period=200, fast_period=50, atr_period=14):
        self.slow_period = slow_period
        self.fast_period = fast_period
        self.atr_period = atr_period

    def compose(self):
        df = self.datas.df

        df["ema_slow"] = talib.EMA(df["close"], timeperiod=self.slow_period)
        df["ema_fast"] = talib.EMA(df["close"], timeperiod=self.fast_period)
        df["atr"] = talib.ATR(df["high"], df["low"], df["close"], timeperiod=self.atr_period)

        df["entry"] = (df["ema_fast"] > df["ema_slow"]) & (df["ema_fast"].shift(1) <= df["ema_slow"].shift(1))

        return df

    def on_entry(self, row: dict, session: Session):
        session.position += "0.01"
        session.stop_loss = row["close"] - row["atr"]
        session.take_profit = row["close"] + row["atr"]
    
    def on_stop(self, row: dict, session: Session) -> None:
        session.position = 0


def main():
    cipher = Cipher()
    cipher.add_source("binance_spot_ohlc", symbol="BTCUSDT", interval="1h")
    cipher.set_strategy(EMACrossoverStrategy())
    cipher.set_commission("0.00075")

    cipher.run(start_ts="2025-01-01", stop_ts="2025-04-01")

    print(cipher.stats)  # prints stats as a Markdown table
    cipher.plot("mplfinance")


if __name__ == "__main__":
    main()
```

## Types

```python
import datetime
from decimal import Decimal
from typing import Optional, Union

from pydantic import BaseModel

from pandas import DataFrame


class Session:
    meta: dict

    @property
    def is_long(self) -> bool:
        ...

    @property
    def is_open(self) -> bool:
        ...

    @property
    def is_closed(self) -> bool:
        ...

    @property
    def take_profit(self) -> Optional[Decimal]:
        ...

    @take_profit.setter
    def take_profit(self, value: Union[Percent, Decimal, int, str, float]):
        ...

    @property
    def stop_loss(self) -> Optional[Decimal]:
        ...

    @stop_loss.setter
    def stop_loss(self, value: Union[Percent, Decimal, int, str, float]):
        ...

    @property
    def position(self) -> Position:
        ...

    @position.setter
    def position(self, value: Union[Base, Quote, Percent, Decimal, int, str, float, Position]):
        ...


class Datas(list):
    @property
    def df(self):
        return self[0]


class Wallet:
    @property
    def base(self) -> Decimal:
        ...

    @property
    def quote(self) -> Decimal:
        ...


class Strategy:
    datas: Datas
    wallet: Wallet

    def compose(self) -> DataFrame:
        ...

    def on_step(self, row: dict, session: Session) -> None:
        """Runs each interval."""
        ...

    def on_entry(self, row: dict, session: Session) -> None:
        """Runs when on entry signal."""
        ...

    # def on_<signal>(self, row: dict, session: Session) -> None:
    #     ...

    def on_take_profit(self, row: dict, session: Session) -> None:
        """Runs when prices hits the current take profit level."""
        session.position = 0

    def on_stop_loss(self, row: dict, session: Session) -> None:
        """Runs when prices hits the current stop loss level."""
        session.position = 0

    def on_stop(self, row: dict, session: Session) -> None:
        """Runs when dataframe reaches the end."""
        ...


class Time(int):
    """Represents time, in seconds."""
    def to_datetime(self) -> datetime.datetime:
        ...

    @classmethod
    def from_datetime(cls, dt: datetime.datetime) -> "Time":
        ...

    @classmethod
    def from_string(cls, s: Union[str, datetime.datetime]) -> "Time":
        ...


class TimeDelta(int):
    def to_timedelta(self) -> datetime.timedelta:
        ...


class Stats(BaseModel):
    # general
    start_ts: Time
    stop_ts: Time
    period: TimeDelta  # dataframe size
    exposed_period: TimeDelta

    # sessions
    sessions_n: int
    success_n: int
    failure_n: int
    shorts_n: int
    longs_n: int
    session_period_median: Optional[TimeDelta]
    session_period_max: Optional[TimeDelta]

    # performance
    pnl: Decimal  # profit and loss
    volume: Decimal
    commission: Decimal
    success_pnl_med: Optional[Decimal]
    failure_pnl_med: Optional[Decimal]
    success_pnl_max: Optional[Decimal]
    failure_pnl_max: Optional[Decimal]
    success_row_max: int
    failure_row_max: int
    balance_min: Decimal
    balance_max: Decimal
    balance_drawdown_max: Decimal
    romad: Optional[Decimal]


class Cipher:
    def set_strategy(self, strategy: Strategy):
        ...

    def add_source(self, source: str, **kwargs):
        ...

    def set_commission(self, value: Union[Decimal, str, Percent]):
        ...

    def run(self, start_ts: Union[Time, str], stop_ts: Union[Time, str]):
        ...

    @property
    def stats(self) -> Stats:
        ...

    def plot(
        self,
        plotter: Union[None, str] = None,
        start: Union[str, int, None] = None,
        limit: Optional[int] = None,
        **kwargs,
    ):
        ...
```

## Architecture

Strategy manipulates positions through a `Session` object, which tracks position size, transactions, and stop loss/take profit levels.

**Key Concepts Translation:**
- `buy` → add to position
- `sell` → reduce position
- `trade` → session (trading session)
- `close trade` → close session (side effect of adjusting position to 0)
- `order(market)` → transaction (side effect for position change)
- `order(limit, stop_loss)` → brackets

### Strategy Class

Strategy explains Cipher when and how to adjust positions.

### Sessions

A session starts from us adding or reducing position inside on_entry method. A session is considered closed when its position is adjusted to zero.

**Session Attributes:**
- `position` - Current position size
- `transactions` - List of transactions (read-only)
- `take_profit` - Take profit level
- `stop_loss` - Stop loss level  
- `meta` - Dictionary for storing custom session data

**Session Meta**: Use `session.meta` to store strategy-specific state between signals.

**Session Types:**
- **Long session** - Starts from adding to position
- **Short session** - Starts from reducing position

**Multiple sessions** can be open simultaneously.

### Position Management

Each new session has a position equal to 0 initially. We can add to a position, or reduce a position (it can be negative).

```python
from cipher import base, quote, percent
from decimal import Decimal

# Different ways to set position
session.position = 1                    # Base units
session.position = base(1)              # Same as above
session.position = "1"                  # String/int/float converted to Decimal
session.position = quote(100)           # Position worth 100 quote asset
session.position += 1                   # Add to position
session.position -= Decimal("1.25")     # Reduce position
session.position += percent(50)         # Add 50% more
session.position *= 1.5                 # Multiply position (same as +50%)
```

### Brackets (Stop Loss & Take Profit)

```python
from cipher import percent

# Fixed price levels
session.take_profit = row["close"] * 1.015
session.stop_loss = row["close"] * 0.985

# Percentage-based (relative to current price)
session.take_profit = percent("1.5")    # +1.5% for long
session.stop_loss = percent("-1")       # -1% for long

# Disable brackets
session.stop_loss = None
session.take_profit = None
```

### Signals

There is one signal that is required - entry. We can define as many as we want.

**Requirements:**
- Signal columns must be **boolean type**
- Column name must match signal handler method name
- Handler method: `on_<signal_name>`

```python
def compose(self):
    df = self.datas.df

    # Required entry signal
    df["entry"] = some_boolean_condition

    # Custom signals
    df["exit_signal"] = another_boolean_condition

    return df

def on_exit_signal(self, row: dict, session: Session):
    """Called for each open session when exit_signal is True"""
    session.position *= 0.5  # Reduce position by 50%
```

**Signal Design**: signal columns have to be boolean type.

**Special Handlers:**
- `on_step(row, session)` - Called for every row for each open session
- `on_stop(row, session)` - Called when dataframe ends for open sessions

## Sources

Sources available are:
- `binance_futures_ohlc` (symbol, interval)
- `binance_spot_ohlc` (symbol, interval)
- `csv_file` (path, ts_format)
- `gateio_spot_ohlc` (symbol, interval)
- `yahoo_finance_ohlc` (symbol, interval)

Use `binance_spot_ohlc` or `gateio_spot_ohlc` for crypto.
Use `yahoo_finance_ohlc` for stocks, commodities, and indices.

## Plotting

Default plot:
```python
cipher.plot("mplfinance")
```

Custom layout:
```python
cipher.plot(
    "mplfinance",
    rows=[
        ["ohlc", "ema_fast", "ema_slow"],  # Price + EMAs
        ["balance"],                       # Account balance
    ]
)
```

Available row types:
```python
rows = [
    ["ohlc"],           # OHLC candlesticks
    ["ohlcv"],          # OHLC + Volume
    ["signals"],        # Entry/exit signals, only can be included into the first row
    ["position"],       # Position size over time
    ["balance"],        # Account balance
    ["sessions"],       # Session markers, only can be included into the first row
    ["brackets"],       # Stop loss/take profit levels, only can be included into the first row
    ["indicator_name"],  # Any custom indicator
]
```

Styling plots - specify colors and markers:
```python
rows = [["ohlc", "my_indicator|^", "another_indicator|s|red"]]
```
## Strategy Examples

Buy o Tuesday Doge worth of 1000 USD, close half at 1ATR and close att at 2ATR, slop loss - 1ATR:
```python
import talib

from cipher import Session, Strategy, quote


class TuesdayATRStrategy(Strategy):
    def __init__(self, atr_period=14):
        self.atr_period = atr_period

    def compose(self):
        df = self.datas.df

        df["atr"] = talib.ATR(df["high"], df["low"], df["close"], timeperiod=self.atr_period)
        df["day_of_week"] = df.index.to_series().dt.dayofweek

        df["entry"] = df["day_of_week"] == 1

        return df

    def on_entry(self, row: dict, session: Session):
        session.position = quote(1000)  # 1000 dollars worth of gold

        session.meta["entry_price"] = row["close"]
        session.meta["entry_atr"] = row["atr"]
        session.meta["partial_exit_done"] = False

        session.stop_loss = row["close"] - row["atr"]
        session.take_profit = row["close"] + row["atr"]

    def on_take_profit(self, row: dict, session: Session) -> None:
        if session.meta.get("partial_exit_done", False):
            session.position = 0
        else:
            session.meta["partial_exit_done"] = True
            session.position *= 0.5
            session.take_profit = row["close"] + row["atr"]
            session.stop_loss = row["close"] - row["atr"]
```

Enter short when volume drops, use trailing stop 1 ATR:
```python
import talib

from cipher import Session, Strategy


class VolumeGoesDownTrailingStopStrategy(Strategy):
    def __init__(self, atr_period=14):
        self.atr_period = atr_period

    def compose(self):
        df = self.datas.df

        df["atr"] = talib.ATR(df["high"], df["low"], df["close"], timeperiod=self.atr_period)

        df["entry"] = df["volume"] < df["volume"].shift(1)

        return df

    def on_entry(self, row: dict, session: Session):
        if self.wallet.base:  # no concurrent sessions
            return

        session.position -= "0.01"

        session.meta["atr"] = row["atr"]
        session.meta["lowest_price"] = row["close"]
        session.stop_loss = row["close"] + row["atr"]
        session.take_profit = row["close"] - row["atr"]

    def on_step(self, row: dict, session: Session):
        if session.is_open and session.meta["lowest_price"] > row["low"]:
            session.meta["lowest_price"] = row["low"]
            session.stop_loss = session.meta["lowest_price"] + session.meta["atr"]
```
