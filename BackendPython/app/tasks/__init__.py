# app/tasks/__init__.py
"""
Tasks module - Background job processing
Handles async task execution via RabbitMQ
"""

from .crawl_worker import CrawlWorker

__all__ = ["CrawlWorker"]
