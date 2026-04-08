"""CrawlService crawlers package"""

from .multi_crawler import MultiCrawler
from .tiki_crawler import TikiCrawler

__all__ = ["MultiCrawler", "TikiCrawler"]
