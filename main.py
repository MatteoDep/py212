import json
import os
import re
import pandas as pd
import requests
from datetime import datetime, timedelta
from requests import Response
from urllib.parse import urlsplit

from py212 import Py212, get_user_selection


def update_holdings_data(url: str, out_path: str) -> None:
    # url = "https://www.schwabassetmanagement.com/sites/g/files/eyrktu361/files/product_files/SCHD/SCHD_FundHoldings_2023-09-15.CSV"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
        ),
    }
    response: Response = requests.get(url, headers=headers)
    html_text = response.text

    lines = [
        line.strip() for line in  html_text.splitlines()
        if line.find("product_files") >= 0 and line.lower().find("holdings") >= 0
    ]
    line = get_user_selection(lines)

    m = re.search(r'href="(.*\.csv)"', line, re.IGNORECASE)
    url = url.split(urlsplit(url).path)[0] + m.group(1)
    response: Response = requests.get(url, headers=headers)
    rows = []
    for row in response.text.splitlines():
        if len(row.strip()) == 0:
            break
        rows.append(row + "\n")

    with open(out_path, "w") as f:
        f.writelines(rows)


def create_pie(py212: Py212, df_holdings: pd.DataFrame) -> None:
    end_date = datetime.now() + timedelta(days=365)
    schd_config = dict(
        dividendCashAction="REINVEST",
        endDate=end_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        goal=0,
        icon="Bills",
        instrumentShares={},
        name="SCHD",
    )
    instrument_shares = py212.get_instrument_shares(df_holdings)
    schd_config["instrumentShares"] = instrument_shares

    print(json.dumps(schd_config, indent=4))

    data, code = py212._post("/pies", body=schd_config)
    print(data)


def main() -> int:
    py212 = Py212()
    save_dir = "data"
    os.makedirs(save_dir, exist_ok=True)

    out_path = os.path.join(save_dir, "schd_holdings.csv")
    # url = "https://www.schwabassetmanagement.com/products/schd"
    # update_holdings_data(url, out_path)

    df_holdings = pd.read_csv(out_path)
    df_holdings = df_holdings[["Symbol", "Percent of Assets"]].rename(
        columns={"Symbol": "ticker", "Percent of Assets": "perc"},
    )
    df_holdings["perc"] /= 100

    create_pie(
        py212,
        df_holdings=df_holdings,
    )

    return 0


if __name__ == "__main__":
    exit(main())
