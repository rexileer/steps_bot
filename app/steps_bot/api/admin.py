"""
Admin API for PVZ management and order retrieval.

Endpoints:
- POST /pvz: Replace PVZ list in database
- GET /order/{date_from-date_to}: Get orders for date range
"""

from __future__ import annotations

import logging
from datetime import datetime, date as date_type
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.steps_bot.settings import config
from app.steps_bot.db.repo import get_session, replace_pvz_list, get_pvz_by_city, get_orders_between


logger = logging.getLogger(__name__)

app = FastAPI(title="steps_bot Admin API", version="1.0.0")


class PVZItem(BaseModel):
    """Model for PVZ item in request."""
    id: str = Field(..., min_length=1)
    full_address: str = Field(..., min_length=1)


class PVZResponse(BaseModel):
    """Response model for POST /pvz."""
    success: bool
    count: int
    message: str


class OrderResponse(BaseModel):
    """Response model for order item."""
    first_name: str
    last_name: str
    phone: str
    email: str
    pvz_id: str
    order_id: str
    created_at: str
    product_code: str


def validate_api_key(api_key: Optional[str] = Header(None)) -> None:
    """
    Validate API_Key header against configured API_KEY.
    
    Args:
        api_key: API_Key from request header
    
    Raises:
        HTTPException: if API_Key is invalid or missing
    """
    if not api_key:
        logger.warning("Request rejected: missing API_Key header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API_Key header required",
        )
    
    if api_key != config.API_KEY:
        logger.warning(f"Request rejected: invalid API_Key (provided: {api_key[:4]}...)")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API_Key",
        )


@app.post("/pvz", response_model=PVZResponse)
async def replace_pvz(
    items: List[PVZItem],
    api_key: Optional[str] = Header(None),
) -> PVZResponse:
    """
    Replace entire PVZ list in database.
    
    Request body: JSON array of PVZ items
    [{
        "id": "019620d8987e745880fb93a122b7da44",
        "full_address": "Москва Ленинградский проспект 75 к1А"
    }, ...]
    
    Returns:
        - success: boolean indicating success
        - count: number of saved PVZ items
        - message: descriptive message
    """
    # Validate API key
    validate_api_key(api_key)
    
    # Validate input
    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PVZ list cannot be empty",
        )
    
    # Convert to dict format for repository
    pvz_list = [{"id": item.id, "full_address": item.full_address} for item in items]
    
    try:
        async with get_session() as session:
            count = await replace_pvz_list(session, pvz_list)
            logger.info(f"PVZ list replaced: {count} items saved")
            return PVZResponse(
                success=True,
                count=count,
                message=f"Successfully saved {count} PVZ items",
            )
    except Exception as e:
        logger.error(f"Error replacing PVZ list: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save PVZ list",
        )


@app.get("/order/{date_range}", response_model=List[OrderResponse])
async def get_orders_by_date_range(
    date_range: str,
    api_key: Optional[str] = Header(None),
) -> List[OrderResponse]:
    """
    Get orders for specified date range.
    
    Path parameter:
        date_range: two ISO dates separated by hyphen
        Format: YYYY-MM-DD-YYYY-MM-DD
        Example: 2025-10-01-2025-10-17
    
    Returns:
        JSON array of order objects with fields:
        - first_name (string)
        - last_name (string)
        - phone (string)
        - email (string)
        - pvz_id (string)
        - order_id (string)
        - created_at (ISO 8601 datetime)
        - product_code (string)
    """
    # Validate API key
    validate_api_key(api_key)
    
    # Parse date range
    try:
        parts = date_range.split("-")
        if len(parts) != 6:  # YYYY-MM-DD-YYYY-MM-DD = 6 parts when split by "-"
            raise ValueError("Invalid date range format")
        
        date_from_str = f"{parts[0]}-{parts[1]}-{parts[2]}"
        date_to_str = f"{parts[3]}-{parts[4]}-{parts[5]}"
        
        date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()
        date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()
        
        if date_from > date_to:
            raise ValueError("Start date cannot be after end date")
            
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date range format: {str(e)}. Use YYYY-MM-DD-YYYY-MM-DD",
        )
    
    try:
        async with get_session() as session:
            orders = await get_orders_between(session, date_from, date_to)
            logger.info(f"Retrieved {len(orders)} orders for range {date_from_str} to {date_to_str}")
            return [OrderResponse(**order) for order in orders]
    except Exception as e:
        logger.error(f"Error retrieving orders: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve orders",
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
