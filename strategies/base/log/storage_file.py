from core.service.base_service import BaseServicePlugin
from core.forfun import banner
import os
import json


class ExampleLogFileService(BaseServicePlugin):
    def __init__(self, name, config=None, log_queue=None, mode='live'):
        self.log_file = None
        super().__init__(name, config=config, log_queue=log_queue, mode=mode)

    def setup(self):
        current_folder = os.path.dirname(os.path.abspath(__file__))
        log_path = os.path.join(current_folder, "example.log")
        file_is_existed = os.path.isfile(log_path)
        if not file_is_existed:
            self.log_file = open(log_path, "w", encoding="utf-8")
            self.log_file.write(banner + "\n")
            self.log_file.write("[SYSTEM] 🚀 Starting TempusOne Engine...\n")
        else:
            self.log_file = open(log_path, "a", encoding="utf-8")

    def run(self, data=None):
        """
        Ghi toàn bộ log trong log_queue vào file.
        """
        logs = self.log_queue.get_all()

        for log in logs:
            self.log_file.write(json.dumps(log, ensure_ascii=False) + "\n")
            self.log_file.flush()

    def teardown(self):
        if self.log_file:
            self.log_file.close()
