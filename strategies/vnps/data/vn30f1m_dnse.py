import time
from datetime import date
from datetime import timedelta
from datetime import datetime
from core.service.base_service import BaseServicePlugin
from lib.stockHistory import get_vn30f1m_ohcl_history_data


DATA_TIME_IS_VALID = 1
DATA_TIME_IS_INVALID = 0
DATA_TIME_IS_SAME = 2


class DataServiceDNSE(BaseServicePlugin):
    def run(self):
        df = None
        current_time = datetime.now()
        system_time = current_time.hour * 60 + current_time.minute
        # VN30F1M: 09:00–11:30, 13:00–14:45
        if (9*60 <= system_time <= 11*60+30) or (13*60 < system_time <= 14*60+30) or system_time == 14*60+45:
            data = self.get_stock_data(current_time)
            if data is not None and len(data) > 0:
                df = data
        self.trigger_after(df, "mix")
        return df

    def get_stock_data(self, current_time):
        # 1 year ago (approx 365 days)
        one_year_ago_ts = int((datetime.now() - timedelta(days=365)).timestamp())
        for i in range(0, 15):
            try:
                data = get_vn30f1m_ohcl_history_data(ticker="VN30F1M", resolution=5,
                                                     from_=one_year_ago_ts, broker="DNSE")
                last_data = data.iloc[-1]
                if self.validate_data_time(last_data, current_time) == DATA_TIME_IS_VALID:
                    return data
                elif self.validate_data_time(last_data, current_time) == DATA_TIME_IS_SAME:
                    return data[:-1]
                else:
                    if i < 7:
                        time.sleep(2)
                    else:
                        time.sleep(3)
            except Exception as e:
                time.sleep(2)
        return None

    @staticmethod
    def validate_data_time(last_data, current_time):
        cur_min = current_time.hour * 60 + current_time.minute
        data_min = last_data.name.hour * 60 + last_data.name.minute
        diff = cur_min - data_min

        # data đúng luôn chậm 5 phút
        if 5 <= diff <= 9:
            return DATA_TIME_IS_VALID

        # data chưa kịp cập nhật
        if diff < 5:
            return DATA_TIME_IS_SAME

        # data quá cũ
        return DATA_TIME_IS_INVALID

