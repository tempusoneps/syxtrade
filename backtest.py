import argparse
import importlib
import sys


def main():
    parser = argparse.ArgumentParser(description="TempusOne Backtest Runner")
    parser.add_argument(
        "-s", "--strategy",
        type=str,
        required=True,
        help="Strategy name to backtest (e.g. vnps)"
    )
    parser.add_argument(
        "--stats-json",
        nargs="?",
        const="",
        default=None,
        help="Export backtest stats to a JSON file. If no path is provided, the strategy default is used."
    )
    args = parser.parse_args()

    module_path = f"strategies.{args.strategy}.backtest.{args.strategy}"
    try:
        bt_module = importlib.import_module(module_path)
    except ModuleNotFoundError as e:
        sys.exit(f"[backtest] Module not found: {module_path}\n{e}")

    if not hasattr(bt_module, "run"):
        sys.exit(f"[backtest] {module_path} does not export a run() function")

    bt_module.run(args)


if __name__ == "__main__":
    main()
