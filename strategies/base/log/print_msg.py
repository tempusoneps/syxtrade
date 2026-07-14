from core.service.base_service import BaseServicePlugin
from core.forfun import banner


class ExampleLogPrintService(BaseServicePlugin):
    def setup(self):
        print(banner)
        print("[SYSTEM] 🚀 Starting TempusOne Engine..." + "\n")

    def run(self, data=None):
        log_queue = self.log_queue.get_all()
        for log in log_queue:
            print(log)
