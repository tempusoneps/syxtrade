import multiprocessing as mp
from core.service.base_service import BaseServicePlugin
from datetime import datetime
import pandas as pd


DEFAULT_SIGNAL_PAYLOAD = {
    "signal": None,
    "Close": None,
    "Open": None,
    "High": None,
    "Low": None
}


class SignalConfig:
    NO_SIGNAL = ""
    BUY_SIGNAL = "buy"
    SELL_SIGNAL = "sell"
    CLOSE_SIGNAL = "close"
    CLOSE_BUY_SIGNAL = "close.buy"
    CLOSE_SELL_SIGNAL = "close.sell"
    SWITCH_TO_BUY_SIGNAL = "switch.to.buy"
    SWITCH_TO_SELL_SIGNAL = "switch.to.sell"


class BaseSignalPlugin(BaseServicePlugin):
    def run(self, data):
        return data


class TempusOnePsSignal:
    def __init__(self, signal_classes, log_queue=None):
        self.signal_classes = signal_classes
        self.log_queue = log_queue
        self._pool = None

    def setup(self):
        cpu_num = max(1, len(self.signal_classes))
        self._pool = mp.Pool(processes=cpu_num)

    def run(self, df):
        # Lazy init: nếu chưa gọi setup() thì tự tạo pool (backward compat)
        if self._pool is None:
            self.setup()
        self.add_log_queue(df, "signal_run", "before")
        results = self._pool.map(
            self.run_single_signal_module,
            [(cfg, df) for cfg in self.signal_classes]
        )
        df_merged = df
        for r in results:
            df_merged = df_merged.merge(r["data"], left_index=True, right_index=True, how='inner')
            self.add_log_queue(r["data"], r["meta_data"]["service_name"], "result")
        return df_merged

    def teardown(self):
        if self._pool:
            self._pool.close()
            self._pool.join()
            self._pool = None

    @staticmethod
    def run_single_signal_module(args):
        signal_cfg, df = args
        return signal_cfg.run(df.copy())

    def add_log_queue(self, data=None, service_name="", step="after"):
        if not self.log_queue:
            return
        if isinstance(data, pd.DataFrame):
            last = data.iloc[-1]
            payload = {
                "index": last.name.isoformat(),
                "values": last.to_dict()
            }
        else:
            payload = data
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "service_name": service_name,
            "trigger_name": service_name + ".trigger_" + step,
            "payload": payload
        }
        self.log_queue.log(log_data)
