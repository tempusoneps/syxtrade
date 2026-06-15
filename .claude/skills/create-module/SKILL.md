---
name: create-module
description: Use when creating a new trading module for the TempusOnePs project — scaffolds directory structure, plugin boilerplate, and config.json for data/signal/execution/log/backtest components.
---

# Create TempusOnePs Module

## Overview

A module is a self-contained directory at `modules/<name>/` containing `config/config.json` and plugin files for each pipeline stage: **data → signals → execution → log**.

## Directory Structure

```
modules/<module_name>/
├── config/
│   └── config.json          ← required
├── data/
│   └── <data_source>.py     ← required
├── signals/
│   └── <strategy>.py        ← required
├── execution/
│   └── <executor>.py        ← required
├── log/
│   └── <logger>.py          ← optional
└── backtest/
    └── <script>.py          ← optional
```

## 1. config/config.json

`path` is a Python module path (use `.` not `/`).

```json
{
  "interval": 5,
  "pipeline": {
    "data": [
      {
        "name": "<data_source>",
        "path": "modules.<module_name>.data.<filename>",
        "class": "<ClassName>",
        "enabled": true
      }
    ],
    "signals": [
      {
        "name": "<strategy>.signal",
        "path": "modules.<module_name>.signals.<filename>",
        "class": "<ClassName>",
        "enabled": true
      }
    ],
    "execution": [
      {
        "name": "<module_name>.executor",
        "path": "modules.<module_name>.execution.<filename>",
        "class": "<ClassName>",
        "enabled": true
      }
    ],
    "log": []
  }
}
```

## 2. Data Plugin

`run()` takes no parameters. Return `None` when data is exhausted to stop the dev/replay loop.

```python
from core.service.base_service import BaseServicePlugin
import pandas as pd


class MyDataService(BaseServicePlugin):
    def setup(self):
        # connect to API, read CSV, initialize state...
        pass

    def run(self):
        # return OHLCV DataFrame, or None when data is exhausted
        return df  # columns: Open, High, Low, Close, Volume (index: Date)
```

## 3. Signal Plugin

Receives `df.copy()` — safe to mutate. **Must** return a dict, not a raw DataFrame.

```python
from core.service.base_service import BaseServicePlugin
from core.service.base_signal import SignalConfig


class MySignalPlugin(BaseServicePlugin):
    def run(self, data):
        # compute indicator
        data['my_indicator'] = ...
        # generate signal column
        data['my_signal'] = data.apply(lambda r: self._get_signal(r), axis=1)
        # return only new columns — they will be merged into the main df
        return {
            "data": data[["my_indicator", "my_signal"]],
            "meta_data": {"service_name": self.name}
        }

    def _get_signal(self, r):
        if ...:
            return SignalConfig.BUY_SIGNAL
        if ...:
            return SignalConfig.SELL_SIGNAL
        return SignalConfig.NO_SIGNAL
```

**Do not** create `mp.Pool` inside a signal plugin — `TempusOnePsSignal` manages a persistent pool.

## 4. Execution Plugin

Read the last bar (`iloc[-1]`) to get the current signal and price.

```python
from core.service.base_service import BaseServicePlugin
from core.service.base_signal import SignalConfig


class MyExecutor(BaseServicePlugin):
    def run(self, data=None):
        self.trigger_before(data, self.name)
        if data is not None and len(data):
            last = data.iloc[-1]
            signal = last["my_signal"]   # column name from signal plugin
            price  = last["Close"]
            if signal == SignalConfig.BUY_SIGNAL:
                # open long / place buy order
                pass
            elif signal == SignalConfig.SELL_SIGNAL:
                # open short / place sell order
                pass
        self.trigger_after({}, self.name)
```

## 5. Log Plugin (optional)

```python
from core.service.base_service import BaseServicePlugin


class MyLogger(BaseServicePlugin):
    def setup(self):
        # open file, connect to DB, Telegram...
        pass

    def run(self, data=None):
        for log in self.log_queue.get_all():
            # write to file / DB / Telegram...
            pass

    def teardown(self):
        # close connections
        pass
```

## 6. Backtest Script (optional)

Compute signals **vectorized once** on the full dataset — do not replay bar-by-bar.

```python
import os, pandas as pd
from backtesting.backtesting import Backtest, Strategy
from core.utils import load_config
from core.service_loader import load_services
from core.log_queue import TempusOnePsLogQueue
from core.service.base_signal import TempusOnePsSignal, SignalConfig

current_folder = os.path.dirname(os.path.abspath(__file__))
dataset = pd.read_csv(os.path.join(current_folder, "../data/data.csv"),
                      index_col='Date', parse_dates=True)

config_file = os.path.join(current_folder, "../../config/config.json")  # adjust path
config = load_config(config_file)
log_queue = TempusOnePsLogQueue()
services = load_services(config, log_queue)

signal_services = services.get("signals", [])
tops = TempusOnePsSignal(signal_services, log_queue)
tops.setup()
signals_output = tops.run(dataset)
tops.teardown()
signals_output.dropna(inplace=True)


class MainStrategy(Strategy):
    def init(self):
        super().init()

    def next(self):
        super().next()
        signal = self.data.my_signal[-1]
        if signal == SignalConfig.BUY_SIGNAL and not self.position.is_long:
            self.buy()
        elif signal == SignalConfig.SELL_SIGNAL and not self.position.is_short:
            self.sell()


bt = Backtest(signals_output, MainStrategy, commission=.0003, exclusive_orders=True)
stats = bt.run()
print(stats)
```

## Run Module

```bash
uv run python run.py --mod <module_name> --mode dev    # fast replay
uv run python run.py --mod <module_name> --mode live   # live with sleep
uv run python run-cron.py --mod <module_name>          # one-shot
uv run python modules/<module_name>/backtest/<script>.py
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Signal plugin returns a raw DataFrame | Must return `{"data": df, "meta_data": {"service_name": self.name}}` |
| Data plugin never returns `None` | Dev mode runs forever |
| `path` uses `/` instead of `.` | Use Python module path: `modules.name.data.file` |
| Creating `mp.Pool` inside a signal plugin | Not needed — core manages the persistent pool |
| Reading wrong signal column name | Column name is whatever you set in the signal plugin, not `"signal"` |
| Wrong arg type for `load_config` | `run.py` passes an `args` object; backtest scripts pass a `config_file` string — see `core/utils.py` |
