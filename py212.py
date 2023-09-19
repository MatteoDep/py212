import json
import os
import pandas as pd
from config import config
import logging
import requests

logging.basicConfig()
logger = logging.getLogger("main")
logger.setLevel(logging.DEBUG)


def get_user_selection(items: list) -> int | None:
    if len(items) == 0:
        return None
    elif len(items) == 1:
        return 0

    print()
    for i, item in enumerate(items):
        print(f"{i}: '{item}'")
    invalid = True
    while invalid:
        try:
            index = int(input("Please enter the index to use: "))
            if index >= 0 and index < len(items):
                invalid = False
            else:
                raise ValueError
        except TypeError or ValueError:
            print(f"Please enter a valid index from 0 to {len(items) - 1}")
    return index


class Py212:
    def __init__(self) -> None:
        self.base_url = config.base_url
        self.headers = {
            "Authorization": f"{config.api_key}",
            "Content-Type": "application/json",
        }
        self.cache_dir = ".cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        path = os.path.join(self.cache_dir, "instruments.json")
        if not os.path.exists(path):
            instruments = self._get("/metadata/instruments")[0]
            with open(path, "w") as f:
                json.dump(instruments, f)
        self.instruments = pd.read_json(path, orient="records")
        self.instruments["stripped_ticker"] = (
            self.instruments["ticker"].str.split("_", expand=True)[0]
        )

    def _get(self, endpoint: str) -> tuple[dict | None, int]:
        url = self.base_url + endpoint
        response = requests.get(url, headers=self.headers)
        code = response.status_code

        if code == 200:
            return response.json(), code
        else:
            logger.error(
                f"Request {response.url=} failed with {response.status_code=}"
            )
            return None, code


    def _post(self, endpoint: str, body: dict) -> int:
        url = self.base_url + endpoint
        response = requests.post(url, json=body, headers=self.headers)
        code = response.status_code

        if code == 200:
            return response.json(), code
        else:
            logger.error(
                f"Request {response.url=} failed with {response.status_code=}"
            )
            return None, code

    def get_instrument_shares(
        self,
        df_holdings: pd.DataFrame,
        precision: int = 3,
        max_holdings_num: int = 40,
    ) -> None:
        mask = df_holdings["ticker"].isin(self.instruments["stripped_ticker"])
        holdings_perc = df_holdings.loc[mask].set_index("ticker")["perc"]
        perc_sum = holdings_perc.sum()
        logger.info(f"Found {perc_sum * 100}% of original holdings. Missing are:")
        logger.info(df_holdings.loc[~mask])
        if len(holdings_perc) > max_holdings_num:
            holdings_perc = holdings_perc[:max_holdings_num]
            perc_sum = holdings_perc.sum()
            logger.info(f"Cutting off to {max_holdings_num}.")
            logger.info(f"Now covering {perc_sum * 100}% of original holdings.")

        weights = holdings_perc / perc_sum
        holdings_perc += weights * (1 - perc_sum)
        holdings_perc = holdings_perc.round(precision)
        new_perc_sum = holdings_perc.sum()
        logger.debug(f"Intermediate renormalization to {new_perc_sum}.")
        shift = round(1 - new_perc_sum, precision)
        assert abs(shift) <= round(10**(-precision), precision)
        if shift > 0:
            idx = holdings_perc.loc[holdings_perc == holdings_perc.min()].index[0]
        else:
            idx = holdings_perc.loc[holdings_perc > holdings_perc.min()].index[-1]
        holdings_perc.loc[idx] += shift
        new_perc_sum = holdings_perc.sum()
        assert new_perc_sum == 1
        logger.info(f"Renormalized to {new_perc_sum}.")

        df_res = self.instruments.set_index("stripped_ticker")
        df_res = df_res.loc[
            holdings_perc.index,
            ["ticker"],
        ]
        df_res["perc"] = holdings_perc
        df_res = df_res.set_index("ticker")

        return df_res["perc"].to_dict()
