import calendar
import logging
import sqlite3
from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP

from .database import get_db, TWO_PLACES # Import DB context and constants
from .models import PreviousMonthData, CurrentPeriodData # Import necessary models

from .settings import logger

logger = logging.getLogger(__name__)

# --- Helper Functions ---
def get_days_in_year(year: int) -> int:
    """Returns the number of days in the year (accounts for leap years)."""
    return 366 if calendar.isleap(year) else 365

# --- Core Service Functions ---

def get_balance_at_date(conn: sqlite3.Connection, account_id: str, target_date: date) -> Decimal:
    """
    Gets the account balance at the beginning of the specified date (i.e., end of the previous day).
    Uses monthly balances as checkpoints if available.
    """
    target_date_str = target_date.strftime('%Y-%m-%d') + ' 00:00:00'
    logger.debug(f"Getting balance for account {account_id} at start of {target_date_str}")

    # 1. Find the most recent monthly balance *before* the target date's month start
    first_day_target_month = target_date.replace(day=1)
    prev_month_date = first_day_target_month - timedelta(days=1)
    prev_month_str = prev_month_date.strftime('%Y-%m')

    cursor = conn.execute(
        "SELECT end_balance FROM monthly_balances WHERE account_id = ? AND month = ?",
        (account_id, prev_month_str)
    )
    row = cursor.fetchone()

    if row:
        start_balance = Decimal(row['end_balance'])
        # Start summing transactions from the beginning of the target month
        start_sum_date_str = first_day_target_month.strftime('%Y-%m-%d') + ' 00:00:00'
        logger.debug(f"Found monthly balance for {prev_month_str}: {start_balance}. Summing transactions from {start_sum_date_str}.")
    else:
        # If no monthly balance, we need to calculate from the beginning (or initial balance)
        # This might require summing *all* transactions up to the target date.
        # For simplicity here, we assume an initial balance transaction exists.
        # A more robust solution might query the very first transaction date.
        logger.warning(f"No monthly balance found for {prev_month_str} for account {account_id}. Calculating from initial balance (potentially inaccurate if history is long).")
        cursor_initial = conn.execute(
            """SELECT SUM(amount) FROM transactions
               WHERE account_id = ? AND date < ? AND comment = 'Начальный остаток'""", # Assuming this comment identifies it
            (account_id, target_date_str)
        )
        initial_row = cursor_initial.fetchone()
        start_balance = Decimal(initial_row[0]) if initial_row and initial_row[0] is not None else Decimal('0.00')
        start_sum_date_str = '0000-00-00 00:00:00' # Start from beginning if no checkpoint
        logger.debug(f"Calculated start balance from initial transaction(s): {start_balance}. Summing transactions from beginning.")


    # 2. Sum transactions from the checkpoint date up to *before* the target date
    cursor_trans = conn.execute(
        """
        SELECT SUM(amount) as total_amount
        FROM transactions
        WHERE account_id = ? AND date >= ? AND date < ? AND comment != 'Начальный остаток'
        """, # Exclude initial balance if calculated separately
        (account_id, start_sum_date_str, target_date_str)
    )
    result = cursor_trans.fetchone()
    sum_transactions = Decimal(result['total_amount']) if result and result['total_amount'] is not None else Decimal('0.00')
    logger.debug(f"Sum of transactions between {start_sum_date_str} and {target_date_str}: {sum_transactions}")

    balance = start_balance + sum_transactions
    logger.debug(f"Calculated balance at start of {target_date}: {balance}")
    return balance.quantize(TWO_PLACES, ROUND_HALF_UP)


def calculate_interest_for_month(conn: sqlite3.Connection, account_id: str, month_str: str) -> tuple[Decimal, Decimal]:
    """
    Calculates interest and end-of-month balance for the specified month ('YYYY-MM').
    Uses daily balance calculation.
    Returns (total_interest, end_of_month_balance_after_interest).
    """
    logger.info(f"Calculating interest for account {account_id}, month {month_str}")
    try:
        year, month = map(int, month_str.split('-'))
        start_date = date(year, month, 1)
        days_in_month = calendar.monthrange(year, month)[1]
        end_date = date(year, month, days_in_month)
        days_in_year = get_days_in_year(year)

        # Get the interest rate for the month
        cursor_rate = conn.execute("SELECT rate FROM interest_rates WHERE month = ?", (month_str,))
        rate_row = cursor_rate.fetchone()
        if not rate_row or rate_row['rate'] is None:
            logger.warning(f"No interest rate found for {month_str}. Interest calculation skipped.")
            # Get balance at end of month without interest calculation
            eom_balance = get_balance_at_date(conn, account_id, end_date + timedelta(days=1))
            return Decimal('0.00'), eom_balance

        monthly_rate_decimal = Decimal(rate_row['rate']) / Decimal('100.0')
        logger.debug(f"Interest rate for {month_str}: {monthly_rate_decimal * 100}%")

        total_interest = Decimal('0.00')

        # Fetch all transactions for the month once
        transactions_in_month = conn.execute(
            """SELECT amount, date FROM transactions
               WHERE account_id = ? AND date >= ? AND date < ?
               ORDER BY date""",
            (account_id, start_date.strftime('%Y-%m-%d') + ' 00:00:00',
             (end_date + timedelta(days=1)).strftime('%Y-%m-%d') + ' 00:00:00')
        ).fetchall()

        # Get balance at the very start of the month
        balance_at_start_of_day = get_balance_at_date(conn, account_id, start_date)
        logger.debug(f"Balance at start of {start_date}: {balance_at_start_of_day}")

        transaction_iter = iter(transactions_in_month)
        current_transaction = next(transaction_iter, None)
        current_day = start_date

        # Iterate through each day of the month
        for _ in range(days_in_month):
            current_day_str = current_day.strftime('%Y-%m-%d')

            # Calculate interest on the balance *at the start* of the day
            daily_interest = (balance_at_start_of_day * monthly_rate_decimal / Decimal(days_in_year))
            total_interest += daily_interest
            # logger.debug(f"Day {current_day_str}: Start Balance={balance_at_start_of_day:.2f}, Daily Interest={daily_interest:.4f}")

            # Apply transactions *for this day* to get the balance for the *next* day's start
            daily_transaction_sum = Decimal('0.00')
            while current_transaction and current_transaction['date'].startswith(current_day_str):
                daily_transaction_sum += Decimal(current_transaction['amount'])
                current_transaction = next(transaction_iter, None)

            balance_at_start_of_next_day = balance_at_start_of_day + daily_transaction_sum
            # logger.debug(f"Day {current_day_str}: Transactions Sum={daily_transaction_sum:.2f}, Balance EOD={balance_at_start_of_next_day:.2f}")

            # Prepare for the next day
            balance_at_start_of_day = balance_at_start_of_next_day
            current_day += timedelta(days=1)

        # Final balance before adding this month's interest
        end_of_month_balance_before_interest = balance_at_start_of_day
        total_interest = total_interest.quantize(TWO_PLACES, ROUND_HALF_UP)
        # Final balance *after* adding this month's interest
        end_of_month_balance_after_interest = (end_of_month_balance_before_interest + total_interest).quantize(TWO_PLACES, ROUND_HALF_UP)

        logger.info(f"Calculation for {month_str}: Total Interest={total_interest:.2f}, Balance EOM (before interest)={end_of_month_balance_before_interest:.2f}, Balance EOM (after interest)={end_of_month_balance_after_interest:.2f}")

        # Return calculated interest and the final balance including interest
        return total_interest, end_of_month_balance_after_interest

    except Exception as e:
        logger.error(f"Error calculating interest for {account_id} month {month_str}: {e}", exc_info=True)
        raise # Propagate the error

# --- You would add more service functions here ---
# e.g., functions to get detailed account data, process uploads, run reports etc.
# These functions would encapsulate the logic currently in your endpoints.


def calculate_interest_for_month(account_id: str, balance: Decimal, rate: Decimal, month_str: str) -> Decimal:
    """Calculate projected interest for the given account and month."""
    if rate is None or balance is None:
        return Decimal("0.00")
    
    try:
        # Parse the month string to get year and month
        year, month = map(int, month_str.split('-'))
        
        # Get the number of days in the month
        days_in_month = calendar.monthrange(year, month)[1]
        
        # Calculate daily interest rate (annual rate / 365)
        daily_rate = rate / Decimal('100') / Decimal('365')
        
        # Calculate interest for the month (balance * daily rate * days in month)
        interest = balance * daily_rate * Decimal(days_in_month)
        
        # Round to 2 decimal places
        rounded_interest = interest.quantize(TWO_PLACES, ROUND_HALF_UP)
        
        logger.debug(f"Calculated interest for account {account_id}, month {month_str}: {rounded_interest}")
        return rounded_interest
    
    except Exception as e:
        logger.error(f"Error calculating interest: {e}", exc_info=True)
        return Decimal("0.00")