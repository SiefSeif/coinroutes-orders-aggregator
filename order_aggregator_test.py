import unittest
import json
import asyncio
from order_aggregator_main import parse_orderbook, calculate_best_price

class TestOrderAggregator(unittest.TestCase):

    def test_order_aggregator(self):

        async def run_test(qty):
            bidsQueue = asyncio.PriorityQueue()
            asksQueue = asyncio.PriorityQueue() 

            # Read coinbase
            with open('api-files-examples/coinbase-api-example.json', 'r') as f:
                coinbase_data = json.load(f)
            await parse_orderbook('coinbase', coinbase_data, bidsQueue, asksQueue)

            # Read gemini
            with open('api-files-examples/gemini-api-example.json', 'r') as f:
                gemini_data = json.load(f)
            await parse_orderbook('gemini', gemini_data, bidsQueue, asksQueue)        
            
            return await calculate_best_price(bidsQueue, asksQueue, qty)
        
        buyPriceSum, sellPriceSum, fullfilledQty = asyncio.run(run_test(10))
        self.assertEqual(buyPriceSum, 1123037.9337469237)
        self.assertEqual(sellPriceSum, 1166268.3396848512)
        self.assertEqual(fullfilledQty, 10)
        
        buyPriceSum, sellPriceSum, fullfilledQty = asyncio.run(run_test(10.4134134))
        self.assertEqual(buyPriceSum, 1169471.146218901)
        self.assertEqual(sellPriceSum, 1214431.2322963553)
        self.assertEqual(fullfilledQty, 10.4134134)
        
        buyPriceSum, sellPriceSum, fullfilledQty = asyncio.run(run_test(0))
        self.assertEqual(buyPriceSum, 0)
        self.assertEqual(sellPriceSum, 0)
        self.assertEqual(fullfilledQty, 0)
        
        buyPriceSum, sellPriceSum, fullfilledQty = asyncio.run(run_test(1034))
        self.assertEqual(buyPriceSum, 122826653.90282701)
        self.assertEqual(sellPriceSum, 113680903.10074314)
        self.assertEqual(fullfilledQty, 1034)
        
        buyPriceSum, sellPriceSum, fullfilledQty = asyncio.run(run_test(100000000))
        self.assertEqual(buyPriceSum, 976451608.7003479)
        self.assertEqual(sellPriceSum, 241575771.51915255)
        self.assertEqual(fullfilledQty, 4696.4381711000315) # max was fullfilled
        
        buyPriceSum, sellPriceSum, fullfilledQty = asyncio.run(run_test(-1))
        self.assertEqual(buyPriceSum, 0)
        self.assertEqual(sellPriceSum, 0)
        self.assertEqual(fullfilledQty, 0)
        
        
if __name__ == "__main__":
    unittest.main()