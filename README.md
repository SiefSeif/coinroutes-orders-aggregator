# :books: Cryptocurrency Order Book Aggregator
Order Book Aggregator for BTC-USD, supporting 36+ exchanges

## :gear: Setup and Run
- Prerequisites: `python`, `aiothttp` and an internat connection
- Download and unzip repo
- Run `/order_agreggator_main.py`
- Specify BTC amount pass `--qty` or `-q`, default to 10
- Specify calculation precision pass `--pr` or `-p`, default to 2
- logging can be found in order_aggregator.YYYYMMDD.log

## :scroll: Assumptions 
- calculated prices are rounded to the default or given precision, not truncated.
- If order books have insufficient liquidity to fullfill quantity required, aggregator will return max quantity can be fullfilled from Order Books, with warning in logs.
- All Order Books prices combined wouldn't overflow the summation stack. otherwise we need to put some quantity limitation to avoid wrong calculations.
- If API call failed, retry assuming prices will be retrieved in the retrial are not expired.
- Precision of price result is defaulted to 2 decimal points.
- If an exchange failed to be retrieved, continue with other available exchanges.
- Machine have enough memory to support loading all order books in memory.
- Partial trading is allowed, i.e. aggregator can use $1 from order with amount $5 to fullfil $4 order, Brokers normally match orders partially.

## :arrows_clockwise: Workflow
1. Creates coroutine task for each API in `config.ini`
2. Run tasks concurrently.
3. Each task calls API and retrives JSON data, adds to priority queues.
3. Calculate best bid/ask using queue

## :heavy_plus_sign: Add more APIs
- Add exchange to `config.ini` file with the proper settings format

## :hourglass_flowing_sand: Future Work
- Support more currencies
- Support streaming trading



