import os

import seaborn as sns
import matplotlib.pyplot as plt
import pandas_datareader.data as web

import pandas as pd
import pyfolio as pf

from backtest import analysis as an
from backtest import plot
from backtest.definitions import RESULTS_DATA

pd.options.display.float_format = '{:,.2f}'.format

def run(name):

    infos = ["returns", "nav", "positions", "transactions", "gross_leverage", "benchmark", "drawdown", 
            "position_value", "value", "fund", 
            "attribution", "attribution_factor", "attribution_sectors", "attribution_position",
            "close", "volume", "score", "recommendations"]
            
    data = an.import_data(name, infos)

    returns = data["returns"]
    nav = data["nav"]
    positions = data["positions"]
    transactions = data["transactions"]
    gross_leverage = data["gross_leverage"]
    benchmark = data["benchmark"]
    drawdown = data["drawdown"]
    position_value = data["position_value"]
    value = data["value"]
    fund = data["fund"]
    attribution = data["attribution"]
    attribution_sectors = data["attribution_sectors"]
    attribution_position = data["attribution_position"]
    attribution_factor = data["attribution_factor"]
    close = data["close"]
    volume = data["volume"]
    recommendations = data["recommendations"]
    score = data["score"]

    start = value.index[0]
    end = value.index[-1]

    # Plot
    plot.cumulative_returns([nav, benchmark, fund], figsize=(15, 5))
    plot.risk_return([nav, fund, benchmark], figsize=(15,5))
    plot.return_windows([nav, fund], benchmark)
    plot.pain_index([nav, benchmark, fund], window=252, figsize=(15, 5))
    plot.attributions(attribution, figsize=(20, 5))
    plot.attributions(attribution_sectors, figsize=(15, 5))
    plot.attributions(attribution_position, figsize=(15, 5))
    plot.allocations(transactions[transactions.symbol!="CASH_FUND"], figsize=(15, 20)) #larg, altura
    plot.long_short_cash(value.eod, position_value, figsize=(15,5))

    # Plots the close price vs recommendation for a certain ticker over time
    # ticker = "SMTO3"
    # plot.price_and_recommendation(ticker, start, end, transactions, recommendations, close, figsize=(20, 5))

    # Retrieves the potential long/short candidates on a certain date
    # date = "2020-08-14"
    # position = "short"
    # head = 20
    # plot.get_candidates(date, position, recommendations, score, volume, min_volume=0, window=63, head=head)




NAME = "AMAGO_backtest_85long_5short"
run(NAME)