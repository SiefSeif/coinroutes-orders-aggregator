#! /usr/bin/env python

import argparse
import datetime
import logging 
import aiohttp
import asyncio
from configparser import ConfigParser

# Constants
_RATE_MIN_SECOND_WAIT: float = 2.0

# setup logs
logging.basicConfig(
            level=logging.INFO, 
            format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s',
            filename='order_aggregator.'+ str(datetime.datetime.now().strftime('%Y%m%d') + '.log'))
logFile = logging.getLogger(__name__)

"""
Calculates the best price from the bids and asks queues
"""
async def calculate_best_price(bidsQueue, asksQueue, qty: float):

    logging.info('Calculating best price to sell ' + str(qty) + ' BTC')

    sellPriceSum: float = 0.0
    buyPriceSum: float = 0.0
    qtySum: float = 0.0

    # calculate best sell price
    if bidsQueue.empty():
        logging.error('No bids to calculate best sell price')
    else:
        while (qtySum < qty and not bidsQueue.empty()):
            bid = await bidsQueue.get()
            bidQty = bid[1]
            if (qtySum + bidQty) > qty: # take only part of the bid to fulfill qty
                bidQty = qty - qtySum
            qtySum += bidQty
            sellPriceSum += (-bid[0]) * bidQty  # Negate back to positive

    fullfilledSellQty = qtySum 
    qtySum = 0.0
    # calculate best buy price
    if asksQueue.empty():
        logging.error('No asks to calculate best buy price')
    else:
        while (qtySum < qty and not asksQueue.empty()):
            ask = await asksQueue.get()
            askQty = ask[1]
            if (qtySum + askQty) > qty: # take only part of the ask to fulfill qty
                askQty = qty - qtySum
            qtySum += askQty
            buyPriceSum += ask[0] * askQty

    if qtySum < qty:
        logging.warning('Could not fulfill the full quantity of ' + str(qty) + \
                        ', only ' + str(qtySum) + ' was fulfilled')
        
    return [buyPriceSum, sellPriceSum, qtySum, fullfilledSellQty]

######################################################################

"""
For passed exchange name, parse data into bid and ask prices with their amount
and put it into bids and asks queues
"""
async def parse_orderbook(exchange_name, data, bidsQueue, asksQueue):

    if exchange_name == 'coinbase':
        try:
            bids = data['bids']
            asks = data['asks']
            logging.info(f'{exchange_name} exchange has {len(bids)} bids and {len(asks)} asks')
            
            # Negate price to acheive descending queue for bids
            for bid in bids:
                await bidsQueue.put((-float(bid[0]), float(bid[1])))
            for ask in asks:
                await asksQueue.put((float(ask[0]), float(ask[1])))
        except (ValueError, TypeError, IndexError, KeyError) as e:
                logging.warning(f'{exchange_name}: Invalid json data, error: {e}')
            
    elif exchange_name == 'gemini':
        try:
            bids = data['bids']
            asks = data['asks']
            logging.info(f'{exchange_name} exchange has {len(bids)} bids and {len(asks)} asks')

            # Negate price to acheive descending queue for bids
            for bid in bids:
                await bidsQueue.put((-float(bid['price']), float(bid['amount'])))
            for ask in asks:
                await asksQueue.put((float(ask['price']), float(ask['amount'])))
        except (ValueError, TypeError, IndexError, KeyError) as e:
            logging.warning(f'{exchange_name}: Invalid json data, error: {e}')
        
    else: 
        logging.error(f'Exchange {exchange_name} not supported')
        
######################################################################

"""
non blocking rate limiter, to limit rate of calls to 1 call per _RATE_MIN_SECOND_WAIT seconds
"""
async def nonblocking_rate_limiter(last_call_datetime):
    logging.info('Rate Limiter called')
    # limit rate to 2 seconds, without blocking
    seconds_since_last_call = (datetime.datetime.now() - last_call_datetime).total_seconds() # preserves microseconds
    await asyncio.sleep(_RATE_MIN_SECOND_WAIT - seconds_since_last_call) # waits 0 if passed negative
    
######################################################################

"""
For each exchange, extract order book and parse it into bids and asks queues
"""
async def extract_orderbook(exchange_name, exchange_url, max_retries,\
                            session, bidsQueue, asksQueue):
    
    logging.info(f'Extracting order book for {exchange_name} exchange')

    last_call_datetime = datetime.datetime.now() - datetime.timedelta(seconds=_RATE_MIN_SECOND_WAIT)

    for i in range(max_retries): 
        
        await nonblocking_rate_limiter(last_call_datetime)
        last_call_datetime = datetime.datetime.now()

        try: 
            response = await session.get(exchange_url)
            response.raise_for_status()
            logging.info(f'Order book for {exchange_name} exchange succefully '\
                          'extracted on the ' + str(i+1) + 'th attempt')
            data = await response.json()
            await parse_orderbook(exchange_name, data, bidsQueue, asksQueue)
            return

        except aiohttp.ClientError as e:
            logging.error(f'HTTP Extracting order book for {exchange_name} exchange failed, {e}')
        except Exception as e:
            logging.error(f'Unexpected error for {exchange_name}: {e}')
        
    # end of for loop
    
    logging.warning(f'Failed to extract order book for {exchange_name}\
                     after {max_retries} attempts')

######################################################################

"""
Aggregator starting point, creates tasks for each exchange and runs them concurrently
"""
async def start_aggregator(exchanges, qty: float, precision: int):

    logging.info('Starting order book aggregator for ' + \
                 str(qty) + ' BTC, and precision: ' + str(precision))

    bidsQueue = asyncio.PriorityQueue()  # O(logN), For bids, highest price first
    asksQueue = asyncio.PriorityQueue()  # O(logN), For asks, lowest price first

    aggregatorTasks = []  

    async with aiohttp.ClientSession() as session:

        # create a task per exchange
        for exchange_name, exchange_url, max_retries in exchanges:
            logging.info('Creating task for ' + exchange_name + ' exchange')
            aggregatorTasks.append(extract_orderbook(exchange_name, exchange_url, max_retries,\
                                                     session, bidsQueue, asksQueue))
        # run tasks concurrently
        await asyncio.gather(*aggregatorTasks)
    
    [buyPriceSum, sellPriceSum, fulffilledBuyQty, fullfilledSellQty] = await calculate_best_price(bidsQueue, asksQueue, qty)
    
    print('To buy', str(fulffilledBuyQty),'BTC:', f'${buyPriceSum:,.{precision}f}')
    print('To sell', str(fullfilledSellQty), 'BTC:', f'${sellPriceSum:,.{precision}f}')

############################# main ##################################

def main():

    # Parse command line args
    parser = argparse.ArgumentParser(description='A cryptocurrency order book aggregator')
    parser.add_argument('--qty', '-q', type=float, default=10, help='Currency Amount (quantity), default is 10.000')
    parser.add_argument('--pr', '-p', type=int, default=2, help='Precision of calculation, default is 2')
    # future work --> parser.add_argument('--ccy', '-c', type=str, default='BTC', help='Currency, default is ''BTC''') 
    args = parser.parse_args()

    if (args.qty < 0):
        print('Quantity cannot be negative')
        logging.error('Quantity cannot be negative')
        return
    if (args.pr < 0):
        print('Precision cannot be negative, defaulting to 2')
        logging.error('Precision cannot be negative, defaulting to 2')
        args.pr = 2

    # Read exchanges from configurations 
    config = ConfigParser()
    config.read('config.ini')
    exchanges = []
    for section in config.sections():
        exchanges.append([section,\
                          config.get(section, 'URL'),\
                          int(config.get(section, 'MAX_CALLS'))])

    # run aggregator
    asyncio.run(start_aggregator(exchanges, args.qty, args.pr))


if __name__ == "__main__":
    main()

