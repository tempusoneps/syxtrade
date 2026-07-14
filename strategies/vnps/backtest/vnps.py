import os
from datetime import datetime, timedelta

import numpy as np
import matplotlib.pyplot as plt
import warnings

from backtesting.backtesting import Backtest, Strategy

from core.utils import load_config
from core.service_loader import load_services
from core.log_queue import TempusOnePsLogQueue
from core.service.base_signal import TempusOnePsSignal, SignalConfig
from lib.stockHistory import get_vn30f1m_ohcl_history_data

plt.rcParams['figure.figsize'] = [12, 6]
plt.rcParams['figure.dpi'] = 120
warnings.filterwarnings('ignore')

BACKTEST_DIR = os.path.dirname(os.path.abspath(__file__))
INITIAL_CASH = 1500
COMMISSION = 0.00027
MARGIN = 0.1


class MainStrategy(Strategy):
    RR = 2
    max_sl = 0.0032

    ema_trailing_sl = 5.5
    ema_tp_step = 27

    strategy = ''

    def init(self):
        self.strategy = ''
        super().init()

    def next(self):
        super().next()
        close_price = self.data.Close[-1]

        # Trailing stoploss theo strategy
        if self.strategy == 'ema':
            if self.position.is_long:
                if close_price < self.data.max_in_range[-1] - self.ema_trailing_sl:
                    self.strategy = ''
                    self.position.close()
            elif self.position.is_short:
                if close_price > self.data.min_in_range[-1] + self.ema_trailing_sl:
                    self.strategy = ''
                    self.position.close()

        # Đóng lệnh cuối phiên 14:25
        current_time = self.data.index[-1]
        if current_time.hour == 14 and current_time.minute >= 25:
            if self.strategy != 'ema' and (self.position.is_long or self.position.is_short):
                self.strategy = ''
                self.position.close()
            return

        ema_signal = self.data.ema_signal[-1]
        predict_is_max = self.data.predict_is_max[-1]

        if self.position:
            if self.strategy != 'ema' and ema_signal != '':
                if self.position.is_long and ema_signal == SignalConfig.BUY_SIGNAL:
                    self.strategy = 'ema'
                elif self.position.is_short and ema_signal == SignalConfig.SELL_SIGNAL:
                    self.strategy = 'ema'
            if self.strategy != 'ema' and predict_is_max == 1 and self.position.is_long:
                self.strategy = ''
                self.position.close()

        if not self.position:
            if ema_signal == SignalConfig.BUY_SIGNAL:
                buy_price = close_price
                self.buy(size=1, sl=buy_price - buy_price * self.max_sl, tp=buy_price + self.ema_tp_step)
                self.strategy = 'ema'
            elif ema_signal == SignalConfig.SELL_SIGNAL:
                sell_price = close_price
                self.sell(size=1, sl=sell_price + sell_price * self.max_sl, tp=sell_price - self.ema_tp_step)
                self.strategy = 'ema'


def _load_data():
    one_year_ago = int((datetime.now() - timedelta(days=365)).timestamp())
    return get_vn30f1m_ohcl_history_data(ticker="VN30F1M", resolution=5, from_=one_year_ago, broker="DNSE")


def _print_report(stats):
    trades = stats['_trades']
    total = len(trades)
    wins = (trades['PnL'] > 0).sum()
    losses = (trades['PnL'] <= 0).sum()
    win_rate = wins / total * 100 if total > 0 else 0

    print("\n" + "=" * 50)
    print("  VNPS BACKTEST REPORT")
    print("=" * 50)
    print(stats.drop(['_trades', '_equity_curve']))
    print("-" * 50)
    print(f"  Tổng lệnh : {total}")
    print(f"  Thắng     : {wins}  ({win_rate:.1f}%)")
    print(f"  Thua      : {losses}")
    print(f"  PnL tích luỹ: {trades['PnL'].sum():.2f}")
    print("=" * 50 + "\n")


def _save_curve(stats):
    trades = stats['_trades'].copy()
    trades['cum_pnl'] = trades['PnL'].cumsum()
    x = np.arange(len(trades))
    plt.figure()
    plt.plot(x, trades['cum_pnl'])
    plt.title("VNPS – Đường cong lợi nhuận tích luỹ")
    plt.xlabel("Số lệnh")
    plt.ylabel("PnL (điểm)")
    chart_path = os.path.join(BACKTEST_DIR, "returns_curve.png")
    plt.savefig(chart_path, dpi=300)
    plt.close()
    print(f"[backtest] Đã lưu biểu đồ: {chart_path}")


def run(args):
    print("[backtest] Đang tải dữ liệu VNPS...")
    data = _load_data()

    log_queue = TempusOnePsLogQueue()
    config = load_config(args, log_queue)
    services = load_services(config, log_queue, mode='dev')

    signal_services = services.get("signals", [])
    tops = TempusOnePsSignal(signal_services, log_queue)
    tops.setup()
    print(f"[backtest] Đang chạy {len(signal_services)} signal(s) trên {len(data)} nến...")
    signals_data = tops.run(data)
    tops.teardown()

    signals_data.dropna(inplace=True)
    print(f"[backtest] Dữ liệu sau khi lọc NaN: {len(signals_data)} nến")
    for column in ("ema_signal", "macd_signal", "predict_is_max"):
        if column in signals_data:
            print(f"[backtest] {column}: {signals_data[column].value_counts(dropna=False).to_dict()}")

    bt = Backtest(
        signals_data,
        MainStrategy,
        cash=INITIAL_CASH,
        commission=COMMISSION,
        margin=MARGIN,
        exclusive_orders=True,
    )
    stats = bt.run()

    _print_report(stats)
    _save_curve(stats)
