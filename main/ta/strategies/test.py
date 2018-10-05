import backtrader as bt
import os
from datetime import datetime, date, time

class MyStrategy(bt.Strategy):
    params = dict(maperiod=5)

    def log(self, txt, dt=None):
        """ Logging function for this strategy"""
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

        # To keep track of pending orders
        self.order = None

        # Add a MovingAverageSimple indicator
        self.sma = bt.ind.SMA(period=self.params['maperiod'])

    def next(self):
        # Simply log the closing price of the series from the reference
        if len(self) > 2 and self.data0.low < self.data[-1].low and \
            self.data[-1].close < self.data[-1].open and \
            self.data[-2].close > self.data[-2].open and not self.position:
            self.sell()
            self.order = self.sell()

        if self.position and self.data[-1].close > self.data[-1].open and \
            self.data[-1].close > self.sma(5) and self.data[0].high > self.data[-1].high:
            self.buy()
            self.order = self.buy()

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price, order.executed.value, order.executed.comm))
            elif order.issell():
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price, order.executed.value, order.executed.comm))

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None




if __name__ == '__main__':
    cerebro = bt.Cerebro()

    # Add a strategy
    cerebro.addstrategy(MyStrategy)

    modpath = os.path.abspath('d:\ib\data')
    datapath = os.path.join(modpath, 'hsi_uptoday.csv')
    #datapath = os.path.join(modpath, '1.txt')
    
    # Create a Data Feed
    #data = bt.feeds.CSVData(dataname=datapath)
    
    data = bt.feeds.GenericCSVData(
        dataname=datapath,

        fromdate=datetime(2018, 7, 1),
        todate=datetime(2018, 12, 31),

        nullvalue=0.0,

        dtformat=('%Y-%m-%d'),

        datetime=0,
        time=1,
        open=2,
        high=3,
        low=4,

        close=5,
        volume=6,
        openinterest=-1
    )

    # Add the Data Feed to Cerebro
    cerebro.adddata(data)

    # Set our desired cash start
    cerebro.broker.setcash(100000.0)

    # Add a FixedSize sizer according to the stake
    cerebro.addsizer(bt.sizers.FixedSize, stake=10)

    # Set the commission - 0.1% ... divide by 100 to remove the %
    cerebro.broker.setcommission(commission=0.001)

    cerebro.run()

    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

