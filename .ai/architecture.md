# TempusOnePs — Architecture

## Overview

TempusOnePs là một nền tảng giao dịch thuật toán (algo trading) dạng **modular plugin**, thiết kế theo mô hình **pipeline + service bus**. Mỗi bước xử lý trong pipeline là một plugin độc lập, có thể bật/tắt và hoán đổi qua config mà không cần sửa code core.

**Stack:** Python 3.8+, pandas, pandas-ta, multiprocessing, backtesting.py, croniter

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Entry Points                       │
│         run.py (scheduler loop)                         │
│         run-cron.py (one-shot / OS cron)                │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                   Core Engine                           │
│                                                         │
│  Scheduler ──► run_pipeline()                           │
│                     │                                   │
│          ┌──────────▼──────────┐                        │
│          │   Pipeline Stages   │                        │
│          │                     │                        │
│          │  1. DATA            │  (sequential)          │
│          │  2. SIGNALS         │  (multiprocessing)     │
│          │  3. EXECUTION       │  (sequential)          │
│          │  4. LOG             │  (sequential)          │
│          └──────────┬──────────┘                        │
│                     │                                   │
│          LogQueue (in-memory event bus)                 │
└─────────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                  Plugin Modules                         │
│         modules/<module_name>/                          │
│           ├── config/config.json                        │
│           ├── data/        ← DataServicePlugin          │
│           ├── signals/     ← SignalPlugin               │
│           ├── execution/   ← ExecutionPlugin            │
│           ├── log/         ← LogPlugin                  │
│           └── backtest/    ← standalone backtest script │
└─────────────────────────────────────────────────────────┘
```

---

## Core Components

### `core/service_loader.py` — Dynamic Plugin Loader

Load tất cả plugin từ `config.json` bằng `importlib.import_module`. Mỗi plugin được instantiate với `(name, config, log_queue, mode)`.

```
config.json pipeline entry  →  importlib.import_module(path)
                            →  getattr(module, class)
                            →  instance(name, config, log_queue, mode)
```

### `core/scheduler.py` — Scheduler

Điều phối thời gian chạy pipeline:
- **Cron mode** (`cron_expr`): polling mỗi 500ms, fire khi đến lịch
- **Interval mode** (`interval`): chạy liên tục
  - `mode='live'`: sleep `interval` giây giữa mỗi tick
  - `mode='dev'`: không sleep, chạy nhanh nhất có thể, dừng khi callback trả `False`

### `core/log_queue.py` — LogQueue (Event Bus)

In-memory queue dùng như một lightweight event bus nội bộ. Mỗi bước trong pipeline ghi sự kiện (trigger_before, trigger_after, kết quả signal...) vào queue. Stage LOG đọc và flush ra file/console. Queue được `clear_all()` sau mỗi tick.

```
Service.trigger_before()  ──►  LogQueue.log(event)
Service.trigger_after()   ──►  LogQueue.log(event)
TempusOnePsSignal.run()   ──►  LogQueue.log(event)
                                    │
LogService.run()          ◄──  LogQueue.get_all()
LogQueue.clear_all()       ── end of tick
```

### `core/service/base_service.py` — BaseServicePlugin

Base class cho tất cả plugin. Lifecycle:

```
setup()      ← gọi 1 lần lúc khởi động
run(data)    ← gọi mỗi tick
teardown()   ← gọi khi shutdown
```

Cung cấp `trigger_before()` / `trigger_after()` để ghi sự kiện vào LogQueue.

### `core/service/base_signal.py` — Signal Engine

```
class TempusOnePsSignal:
    setup()       → tạo mp.Pool (1 lần duy nhất, persistent)
    run(df)       → pool.map(run_single_signal_module, signals×df)
                  → merge kết quả vào DataFrame
    teardown()    → đóng pool
```

**Quan trọng:** Pool được tạo 1 lần trong `setup()`, tái sử dụng qua mọi tick để tránh overhead spawn process. Lazy init nếu `setup()` chưa được gọi.

### `core/service/base_signal.py` — SignalConfig

Enum-style constants cho tín hiệu giao dịch:

| Constant | Value | Ý nghĩa |
|---|---|---|
| `NO_SIGNAL` | `""` | Không có tín hiệu |
| `BUY_SIGNAL` | `"buy"` | Mở Long |
| `SELL_SIGNAL` | `"sell"` | Mở Short |
| `CLOSE_SIGNAL` | `"close"` | Đóng vị thế |
| `CLOSE_BUY_SIGNAL` | `"close.buy"` | Đóng Long |
| `CLOSE_SELL_SIGNAL` | `"close.sell"` | Đóng Short |
| `SWITCH_TO_BUY_SIGNAL` | `"switch.to.buy"` | Đảo chiều sang Long |
| `SWITCH_TO_SELL_SIGNAL` | `"switch.to.sell"` | Đảo chiều sang Short |

---

## Pipeline Flow (mỗi tick)

```
run_pipeline()
│
├── [DATA] DataPlugin.run()
│         └── trả về DataFrame (OHLCV + custom cols)
│               Nếu None → return False (data exhausted, dừng loop)
│
├── [SIGNALS] TempusOnePsSignal.run(df)
│         └── pool.map() → mỗi signal plugin nhận df.copy()
│             └── plugin trả về {"data": df_with_cols, "meta_data": {...}}
│             └── merge tất cả kết quả vào df gốc
│
├── [EXECUTION] ExecutionPlugin.run(signals_df)
│         └── đọc signal của bar cuối, gửi lệnh / simulate
│
├── [LOG] LogPlugin.run()
│         └── flush LogQueue ra file / console
│
└── LogQueue.clear_all()
```

---

## Run Modes

| Mode | Lệnh | Hành vi |
|---|---|---|
| **Live** | `python run.py --mod <name> --mode live` | Sleep `interval`s giữa mỗi tick, data source pull từ API real-time |
| **Dev/Replay** | `python run.py --mod <name> --mode dev` | Không sleep, replay CSV row-by-row với tốc độ tối đa |
| **One-shot** | `python run-cron.py --mod <name>` | Chạy 1 tick duy nhất, thường dùng với OS cron |
| **Backtest** | `python modules/<name>/backtest/<script>.py` | Tính signal vectorized trên toàn bộ dataset, dùng `backtesting.py` |

---

## Plugin System

### Cách đăng ký plugin (config.json)

```json
{
  "interval": 3,
  "pipeline": {
    "data":      [{ "name": "...", "path": "modules.X.data.Y",      "class": "Z", "enabled": true }],
    "signals":   [{ "name": "...", "path": "modules.X.signals.Y",   "class": "Z", "enabled": true }],
    "execution": [{ "name": "...", "path": "modules.X.execution.Y", "class": "Z", "enabled": true }],
    "log":       [{ "name": "...", "path": "modules.X.log.Y",       "class": "Z", "enabled": true }]
  }
}
```

`path` là Python module path, `class` là tên class trong file đó. Nhiều plugin trong cùng một stage chạy **song song** (signals) hoặc **tuần tự** (data, execution, log).

### Tạo signal plugin mới

```python
from core.service.base_service import BaseServicePlugin
from core.service.base_signal import SignalConfig

class MyStrategy(BaseServicePlugin):
    def run(self, data):
        # data là DataFrame OHLCV, thêm cột signal
        data['my_signal'] = ...
        return {
            "data": data[["my_signal"]],      # chỉ trả cột mới
            "meta_data": {"service_name": self.name}
        }
```

**Lưu ý:** Signal plugin nhận `df.copy()` — an toàn để mutate, không ảnh hưởng các plugin khác chạy song song.

### Tạo data plugin mới

```python
from core.service.base_service import BaseServicePlugin

class MyDataService(BaseServicePlugin):
    def setup(self):
        # kết nối API, đọc file...

    def run(self):
        # trả về DataFrame hoặc None nếu hết data
        return df
```

---

## Module Structure

```
modules/
└── <module_name>/
    ├── config/
    │   └── config.json          ← pipeline config của module
    ├── data/
    │   └── my_data_source.py    ← DataServicePlugin
    ├── signals/
    │   └── my_strategy.py       ← BaseServicePlugin (signal)
    ├── execution/
    │   └── my_executor.py       ← BaseServicePlugin (execution)
    ├── log/
    │   └── my_logger.py         ← BaseServicePlugin (log)
    └── backtest/
        └── my_backtest.py       ← standalone script, dùng backtesting.py
```

---

## Data Flow: DataFrame Schema

```
DataPlugin.run()
└── DataFrame: [Date(index), Open, High, Low, Close, Volume, ...]
        │
        ▼ (merged)
SignalPlugin.run(df)
└── DataFrame: [+ ema_fast, ema_low, ema_signal, ...]
        │
        ▼
ExecutionPlugin.run(signals_df)
└── đọc signals_df.iloc[-1]["ema_signal"]  ← bar cuối cùng
```

---

## Performance Notes

| Vấn đề | Nguyên nhân | Giải pháp |
|---|---|---|
| Dev/replay chậm | `time.sleep(interval)` mỗi tick | `mode='dev'` bỏ sleep hoàn toàn |
| Backtest chậm | `mp.Pool` spawn mỗi tick | Pool persistent, tạo 1 lần trong `setup()` |
| Backtest signal | replay row-by-row | Dùng `backtest/` script: tính signal vectorized 1 lần trên full dataset |

---

## Key Design Decisions

1. **Plugin qua importlib**: Không cần import tĩnh, thêm plugin chỉ cần thêm entry trong config.json.
2. **Signals chạy multiprocessing**: Mỗi signal plugin nhận `df.copy()` độc lập, kết quả được merge lại. Tốt cho nhiều strategy song song.
3. **LogQueue tách biệt**: Các plugin không ghi log trực tiếp ra file/console. Chúng đẩy event vào queue, stage LOG quyết định flush đi đâu.
4. **mode='dev' vs 'live'**: Cùng một pipeline code, chỉ khác ở Scheduler behavior. Data source quy định khi nào dừng (trả `None`/`False`).
5. **Backtest tách riêng**: Script backtest trong `modules/<name>/backtest/` chạy độc lập, không đi qua Scheduler, cho phép dùng thư viện backtesting.py với vectorized signals.
