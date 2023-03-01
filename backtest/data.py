import os
import re
import json
import pandas as pd
from importlib import import_module

import progressbar as pb

from .support import get_calendar
from .definitions import SERIES_DATA, AMAGO_MASTER_CNPJ


AMAGO_MASTER_CNPJ = re.sub("\D", "", AMAGO_MASTER_CNPJ)


def get_series(first_date, last_date, code, name, calendar=None, replace=False):
    """Gets series historical values from Amago

    If there is information saved, loads from disk, unless **replace=True**

    Parameters
    ----------
    first_date : str
        First date to retrieve **YYYY-MM-DD**
    last_date : str
        Last date to retrieve **YYYY-MM-DD**
    code : str
        Series code
    replace : boolean, default : False
        Force download new data

    Returns
    -------
    pandas.Series
        Series with "date" as index
    """
    _url = "https://data.amago.capital/data/api/json/hist/{}/{}/{}/"
    path = os.path.join(SERIES_DATA, name+".csv")
    if calendar is not None:
        calendar_adj = get_calendar(calendar, first_date, last_date)

    if not os.path.isfile(path) or replace:
        print("Series: downloading:", name)
        url = _url.format(code, first_date, last_date)
        df = pd.read_json(url).set_index("date")
        df.index = pd.to_datetime(df.index)
        df = df.sort_index(ascending=True)
        df = df["value"]
        df.name = name
        if calendar is not None:
            df = df.reindex(calendar_adj).fillna(method="ffill")
        df.to_csv(path)
    else:
        print("Series: loading from file:", name)
        df = pd.read_csv(path).set_index("date")
        df.index = pd.to_datetime(df.index)
        df = df[df.columns[0]]
        if calendar is not None:
            df = df.reindex(calendar_adj).fillna(method="ffill")
    return df.fillna(method="ffill")


def get_fund(first_date, last_date, cnpj, name, calendar=None, replace=False):
    """
    """
    _url = "https://data.amago.capital/funds/api/funds/v3/{}/{}/{}/nav/"
    cnpj_clean = re.sub("\D", "", cnpj)
    path = os.path.join(SERIES_DATA, name+".csv")
    if calendar is not None:
        calendar_adj = get_calendar(calendar, first_date, last_date)
    
    if not os.path.isfile(path) or replace:
        print("Fund: downloading:", name)
        url = _url.format(cnpj_clean, first_date, last_date)
        df = pd.read_json(url).set_index("date")
        df.index = pd.to_datetime(df.index)
        df = df.sort_index(ascending=True)
        df = df["nav"]
        df.name = name
        if calendar is not None:
            df = df.reindex(calendar_adj).fillna(method="ffill")
        df.to_csv(path)
    else:
        print("Fund: loading from file:", name)
        df = pd.read_csv(path).set_index("date")
        df.index = pd.to_datetime(df.index)
        df = df[df.columns[0]]
        if calendar is not None:
            df = df.reindex(calendar_adj).fillna(method="ffill")
    return df


def cash_fund_from_risk_free_rate(risk_free_rate, calendar):
    cash_fund = (1 + risk_free_rate).cumprod()
    cash_fund = cash_fund.reindex(self.calendar)
    cash_fund = cash_fund.fillna(method="ffill").fillna(method="bfill")
    cash_fund.name = "cash_fund"


class CSVData:

    widgets_load = ['Loading securities info: ', pb.Percentage(), ' ', pb.Bar(marker=pb.RotatingMarker()), ' ', pb.ETA()]
    
    def __init__(self, path, first_date, last_date, lines=None):
        self.__lines = dict()

        self.path = path
        self.lines = lines
        self.first_date = first_date
        self.last_date = last_date

        self.tickers = list()
    

    def __getattr__(self, name):
        try:
            return self.__lines[name]
        except KeyError:
            msg = "'{0}' object has no attribute '{1}'"
            raise AttributeError(msg.format(type(self).__name__, name))


    def load(self):

        self.files = [file for file in os.listdir(self.path) \
                        if file.split(".")[1]=="csv"]
        
        #temporary list to hold data frame for each ticker which will then be concatenated in single dataframe
        df_list = list() 
        
        timer_load = pb.ProgressBar(widgets=self.widgets_load, 
                                    maxval=len(self.files)).start()
        
        for i, file in enumerate(self.files):
            path = os.path.join(self.path, file)
            df = pd.read_csv(path)
            ticker = file.split(".")[0]
            df["ticker"] = ticker
            df_list.append(df)
            self.tickers.append(ticker)

            timer_load.update(i)
            
        timer_load.finish()
            
        dfs = pd.concat(df_list).set_index(["date", "ticker"]) # concatenate list of dfs and set index
        
        lines = self.lines or dfs.columns
        for line in lines:
            tmp = dfs[line].unstack("ticker")
            tmp.index = pd.to_datetime(tmp.index)
            tmp = tmp.loc[self.first_date:self.last_date]
            self.__lines[line] = tmp

    def get_lines(self):
        return self.__lines


    
class Series:

    def __init__(self, code, 
                 first_date, last_date, calendar, 
                 series_type, name,
                 replace=False):

        self.name = name
        self.series_type = series_type
        self.code = code
        self.first_date = first_date
        self.last_date = last_date
        self.calendar = calendar
        self.replace = replace
        
        self.series = None
    
    def load(self):
        if self.series_type=="series":
            self.series = self._load_series()
        elif self.series_type=="fund":
            self.series = self._load_fund()
        else:
            self.series = None

    def _load_series(self):
        return get_series(first_date=self.first_date, 
                          last_date=self.last_date, 
                          calendar=self.calendar, 
                          code=self.code, 
                          name=self.name, 
                          replace=self.replace)

    def _load_fund(self):
        return get_fund(first_date=self.first_date, 
                        last_date=self.last_date, 
                        calendar=self.calendar, 
                        cnpj=self.code, 
                        name=self.name, 
                        replace=self.replace)


class RiskFree(Series):
    def __init__(self, first_date, last_date, calendar, replace=False):
        series_type = "series"
        name = "risk_free_rate"
        code = "sgs.12"
        super().__init__(code=code,
                         first_date=first_date, 
                         last_date=last_date, 
                         calendar=calendar, 
                         series_type=series_type,
                         name=name,
                         replace=replace)
    
    def load(self):
        self.series = super()._load_series()
        self.series = 0.01 * self.series


class MarketIndex(Series):
    def __init__(self, first_date, last_date, calendar, name, replace=False):
        series_type = "series"
        code = "IBOV.IndxVal"
        super().__init__(code=code,
                         first_date=first_date, 
                         last_date=last_date, 
                         calendar=calendar, 
                         series_type=series_type,
                         name=name,
                         replace=replace)
    
    def load(self):
        self.series = super()._load_series()


class Fund(Series):
    def __init__(self, first_date, last_date, calendar, cnpj, name, replace=False):
        series_type = "fund"
        super().__init__(code=cnpj,
                         first_date=first_date, 
                         last_date=last_date, 
                         calendar=calendar, 
                         series_type=series_type,
                         name=name,
                         replace=replace)
    
    def load(self):
        self.series = super()._load_fund()







def ingest_data(config="config.json", data=CSVData):
    with open(config, "r") as file:
        config_data = json.load(file)
    data_obj = data(**config_data["data"])
    data_obj.load()
    return data_obj


def ingest_series(config="config.json"):
    with open(config, "r") as file:
        args = json.load(file)
    
    series = dict()
    if "risk_free_rate" in args:
        tmp = args["risk_free_rate"]
        tmp["calendar"] = getattr(import_module("backtest.calendars"), tmp["calendar"])
        obj = RiskFree(**tmp)
        obj.load()
        series["risk_free_rate"] = obj
    
    if "benchmark" in args:
        tmp = args["benchmark"]
        tmp["calendar"] = getattr(import_module("backtest.calendars"), tmp["calendar"])
        obj = MarketIndex(**tmp)
        obj.load()
        series["benchmark"] = obj
    
    if "fund" in args:
        tmp = args["fund"]
        tmp["calendar"] = getattr(import_module("backtest.calendars"), tmp["calendar"])
        obj = Fund(**tmp)
        obj.load()
        series["fund"] = obj

    return series