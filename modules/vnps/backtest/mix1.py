import os
from datetime import timedelta
from datetime import datetime
import numpy as np
from backtesting.backtesting import Backtest, Strategy
from core.utils import load_config
from core.service_loader import load_services
from core.log_queue import TempusOnePsLogQueue
from core.service.base_signal import TempusOnePsSignal, SignalConfig
from lib.stockHistory import get_vn30f1m_ohcl_history_data
import matplotlib.pyplot as plt
plt.rcParams['figure.figsize'] = [12, 6]
plt.rcParams['figure.dpi'] = 120
import warnings
warnings.filterwarnings('ignore')


# dataset = pd.read_csv(
    #     "https://raw.githubusercontent.com/zuongthaotn/vn-stock-data/main/VN30ps/VN30F1M_5minutes.csv",
    #     index_col='Date', parse_dates=True)
one_year_ago_ts = int((datetime.now() - timedelta(days=365)).timestamp())
dataset = get_vn30f1m_ohcl_history_data(ticker="VN30F1M", resolution=5,
                                                     from_=one_year_ago_ts, broker="DNSE")
data = dataset.copy()
current_folder = os.path.dirname(os.path.abspath(__file__))
parent_folder = os.path.dirname(current_folder)
temop_folder = os.path.dirname(os.path.dirname(parent_folder))
config_file = os.path.join(temop_folder, "config", "config.json")
config = load_config(config_file)
log_queue = TempusOnePsLogQueue()
services = load_services(config, log_queue, 'dev')

signal_services = services.get("signals", [])
tops = TempusOnePsSignal(signal_services, data)
signals_data = tops.run()
signals_data.dropna(inplace=True)
# print(signals_data[signals_data.index > "2025-11-25 11:55:00"].columns)
# print(signals_data[signals_data.momentum_signal != ""][["momentum_signal"]])
# exit()


class MainStrategy(Strategy):
    RR = 2
    max_sl = 0.0032
    #
    ema_trailing_sl = 5.5
    ema_tp_step = 27
    #
    momentum_trailing_sl = 4.5
    momentum_tp_step = 27
    #
    cs_trailing_sl = 7.5
    cs_tp_step = 27
    strategy = ''

    #
    def init(self):
        self._broker._cash = 1500
        self.strategy = ''
        super().init()

    def next(self):
        super().next()
        close_price = self.data.Close[-1]
        # Strategy trailing stoploss
        if self.strategy == 'ema':
            if self.position.is_long:
                max_in_range = self.data.max_in_range[-1]
                if close_price < max_in_range - self.ema_trailing_sl:
                    self.strategy = ''
                    self.position.close()
            elif self.position.is_short:
                min_in_range = self.data.min_in_range[-1]
                if close_price > min_in_range + self.ema_trailing_sl:
                    self.strategy = ''
                    self.position.close()
        elif self.strategy != 'couple_cs':
            if self.position.is_long:
                max_5 = self.data.max_5[-1]
                if close_price < max_5 - self.cs_trailing_sl:
                    self.strategy = ''
                    self.position.close()
            elif self.position.is_short:
                min_5 = self.data.min_5[-1]
                if close_price > min_5 + self.cs_trailing_sl:
                    self.strategy = ''
                    self.position.close()

        # Close deal at 14:30
        _time = self.data.index
        current_time = _time[-1]
        if current_time.hour == 14 and current_time.minute >= 25:
            if self.strategy != 'ema':
                if self.position.is_long or self.position.is_short:
                    self.strategy = ''
                    self.position.close()
            # Do nothing after 14h30
            return

        # Main Strategy
        ema_signal = self.data.ema_signal[-1]
        momentum_signal = self.data.momentum_signal[-1]
        couple_cs_signal = self.data.couple_cs_signal[-1]
        macd_signal = self.data.macd_signal[-1]
        if self.position:
            # return
            if self.strategy != 'ema' and ema_signal != '':
                if self.position.is_long and ema_signal == SignalConfig.BUY_SIGNAL:
                    self.strategy = 'ema'
                elif self.position.is_short and ema_signal == SignalConfig.SELL_SIGNAL:
                    self.strategy = 'ema'
        #
        if not self.position:
            if ema_signal == SignalConfig.BUY_SIGNAL:
                buy_price = close_price
                sl = buy_price - (buy_price * self.max_sl)
                tp = buy_price + self.ema_tp_step
                self.buy(size=1, sl=sl, tp=tp)
                self.strategy = 'ema'
            elif ema_signal == SignalConfig.SELL_SIGNAL:
                sell_price = close_price
                sl = sell_price + (sell_price * self.max_sl)
                tp = sell_price - self.ema_tp_step
                self.sell(size=1, sl=sl, tp=tp)
                self.strategy = 'ema'
            elif momentum_signal == SignalConfig.BUY_SIGNAL:
                buy_price = close_price
                sl = buy_price - (buy_price * self.max_sl)
                tp = buy_price + self.momentum_tp_step
                self.buy(size=1, sl=sl, tp=tp)
                self.strategy = 'momentum'
            elif momentum_signal == SignalConfig.SELL_SIGNAL:
                sell_price = close_price
                sl = sell_price + (sell_price * self.max_sl)
                tp = sell_price - self.momentum_tp_step
                self.sell(size=1, sl=sl, tp=tp)
                self.strategy = 'momentum'
            elif couple_cs_signal == SignalConfig.BUY_SIGNAL:
                buy_price = close_price
                sl = buy_price - (buy_price * self.max_sl)
                tp = buy_price + self.cs_tp_step
                self.buy(size=1, sl=sl, tp=tp)
                self.strategy = 'couple_cs'
            elif couple_cs_signal == SignalConfig.SELL_SIGNAL:
                sell_price = close_price
                sl = sell_price + (sell_price * self.max_sl)
                tp = sell_price - self.cs_tp_step
                self.sell(size=1, sl=sl, tp=tp)
                self.strategy = 'couple_cs'


bt = Backtest(signals_data, MainStrategy, commission=0.00027, exclusive_orders=True)
stats = bt.run()

print(stats)

trades = stats['_trades']
copy_trades = trades.copy()
copy_trades['cum_sum'] = copy_trades['PnL'].cumsum()
X = np.array(range(0, len(copy_trades['cum_sum'])))
Y = copy_trades['cum_sum']
plt.plot(X, Y)
plt.title("Curve plotted for returns")
plt.xlabel("Trades")
plt.ylabel("Returns")
plt.savefig("returns_curve.png", dpi=300)
plt.close()
