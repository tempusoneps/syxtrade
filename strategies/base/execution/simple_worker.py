from datetime import datetime
from core.service.base_service import BaseServicePlugin
from core.service.base_signal import SignalConfig

LONG_DEAL_TYPE = "NB"
SHORT_DEAL_TYPE = "NS"
TRADING_FEE = 0.7


class BrokerSimulator:
    def __init__(self):
        self.symbol = ""
        self.entry_price = 0
        self.exit_price = 0
        self.entry_time = ''
        self.exit_time = ''
        self.is_long_open = False
        self.is_short_open = False
        self.mode = 'dev'
        self.qty = 0
        self.stoploss = 0
        self.trailing_sl = 0
        self.take_profit = 0
        self.deal_id = 0

    def set_qty(self, new_qty):
        self.qty = new_qty

    def set_symbol(self, symbol):
        self.qty = symbol

    def set_stoploss(self, price):
        self.stoploss = price

    def set_trailing_sl(self, price):
        self.trailing_sl = price

    def set_take_profit(self, price):
        self.take_profit = price

    def pull_deal_data(self):
        # Call API
        pass

    def has_opened_deal(self):
        return True if (self.is_short_open or self.is_long_open) else False

    def trigger_before(self):
        pass

    def trigger_after(self):
        pass

    def open_long_deal(self, price):
        self.trigger_before()
        deal_type = LONG_DEAL_TYPE
        self.open_deal(deal_type, price)
        self.trigger_after()

    def open_short_deal(self, price):
        self.trigger_before()
        deal_type = SHORT_DEAL_TYPE
        self.open_deal(deal_type, price)
        self.trigger_after()

    def open_deal(self, deal_type, price):
        cur_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if deal_type == LONG_DEAL_TYPE:
            self.entry_time = cur_time
            self.is_long_open = True
            self.entry_price = price
        elif deal_type == SHORT_DEAL_TYPE:
            self.entry_time = cur_time
            self.is_short_open = True
            self.entry_price = price

    def close_all_open_deal(self, current_price):
        self.trigger_before()
        if self.is_long_open:
            self.close_long_deal(current_price)
        elif self.is_short_open:
            self.close_short_deal(current_price)
        self.trigger_after()

    def close_long_deal(self, price):
        cur_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.trigger_before()
        self.entry_time = ''
        self.qty = 0
        self.exit_price = price
        self.exit_time = cur_time
        self.is_long_open = False
        self.trigger_after()

    def close_short_deal(self, price):
        cur_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.trigger_before()
        self.entry_time = ''
        self.qty = 0
        self.exit_price = price
        self.exit_time = cur_time
        self.is_short_open = False
        self.trigger_after()


class SimpleWorkerExecutionService(BaseServicePlugin):
    def __init__(self, name, config=None, log_queue=None, mode='live'):
        self.broker = BrokerSimulator()
        super().__init__(name, config=config, log_queue=log_queue, mode=mode)

    def run(self, data=None):
        self.trigger_before(data, "ema_cross")
        if data is not None and len(data):
            last_data = data.iloc[-1]
            signal = last_data["ema_signal"]
            current_price = last_data["Close"]
            output = {}
            if current_price:
                if signal == SignalConfig.BUY_SIGNAL:
                    self.broker.open_long_deal(current_price)
                    output = {"price": current_price, "signal": signal, "order_side": LONG_DEAL_TYPE}
                elif signal == SignalConfig.SELL_SIGNAL:
                    self.broker.open_short_deal(current_price)
                    output = {"price": current_price, "signal": signal, "order_side": SHORT_DEAL_TYPE}
                if signal == SignalConfig.CLOSE_SIGNAL:
                    if self.broker.has_opened_deal():
                        self.broker.close_all_open_deal(current_price)
                        output = {"price": current_price, "signal": signal}
            self.trigger_after(output, "ema_cross")
