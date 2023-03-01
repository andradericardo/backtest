import os
import datetime as dt
import numpy as np
import pandas as pd

from itertools import cycle
import progressbar as pb

from .definitions import (INSTANTS, RESULTS_DATA, SECTORS, MKT_PORTFOLIO)

# Loading bar widget
widgets_run =  ['Running backtest       : ', pb.Percentage(), ' ', pb.Bar(marker=pb.RotatingMarker()), ' ', pb.ETA()]


class Backtest():
    """
    A class to represent a backtest.


    Attributes
    ----------
    start : str
        start day of the backtest in YYYY-MM-DD format
    end : str
        start day of the backtest in YYYY-MM-DD format
    number_long : int
        number of long positions to allocate
    number_short : int
        number of short positions to allocate

    Methods
    -------
    run():
        Runs the simulation
    """
    
    def __init__(self, start, end, 
                 number_long, number_short,
                 target_long, target_short,
                 volume_floor,
                 pct_cdi, commission, fund_fees=0,
                 name="backtest", initial_date="2010-06-30",
                 start_cash=10000000.0):
        
        self.__lines = dict()
        self.start = dt.date.fromisoformat(start)
        self.end = dt.date.fromisoformat(end)
        self.initial_date = initial_date
        
        self.start_cash = np.float64(start_cash)
        
        self.number_long = number_long
        self.number_short = number_short
        
        self.target_long = target_long
        self.target_short = target_short
        self.target_cash = 1 - (self.target_long - self.target_short)
        if self.target_cash < 0:
            print("Target cash less than zero!!")
        
        self.volume_floor = volume_floor
        
        self.pct_cdi = pct_cdi
        self.commission = commission
        self.fund_fees = fund_fees
        self.fund_fees_daily = (1 + self.fund_fees)**(1/252) - 1
        self.name = name
        
        self.percentage_long = self.target_long / self.number_long
        self.percentage_short = -self.target_short / self.number_short
        
        self.day = None
        self.date = None
        self.previous_date = None
        
        self.instants = cycle(INSTANTS)
        self.instant = None
        
        self.last_calendar_date = None
                
        self.zero = np.float64(0.0)
 

    def add_data(self, data):
        self.tickers = data.tickers
        lines = data.get_lines()
        self.__lines.update(lines)

    def add_series(self, series):
        for key, value in series.items():
            self.__lines.update({key:value.series})


    def load_sectors_data(self):
        df = pd.read_csv(SECTORS).set_index("ticker")
        self.sectors = df

    
    def load_mkt_portfolio(self):
        df = pd.read_csv(MKT_PORTFOLIO).set_index("date")
        df.index = pd.to_datetime(df.index)
        df = df.reindex(self.calendar).fillna(method="ffill")
        self.mkt_portfolio = df

            
    def set_calendar(self):
        cal = self.close.index
        self.calendar = cal[(cal >= self.start.isoformat()) & (cal < self.end.isoformat())]
        self.start_adj = self.calendar[0]
        self.end_adj = self.calendar[-1]
        
        self.date = self.start_adj
        self.day = 0
        
            
    def _create_support_ledgers(self):
        # TODO: Improve this check
        if self.calendar.empty or self.tickers is None:
            raise AttributeError("Need to load assets and set a simulation calendar")
        
        instants = ["bod", "bod_adjusted", "post_open", "pre_close", "eod"]
        column_index = pd.MultiIndex.from_product([instants, self.tickers], names=['intstants', 'ticker'])
        
        # Portfolio Value ledger - All day
        self.value = pd.DataFrame(index=self.calendar, columns=instants, data=self.zero)

        # Cash amount ledger - All day
        self.cash = pd.DataFrame(index=self.calendar, columns=instants, data=self.zero)

        # Cash flow support ledgers
        self.injection = pd.Series(index=self.calendar, data=self.zero)
        self.withdrawal = pd.Series(index=self.calendar, data=self.zero)
        
        # Assets & Cash Fund position ledgers - All day
        self.position = pd.DataFrame(index=self.calendar, columns=column_index, data=self.zero)
        self.cash_fund_position = pd.DataFrame(index=self.calendar, columns=instants, data=self.zero)

        # Assets & Cash Fund value ledgers - end of day
        self.position_value = pd.DataFrame(index=self.calendar, columns=self.tickers, data=self.zero)
        self.cash_fund_value = pd.Series(index=self.calendar, data=self.zero, name="CASH_FUND")
        self.value_long = pd.Series(index=self.calendar, data=self.zero, name="LONG_VALUE")
        self.value_short = pd.Series(index=self.calendar, data=self.zero, name="SHORT_VALUE")
        self.number_positions = pd.DataFrame(index=self.calendar, columns=["long", "short"], data=self.zero)

        # Fund Fees Provisions - All day
        self.fund_fees_provision = pd.DataFrame(index=self.calendar, columns=instants, data=self.zero)
        
        # Corporate action ledgers
        self.dividends = pd.DataFrame(index=self.calendar, columns=column_index, data=self.zero)
        # TODO: Implement adjustments
        #self.stock_dividend = pd.DataFrame(index=self.calendar, columns=column_index, data=0)
        #self.m_and_a_payments = pd.DataFrame(index=self.calendar, columns=column_index, data=0)

        # Metrics - end of day
        self.net_exposure = pd.Series(index=self.calendar, data=self.zero)
        self.gross_exposure = pd.Series(index=self.calendar, data=self.zero)
        self.net_exposure_pct = pd.Series(index=self.calendar, data=self.zero)
        self.gross_exposure_pct = pd.Series(index=self.calendar, data=self.zero)
        
        # Order Book ledger
        order_columns = ["day", "date", "order_type", "ticker", "quantity", 
                         "price", "value", "commission", "cost", "status", "purpose", "message"]
        self.orders = pd.DataFrame(columns=order_columns)

        # Fund Expenses ledger
        expenses_columns = ["day", "date", "expense_type", "ticker", "value", "purpose"]
        self.expenses = pd.DataFrame(columns=expenses_columns)
    
    
    def _next_instant(self):
        self.instant = next(self.instants)


    def get_cash_fund(self):
        if self.risk_free_rate is None:
            print("Sem risk free rate")
            self.risk_free_rate = pd.Series(index=self.calendar, data=self.zero)

        nav = (1 + self.risk_free_rate).cumprod()
        nav = nav.reindex(self.calendar)
        nav.name = "cash_fund_nav"
        nav = nav.shift(1).fillna(method="ffill").fillna(method="bfill")
        self.cash_fund_nav = nav


    def _loop_calendar(self):
        timer_run = pb.ProgressBar(widgets=widgets_run, maxval=self.calendar.size).start()
            
        for day, date in enumerate(self.calendar):
            self.day = day
            self.date = date
            
            ### Instants to loop ###
            self._next_instant()
            self._bod_routine()
            
            self._next_instant()
            self._bod_adjustments_routine() 
            if self.day > 0: self.open_strategy()

            self._next_instant()
            self._post_open_routine()

            self._next_instant()
            self._pre_close_routine()
            if self.day > 0 and self.date < self.end_adj: self.close_strategy()

            self._next_instant()
            self._eod_routine()
            ### END OF INSTANTS ###
            
            self.previous_date = self.date

            timer_run.update(day)

        timer_run.finish()
    
        
    def run(self):
        #self.set_calendar()
        self.get_cash_fund()
        self.calculate_support_index()
        
        self._create_support_ledgers()
        self._loop_calendar()


    def _bod_routine(self):
        # _bod_routine : equals previous day / zeroes open on first day
        if self.day == 0:
            self.position.iloc[self.day].loc["bod", :] = self.zero
            self.cash_fund_position.iloc[self.day].loc["bod"] = self.zero
            self.cash.iloc[self.day].loc["bod"] = self.zero
            self.fund_fees_provision.iloc[self.day].loc["bod"] = self.zero
            self.value.iloc[self.day].loc["bod"] = self.zero
            self.injection.iloc[self.day] = self.start_cash
        else:
            self.position.iloc[self.day].loc["bod"] = self.position.iloc[self.day - 1].loc["eod"].values
            self.cash_fund_position.iloc[self.day].loc["bod"] = self.cash_fund_position.iloc[self.day - 1].loc["eod"]
            self.cash.iloc[self.day].loc["bod"] = self.cash.iloc[self.day - 1].loc["eod"]
            self.fund_fees_provision.iloc[self.day].loc["bod"] = self.fund_fees_provision.iloc[self.day - 1].loc["eod"]
            self.value.iloc[self.day].loc["bod"] = self.value.iloc[self.day - 1].loc["eod"]
    
    
    def _bod_adjustments_routine(self):
        # _bod_adjustments_routine: bod_adjusted = bod + adjustments
        # TODO: implement adjustments for splits and others
        self.position.iloc[self.day].loc["bod_adjusted"] = self.position.iloc[self.day].loc["bod"].values
        self.cash_fund_position.iloc[self.day].loc["bod_adjusted"] = self.cash_fund_position.iloc[self.day].loc["bod"]
        self.cash.iloc[self.day].loc["bod_adjusted"] = self.cash.iloc[self.day].loc["bod"]
        self.fund_fees_provision.iloc[self.day].loc["bod_adjusted"] = self.fund_fees_provision.iloc[self.day].loc["bod"]
        # The value should not change due to adjustments, but may lack appropriate information for the calculation 
        # (e.g. M&A, when the holder receives shares of other companies the lack pricing information)
        self.value.iloc[self.day].loc["bod_adjusted"] = self.value.iloc[self.day].loc["bod"]
        
        
    def _post_open_routine(self):
        # _post_open_routine: bod_adjusted + orders executed
        self.position.iloc[self.day].loc["post_open"] = self.position.iloc[self.day].loc["bod_adjusted"].values
        self.cash_fund_position.iloc[self.day].loc["post_open"] = self.cash_fund_position.iloc[self.day].loc["bod_adjusted"]
        self.cash.iloc[self.day].loc["post_open"] = self.cash.iloc[self.day].loc["bod_adjusted"]
        self.fund_fees_provision.iloc[self.day].loc["post_open"] = self.fund_fees_provision.iloc[self.day].loc["bod_adjusted"]
        
        # Execute orders and update positions and cash
        self._execute_orders(auction="open")
        
        # Check if first day of month to pay fund fees and write down fund fee provision
        if self.day > 0:
            if self.date.month != self.previous_date.month:
                fund_fees_provision = self.fund_fees_provision.iloc[self.day].loc["post_open"]
                self.fund_fees_provision.iloc[self.day].loc["post_open"] = 0

                cash, cash_fund_movement = self.calculate_cash_or_cash_fund_charge(fund_fees_provision)

                # Update cash
                self.cash.iloc[self.day].loc[self.instant] += cash

                # Update cash fund positions
                if cash_fund_movement != 0.0:
                    # Book order and charge cash fund
                    self.charge_cash_fund(cash_fund_movement)
        
        # Calculate the portfolio value
        self.value.loc[self.date].loc["post_open"] = self.get_value("open")


    def _pre_close_routine(self):
        # _pre_close_routine = post_open + cash/stock dividends + cash flow
        self.position.iloc[self.day].loc["pre_close"] = self.position.iloc[self.day].loc["post_open"].values
        self.cash_fund_position.iloc[self.day].loc["pre_close"] = self.cash_fund_position.iloc[self.day].loc["post_open"]
        self.cash.iloc[self.day].loc["pre_close"] = self.cash.iloc[self.day].loc["post_open"]
        self.fund_fees_provision.iloc[self.day].loc["pre_close"] = self.fund_fees_provision.iloc[self.day].loc["post_open"]
        
        injection = self.injection.iloc[self.day]
        dividends = self.dividends.iloc[self.day]
        withdrawal = self.withdrawal.iloc[self.day]
        cash_flow = + injection + dividends.sum() - withdrawal
        cash_position = self.cash.iloc[self.day].loc["pre_close"]

        # Update cash with daily cash flow
        self.cash.iloc[self.day].loc["pre_close"] = cash_position + cash_flow

        # Calculate the portfolio value
        self.value.iloc[self.day].loc["pre_close"] = self.get_value("open")
        
        # if last day, book orders to close all positions
        #if self.date==self.end_adj:
        #    self.allocate(long=[], short=[])


    def _eod_routine(self):
        # _eod_routine = pre_close + trades executed on closing auction
        self.position.iloc[self.day].loc["eod"] = self.position.iloc[self.day].loc["pre_close"].values
        self.cash_fund_position.iloc[self.day].loc["eod"] = self.cash_fund_position.iloc[self.day].loc["pre_close"]
        self.cash.iloc[self.day].loc["eod"] = self.cash.iloc[self.day].loc["pre_close"]
        self.fund_fees_provision.iloc[self.day].loc["eod"] = self.fund_fees_provision.iloc[self.day].loc["pre_close"]
        
        # Execute orders and update positions and cash
        self._execute_orders(auction="close")

        # Calculate Fund Fee provision over last value and register provision expense
        value = self.get_value("close")
        provision = value * self.fund_fees_daily
        self.fund_fees_provision.iloc[self.day].loc["eod"] += provision

        self.register_expense(self.day, self.date, "FUND_FEES", None, provision, None)

        # Update value to reflect provision
        self.value.iloc[self.day].loc["eod"] = self.get_value("close")

        # Support metrics
        prices = self.close.loc[self.date].fillna(0)
        positions = self.position.loc[self.date].loc["eod"].fillna(0)
        position_value = prices * positions
        self.position_value.loc[self.date] = position_value

        cash_fund_nav = self.cash_fund_nav.loc[self.date]
        cash_fund_position = self.cash_fund_position.loc[self.date].loc["eod"]
        cash_fund_value = cash_fund_nav * cash_fund_position
        self.cash_fund_value.iloc[self.day] = cash_fund_value

        self.value_long.iloc[self.day] = position_value[position_value > 0].sum()
        self.value_short.iloc[self.day] = position_value[position_value < 0].sum()
        self.number_positions.iloc[self.day].loc["long"] = positions[positions > 0].count()
        self.number_positions.iloc[self.day].loc["short"] = positions[positions < 0].count()
        self.net_exposure.iloc[self.day] = self.value_long.iloc[self.day] + self.value_short.iloc[self.day]
        self.gross_exposure.iloc[self.day] = self.value_long.iloc[self.day] - self.value_short.iloc[self.day]
        self.net_exposure_pct.iloc[self.day] = self.net_exposure.iloc[self.day] / value
        self.gross_exposure_pct.iloc[self.day] = self.gross_exposure.iloc[self.day] / value


    def get_positions(self, long=True):
        if long:
            fltr = self.position[self.instant].iloc[self.day] > 0
        else:
            fltr = self.position[self.instant].iloc[self.day] < 0
        return self.position[self.instant].iloc[self.day].loc[fltr].index

    
    def get_value(self, price_reference):
        if price_reference == "open":
            prices = self.open.loc[self.date].fillna(0)
        elif price_reference == "close":
            prices = self.close.loc[self.date].fillna(0)
        
        positions = self.position.loc[self.date].loc[self.instant]
        cash_fund_nav = self.cash_fund_nav.loc[self.date]
        cash_fund_position = self.cash_fund_position.loc[self.date].loc[self.instant]
        cash_fund_value = cash_fund_nav * cash_fund_position
        cash = self.cash.loc[self.date].loc[self.instant]
        fund_fees_provision = self.fund_fees_provision.loc[self.date].loc[self.instant]
        value = prices.dot(positions) + cash_fund_value + cash - fund_fees_provision
        return value


    def charge_cash_fund(self, quantity):
        cash_fund_nav = self.cash_fund_nav.loc[self.date]
        value = cash_fund_nav * quantity
        cash_fund_order = {
            "day": self.day, 
            "date": self.date,
            "order_type": "buy" if quantity > 0 else "sell",
            "ticker": "CASH_FUND",
            "quantity": quantity,
            "price": cash_fund_nav,
            "value": value,
            "commission": 0.0,
            "cost": value - 0.0,
            "status": "completed",
            "purpose": "cash movement",
        }
        self.orders = self.orders.append(cash_fund_order, ignore_index=True)
        # Update cash fund positions
        self.cash_fund_position.iloc[self.day].loc[self.instant] += quantity


    def calculate_cash_or_cash_fund_charge(self, amount):
        cash_fund_nav = self.cash_fund_nav.loc[self.date]
        cash_value = self.cash.iloc[self.day].loc[self.instant]
        cash_fund_position = self.cash_fund_position.iloc[self.day].loc[self.instant]
        liquidity = cash_value + cash_fund_position*cash_fund_nav
        
        if liquidity - amount >= 0:
            cash_to_charge = max([-min([cash_value, amount]), -amount]) # charge cash as much as possible
            cash_fund_to_charge = - amount - cash_to_charge # charge difference to cash fund
            cash_fund_position_to_charge = cash_fund_to_charge/cash_fund_nav
            return cash_to_charge, cash_fund_position_to_charge
        else:
            print("Not enough cash!!!")
            return False, False



    def allocate(self, long, short):
        long_positions = self.get_positions(long=True)
        short_positions = self.get_positions(long=False)

        long = dict(long)
        short = dict(short)
        
        # 1) Close long positions
        for d in (d for d in long_positions if d not in long.keys()):
            self.order_target_percent(ticker=d, 
                                      target=0.0, 
                                      price_reference="open", 
                                      price_offset=0, 
                                      purpose="close long")
        
        # 2) Enter short positions
        for d in (d for d in short.keys() if d not in short_positions):
            self.order_target_percent(ticker=d, 
                                      target=short[d], 
                                      price_reference="open", 
                                      price_offset=0, 
                                      purpose="enter short")
            
        # 3) Rebalance short positions
        for d in (d for d in short_positions if d in short.keys()):
            self.order_target_percent(ticker=d, 
                                      target=short[d],
                                      price_reference="open", 
                                      price_offset=0, 
                                      purpose="rebalance short")

        # 4) Rebalance long positions
        for d in (d for d in long_positions if d in long.keys()):
            self.order_target_percent(ticker=d, 
                                      target=long[d], 
                                      price_reference="open", 
                                      price_offset=0, 
                                      purpose="rebalance long")
            
        # 5) Close short positions   
        for d in (d for d in short_positions if d not in short.keys()):
            self.order_target_percent(ticker=d, 
                                      target=0.0, 
                                      price_reference="open", 
                                      price_offset=0, 
                                      purpose="close short")
         
        # 6) Enter long positions
        for d in (d for d in long.keys() if d not in long_positions):
            self.order_target_percent(ticker=d, 
                                      target=long[d], 
                                      price_reference="open", 
                                      price_offset=0, 
                                      purpose="enter long")
        
        
    def open_strategy(self):
        # _open_strategy: calculates orders to be entered in opening auction
        raise NotImplementedError("Must override open_strategy")
        

    def close_strategy(self):
        # _close_strategy: calculates orders to be entered in closing auction
        raise NotImplementedError("Must override close_strategy")


    def _execute_orders(self, auction):
        # checks if executing orders at opening or closing auctions
        # if opening auction, use open prices as reference;
        # or use close prices otherwise
        if auction == "open":
            prices = self.open.loc[self.date]
        elif auction == "close":
            prices = self.close.loc[self.date]

        # Cash fund nav reference is always from the previous day
        cash_fund_nav = self.cash_fund_nav.loc[self.date]

        # net number of cash fund shares to buy/sell
        cash_fund_movement = 0.0

        # filter then loop through order book for orders 
        # (i) valid on the current day and 
        # (ii) with status = registered
        order_filter = (self.orders["day"]==self.day) & (self.orders["status"]=="registered")
        orders = self.orders[order_filter].copy()
        
        for idx, order in orders.iterrows():
            ticker = order.ticker
            quantity = order.quantity
            order_price = prices[ticker]
            value = quantity * order_price
            commission = abs(value) * self.commission
            cost = value + commission
            #print("ORDER TO BE EXECUTED: ticker {}, quantity {}, price {}".format(ticker, quantity, order_price))

            # Calculates current liquidity position
            cash_value = self.cash.iloc[self.day].loc[self.instant]
            cash_fund_position = self.cash_fund_position.iloc[self.day].loc[self.instant]
            liquidity = cash_value + (cash_fund_position+cash_fund_movement)*cash_fund_nav

            # check if enough cash
            resulting_cash = liquidity - cost
            
            if resulting_cash >= 0:
                # Charge the cash and cash fund for the order...
                cash_charged = max([-min([cash_value,cost]),-cost]) # charge cash as much as possible
                cash_fund_charged = - cost - cash_charged # charge difference to cash fund

                self.cash.iloc[self.day].loc[self.instant] += cash_charged
                cash_fund_movement += cash_fund_charged/cash_fund_nav
        
                # Update positions 
                self.position.iloc[self.day].loc[self.instant, ticker] += quantity
                
                # Update orders
                self.orders.loc[idx, "status"] = "completed"
                self.orders.loc[idx, "value"] = value
                self.orders.loc[idx, "commission"] = commission
                self.orders.loc[idx, "cost"] = cost
                self.orders.loc[idx, "price"] = order_price

                # Register expenses
                self.register_expense(self.day, self.date, 
                                      "COMMISSION", ticker, 
                                      commission, order.purpose)
                
            else:
                self.orders.loc[idx, "status"] = "not completed"
                self.orders.loc[idx, "message"] = "not enough cash to complete"        
        
        # After all orders have been processed, book cash fund movement
        cash_value = self.cash.iloc[self.day].loc[self.instant]
        self.cash.iloc[self.day].loc[self.instant] = cash_value - cash_value
        cash_fund_movement += cash_value/cash_fund_nav
        cash_fund_movement_value = cash_fund_movement * cash_fund_nav

        # Update cash fund positions
        self.cash_fund_position.iloc[self.day].loc[self.instant] += cash_fund_movement

        if cash_fund_movement != 0.0:
            # Book cash fund order
            cash_fund_order = {
                "day": self.day, 
                "date": self.date,
                "order_type": "buy" if cash_fund_movement > 0 else "sell",
                "ticker": "CASH_FUND",
                "quantity": cash_fund_movement,
                "price": cash_fund_nav,
                "value": cash_fund_movement_value,
                "commission": 0.0,
                "cost": cash_fund_movement_value - 0.0,
                "status": "completed",
                "purpose": "cash movement",
            }
            self.orders = self.orders.append(cash_fund_order, ignore_index=True)
        

    
    def order_target_percent(self, ticker, target, price_reference, price_offset, purpose):
        prices = getattr(self, price_reference)
        
        price_day = prices.index.get_loc(self.date)
        reference_price = prices.iloc[price_day + price_offset].loc[ticker]
        
        current_position = self.position.iloc[self.day].loc[self.instant, ticker]
        # Need to add previously booked orders that were not yet executed
        c_date = self.orders.date==self.date
        c_ticker = self.orders.ticker==ticker
        c_status = self.orders.status=="registered"
        registered_position = self.orders[c_date & c_ticker & c_status].quantity.sum()

        adjusted_position = current_position + registered_position

        reference_value = reference_price * adjusted_position
        
        portfolio_value = self.value.iloc[self.day].loc[self.instant]
        current_pct = reference_value / portfolio_value

        if abs(target) == 0.0:
            order_quantity = -adjusted_position
            if adjusted_position > 0:
                order_type = "sell"
            elif adjusted_position < 0:
                order_type = "buy"
            else:
                order_type = None
        else:
            delta_pct = target - current_pct
            delta_position = delta_pct * portfolio_value / reference_price
            delta_position_adjusted = divmod(abs(delta_position),100)[0] * 100
            order_quantity = delta_position_adjusted if delta_position > 0 else -delta_position_adjusted
            order_type = "buy" if delta_position > 0 else "sell"

        if order_quantity == 0.0:
            return
        
        order = {"day": self.day + price_offset, 
                 "date": self.calendar[self.day + price_offset],
                 "purpose": purpose,
                 "order_type": order_type,  
                 "ticker": ticker,  
                 "quantity": order_quantity,  
                 "status": "registered"}
        
        self.orders = self.orders.append(order, ignore_index=True)


    def register_expense(self, day, date, expense_type, ticker, value, purpose):
        expense = {
            "day": day,
            "date": date,
            "expense_type": expense_type,
            "ticker": ticker,
            "value": value,
            "purpose": purpose}

        self.expenses = self.expenses.append(expense, ignore_index=True)

    
    def _generate_analytics(self):
        # returns
        tmp = self.value["eod"].pct_change(1).fillna(0)
        tmp.name = self.name
        self.returns = tmp
        
        # positions
        tmp1 = self.position_value
        tmp2 = self.cash_fund_value
        tmp2.name = "CASH_FUND"
        tmp3 = pd.concat([tmp1, tmp2], axis=1)
        self.positions = tmp3.loc[:, (tmp3 != 0).any(axis=0)]
        
        # transactions
        tmp1 = self.orders
        tmp1["amount"] = tmp1["quantity"].apply(lambda x: abs(x))
        tmp1 = tmp1.rename(columns={"ticker":"symbol"})
        tmp1 = tmp1[["date", "order_type", "amount", "price", "symbol", "value", "purpose"]].set_index("date")
        self.transactions = tmp1
        
        # gross leverage
        gross_exposure = self.positions.drop('CASH_FUND', axis=1).abs().sum(axis=1)
        self.gross_leverage =  gross_exposure / self.positions.sum(axis=1)
        
        # drawdown
        value = self.value["eod"]
        max_value = value.cummax()
        self.drawdown = value / max_value - 1
        self.drawdown.name = "backtest"

        # Performance Attribution
        factor = self.value.eod / self.value.eod.loc[self.start_adj]

        quantity = self.position.eod
        price = self.close.reindex(self.calendar).fillna(0)
        position = quantity * price
        position = position.loc[:, (position != 0).any(axis=0)]
        position = position.merge(right=self.cash_fund_value, on="date")

        orders = self.orders.groupby(["date", "ticker"])["value"].sum().unstack()
        orders = orders.reindex(self.calendar).fillna(value=self.zero)

        expenses = self.expenses.groupby(["date", "expense_type"])["value"].sum().unstack()
        expenses = -expenses.reindex(self.calendar).fillna(value=self.zero)

        attribution = position - position.shift(1) - orders
        attribution = attribution.merge(right=expenses, on="date")
        attribution = attribution.divide(value.shift(1), axis=0).fillna(value=self.zero)
        attribution = attribution.multiply(factor.shift(1), axis=0).fillna(value=self.zero)
        attribution = attribution.loc[self.start_adj:self.end_adj].iloc[1:]
        self.attribution = attribution
        self.attribution_factor = factor

        # Attribution by sector
        tmp = self.attribution.T
        sectors = self.sectors.amago_sector.reindex(tmp.index)
        sectors = sectors.where(sectors.notnull(), sectors.index.values)
        tmp["sectors"]= sectors
        tmp = tmp.groupby("sectors").sum().T
        self.attribution_sectors = tmp

        # Attribution by type of position
        tmp = self.attribution.copy()
        position = self.position.eod.copy()
        other_cols = ["CASH_FUND", "FUND_FEES", "COMMISSION"]
        attribution_position = pd.DataFrame(index=tmp.index, columns=["LONG", "SHORT"], data=0.0)
        attribution_position[other_cols] = tmp[other_cols]
        tmp = tmp.drop(columns=other_cols, axis=1)
        for date, row in tmp.iterrows():
            position_date = position.loc[date]
            long_position = position_date[position_date >= 0]
            short_position = position_date[position_date < 0]
            attribution_position.loc[date, "LONG"] = row.reindex(long_position.index).sum()
            attribution_position.loc[date, "SHORT"] = row.reindex(short_position.index).sum()
        self.attribution_position = attribution_position

    
    def save_results(self):
        self._generate_analytics() # generate analytics for the results

        path = os.path.join(RESULTS_DATA, self.name + ".h5")
        
        # save files to HD5 format
        self.returns.to_hdf(path, 'returns')
        self.positions.to_hdf(path, 'positions')
        self.position_value.to_hdf(path, 'position_value')
        self.transactions.to_hdf(path, 'transactions')
        self.gross_leverage.to_hdf(path, 'gross_leverage')
        self.value.to_hdf(path, 'value')
        self.drawdown.to_hdf(path, 'drawdown')
        
        self.benchmark.to_hdf(path, 'benchmark')
        self.risk_free_rate.to_hdf(path, 'risk_free_rate')
        self.fund.to_hdf(path, 'fund')
        self.close.to_hdf(path, 'close')
        self.volume.to_hdf(path, 'volume')
        self.recommendations.to_hdf(path, 'recommendations')
        self.attribution.to_hdf(path, 'attribution')
        self.attribution_factor.to_hdf(path, 'attribution_factor')
        self.attribution_sectors.to_hdf(path, 'attribution_sectors')
        self.attribution_position.to_hdf(path, 'attribution_position')
        self.score.to_hdf(path, 'score')

        # TODO: Update with actual NAV calculation in the future
        self.nav = self.value.eod / self.value.eod.iloc[0]
        self.nav.name = self.name
        self.nav.to_hdf(path, 'nav')


    def __getattr__(self, name):
        try:
            return self.__lines[name]
        except KeyError:
            msg = "'{0}' object has no attribute '{1}'"
            raise AttributeError(msg.format(type(self).__name__, name))
            
    def calculate_support_index(self):
        pass

