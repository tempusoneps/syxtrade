import os
from datetime import datetime
import pandas as pd
import pandas_ta as ta
from xgboost import XGBClassifier
from core.service.base_service import BaseServicePlugin


def labeling_data(df):
    merged_data = df.copy()
    merged_data['hour'] = merged_data.index.hour
    merged_data['minute'] = merged_data.index.minute
    merged_data['prev_High'] = merged_data['High'].shift(1)
    merged_data['prev_Low'] = merged_data['Low'].shift(1)
    merged_data['prev_Close'] = merged_data['Close'].shift(1)
    merged_data['prev_Open'] = merged_data['Open'].shift(1)
    merged_data['prev_Vol'] = merged_data['Volume'].shift(1)
    ana_data = merged_data.dropna()
    ana_data['upper_shadow'] = ana_data.apply(lambda r: r["High"] - max(r["Open"], r["Close"]), axis=1)
    ana_data['prev_upper_shadow'] = ana_data['upper_shadow'].shift(1)
    ana_data['ibs'] = ana_data.apply(
        lambda r: 0 if r["High"] == r["Low"] else (r["Close"] - r["Low"]) / (r["High"] - r["Low"]), axis=1)
    ana_data['prev_ibs'] = ana_data['ibs'].shift(1)
    ana_data['RSI20'] = ta.rsi(ana_data["Close"], length=20)
    ana_data['RSI10'] = ta.rsi(ana_data["Close"], length=10)
    ana_data['avg_Volume'] = ana_data['Volume'].rolling(20).mean()
    ana_data['prev_avg_Volume'] = ana_data['avg_Volume'].shift(1)
    ana_data["MB"] = ana_data["Close"].rolling(20).mean()
    ana_data["STD"] = ana_data["Close"].rolling(20).std()
    ana_data["UB"] = ana_data["MB"] + 1.5 * ana_data["STD"]
    #
    ana_data['upper_wick_group'] = ana_data.apply(
        lambda r: 1 if r["upper_shadow"] > r["prev_upper_shadow"] else -1, axis=1)
    ana_data["ibs_vol_group"] = ana_data.apply(lambda r: get_ibs_vol_group(r), axis=1)
    ana_data['rsi_area'] = ana_data.apply(
        lambda r: 1 if r["RSI20"] > 55 else (0.33 if r["RSI20"] < 45 else 0.66), axis=1)
    ana_data['higher_high_lower_vol'] = ana_data.apply(
        lambda r: 1 if (r["High"] > r["prev_High"] and r["Volume"] < r["prev_Vol"]) else -1, axis=1)
    ana_data['Volume_higher_avg'] = ana_data.apply(lambda r: 1 if r["Volume"] > r["avg_Volume"] else -1, axis=1)
    ana_data['Volume_vs_prev_Vol'] = ana_data.apply(lambda r: 1 if r["Volume"] > r["prev_Vol"] else -1, axis=1)
    ana_data['Volume_avg_group'] = ana_data.apply(
        lambda r: 1 if r["avg_Volume"] > r["prev_avg_Volume"] else -1, axis=1)
    ana_data['close_price_group'] = ana_data.apply(lambda r: get_close_price_position(r), axis=1)
    ana_data['open_price_group'] = ana_data.apply(lambda r: get_open_price_position(r), axis=1)
    ana_data['High_position'] = ana_data.apply(lambda r: 1 if r["High"] > r["UB"] else -1, axis=1)
    ana_data["BB_rejection"] = ana_data.apply(lambda r: 1 if r["Close"] < r["UB"] else -1, axis=1)
    ana_data['is_max_3'] = (ana_data["High"] > ana_data["High"].shift(1).rolling(3).max())
    ana_data.dropna(inplace=True)
    return ana_data


def get_open_price_position(r):
    if r["Open"] > r["prev_Close"]:
        return -0.5
    if r["Open"] == r["prev_Close"]:
        return 0
    if r["Open"] < r["prev_Close"]:
        return 0.5


def get_ibs_vol_group(r):
    if r["Volume"] > r["prev_Vol"] and r["ibs"] > r["prev_ibs"]:
        return -1
    if r["Volume"] > r["prev_Vol"] and r["ibs"] < r["prev_ibs"]:
        return -0.5
    if r["Volume"] < r["prev_Vol"] and r["ibs"] > r["prev_ibs"]:
        return 0.5
    if r["Volume"] < r["prev_Vol"] and r["ibs"] < r["prev_ibs"]:
        return 1


def get_close_price_position(r):
    if r["Close"] > r["prev_High"]:
        return -1
    if r["Close"] > max(r["prev_Close"], r["prev_Open"]):
        return -0.5
    if max(r["prev_Close"], r["prev_Open"]) > r["Close"] > min(r["prev_Close"], r["prev_Open"]):
        return 0
    if r["Close"] < min(r["prev_Close"], r["prev_Open"]):
        return 0.5
    if r["Close"] < r["prev_Low"]:
        return 1


class AIPredictSignalPlugin(BaseServicePlugin):
    def run(self, data=None):
        model_xgb = None
        current_folder = os.path.dirname(os.path.abspath(__file__))
        xgboost_model_file = current_folder + "/xgb_model.json"
        is_file = os.path.isfile(xgboost_model_file)
        if is_file:
            model_xgb = XGBClassifier()
            model_xgb.load_model(xgboost_model_file)
        if model_xgb is not None:
            labeled_data = labeling_data(data)
            threshold = 0.876
            features = [
                "upper_wick_group", "ibs_vol_group", "rsi_area", "higher_high_lower_vol",
                "Volume_higher_avg", "Volume_vs_prev_Vol", "Volume_avg_group", "is_max_3",
                "close_price_group", "open_price_group", "High_position", "BB_rejection"
            ]
            if self.mode == 'live':
                labeled_data['predict_is_max'] = ''
                labeled_data['proba_is_max'] = ''
                labeled_data['threshold_is_max'] = ''
                last5 = labeled_data[features].tail(5)
                proba = model_xgb.predict_proba(last5)[:, 1]
                predict = (proba > threshold).astype(int)
                labeled_data.loc[last5.index, 'predict_is_max'] = predict
                labeled_data.loc[last5.index, 'proba_is_max'] = proba
                labeled_data.loc[last5.index, 'threshold_is_max'] = threshold
            else:
                proba = model_xgb.predict_proba(labeled_data[features])[:, 1]
                predict = (proba > threshold).astype(int)
                labeled_data['predict_is_max'] = predict
                labeled_data['proba_is_max'] = proba
                labeled_data['threshold_is_max'] = threshold
            return {
                "data": labeled_data[["predict_is_max", "proba_is_max", "threshold_is_max"]],
                "meta_data": {
                    "service_name": self.name
                }
            }
