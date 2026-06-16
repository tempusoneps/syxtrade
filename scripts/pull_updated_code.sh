#!/bin/bash
#
# git submodule add git@github.com:zuongthaotn/brokers.git lib/brokers
# git submodule add git@github.com:zuongthaotn/stock-price-patterns.git lib/stock_price_patterns
git pull --recurse-submodules
#
git submodule update --init --recursive
#
git submodule update --recursive --remote
