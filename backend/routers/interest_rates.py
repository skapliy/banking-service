import logging
import sqlite3
from datetime import datetime
from decimal import Decimal
from typing import Dict

from fastapi import APIRouter, HTTPException, Depends

from .. import models # Use relative imports
from ..database import get_db, TWO_PLACES
from ..settings import logger # Use logger from settings

router = APIRouter(
    prefix="/api/interest-rate", # Prefix for all routes in this router
    tags=["interest rates"],     # Tag for OpenAPI documentation
)

@router.get("/{month_str}", response_model=models.InterestRate)
async def get_interest_rate_for_month(month_str: str, conn: sqlite3.Connection = Depends(get_db)):
    """Gets the interest rate for a specific month (YYYY-MM)."""
    logger.info(f"Fetching interest rate for month: {month_str}")
    try:
        datetime.strptime(month_str, '%Y-%m')
    except ValueError:
        logger.warning(f"Invalid month format requested: {month_str}")
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM.")

    try:
        cursor = conn.execute("SELECT rate FROM interest_rates WHERE month = ?", (month_str,))
        rate_row = cursor.fetchone()

        if rate_row is None or rate_row['rate'] is None:
            logger.warning(f"Interest rate not found for month: {month_str}")
            # Return 0 rate instead of 404, as frontend might expect a value
            return models.InterestRate(rate=Decimal("0.00"))
            # raise HTTPException(status_code=404, detail="Interest rate not found for this month.")

        return models.InterestRate(rate=Decimal(rate_row['rate']))

    except HTTPException:
        raise # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error fetching interest rate for {month_str}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{month_str}", status_code=200)
async def set_interest_rate_for_month(month_str: str, rate_in: models.InterestRate, conn: sqlite3.Connection = Depends(get_db)):
    """Sets or updates the interest rate for a specific month (YYYY-MM)."""
    logger.info(f"Attempting to set interest rate for month {month_str} to {rate_in.rate}%")
    try:
        datetime.strptime(month_str, '%Y-%m')
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM.")

    if rate_in.rate < 0:
        raise HTTPException(status_code=400, detail="Interest rate cannot be negative.")

    rate_value = rate_in.rate.quantize(TWO_PLACES, services.ROUND_HALF_UP)

    try:
        # Use INSERT OR REPLACE (or ON CONFLICT DO UPDATE) for simplicity
        conn.execute(
            """
            INSERT INTO interest_rates (month, rate) VALUES (?, ?)
            ON CONFLICT(month) DO UPDATE SET rate = excluded.rate
            """,
            (month_str, rate_value)
        )
        conn.commit()
        logger.info(f"Interest rate for month {month_str} set/updated to {rate_value}%")
        return {"message": f"Interest rate for {month_str} set to {rate_value}%"}
    except sqlite3.Error as db_err:
        logger.error(f"Database error setting interest rate for {month_str}: {db_err}", exc_info=True)
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {db_err}")
    except Exception as e:
        logger.error(f"Unexpected error setting interest rate for {month_str}: {e}", exc_info=True)
        conn.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("s", response_model=Dict[str, Decimal]) # Note the 's' for plural: /api/interest-rates
async def get_all_interest_rates(conn: sqlite3.Connection = Depends(get_db)):
    """Gets all defined interest rates."""
    logger.info("Fetching all interest rates")
    try:
        cursor = conn.execute("SELECT month, rate FROM interest_rates ORDER BY month")
        rates = {row['month']: Decimal(row['rate']) for row in cursor.fetchall()}
        logger.info(f"Found {len(rates)} interest rates.")
        return rates
    except Exception as e:
        logger.error(f"Error fetching all interest rates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")