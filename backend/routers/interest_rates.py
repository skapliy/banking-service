import re
import sqlite3
from datetime import datetime  # Add this import
from fastapi import APIRouter, HTTPException, Depends
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional

from ..database import get_db, TWO_PLACES
from .. import models
from ..settings import logger

router = APIRouter(
    prefix="/api/interest-rate",
    tags=["Interest Rates"],
    responses={404: {"description": "Not found"}},
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


# Remove this endpoint as it conflicts with the one below
# @router.put("/{month_str}", status_code=200)
# async def set_interest_rate_for_month(month_str: str, rate_in: models.InterestRate, conn: sqlite3.Connection = Depends(get_db)):
#     """Sets or updates the interest rate for a specific month (YYYY-MM)."""
#     logger.info(f"Attempting to set interest rate for month {month_str} to {rate_in.rate}%")
#     try:
#         datetime.strptime(month_str, '%Y-%m')
#     except ValueError:
#         raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM.")

#     if rate_in.rate < 0:
#         raise HTTPException(status_code=400, detail="Interest rate cannot be negative.")

#     rate_value = rate_in.rate.quantize(TWO_PLACES, services.ROUND_HALF_UP)

#     try:
#         # Use INSERT OR REPLACE (or ON CONFLICT DO UPDATE) for simplicity
#         conn.execute(
#             """
#             INSERT INTO interest_rates (month, rate) VALUES (?, ?)
#             ON CONFLICT(month) DO UPDATE SET rate = excluded.rate
#             """,
#             (month_str, rate_value)
#         )
#         conn.commit()
#         logger.info(f"Interest rate for month {month_str} set/updated to {rate_value}%")
#         return {"message": f"Interest rate for {month_str} set to {rate_value}%"}
#     except sqlite3.Error as db_err:
#         logger.error(f"Database error setting interest rate for {month_str}: {db_err}", exc_info=True)
#         conn.rollback()
#         raise HTTPException(status_code=500, detail=f"Database error: {db_err}")
#     except Exception as e:
#         logger.error(f"Unexpected error setting interest rate for {month_str}: {e}", exc_info=True)
#         conn.rollback()
#         raise HTTPException(status_code=500, detail="Internal server error")


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


@router.put("/{month}", response_model=dict)
async def update_interest_rate(
    month: str, 
    rate_data: models.InterestRate,
    conn: sqlite3.Connection = Depends(get_db)
):
    """Update interest rate for a specific month."""
    try:
        # Validate month format (YYYY-MM)
        if not re.match(r'^\d{4}-\d{2}$', month):
            raise HTTPException(
                status_code=400, 
                detail="Invalid month format. Use YYYY-MM format."
            )
        
        # Get the rate value and round it
        rate_value = rate_data.rate.quantize(TWO_PLACES, ROUND_HALF_UP)  # Fixed: removed services.
        
        # Log the operation
        logger.info(f"Setting interest rate for month {month} to {rate_value}%")
        
        cursor = conn.cursor()
        
        # Insert or update the interest rate for the month
        cursor.execute(
            """
            INSERT INTO interest_rates (month, rate) VALUES (?, ?)
            ON CONFLICT(month) DO UPDATE SET rate = excluded.rate
            """,
            (month, rate_value)
        )
        
        conn.commit()
        
        return {"message": f"Interest rate for {month} set to {rate_value}%"}
    
    except sqlite3.Error as e:
        logger.error(f"Database error setting interest rate: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        logger.error(f"Error setting interest rate: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error setting interest rate: {e}")