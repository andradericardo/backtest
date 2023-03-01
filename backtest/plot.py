import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from . import analysis as an
from .support import check_dir, check_file
from .definitions import EXPORTED_DATA

pd.set_option('display.expand_frame_repr', False)
np.random.seed(42)
sns.set_style('darkgrid')


def get_file_path(backtest_name, filename):
    path = check_dir(os.path.join(EXPORTED_DATA, backtest_name))
    return os.path.join(path, filename)


def cumulative_returns(series, figsize, name):
    start_date = max([serie.index[0] for serie in series])
    series_adj = [serie.loc[start_date:] for serie in series]
    df = pd.concat(series_adj, axis=1)
    df = df / df.iloc[0]
    ax = df.plot(title='Cumulative Returns', rot=90, figsize=figsize)
    ax.figure.show()
    ax.figure.savefig(get_file_path(name, "cumulative_returns.png"))
    df.to_excel(get_file_path(name, "cumulative_returns.xlsx"))


def allocations(transactions, figsize):
    labels = {"enter short":-10, "rebalance short":-10, "close short":-10,
              "enter long":10, "rebalance long":10, "close long":10,
              "cash movement": 0}
    df = transactions.copy()
    df["label"] = df["purpose"].apply(lambda x: labels[x])
    df.index = df.index.date
    df.index.name = "date"
    grouped = df.groupby(['date','symbol']).last()['label'].reset_index([0,1])
    piv_grouped = grouped.pivot(index='symbol', columns='date', values='label')
    fig = plt.figure(figsize=figsize)
    sns.heatmap(piv_grouped, cmap='RdYlGn', linewidths=0.5, square=False, cbar=False)
    plt.xticks(rotation=90)
    plt.show()


def price_and_recommendation(ticker, start, end, transactions, recommendations, close, figsize, name):
    transactions = transactions[transactions["symbol"]!="CASH_FUND"]
    ticks = pd.to_datetime(transactions.index.unique())
    _recommendations = recommendations[ticker]
    _recommendations.name = "recommendations"
    _close = close[ticker]
    _close.name = "close"
    df = pd.concat([_close, _recommendations], axis=1)
    df.index = pd.to_datetime(df.index)
    df = df.loc[start:end]
    ax = df.close.plot(figsize=(20, 5), xticks=ticks, rot=90)
    df.recommendations.plot(figsize=figsize, ax=ax, secondary_y=True, xticks=ticks, rot=90)
    ax.xaxis.grid(True)
    ax.figure.show()
    ax.figure.savefig(get_file_path(name, f"price_and_recommendation_{ticker}.png"))
    df.to_excel(get_file_path(name, f"price_and_recommendation_{ticker}.xlsx"))


def attributions(attribution, figsize, name, filename):
    df = attribution.sum()
    df = df.sort_values(ascending=False)*100
    ax = df.plot.bar(figsize=figsize, title="Performance Attribution")
    ax.figure.show()
    ax.figure.savefig(get_file_path(name, f"{filename}.png"))
    df.to_excel(get_file_path(name, f"{filename}.xlsx"))


def long_short_cash(value, position_value, figsize, name):
    value_cash = value.subtract(position_value.sum(axis=1))
    value_long = position_value[position_value > 0].sum(axis=1)
    value_short = position_value[position_value < 0].sum(axis=1)
    pct_cash = value_cash / value
    pct_long = value_long / value
    pct_short = value_short / value
    pct_cash.name = "cash"
    pct_long.name = "long"
    pct_short.name = "short"
    df = pd.concat([pct_cash, pct_long, pct_short], axis=1)
    title = "Long, Short, Cash (% assets)"
    ax = df.plot.area(figsize=figsize, rot=90, title=title)
    ax.figure.show()
    ax.figure.savefig(get_file_path(name, "long_short_cash.png"))
    df.to_excel(get_file_path(name, "long_short_cash.xlsx"))
    print("Average position during whole period:\n", 100*df.mean())


def pain_index(series, window, figsize, name):
    start_date = max([serie.index[0] for serie in series])
    series_adj = [serie.loc[start_date:] for serie in series]
    series_pain = [an.pain_index(serie, window) for serie in series_adj]
    df = pd.concat(series_pain, axis=1)
    title = "Pain Index ({} days)".format(window)
    ax = df.plot(figsize=figsize, rot=90, title=title)
    ax.figure.show()
    ax.figure.savefig(get_file_path(name, "pain_index.png"))
    df.to_excel(get_file_path(name, "pain_index.xlsx"))


def modified_pain_index(series, window, figsize):
    start_date = max([serie.index[0] for serie in series])
    series_adj = [serie.loc[start_date:] for serie in series]
    series_pain = [an.modified_pain_index(serie, window) for serie in series_adj]
    df = pd.concat(series_pain, axis=1)
    title = "Modified Pain Index ({} days)".format(window)
    df.plot(figsize=figsize, rot=90, title=title)


def risk_return(series, figsize, name):
    start_date = max([serie.index[0] for serie in series])
    series_adj = [serie.loc[start_date:] for serie in series]
    df = pd.concat(series_adj, axis=1)
    risk = df.pct_change(1).std()*(252**0.5)*100
    ret = 100*((df.iloc[-1]/df.iloc[0])**(252/(df.count()-1))-1)
    df = pd.DataFrame(index=["risk", "return"], data=[risk, ret]).T
    x, y = df["risk"], df["return"]
    fig, ax = plt.subplots(figsize=figsize)
    ax.scatter(x, y)
    ax.set_xlabel('Risk (% annualized)', fontsize=14)
    ax.set_ylabel('Return (% annualized)', fontsize=14)
    ax.set_title('Risk vs. Return', fontsize=14)
    plt.tick_params(axis="both", labelsize=14)
    for i, txt in enumerate(df.index):
        ax.annotate(txt, (x[i], y[i]), xytext=(10,10), textcoords='offset points', ha='right', va='bottom', size=14)
        plt.scatter(x, y, color='DarkBlue', s=100)
        plt.xlim(0, x.max()+10)
        plt.ylim(0, y.max()+10)
    ax.figure.show()
    ax.figure.savefig(get_file_path(name, "risk_return.png"))
    df.to_excel(get_file_path(name, "risk_return.xlsx"))


def return_windows(series, benchmark, name):
    series = series + [benchmark]
    start_date = max([serie.index[0] for serie in series])
    series_adj = [serie.loc[start_date:] for serie in series]
    df = pd.concat(series_adj, axis=1)
    result = pd.DataFrame(columns=list(df.columns[0:-1]) + ["n_size"], 
                        index=[10, 20, 30, 40, 50, 60, 
                                70, 80, 90, 120, 180, 360])
    result.index.name = "days"
    for day in result.index:
        tmp = df.iloc[:,0:-1].pct_change(day).subtract(df.iloc[:,-1].pct_change(day), axis=0)
        tmp = tmp.dropna().applymap(lambda x: x > 0).astype(int)
        count = tmp.count()
        tmp =  100 * tmp.sum() / count
        tmp["n_size"] = count[0]
        result.loc[day] = tmp
    print("Percentage of windows overperforming Ibovespa (window lengths in trade days)\n")
    result["n_size"] = result["n_size"].astype(int)
    print(result.T)
    result.to_excel(get_file_path(name, "return_windows.xlsx"))



def get_candidates(date, position, recommendations, score, volume, min_volume=20000000, window=63, head=20):
    tmp1 = recommendations.loc[date]
    tmp1.name = "recommendation"
    tmp2 = score.loc[date]
    tmp2.name = "score"
    tmp3 = volume.rolling(window).mean().loc[date]
    tmp3.name = "volume"
    df = pd.concat([tmp1, tmp2, tmp3], axis=1)

     # Get only the most liquid security for each company
    df["asset"] = df.index.str[0:4]
    df = df.sort_values("volume", na_position="first").reset_index()
    df = df.groupby("asset").tail(1).set_index("ticker")

    # get long
    df = df.sort_values(["recommendation", "score", "volume"], ascending=[False, False, False])
    df_filter_long = df[df.volume > min_volume]
    long = [ticker for ticker in df_filter_long.index]
    # excludes restricted sectors
    long = [ticker for ticker in long]
    
    # get short
    df = df.sort_values(["recommendation", "score", "volume"], ascending=[True, True, False])
    df_filter_short = df[df.volume > min_volume]
    short = [ticker for ticker in df_filter_short.index if ticker not in long]
    # excludes restricted sectors
    short = [ticker for ticker in short]

    if position=="long":
        print(df_filter_long.head(head))
    elif position=="short":
        print(df_filter_short.head(head))
    else:
        print("Wrong input!")