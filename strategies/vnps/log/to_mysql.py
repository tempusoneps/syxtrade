import pymysql
import os
import json
from core.service.base_service import BaseServicePlugin
from dotenv import load_dotenv
import pandas as pd


class LogMySQLService(BaseServicePlugin):
    def __init__(self, name, config=None, log_queue=None, mode='live'):
        super().__init__(name, config=config, log_queue=log_queue, mode=mode)
        load_dotenv()
        self.connection = None
        self.db_host = os.environ.get("DB_HOST", "localhost")
        self.db_user = os.environ.get("DB_USER", "root")
        self.db_password = os.environ.get("DB_PASSWORD", "")
        self.db_name = os.environ.get("DB_NAME", "tempusone")
        self.db_port = int(os.environ.get("DB_PORT", 3306))

    def setup(self):
        try:
            self.connection = pymysql.connect(
                host=self.db_host,
                user=self.db_user,
                password=self.db_password,
                database=self.db_name,
                port=self.db_port,
                cursorclass=pymysql.cursors.DictCursor
            )
            self._create_table_syxtrade_signals_if_not_exists()
        except Exception as e:
            print(f"[ERROR] Failed to connect to MySQL: {e}")
    
    def _create_table_syxtrade_signals_if_not_exists(self):
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS syxtrade_signals (
            `id` int AUTO_INCREMENT PRIMARY KEY,
            `cs_time` timestamp,
            `cs_time_utc` timestamp,
            `open` float,
            `high` float,
            `low` float,
            `close` float,
            `volume` float,
            `ema_signal` VARCHAR(255),
            `couple_cs_signal` VARCHAR(255),
            `momentum_signal` VARCHAR(255),
            `macd_reverse_signal` VARCHAR(255),
            `daily_peak_proba` float,
            `daily_peak_proba_threshold` float,
            `daily_valley_proba` float,
            `daily_valley_proba_threshold` float
        )
        """
        with self.connection.cursor() as cursor:
            cursor.execute(create_table_sql)
        self.connection.commit()

    def run(self, data=None):
        logs = self.log_queue.get_all()
        if not logs or not self.connection:
            return

        signal_insert_sql = """
        INSERT INTO syxtrade_signals (
            cs_time, cs_time_utc,  `open`, `high`, `low`, `close`, `volume`, 
            ema_signal, couple_cs_signal, momentum_signal, macd_reverse_signal, 
            daily_peak_proba, daily_peak_proba_threshold, daily_valley_proba, daily_valley_proba_threshold
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        signal_data_to_insert = None
        try:
            for log in logs:
                log_content = log['log_data']
                if 'service_name' in log_content and 'trigger_name' in log_content:
                    if True or (log_content['service_name'] == 'vnps.live_worker' and log_content['trigger_name'] == 'vnps.live_worker.trigger_before'):
                        payload = log_content.get('payload', {})
                        if not payload:
                            continue
                        cs_time = payload.get('index')
                        if not cs_time:
                            continue
                            
                        ts = pd.to_datetime(cs_time)
                        if pd.isna(ts):
                            continue
                            
                        cs_time_utc = ts.tz_localize("Asia/Ho_Chi_Minh").tz_convert("UTC")
                        cs_time_utc_str = cs_time_utc.strftime('%Y-%m-%d %H:%M:%S')
                        row_values = payload.get('values', {})
                        momentum_signal = row_values.get('momentum_signal', '')
                        macd_reverse_signal = row_values.get('macd_signal', '')
                        
                        if cs_time is not None:
                            signal_data_to_insert = (
                                cs_time,
                                cs_time_utc_str,
                                row_values.get('Open'),
                                row_values.get('High'),
                                row_values.get('Low'),
                                row_values.get('Close'),
                                row_values.get('Volume'),
                                row_values.get('ema_signal'),
                                row_values.get('couple_cs_signal'),
                                momentum_signal,
                                macd_reverse_signal,
                                row_values.get('proba_is_max'),
                                row_values.get('threshold_is_max'),
                                row_values.get('proba_is_min'), # Assuming this maps to valley
                                row_values.get('threshold_is_min') # Assuming this maps to valley threshold
                            )
        except Exception as e:
            print(f"[ERROR] There is some issues in loop")

        try:
            with self.connection.cursor() as cursor:
                if signal_data_to_insert is not None:
                    cursor.execute(signal_insert_sql, signal_data_to_insert)
            self.connection.commit()
        except Exception as e:
            print(f"[ERROR] Failed to save data to MySQL: {e}")

    def teardown(self):
        if self.connection:
            self.connection.close()
