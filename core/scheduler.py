import time
from datetime import datetime
from croniter import croniter


class Scheduler:
    def __init__(self, interval=None, cron_expr=None, callback=None, mode='live'):
        self.interval = interval
        self.cron_expr = cron_expr
        self.callback = callback
        self.mode = mode
        self.cron_job = None

    def start(self):
        if self.cron_expr:
            base = datetime.now()
            itr = croniter(self.cron_expr, base)
            next_run = itr.get_next(datetime)
            while True:
                now = datetime.now()
                if now >= next_run:
                    self.callback()
                    next_run = itr.get_next(datetime)
                time.sleep(0.5)
        elif self.interval:
            while True:
                result = self.callback()
                # dev mode: chạy nhanh nhất có thể, dừng khi data source báo hết
                if result is False:
                    break
                if self.mode == 'live':
                    time.sleep(self.interval)

