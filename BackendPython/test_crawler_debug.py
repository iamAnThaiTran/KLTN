import asyncio
import logging
import traceback
import sys
from app.crawler.crawler import TikiCrawler

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s: %(message)s')

async def test():
    crawler = TikiCrawler()
    try:
        products = await crawler.crawl(
            category='giày thể thao nam',
            attributes={'size': ['36', '37']},
            get_details=True
        )
        print('Done')
        print(f'Products: {len(products)}')
    except Exception as e:
        print(f'\nERROR: {e}')
        print(f'ERROR Type: {type(e)}')
        traceback.print_exc(file=sys.stdout)

asyncio.run(test())
