#! /usr/bin/env python3.13

import argparse
import datetime
import logging 
import aiohttp
import asyncio
from queue import PriorityQueue
from configparser import ConfigParser

# Constants
_MICRO_TO_SECONDS = 1000000
_RATE_MIN_SECOND_WAIT = 2

# setup logs
logging.basicConfig(
            level=logging.INFO, 
            format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s',
            filename='order_aggregator.'+ str(datetime.datetime.now().strftime('%Y%m%d') + '.log'))
logFile = logging.getLogger(__name__)
logFile.setLevel(logging.INFO)


"""
Calculates the best price from the bids and asks queues
"""
def calculate_best_price(bidsQueue, asksQueue, qty):

    logging.info('Calculating best price to sell ' + str(qty) + ' BTC')

    sellPriceSum: float = 0.0
    buyPriceSum: float = 0.0

    # calculate best sell price
    if bidsQueue.empty():
        logging.error('No bids to calculate best sell price')
    else:
        qtySum: float = 0.0

        while (qtySum < qty and not bidsQueue.empty()):
            bid = bidsQueue.get_nowait()
            bidQty = bid[1]
            if (qtySum + bidQty) > qty: # take only part of the bid to fulfill qty
                bidQty = qty - qtySum
            qtySum += bidQty
            sellPriceSum += (-bid[0]) * bidQty  # Negate back to positive

    # calculate beset buy price
    if asksQueue.empty():
        logging.error('No asks to calculate best buy price')
    else:
        qtySum: float = 0.0

        while (qtySum < qty and not asksQueue.empty()):
            ask = asksQueue.get_nowait()
            askQty = ask[1]
            if (qtySum + askQty) > qty: # take only part of the ask to fulfill qty
                askQty = qty - qtySum
            qtySum += askQty
            buyPriceSum += ask[0] * askQty

    return [buyPriceSum, sellPriceSum]

######################################################################

async def parse_orderbook(exchange_name, data, bidsQueue, asksQueue):

    if exchange_name == 'coinbase':
        bids = data['bids']
        asks = data['asks']
        logging.info(f'{exchange_name} exchange has {len(bids)} bids and {len(asks)} asks')
        
        # Negate price to acheive descending queue for bids
        for bid in bids:
            bidsQueue.put((-float(bid[0]), float(bid[1])))
        for ask in asks:
            asksQueue.put((float(ask[0]), float(ask[1])))
            
    elif exchange_name == 'gemini':
        
        bids = data['bids']
        asks = data['asks']
        logging.info(f'{exchange_name} exchange has {len(bids)} bids and {len(asks)} asks')

        # Negate price to acheive descending queue for bids
        for bid in bids:
            bidsQueue.put((-float(bid['price']), float(bid['amount'])))
        for ask in asks:
            asksQueue.put((float(ask['price']), float(ask['amount'])))
            
    else: 
        logging.error(f'Exchange {exchange_name} not supported')
        
    
######################################################################

async def extract_orderbook(exchange_name, exchange_url, max_retries,\
                            session, bidsQueue, asksQueue):
    
    logging.info(f'Extracting order book for {exchange_name} exchange')

    for i in range(max_retries): 
        
        last_call_datetime = datetime.datetime.now()
        
        try: 
            response = await session.get(exchange_url)
            response.raise_for_status()
            logging.info(f'Order book for {exchange_name} exchange succefully '\
                          'extracted on the ' + str(i+1) + 'th attempt')
            data = await response.json()
            await parse_orderbook(exchange_name, data, bidsQueue, asksQueue)
            return
        
        except:
            logging.error(f'Extracting order book for {exchange_name} exchange failed, status code {response.status}')
            # limit rate to 2 seconds before reattempt, without blocking
            last_call_seconds = last_call_datetime.second + (last_call_datetime.microsecond / _MICRO_TO_SECONDS)
            datetime_now = datetime.datetime.now()
            current_seconds = datetime_now.second + (datetime_now.microsecond / _MICRO_TO_SECONDS)
            await asyncio.sleep(float(_RATE_MIN_SECOND_WAIT - (current_seconds - last_call_seconds)))  
    # end of for loop
    
    logging.warning(f'Failed to extract order book for {exchange_name}\
                     after {max_retries} attempts')

######################################################################

async def start_aggregator(exchanges, qty, precision):

    logging.info('Starting order book aggregator for ' + \
                 str(qty) + ' BTC, and precision: ' + str(precision))

    bidsQueue = PriorityQueue()  # O(logN), For bids, highest price first
    asksQueue = PriorityQueue()  # O(logN), For asks, lowest price first

    aggregatorTasks = []  

    async with aiohttp.ClientSession() as session:

        for exchange_name, exchange_url, max_retries in exchanges:
            logging.info('Creating task for ' + exchange_name + ' exchange')
            aggregatorTasks.append(extract_orderbook(exchange_name, exchange_url, max_retries,\
                                                     session, bidsQueue, asksQueue))

        await asyncio.gather(*aggregatorTasks)
        
        [buyPriceSum, sellPriceSum] = calculate_best_price(bidsQueue, asksQueue, qty)
        
        print(f'${buyPriceSum:,.{precision}f}')
        print(f'${sellPriceSum:,.{precision}f}')


############################# main ##################################

def main():

    # Parse command line args
    parser = argparse.ArgumentParser(description='A cryptocurrency order book aggregator')
    parser.add_argument('--qty', '-q', type=float, default=10, help='Currency Amount (quantity), default is 10.000')
    parser.add_argument('--pr', '-p', type=int, default=2, help='Precision of calculation, default is 2')
    # future work --> parser.add_argument('--ccy', '-c', type=str, default='BTC', help='Currency, default is ''BTC''') 
    args = parser.parse_args()

    # Read exchanges from configurations 
    config = ConfigParser()
    config.read('config.ini')
    exchanges = []
    for section in config.sections():
        exchange_name = config.items(section)[0][1]
        exchange_url = config.items(section)[1][1]
        max_retries = int(config.items(section)[2][1])
        exchanges.append([exchange_name, exchange_url, max_retries])

    # run aggregator
    asyncio.run(start_aggregator(exchanges, args.qty, args.pr))


if __name__ == "__main__":
    main()

