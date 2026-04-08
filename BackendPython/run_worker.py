#!/usr/bin/env python3
# BackendPython/run_worker.py
"""
Crawl Worker Startup Script
Starts RabbitMQ consumer workers for async crawling

Usage:
    python run_worker.py --queue crawl_tasks
    python run_worker.py --queue crawl_tasks --workers 3
"""

import os
import sys
import logging
import argparse
import multiprocessing
from app.tasks.crawl_worker import CrawlWorker
from app.config.rabbitmq import RabbitMQConfig, get_rabbitmq_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

class WorkerPool:
    """Manage multiple crawl worker processes"""
    
    def __init__(self, queue_name: str, num_workers: int = 1):
        self.queue_name = queue_name
        self.num_workers = num_workers
        self.processes = []
    
    def start(self) -> None:
        """Start worker processes"""
        logger.info(f"🚀 Starting {self.num_workers} workers on queue: {self.queue_name}")
        
        for i in range(self.num_workers):
            try:
                p = multiprocessing.Process(
                    target=self._run_worker,
                    args=(f"Worker-{i+1}",),
                    name=f"crawl-worker-{i+1}"
                )
                p.start()
                self.processes.append(p)
                logger.info(f"✅ Started worker process: {p.name} (PID: {p.pid})")
            except Exception as e:
                logger.error(f"❌ Failed to start worker {i+1}: {e}")
        
        logger.info(f"✅ All {len(self.processes)} workers started. Waiting for messages...")
        
        # Wait for all processes
        try:
            for p in self.processes:
                p.join()
        except KeyboardInterrupt:
            logger.info("⏹️ Received interrupt signal, shutting down gracefully...")
            self.stop()
    
    def _run_worker(self, worker_name: str) -> None:
        """Run a single worker (in separate process)"""
        try:
            logger.info(f"[{worker_name}] Starting")
            worker = CrawlWorker(queue_name=self.queue_name)
            worker.start()
        except KeyboardInterrupt:
            logger.info(f"[{worker_name}] Interrupted")
        except Exception as e:
            logger.error(f"[{worker_name}] Fatal error: {e}")
            sys.exit(1)
    
    def stop(self) -> None:
        """Stop all worker processes"""
        for p in self.processes:
            if p.is_alive():
                logger.warning(f"Terminating {p.name}...")
                p.terminate()
                p.join(timeout=5)
                
                if p.is_alive():
                    logger.warning(f"Force killing {p.name}...")
                    p.kill()
                    p.join()
        
        logger.info("✅ All workers stopped")

def check_rabbitmq_connection() -> bool:
    """Check if RabbitMQ is accessible"""
    try:
        logger.info("🔍 Checking RabbitMQ connection...")
        conn = get_rabbitmq_connection()
        is_connected = conn.is_connected()
        
        if is_connected:
            logger.info(f"✅ Connected to RabbitMQ at {RabbitMQConfig.HOST}:{RabbitMQConfig.PORT}")
            return True
        else:
            logger.error("❌ RabbitMQ connection check returned False")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to connect to RabbitMQ: {e}")
        logger.error(f"   Host: {RabbitMQConfig.HOST}")
        logger.error(f"   Port: {RabbitMQConfig.PORT}")
        logger.error(f"   Vhost: {RabbitMQConfig.VHOST}")
        
        # Provide helpful suggestions
        logger.info("\n💡 Troubleshooting:")
        logger.info("   1. Make sure RabbitMQ is running:")
        logger.info("      - Docker: docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3.13-management")
        logger.info("      - Local: brew services start rabbitmq (macOS) or service rabbitmq start (Linux)")
        logger.info("      - Windows: Start RabbitMQ service from Services")
        logger.info(f"   2. Check .env file has correct RABBITMQ_* settings")
        logger.info(f"   3. Current settings: {RabbitMQConfig.HOST}:{RabbitMQConfig.PORT}/{RabbitMQConfig.VHOST}")
        
        return False

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Crawl Worker - RabbitMQ Consumer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_worker.py
  python run_worker.py --queue crawl_tasks --workers 3
  python run_worker.py --queue crawl_tasks --workers 4 --verbose
        """
    )
    
    parser.add_argument(
        "--queue",
        default=RabbitMQConfig.CRAWL_QUEUE,
        help=f"Queue to consume from (default: {RabbitMQConfig.CRAWL_QUEUE})"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, multiprocessing.cpu_count() - 1),
        help="Number of worker processes (default: CPU count - 1)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Update logging level if verbose
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Print startup info
    logger.info("=" * 80)
    logger.info("🐰 CRAWL WORKER STARTUP")
    logger.info("=" * 80)
    logger.info(f"Queue: {args.queue}")
    logger.info(f"Workers: {args.workers}")
    logger.info(f"RabbitMQ: {RabbitMQConfig.HOST}:{RabbitMQConfig.PORT}/{RabbitMQConfig.VHOST}")
    logger.info(f"Verbose: {args.verbose}")
    logger.info("=" * 80)
    
    # Check RabbitMQ connection
    if not check_rabbitmq_connection():
        logger.error("\n❌ Cannot connect to RabbitMQ. Exiting.")
        sys.exit(1)
    
    # Start workers
    pool = WorkerPool(
        queue_name=args.queue,
        num_workers=args.workers
    )
    
    try:
        pool.start()
    except KeyboardInterrupt:
        logger.info("\n⏹️ Received interrupt signal")
        pool.stop()
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
