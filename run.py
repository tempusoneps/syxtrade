import argparse
from core.utils import load_config
from core.service_loader import load_services
from core.scheduler import Scheduler
from core.log_queue import TempusOnePsLogQueue
from core.service.base_signal import TempusOnePsSignal


def main():
    parser = argparse.ArgumentParser(description="TempusOne Pipeline Runner")
    parser.add_argument(
        "-s", "--strategy",
        type=str,
        required=False,
        help="Strategy name to run",
        default=""
    )
    args = parser.parse_args()
    #
    log_queue = TempusOnePsLogQueue()
    config = load_config(args, log_queue)
    services = load_services(config, log_queue)

    # Setup phase
    for group in services.values():
        for s in group:
            s.setup()

    # Tạo pool 1 lần duy nhất cho toàn bộ session
    signal_services = services.get("signals", [])
    tops = TempusOnePsSignal(signal_services, log_queue)
    tops.setup()

    # Pipeline flow
    def run_pipeline():
        # 1. DATA
        df = None
        for se in services.get("data", []):
            df = se.run()

        if df is None:
            return False  # báo scheduler dừng loop (data exhausted)

        # 2. SIGNALS — dùng pool đã có sẵn
        signals_output = tops.run(df)

        # 3. EXECUTION
        for se in services.get("execution", []):
            se.run(signals_output)

        # 4. LOG
        for se in services.get("log", []):
            se.run()

        # 5. clear log queue
        log_queue.clear_all()

    cron_expr = config.get("cron")
    interval = config.get("interval", None)
    scheduler = Scheduler(interval=interval, cron_expr=cron_expr, callback=run_pipeline)
    scheduler.start()

    # Finish phase
    tops.teardown()
    for group in services.values():
        for s in group:
            s.teardown()


if __name__ == "__main__":
    main()
