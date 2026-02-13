# app/api/product_automation_routes.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import subprocess
import asyncio
import sys
import os
from pathlib import Path
import logging
from datetime import datetime

router = APIRouter(prefix="/api", tags=["product-automation"])
logger = logging.getLogger(__name__)

class OpenProductRequest(BaseModel):
    """Request to open product with Playwright automation"""
    product_url: str


@router.post("/open-product")
async def open_product_with_playwright(request: OpenProductRequest):
    """
    Open product with Playwright automation
    
    This endpoint opens a product URL in Chrome using Playwright,
    clicks "Mua ngay" button, and stops (no transaction).
    
    Request:
    ```json
    {
      "product_url": "https://tiki.vn/..."
    }
    ```
    
    Response:
    ```json
    {
      "success": true,
      "message": "Playwright automation started",
      "product_url": "https://tiki.vn/..."
    }
    ```
    """
    try:
        product_url = request.product_url
        
        if not product_url:
            raise HTTPException(status_code=400, detail="product_url is required")
        
        logger.info(f"🎬 Starting Playwright automation for: {product_url}")
        
        # Path to Python Playwright script
        script_path = Path(__file__).parent.parent.parent / "open_product.py"
        
        logger.info(f"📂 Looking for script at: {script_path}")
        
        if not script_path.exists():
            logger.error(f"❌ Script not found at {script_path}")
            raise HTTPException(
                status_code=500,
                detail=f"Playwright script not found at {script_path}"
            )
        
        logger.info(f"✅ Script found at: {script_path}")
        
        # Run script in background (detached process)
        # On Windows: use CREATE_NEW_PROCESS_GROUP
        if sys.platform == "win32":
            # Windows: spawn detached process with logging
            log_file = Path(__file__).parent.parent.parent / "playwright_log.txt"
            with open(log_file, "a") as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"[{datetime.now()}] Starting: {product_url}\n")
                f.write(f"{'='*80}\n")
            
            process = subprocess.Popen(
                [sys.executable, str(script_path), product_url],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                stdout=open(log_file, "a"),
                stderr=subprocess.STDOUT,
                text=True
            )
            logger.info(f"✅ Process spawned with PID: {process.pid}")
            logger.info(f"📝 Logs written to: {log_file}")
        else:
            # Linux/Mac: spawn detached process
            log_file = Path(__file__).parent.parent.parent / "playwright_log.txt"
            with open(log_file, "a") as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"[{datetime.now()}] Starting: {product_url}\n")
                f.write(f"{'='*80}\n")
            
            process = subprocess.Popen(
                [sys.executable, str(script_path), product_url],
                preexec_fn=os.setsid,
                stdout=open(log_file, "a"),
                stderr=subprocess.STDOUT,
                text=True
            )
            logger.info(f"✅ Process spawned with PID: {process.pid}")
            logger.info(f"📝 Logs written to: {log_file}")
        
        
        logger.info(f"✅ Playwright automation process started")
        
        return {
            "success": True,
            "message": "Playwright automation started",
            "product_url": product_url,
            "status": "running"
        }
    
    except Exception as e:
        logger.error(f"❌ Error opening product: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/playwright-status")
async def check_playwright_status():
    """
    Check if Playwright automation is available
    
    Response:
    ```json
    {
      "success": true,
      "playwright_available": true,
      "script_exists": true
    }
    ```
    """
    try:
        script_path = Path(__file__).parent.parent.parent / "open_product.py"
        exists = script_path.exists()
        
        return {
            "success": True,
            "playwright_available": True,
            "script_exists": exists,
            "script_path": str(script_path)
        }
    except Exception as e:
        return {
            "success": False,
            "playwright_available": False,
            "error": str(e)
        }


@router.get("/playwright-logs")
async def get_playwright_logs():
    """
    Get Playwright automation logs for debugging
    
    Returns the last 50 lines of the log file
    """
    try:
        log_file = Path(__file__).parent.parent.parent / "playwright_log.txt"
        
        if not log_file.exists():
            return {
                "success": True,
                "message": "No logs yet",
                "logs": []
            }
        
        # Read last 50 lines
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        
        last_lines = lines[-50:] if len(lines) > 50 else lines
        
        return {
            "success": True,
            "total_lines": len(lines),
            "showing_last": len(last_lines),
            "logs": "".join(last_lines)
        }
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        return {
            "success": False,
            "error": str(e)
        }

