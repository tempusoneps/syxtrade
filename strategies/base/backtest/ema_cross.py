import os
import pandas as pd
import numpy as np
from backtesting.backtesting import Backtest, Strategy
from core.utils import load_config
from core.service_loader import load_services
from core.log_queue import TempusOnePsLogQueue
from core.service.base_signal import TempusOnePsSignal, SignalConfig
import matplotlib.pyplot as plt
plt.rcParams['figure.figsize'] = [12, 6]
plt.rcParams['figure.dpi'] = 120
import warnings
warnings.filterwarnings('ignore')


current_folder = os.path.dirname(os.path.abspath(__file__))
parent_folder = os.path.dirname(current_folder)
csv_file = os.path.join(parent_folder, "data", "VN30F1M_5m.csv")
is_file = os.path.isfile(csv_file)
if is_file:
    dataset = pd.read_csv(csv_file, index_col='Date', parse_dates=True)
else:
    print("remote")
    dataset = pd.read_csv(
        "https://raw.githubusercontent.com/zuongthaotn/vn-stock-data/main/VN30ps/VN30F1M_5minutes.csv",
        index_col='Date', parse_dates=True)

data = dataset.copy()
data['max_in_range'] = data['High'].rolling(10).max()
data['min_in_range'] = data['Low'].rolling(10).min()

temop_folder = os.path.dirname(os.path.dirname(parent_folder))
config_file = os.path.join(temop_folder, "config", "config.json")
config = load_config(config_file)
log_queue = TempusOnePsLogQueue()
services = load_services(config, log_queue)

signal_services = services.get("signals", [])
tops = TempusOnePsSignal(signal_services, log_queue)
tops.setup()
signals_output = tops.run(data)
tops.teardown()
signals_output.dropna(inplace=True)


class MainStrategy(Strategy):
    max_sl = 3.1
    trailing_sl = 5.5
    tp_step = 27

    def init(self):
        self._broker._cash = 1500
        super().init()

    def next(self):
        super().next()
        close_price = self.data.Close[-1]
        if self.position.is_long:
            max_in_range = self.data.max_in_range[-1]
            if close_price < max_in_range - self.trailing_sl:
                self.position.close()
        elif self.position.is_short:
            min_in_range = self.data.min_in_range[-1]
            if close_price > min_in_range + self.trailing_sl:
                self.position.close()

        signal = self.data.signal[-1]
        if self.position:
            if signal == SignalConfig.BUY_SIGNAL and self.position.is_short:
                self.position.close()
                buy_price = close_price
                sl = buy_price - self.max_sl
                tp = buy_price + self.tp_step
                self.buy(size=1, sl=sl, tp=tp)
            elif signal == SignalConfig.SELL_SIGNAL and self.position.is_long:
                sell_price = close_price
                self.position.close()
                sl = sell_price + self.max_sl
                tp = sell_price - self.tp_step
                self.sell(size=1, sl=sl, tp=tp)
        else:
            if signal == SignalConfig.BUY_SIGNAL:
                buy_price = close_price
                sl = buy_price - self.max_sl
                tp = buy_price + self.tp_step
                self.buy(size=1, sl=sl, tp=tp)
            elif signal == SignalConfig.SELL_SIGNAL:
                sell_price = close_price
                sl = sell_price + self.max_sl
                tp = sell_price - self.tp_step
                self.sell(size=1, sl=sl, tp=tp)

bt = Backtest(signals_output, MainStrategy, commission=.0003, exclusive_orders=True)
stats = bt.run()

print(stats)

trades = stats['_trades']
copy_trades = trades.copy()
copy_trades['cum_sum'] = copy_trades['PnL'].cumsum()
X = np.array(range(0, len(copy_trades['cum_sum'])))
Y = copy_trades['cum_sum']
# Plotting the Graph
plt.plot(X, Y)
plt.title("Curve plotted for returns")
plt.xlabel("X")
plt.ylabel("Rerurns")
plt.savefig("returns_curve.png", dpi=300)  # png, 300 dpi
plt.close()
