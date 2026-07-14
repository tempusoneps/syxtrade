import time
from datetime import date
from datetime import timedelta
from datetime import datetime
from core.service.base_service import BaseServicePlugin
from lib.stockHistory import get_vn30f1m_ohcl_history_data


class DataServiceDNSE(BaseServicePlugin):
    def run(self):
        df = None
        current_time = datetime.now()        
        if (current_time.hour >= 9 and current_time.hour <= 14) \
            and (
                not (current_time.hour == 9 and current_time.minute == 0) \
                and not (current_time.hour == 11 and current_time.minute > 30) \
                and not current_time.hour == 12 \
                and not (current_time.hour == 13 and current_time.minute == 0) \
                and not (current_time.hour == 14 and current_time.minute > 30)
            ):
            data = self.get_stock_data(current_time)
            if data is not None and len(data) > 0:
                last_expire_date = date.today() - timedelta(days=180)
                last_expire_date = last_expire_date.strftime("%Y-%m-%d 00:00:00")
                df = data[data.index > last_expire_date]
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
                if self.validate_data_time(last_data, current_time) == 1:
                    return data
                elif self.validate_data_time(last_data, current_time) == 2:
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
        if current_time.minute == last_data.name.minute:
            return 2
        elif current_time.minute % 5 == 0:
            if current_time.minute - last_data.name.minute == 5:
                return 1
        else:
            if current_time.minute - last_data.name.minute < 4:
                return 2
            elif 5 < current_time.minute - last_data.name.minute < 9:
                return 1
        return 0
