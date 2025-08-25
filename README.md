# Coinroutes Order Book Aggregator
Order Book Aggregator for BTC-USD

## Setup & Run
- Prerequisites: `python3.X`, `aiothttp` and an internat connection
- Download and unzip repo
- Run `/order_agreggator_main.py`
- Specify BTC amount pass `--qty` or `-q`, default to 10
- Specify calculation precision pass `--pr` or `-p`, default to 2

## Workflow
1. Creates coroutine task for each API in `config.ini`
2. Each task calls API and retrives JSON data
3. 



## Add more APIs
1. Add api ***NAME***, ***URL*** and ***MAX_CALLS*** to `config.ini` file
2. Provide parser for API response into order_aggregator_main.py

## Assumptions 
- Fraction trading is allowed, i.e. aggregator can use order with price $5 to fullfil $4 order
- Precision is defaulted to 2 decimal points.
-  


## Exchanges
bids and asks are retrieved in the expected orders, bids descending, and asks are ascending
### Coinbase ([Documentation](https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-book))
A bid or ask has the following format `[price, size, num-orders]`, e.g. `[ "112285.27",  "0.0000274", 1]`, 
--> [URL](https://api.exchange.coinbase.com/products/BTC-USD/book?level=2)
- **price**: price of currency
- **size**: quantity available of currency at this price
- **num-orders**: count of orders at that price  


### Gemini ([Documentation](https://docs.gemini.com/rest/market-data#get-current-order-book))
A bid or ask has the following format 
`{
    "price": "116728.77",
    "amount": "0.00089935",
    "timestamp": "1755878881"
}` --> [URL](https://api.gemini.com/v1/book/BTCUSD)

## References
- [aiohttp](https://docs.aiohttp.org/en/stable/client_reference.html)
- [Gemini API](https://docs.gemini.com/rest/market-data#get-current-order-book)
- [Coinbase API](https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-book)

## Future Work
- Support more currencies
- Support streaming tradeing
- Support more exchanges


