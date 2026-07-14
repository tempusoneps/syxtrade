#!/bin/bash
#
DIR=$(cd "$(dirname "$0")"; pwd)
PARENT_DIR=$(dirname "$DIR")
__python_version="3.12"
#
rm -rf venv/lib/python"$__python_version"/site-packages/telegram_api.json
ln -s ""$PARENT_DIR/lib/telegram_api.json"" venv/lib/python"$__python_version"/site-packages/telegram_api.json
rm -rf venv/lib/python"$__python_version"/site-packages/telegram_api.py
ln -s ""$PARENT_DIR/lib/telegram_api.py"" venv/lib/python"$__python_version"/site-packages/telegram_api.py
#
rm -rf venv/lib/python"$__python_version"/site-packages/brokers
ln -s ""$PARENT_DIR/lib/brokers"" venv/lib/python"$__python_version"/site-packages/brokers
#
rm -rf venv/lib/python"$__python_version"/site-packages/stock_price_patterns
ln -s ""$PARENT_DIR/lib/stock_price_patterns"" venv/lib/python"$__python_version"/site-packages/stock_price_patterns
