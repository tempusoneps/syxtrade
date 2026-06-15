from lib.telegram_api import send_telegram_message
from core.service.base_service import BaseServicePlugin
import time


class SendTelegrameService(BaseServicePlugin):
    def run(self, data=None):
        logs = self.log_queue.get_all()
        if not logs:
            return
        messages = []
        try:
            for log in logs:
                log_content = log['log_data']
                trigger_name = log_content['trigger_name']
                if 'around' in trigger_name or 'error' in trigger_name:
                    messages.append(str(log_content['payload']))

            if len(messages) > 0:
                if len(messages) == 1:
                    send_telegram_message(messages[0])
                else:
                    for message in messages:
                        send_telegram_message(message)
                        time.sleep(1)
        except Exception as e:
            print(f"[ERROR] There is some issues in loop. {e}")