from datetime import date, datetime
import time

import numpy as np
import pandas as pd
import requests


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 "
        "Safari/537.36"
    ),
    "Origin": "https://iboard.ssi.com.vn",
}
VNDIRECT_DATA_HISTORY_URL = "https://dchart-api.vndirect.com.vn/dchart/history"

SSI_HEADERS = {
    "Connection": "keep-alive",
    "sec-ch-ua": '"Not A;Brand";v="99", "Chromium";v="98", "Google Chrome";v="98"',
    "DNT": "1",
    "sec-ch-ua-mobile": "?0",
    "X-Fiin-Key": "KEY",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "X-Fiin-User-ID": "ID",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 "
        "Safari/537.36"
    ),
    "X-Fiin-Seed": "SEED",
    "sec-ch-ua-platform": "Windows",
    "Origin": "https://iboard.ssi.com.vn",
    "Sec-Fetch-Site": "same-site",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Referer": "https://iboard.ssi.com.vn/",
    "Accept-Language": "en-US,en;q=0.9,vi-VN;q=0.8,vi;q=0.7",
}
SSI_DATA_HISTORY_URL = "https://iboard-api.ssi.com.vn/statistics/charts/history"

DNSE_DATA_HISTORY_URL_V2 = "https://api.dnse.com.vn/chart-api/v2/ohlcs/derivative"

VPS_DATA_HISTORY_URL = "https://histdatafeed.vps.com.vn/tradingview/history"
VPS_HEADERS = {
    "host": "histdatafeed.vps.com.vn",
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "dnt": "1",
    "origin": "https://chart.vps.com.vn",
    "referer": "https://chart.vps.com.vn/",
    "sec-ch-ua": '"Edge";v="114", "Chromium";v="114", "Not=A?Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    ),
}

YEAR_CODE_MAP = "0123456789ABCDEFGHJKLMNPQRSTVWXYZ"
MONTH_CODE_MAP = {
    1: "1",
    2: "2",
    3: "3",
    4: "4",
    5: "5",
    6: "6",
    7: "7",
    8: "8",
    9: "9",
    10: "A",
    11: "B",
    12: "C",
}


def get_data_from_ssi(params):
    return requests.get(SSI_DATA_HISTORY_URL, params=params, headers=SSI_HEADERS, timeout=7)


def get_data_from_vndrirect(params):
    return requests.get(VNDIRECT_DATA_HISTORY_URL, params=params, headers=HEADERS, timeout=7)


def get_data_from_dnse(params):
    params.update({"symbol": "VN30F1M"})
    return requests.get(DNSE_DATA_HISTORY_URL_V2, params=params, headers=HEADERS, timeout=7)


def get_data_from_vps(params):
    params.update({"symbol": "VN30F1M"})
    return requests.get(VPS_DATA_HISTORY_URL, params=params, headers=VPS_HEADERS, timeout=7)


def get_vn30f1m_ohcl_history_data(
    ticker="VN30F1M",
    resolution=1,
    from_=1,
    broker="DNSE",
    keep_time=False,
):
    params = {
        "resolution": resolution,
        "symbol": ticker,
        "from": from_,
        "to": int(time.time()),
    }

    try:
        if broker == "DNSE":
            response = get_data_from_dnse(params)
        elif broker == "SSI":
            response = get_data_from_ssi(params)
        elif broker == "VPS":
            response = get_data_from_vps(params)
        else:
            response = get_data_from_vndrirect(params)
    except requests.exceptions.Timeout:
        print("Time out.")
        return []

    if response.status_code != 200:
        return []

    payload = response.json()
    if broker == "SSI":
        payload = payload["data"]

    dataset = pd.DataFrame(
        {
            "Time": np.array(payload["t"]).astype(int),
            "Open": np.array(payload["o"]).astype(float),
            "High": np.array(payload["h"]).astype(float),
            "Low": np.array(payload["l"]).astype(float),
            "Close": np.array(payload["c"]).astype(float),
            "Volume": np.array(payload["v"]).astype(int),
        },
        columns=["Time", "Open", "High", "Low", "Close", "Volume"],
    )
    dataset["DateStr"] = dataset.apply(
        lambda row: datetime.fromtimestamp(row["Time"]).strftime("%Y-%m-%d, %H:%M:%S"),
        axis=1,
    )
    dataset["Date"] = pd.to_datetime(dataset["DateStr"])

    ticker_data = dataset.set_index("Date")
    if not keep_time:
        ticker_data.drop(["Time"], axis=1, inplace=True)
    ticker_data.drop(["DateStr"], axis=1, inplace=True)
    return ticker_data


def get_this_month_ticker():
    if datetime.now().day < 14:
        return "VN30F" + datetime.now().strftime("%y%m")

    cross_thursday_time = 0
    today = datetime.now().day
    month = datetime.now().month
    year = datetime.now().year

    for day in range(1, today):
        if date(day=day, month=month, year=year).weekday() == 3:
            cross_thursday_time += 1

    if cross_thursday_time < 3:
        return "VN30F" + datetime.now().strftime("%y%m")

    next_month = datetime.now().month + 1
    year_code = datetime.now().strftime("%y")
    if next_month < 10:
        next_month = "0" + str(next_month)
    elif next_month > 12:
        next_month = "01"
        year_code = int(year_code) + 1

    return "VN30F" + str(year_code) + str(next_month)


def get_new_vn30f1m_ticker():
    current_year = datetime.now().strftime("%Y")
    current_month = datetime.now().strftime("%m")

    if datetime.now().day >= 14:
        cross_thursday_time = 0
        today = datetime.now().day
        month = datetime.now().month
        year = datetime.now().year
        for day in range(1, today):
            if date(day=day, month=month, year=year).weekday() == 3:
                cross_thursday_time += 1

        if cross_thursday_time >= 3:
            next_month = datetime.now().month + 1
            year_code = datetime.now().strftime("%Y")
            if next_month > 12:
                next_month = "1"
                current_year = int(year_code) + 1
            current_month = next_month

    year_diff = int(current_year) - 2010
    year_code = YEAR_CODE_MAP[year_diff]
    month_code = MONTH_CODE_MAP[int(current_month)]
    return "41I1" + str(year_code) + str(month_code) + "000"
