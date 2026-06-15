import os
import pandas as pd
from core.service.base_service import BaseServicePlugin


class DataServiceExampleCsv(BaseServicePlugin):
    def __init__(self, name, config=None, log_queue=None, mode='live'):
        self.start_from = 0
        self.csv_file = "VN30F1M_5m.csv"
        self.df = None
        super().__init__(name, config=config, log_queue=log_queue, mode=mode)

    def setup(self):
        current_folder = os.path.dirname(os.path.abspath(__file__))
        csv_file = current_folder + "/" + self.csv_file
        is_file = os.path.isfile(csv_file)
        if is_file:
            self.df = pd.read_csv(csv_file, index_col='Date', parse_dates=True)
        else:
            self.df = pd.read_csv(
                "https://raw.githubusercontent.com/zuongthaotn/vn-stock-data/main/VN30ps/VN30F1M_5minutes.csv",
                index_col='Date', parse_dates=True)

    def run(self):
        start_row = self.start_from
        to_row = start_row + 350
        if to_row < len(self.df):
            self.start_from = self.start_from + 1
            # return self.df.iloc[start_row: to_row]
            return self.df.iloc[: to_row]
            
