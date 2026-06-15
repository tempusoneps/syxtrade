from core.service.base_service import BaseServicePlugin
from core.service.base_signal import SignalConfig
import pandas_ta as ta


def get_signal(r):
    signal = ''
    if r['ema_fast_s1'] < r['ema_low_s1'] and r['ema_fast'] > r['ema_low']:
        signal = SignalConfig.BUY_SIGNAL
    elif r['ema_fast_s1'] > r['ema_low_s1'] and r['ema_fast'] < r['ema_low']:
        signal = SignalConfig.SELL_SIGNAL
    return signal


class EMACrossSignalPlugin(BaseServicePlugin):
    def run(self, data=None):
        data["ema_fast"] = ta.ema(data["Close"], length=20)
        data["ema_low"] = ta.ema(data["Close"], length=250)
        data['ema_fast_s1'] = data['ema_fast'].shift(1)
        data['ema_low_s1'] = data['ema_low'].shift(1)
        data['ema_signal'] = data.apply(lambda r: get_signal(r), axis=1)
        return {
            "data": data[["ema_fast", "ema_low", "ema_signal"]],
            "meta_data": {
                "service_name": self.name
            }
        }
