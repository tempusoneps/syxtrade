from core.service.base_service import BaseServicePlugin
from core.service.base_signal import SignalConfig
import pandas_ta as ta
import pandas as pd


def cal_signal(r):
    signal = ''
    if r['can_long'] is True and r['MACDh'] < 0 and r['after_min_MACDh'] is True and \
            r['after_negative_MACDh_series'] is True and r["Close"] > r["prev_Open"] and r["Close"] - r["prev_Low"] < 5:
        signal = SignalConfig.BUY_SIGNAL
    elif r['can_short'] is True and r['MACDh'] > 0 and r['after_max_MACDh'] is True \
            and r['after_positive_MACDh_series'] is True \
            and r["Close"] < r["prev_Open"] and r["prev_High"] - r["Close"] < 5:
        signal = SignalConfig.SELL_SIGNAL
    return signal


class OnlyMACDSignalPlugin(BaseServicePlugin):
    def run(self, data=None):
        if data is not None:
            macd = ta.macd(data["Close"], fast=12, slow=26, signal=9)
            data = pd.concat([data, macd], axis=1)
            data.rename(columns={'MACD_12_26_9': 'MACD', 'MACDh_12_26_9': 'MACDh', 'MACDs_12_26_9': 'MACDs'},
                        inplace=True)
            data['ibs'] = data.apply(lambda r: 0 if r["High"] == r["Low"] else (r["Close"] - r["Low"]) / (r["High"] - r["Low"]), axis=1)
            data['is_max_MACDh'] = data['MACDh'] == data['MACDh'].rolling(10).max()
            data['after_max_MACDh'] = data['is_max_MACDh'].shift(1)
            data['after_positive_MACDh_series'] = data['MACDh'].rolling(5).sum() > 0
            data['is_min_MACDh'] = data['MACDh'] == data['MACDh'].rolling(10).min()
            data['after_negative_MACDh_series'] = data['MACDh'].rolling(5).sum() < 0
            data['after_min_MACDh'] = data['is_min_MACDh'].shift(1)
            data['prev_Open'] = data['Open'].shift(1)
            data['prev_Close'] = data['Close'].shift(1)
            data['prev_High'] = data['High'].shift(1)
            data['prev_Low'] = data['Low'].shift(1)
            data['max_5'] = data['High'].rolling(5).max()
            data['min_5'] = data['Low'].rolling(5).min()
            data['can_short'] = data['Open'].shift(1) <= data['Close'].shift(1)
            data['can_long'] = data['Open'].shift(1) >= data['Close'].shift(1)
            data['macd_signal'] = data.apply(lambda r: cal_signal(r), axis=1)
            return {
                "data": data[["prev_Open", "prev_Close", "prev_High", "prev_Low", "macd_signal"]],
                "meta_data": {
                    "service_name": self.name
                }
            }
