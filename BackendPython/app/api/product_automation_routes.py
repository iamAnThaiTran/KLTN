# app/api/product_automation_routes.py
# 
# ⚠️ DEPRECATED: All browser automation logic has been moved to frontend
# This file is kept for reference but contains no active endpoints
#
# Frontend now handles:
# - Opening product URLs in browser
# - Clicking "Mua ngay" button
# - Managing user interactions
#
# Backend now only provides:
# - Product search & filtering (via product routes)
# - Product details (via product routes)
# - No direct browser automation

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["product-automation"])

