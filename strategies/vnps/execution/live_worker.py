import pickle
from pathlib import Path
import os
from datetime import datetime
from core.service.base_service import BaseServicePlugin
from core.service.base_signal import SignalConfig
import lib.stockHistory as stockHistory
from brokers.entrade import Broker

#
#
QTY_ORDER = 1
#
SL = 4.1
FORCE_SL = 4.1
EMA_TRAILING_SL = 5.5
EMA_TP = 30
CCS_TRAILING_SL = 7.5
CSS_TP = 30
#
WORKER_FILE = 'worker.pl'
STRATEGY_NAME = 'vnps_mix'


class DnseWorkerExecutionService(BaseServicePlugin):
    def __init__(self, name, config=None, log_queue=None, mode='live'):
        self.broker = None
        self.algo_version = ''
        self.stoploss = 0
        self.force_stoploss = 0
        self.take_profit = 0
        #
        self.changed = False
        self.worker_data = None
        super().__init__(name, config=config, log_queue=log_queue, mode=mode)

    def run(self, data=None):
        self.changed = False
        self.trigger_before(data, STRATEGY_NAME)
        if data is not None and len(data):
            last_data = data.iloc[-1]
            expected_price = expected_long_price = expected_sell_price = current_price = last_data["Close"]
            order_type = "MTL"
            try:
                current_time = datetime.now()
                ticker = stockHistory.get_new_vn30f1m_ticker()
                self.broker = Broker(ticker)
                worker_data = WorkerData(mode='live')
                self.set_worker_data(worker_data)
                self.broker.pull_deal_data()
                self.broker.do_date = current_time
                self._validate_algo_version()
                """
                    Handle trailing stoploss
                """
                if self.broker.has_opened_deal():
                    dt = "Long" if self.broker.is_long_open else "Short"
                    deal_info = {"deal_type": dt, "entry_price": self.broker.entry_price, "qty": self.broker.opened_qty,
                                "algo_version": self.algo_version, "SL": self.force_stoploss,
                                "TP": self.take_profit}
                    self.trigger_before(deal_info, STRATEGY_NAME)
                    if self.algo_version == 'ema':
                        if self.broker.is_long_open:
                            max_in_range = last_data['max_in_range']
                            if current_price < max_in_range - EMA_TRAILING_SL:
                                self.close_all_open_deal(current_price)
                                self.algo_version = ''
                                self.changed = True
                        elif self.broker.is_short_open:
                            min_in_range = last_data['min_in_range']
                            if current_price > min_in_range + EMA_TRAILING_SL:
                                self.close_all_open_deal(current_price)
                                self.algo_version = ''
                                self.changed = True
                    elif self.algo_version == 'couple_cs':
                        if self.broker.is_long_open:
                            max_5 = last_data['max_5']
                            if current_price < max_5 - CCS_TRAILING_SL:
                                self.close_all_open_deal(current_price)
                                self.algo_version = ''
                                self.changed = True
                        elif self.broker.is_short_open:
                            min_5 = last_data['min_5']
                            if current_price > min_5 + CCS_TRAILING_SL:
                                self.close_all_open_deal(current_price)
                                self.algo_version = ''
                                self.changed = True

                """
                    Reset algo version after get force SL
                """
                if not self.broker.has_opened_deal() and self.algo_version != '':
                    self.algo_version = ''
                    self.handle_worker_data('update')

                """
                    Handle deal & order at 14:30 (14:28).
                    Close all orders. Keeps deal(EMA strategy ) open overnight and close all others.
                """
                if current_time.hour == 14 and current_time.minute >= 25:
                    self.broker.close_all_orders()
                    if self.broker.has_opened_deal() and current_time.minute >= 27 and self.algo_version != 'ema':
                        self.close_all_open_deal(current_price)
                        self.algo_version = ''
                        self.changed = True
                        self.handle_worker_data('update')
                    #
                    return None

                if self.broker.has_opened_deal():
                    """
                    Convert algo_version to ema when we have ema_signal
                """
                    if self.algo_version != 'ema':
                        if self.broker.is_long_open and last_data['ema_signal'] == SignalConfig.BUY_SIGNAL:
                            # Keep deal continue OPEN if ema_signal is Long':
                            self.algo_version = 'ema'
                            self.changed = True
                        elif self.broker.is_short_open and last_data['ema_signal'] == SignalConfig.SELL_SIGNAL:
                            # Keep deal continue OPEN if ema_signal is Short':
                            self.algo_version = 'ema'
                            self.changed = True
                else:
                    """
                    Open new deal
                    """
                    self.broker.set_qty(QTY_ORDER)
                    if current_price > 1450 and self.mode == 'live':
                        order_type = "LO"
                    #
                    if "momentum_signal" not in last_data:
                        last_data["momentum_signal"] = None
                    if last_data['ema_signal'] == SignalConfig.BUY_SIGNAL:
                        self.algo_version = 'ema'
                        self.open_long_deal(expected_long_price, order_type)
                        self.changed = True
                    elif last_data['ema_signal'] == SignalConfig.SELL_SIGNAL:
                        self.algo_version = 'ema'
                        self.open_short_deal(expected_sell_price, order_type)
                        self.changed = True
                    elif last_data['momentum_signal'] == SignalConfig.BUY_SIGNAL:
                        self.algo_version = 'momentum'
                        self.open_long_deal(expected_long_price, order_type)
                        self.changed = True
                    elif last_data['momentum_signal'] == SignalConfig.SELL_SIGNAL:
                        self.algo_version = 'momentum'
                        self.open_short_deal(expected_sell_price, order_type)
                        self.changed = True
                    elif last_data['couple_cs_signal'] == SignalConfig.BUY_SIGNAL:
                        self.algo_version = 'couple_cs'
                        self.open_long_deal(expected_long_price, order_type)
                        self.changed = True
                    elif last_data['couple_cs_signal'] == SignalConfig.SELL_SIGNAL:
                        self.algo_version = 'couple_cs'
                        self.open_short_deal(expected_sell_price, order_type)
                        self.changed = True
                #
                if self.mode == 'live':
                    self.broker.pull_deal_data()
                    if self.broker.has_opened_deal():
                        if self.broker.is_long_open:
                            deal_type = 'Long'
                        else:
                            deal_type = 'Short'
                        if self.changed:
                            # Storage the algo version to use later
                            self.handle_worker_data('update')  
                        output = {"deal_type": deal_type, "symbol": self.broker.symbol, "entry_price": self.broker.entry_price,
                                "qty": self.broker.opened_qty, "algo_version": self.algo_version,
                                "SL": self.force_stoploss, "TP": self.take_profit}
                    else:
                        output = {"deal_type": 'None', "algo_version": self.algo_version}
                    self.trigger_after(output, STRATEGY_NAME)
            except Exception as e:
                self.trigger(str(e), STRATEGY_NAME, "error")
                log_error = {"error": True,"symbol": self.broker.symbol, "qty": self.broker.qty, "order_type": order_type,
                            "expect_long_price": expected_long_price, "expected_sell_price": expected_sell_price,
                            "SL": self.stoploss, "force_SL": self.force_stoploss, "TP": self.take_profit, 
                            "algo_version": self.algo_version
                                    }
                self.trigger(log_error, STRATEGY_NAME, "error")

    def open_long_deal(self, expected_price, order_type):
        try:
            if self.algo_version == 'momentum' or self.algo_version == 'couple_cs':
                self.stoploss = expected_price - SL
                self.force_stoploss = expected_price - FORCE_SL
                self.take_profit = expected_price + CSS_TP
                self.broker.set_stoploss(self.stoploss)
                self.broker.set_force_stoploss(self.force_stoploss)
                self.broker.set_take_profit(self.take_profit)
            elif self.algo_version == 'ema':
                self.stoploss = expected_price - SL
                self.force_stoploss = expected_price - FORCE_SL
                self.take_profit = expected_price + EMA_TP
                self.broker.set_stoploss(self.stoploss)
                self.broker.set_force_stoploss(self.force_stoploss)
                self.broker.set_take_profit(self.take_profit)
            self.broker.open_long_deal(expected_price, order_type=order_type)
            log_info = f'Signal: Long. Expected price: {expected_price}. Algo_version: {self.algo_version}, Stoploss: {self.force_stoploss}. TP: {self.take_profit}.'
            self.trigger({"text": log_info, "mode": self.mode}, STRATEGY_NAME, "around")
        except Exception as e:
                self.trigger(str(e), STRATEGY_NAME, "error")

    def open_short_deal(self, expected_price, order_type):
        try:
            if self.algo_version == 'momentum' or self.algo_version == 'couple_cs':
                self.stoploss = expected_price + SL
                self.force_stoploss = expected_price + FORCE_SL
                self.take_profit = expected_price - CSS_TP
                self.broker.set_stoploss(self.stoploss)
                self.broker.set_force_stoploss(self.force_stoploss)
                self.broker.set_take_profit(self.take_profit)
            elif self.algo_version == 'ema':
                self.stoploss = expected_price + SL
                self.force_stoploss = expected_price + FORCE_SL
                self.take_profit = expected_price - EMA_TP
                self.broker.set_stoploss(self.stoploss)
                self.broker.set_force_stoploss(self.force_stoploss)
                self.broker.set_take_profit(self.take_profit)
            self.broker.open_short_deal(expected_price, order_type=order_type)
            log_info = f'Signal: Short. Expected price: {expected_price}. Algo_version: {self.algo_version}, Stoploss: {self.force_stoploss}. TP: {self.take_profit}.'
            self.trigger({"text": log_info, "mode": self.mode}, STRATEGY_NAME, "around")
        except Exception as e:
                self.trigger(str(e), STRATEGY_NAME, "error")
    
    def close_all_open_deal(self, current_price):
        try:
            self.broker.close_all_open_deal(current_price)
            self.trigger({"text": "Close all open deal", "mode": self.mode}, STRATEGY_NAME, "around")
        except Exception as e:
                self.trigger(str(e), STRATEGY_NAME, "error")
    
    
    def set_worker_data(self, data_object):
        self.worker_data = data_object

    def handle_worker_data(self, action='read'):
        if action == 'read':
            data = self.worker_data.read()
            self.algo_version = data.algo_version
        elif action == 'update':
            self.worker_data.update(algo_version=self.algo_version)

    def _validate_algo_version(self):
        if self.broker.has_opened_deal() and not self.algo_version:
            self.algo_version = 'manually'
        return True


class WorkerData:
    def __init__(self, mode='dev'):
        self.mode = mode
        self.algo_version = ''
        self.make_file_if_not_exits()

    def read(self):
        if self.mode == 'live':
            current_dir = Path(__file__).parent
            file = str(current_dir / WORKER_FILE)
            with open(file, 'rb') as fp:
                return pickle.load(fp)
        return self

    def make_file_if_not_exits(self):
        if self.mode == 'live':
            current_dir = Path(__file__).parent
            file = str(current_dir / WORKER_FILE)
            is_file = os.path.isfile(file)
            if not is_file:
                with open(file, 'wb') as fp:
                    pickle.dump(self, fp)

    def update(self, **kwargs):
        if 'algo_version' not in kwargs:
            raise ValueError('Some required worker data attributes are missing.')
        self.algo_version = kwargs['algo_version']
        if self.mode == 'live':
            current_dir = Path(__file__).parent
            file = str(current_dir / WORKER_FILE)
            with open(file, 'wb') as fp:
                pickle.dump(self, fp)
