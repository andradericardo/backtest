import os
import numpy as np
import pandas as pd

from .definitions import RESULTS_DATA

# TODO: Finish implementing and testing this class
class Analytics:

    _save = ["returns", "positions", "position_value", "transactions", 
             "gross_leverage", "value", "drawdown"]

    def __init__(self, backtest=None, file=None):

        # Properties
        self.backtest = backtest
        self.zero = self.backtest.zero
        self.calendar = self.backtest.calendar
        self.start_adj = self.backtest.start_adj
        self.end_adj = self.backtest.end_adj

    @property
    def value(self):
        return self.value["eod"]

    @property
    def returns(self):
        df = self.backtest.value["eod"].pct_change(1).fillna(0)
        df.name = self.backtest.name
        return df
    
    @property
    def positions(self):
        df1 = self.backtest.position_value
        df2 = self.backtest.cash_fund_value
        df2.name = "CASH_FUND"
        df3 = pd.concat([df1, df2], axis=1)
        return df3.loc[:, (df3 != 0).any(axis=0)]

    @property
    def position_value(self):
        return self.backtest.position_value
    
    @property
    def transactions(self):
        df = self.backtest.orders
        df["amount"] = df["quantity"].apply(lambda x: abs(x))
        df = df.rename(columns={"ticker":"symbol"})
        df = df[["date", "order_type", "amount", "price", 
                 "symbol", "value", "purpose"]].set_index("date")
        return df
    
    @property
    def gross_leverage(self):
        df = self.backtest.positions.drop('CASH_FUND', axis=1).abs().sum(axis=1)
        return df / self.positions.sum(axis=1)
    
    @property
    def drawdown(self):
        value = self.backtest.value["eod"]
        max_value = value.cummax()
        drawdown = value / max_value - 1
        drawdown.name = self.backtest.name
        return drawdown

    @property
    def attribution_factor(self):
        return self.value / self.value.loc[self.start_adj]

    @property
    def attribution(self):
        orders = self.backtest.orders.groupby(["date", "ticker"])["cost"].sum().unstack()
        orders = orders.reindex(self.calendar).fillna(value=self.zero)
        df = self.positions - self.positions.shift(1) - orders
        df = df.divide(self.value.shift(1), axis=0).fillna(value=self.zero)
        df = df.multiply(self.attribution_factor.shift(1), axis=0).fillna(value=self.zero)
        return df.loc[self.start_adj:self.end_adj].iloc[1:]


def import_data(name, infos):
    path = os.path.join(RESULTS_DATA, name+".h5")
    return {info:pd.read_hdf(path, info) for info in infos}


def cumulative_return(daily_returns, first_value=1):
    """
    Calculates the cumulative return from a series of daily returns.

    Parameters
    ----------
    daily_returns : pd.Series
        Series of daily returns.
    first_value : float or int
        Value of first data point.

    Returns
    -------
    pd.Series
        Cumulative return.
    """
    
    cumulative_return = (1 + daily_returns).cumprod()
    return first_value * cumulative_return


def drawdown(series):
    """
    Calculates the drawdown of a series.

    Parameters
    ----------
    series : pd.Series
        Price series of cumulative return series.

    Returns
    -------
    pd.Series
        Drawdown series.
    """
    
    max_value = series.cummax()
    return series / max_value - 1


def pain_index(series, window):
    _drawdown = drawdown(series)
    rolling = _drawdown.rolling(window, window)
    return - rolling.sum() / rolling.count()


def modified_pain_index(series, window):
    _series = drawdown(series) + drawdown(-series)
    rolling = _series.rolling(window, window)
    return rolling.sum() / rolling.count()


def volatility(returns, window):
    """
    Calculates the volatility over a rolling window.

    Parameters
    ----------
    returns : pd.Series
        Daily returns.
    window : int
        Rolling window, in trading days.

    Returns
    -------
    pd.Series
        Annualized rolling volatility.
    
    Note
    ----
    Annualized on a 252 business days year basis.
    """
    
    return returns.rolling(window).std() * np.sqrt(252)


def sharpe(returns, risk_free_rate, window):
    """
    Calculates the Sharpe Ratio over a rolling window.

    Parameters
    ----------
    returns : pd.Series
        Daily returns.
    risk_free_rate : pd.Series
        Risk free rate overnight.
    window : int
        Rolling window, in trading days.

    Returns
    -------
    pd.Series
        Rolling Sharpe ratio.
        
    Note
    ----
    Annualized on a 252 business days year basis.
    """
    
    tmp = returns.to_frame().join(risk_free_rate).fillna(method="pad")
    tmp = tmp.iloc[:,0] - tmp.iloc[:,1]
    tmp.name = returns.name
    
    return tmp.rolling(window).mean() / tmp.rolling(window).std() * np.sqrt(252)