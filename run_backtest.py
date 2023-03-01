import json
from backtest.backtest import Backtest
from backtest.data import CSVData, RiskFree, MarketIndex, Fund, ingest_series
from backtest.data import ingest_data, get_series, get_fund
from backtest.run import run
from backtest.analysis import Analytics
import datetime as dt

import pandas as pd
pd.options.display.float_format = '{:,.2f}'.format

from exclusion import EXCLUDED

REBALANCE_DATES = [
    dt.date(1904,3,31), 
    dt.date(1904,5,15), 
    dt.date(1904,8,14), 
    dt.date(1904,11,14)]

AVERAGE_VOLUME_ROLLING_WINDOW = 63
MINIMUM_AVERAGE_VOLUME = 10000000


class Amago(Backtest):

    def calculate_support_index(self):
        average_volume = self.volume.rolling(AVERAGE_VOLUME_ROLLING_WINDOW).mean()
        self.average_volume = average_volume

        tmp = self.mkt_portfolio.copy()
        tmp = tmp.T
        tmp.loc[:,"sector"] = self.sectors.amago_sector.reindex(tmp.index)
        tmp = tmp.groupby("sector").sum().T
        tmp.index = pd.to_datetime(tmp.index)
        tmp = tmp.reindex(self.calendar)
        self.mkt_portfolio_sectors = tmp


    def check_rebalance(self):
        current_date = dt.date(1904, self.date.month, self.date.day)
        previous_date = dt.date(1904, self.previous_date.month, self.previous_date.day)
        for rebalance_date in REBALANCE_DATES:
            if previous_date < rebalance_date and current_date >= rebalance_date:
                return True
        return False
    
    
    def open_strategy(self):
        # _open_strategy: calculates orders to be entered in opening auction
        c1 = self.day==1
        c2 = self.check_rebalance()
        c3 = self.date.week != self.previous_date.week
        if c1 or c2 or c3:
            long, short = self.strategy()
            self.allocate(long, short)
            
    def close_strategy(self):
        pass


    def strategy(self):
        # First lets allocate Financials and Real Estate
        number_financials = 4
        number_realestate = 1

        mkt_port = self.mkt_portfolio.loc[self.date]
        mkt_port = mkt_port[mkt_port>0]
        mkt_port.name = "share"
        sector = self.sectors.reindex(mkt_port.index).amago_sector
        vol = self.average_volume.loc[self.date].reindex(mkt_port.index)
        vol.name = "volume"
        df = pd.concat([mkt_port, sector, vol], axis=1).sort_values("volume", ascending=False)

        target_financials = df.groupby("amago_sector").sum().loc["Financials"].share
        pct_financials = target_financials / number_financials

        target_realestate = df.groupby("amago_sector").sum().loc["Real Estate"].share
        pct_realestate = target_realestate / number_realestate

        long_financials = list(df[df["amago_sector"]=="Financials"].index)[0:number_financials]
        long_realestate = list(df[df["amago_sector"]=="Real Estate"].index)[0:number_realestate]

        long = [(long,pct_financials) for long in long_financials]
        long += [(long,pct_realestate) for long in long_realestate]
        short = []

        number_long = self.number_long - number_financials - number_realestate
        number_short = self.number_short

        percentage_long = (self.target_long - target_financials - target_realestate) / number_long
        percentage_short = -self.target_short / number_short

        # Now lets allocate the rest of the portfolio
        recom = self.recommendations.loc[self.date]
        recom.name = "recommendation"
        score = self.score.loc[self.date]
        score.name = "score"
        vol = self.average_volume.loc[self.date]
        vol.name = "volume"
        df = pd.concat([recom, score, vol], axis=1)

        # Get only the most liquid security for each company
        df["asset"] = df.index.str[0:4]
        df = df.sort_values("volume", na_position="first").reset_index()
        df = df.groupby("asset").tail(1).set_index("ticker")

        # get long
        df = df.sort_values(["recommendation", "score", "volume"], ascending=[False, False, False])
        df_filter = df[df["volume"] > MINIMUM_AVERAGE_VOLUME]
        long_tickers = [ticker for ticker in df_filter.index]
        # excludes restricted sectors
        long_tickers = [ticker for ticker in long_tickers if ticker not in EXCLUDED]
        long_tickers = long_tickers[0:number_long]
        long += [(ticker,percentage_long) for ticker in long_tickers]

        # get short
        df = df.sort_values(["recommendation", "score", "volume"], ascending=[True, True, False])
        df_filter = df[(df["volume"] > MINIMUM_AVERAGE_VOLUME) & (df["recommendation"]==-1)]
        short_tickers = [ticker for ticker in df_filter.index if ticker not in long_tickers]
        # excludes restricted sectors
        short_tickers = [ticker for ticker in short_tickers if ticker not in EXCLUDED]
        short_tickers = short_tickers[0:number_short]
        short += [(ticker,percentage_short) for ticker in short_tickers]

        return long, short


data = ingest_data(config="config.json", data=CSVData)
series = ingest_series(config="config.json")

backtest = run(amago=Amago, data_obj=data, series=series, config="config.json", test=True)