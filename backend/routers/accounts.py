# Standard libraries
import uuid
import sqlite3
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP # <<< Import ROUND_HALF_UP from decimal
from typing import List, Dict, Optional

# Third-party libraries
from fastapi import APIRouter, HTTPException, Depends

# Project modules
# Assuming models are in backend.models, services in backend.services, etc.
# <<< REMOVE ROUND_HALF_UP from this import if it was here >>>
from ..database import get_db, TWO_PLACES # Assuming constants are here too
from .. import models # Assuming models like AccountCreate, AccountDB, etc. are here
from .. import services # Assuming calculate_interest_for_month is here
from ..settings import logger # Assuming logger is configured in settings

router = APIRouter(
    prefix="/api/accounts", # Add prefix for all routes in this router
    tags=["Accounts"]       # Tag for OpenAPI documentation
)

# --- Endpoint to Create Account ---
@router.post("", response_model=models.AccountDB, status_code=201) # Use router, relative path ""
async def create_account(account_in: models.AccountCreate, conn: sqlite3.Connection = Depends(get_db)):
    """Создание нового банковского счета."""
    logger.info(f"Attempting to create account: {account_in.name}")

    # --- Проверки ---
    if account_in.balance < 0:
        raise HTTPException(status_code=400, detail="Initial balance cannot be negative")
    if not account_in.name.strip():
         raise HTTPException(status_code=400, detail="Account name cannot be empty")
    # Проверка ставки (если она передана)
    if account_in.interest_rate is not None and account_in.interest_rate < 0:
         raise HTTPException(status_code=400, detail="Interest rate cannot be negative")

    account_id = str(uuid.uuid4())
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    current_month_str = datetime.now().strftime('%Y-%m') # Текущий месяц для ставки
    initial_balance = account_in.balance.quantize(TWO_PLACES, ROUND_HALF_UP)

    try:
        # with get_db() as conn: # Remove with get_db(), use Depends
        cursor = conn.cursor()

        # 1. Создаем счет (как и раньше)
        cursor.execute(
            "INSERT INTO accounts (id, name, balance) VALUES (?, ?, ?)",
            (account_id, account_in.name.strip(), initial_balance)
        )
        # 2. Создаем транзакцию начального остатка (как и раньше)
        transaction_id = str(uuid.uuid4())
        cursor.execute(
            """INSERT INTO transactions (id, account_id, amount, date, comment)
               VALUES (?, ?, ?, ?, ?)""",
            (transaction_id, account_id, initial_balance, current_time, "Начальный остаток")
        )

        # 3. ---> НОВОЕ: Устанавливаем процентную ставку на текущий месяц, если она передана <---
        if account_in.interest_rate is not None:
            rate_value = account_in.interest_rate.quantize(TWO_PLACES, ROUND_HALF_UP)
            logger.info(f"Setting initial interest rate for account {account_id} for month {current_month_str} to {rate_value}%")
            # IMPORTANT: This assumes interest_rates table uses only 'month' as primary/unique key.
            # If rates are per-account, the schema and logic need changing.
            # This will set/update the rate globally for the month.
            cursor.execute(
                """
                INSERT INTO interest_rates (month, rate) VALUES (?, ?)
                ON CONFLICT(month) DO UPDATE SET rate = excluded.rate
                """,
                (current_month_str, rate_value)
            )

        conn.commit() # Commit all changes

        # Fetch and return the created account
        cursor.execute("SELECT id, name, balance FROM accounts WHERE id = ?", (account_id,))
        new_account_row = cursor.fetchone()
        logger.info(f"Account created successfully in DB: {account_id}")

        if new_account_row:
            try:
                account_dict = dict(new_account_row)
                # Assuming AccountDB is your Pydantic model for DB representation
                validated_account = models.AccountDB.model_validate(account_dict)
                return validated_account
            except Exception as validation_err:
                 logger.error(f"Pydantic validation failed for new account {account_id}: {validation_err}", exc_info=True)
                 raise HTTPException(status_code=500, detail="Failed to validate created account data for response.")
        else:
            logger.error(f"CRITICAL: Failed to fetch newly created account from DB: {account_id}")
            raise HTTPException(status_code=500, detail="Failed to retrieve created account after insertion.")

    except sqlite3.IntegrityError as e:
        logger.error(f"Database integrity error during account creation: {e}", exc_info=True)
        # Consider more specific error messages based on constraint violation if possible
        raise HTTPException(status_code=409, detail=f"Failed to create account. Possible duplicate or constraint violation.") # 409 Conflict might be better
    except Exception as e:
        logger.error(f"Unexpected error during account creation endpoint execution for {account_in.name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during account creation.")


# --- Endpoint to Get List of Accounts with Details ---
@router.get("", response_model=List[models.AccountDetails]) # Use router, relative path ""
async def get_accounts_list(conn: sqlite3.Connection = Depends(get_db)):
    logger.info(">>> ENTERING get_accounts_list") # <<< Лог входа
    try:
        logger.info("Fetching account list details")
        accounts_details: List[models.AccountDetails] = [] # Use the specific Pydantic model
        today = date.today()
        current_month_str = today.strftime('%Y-%m')
    
        # Determine the previous 3 months
        previous_months_keys = []
        first_day_current_month = today.replace(day=1)
        for i in range(1, 4):
            target_month_first_day = first_day_current_month
            for _ in range(i):
                target_month_first_day = (target_month_first_day - timedelta(days=1)).replace(day=1)
            previous_months_keys.append(target_month_first_day.strftime('%Y-%m'))
        previous_months_keys.sort()
        logger.debug(f"Previous 3 months identified: {previous_months_keys}")
    
        try:
            # <<< FIX: Get a cursor from the connection >>>
            cursor = conn.cursor()
    
            # Fetch all accounts
            # <<< FIX: Use the cursor to execute the query >>>
            logger.debug("Fetching accounts from DB...")
            cursor = conn.execute("SELECT id, name, balance FROM accounts ORDER BY name")
            accounts_raw = cursor.fetchall()
            logger.debug(f"Fetched {len(accounts_raw)} accounts raw.")
    
            # Fetch all relevant monthly balances and interest rates
            all_months = [current_month_str] + previous_months_keys
            placeholders = ','.join('?' * len(all_months)) # Create placeholders like ?,?,?
    
            # <<< FIX: Use the cursor to execute the query >>>
            cursor.execute(f"SELECT month, rate FROM interest_rates WHERE month IN ({placeholders})", all_months)
            rates_raw = cursor.fetchall()
            interest_rates_dict = {row['month']: row['rate'] for row in rates_raw}
            logger.debug(f"Fetched interest rates for months: {list(interest_rates_dict.keys())}")
    
            # <<< FIX: Use the cursor to execute the query >>>
            cursor.execute(f"SELECT account_id, month, closing_balance FROM monthly_balances WHERE month IN ({placeholders})", all_months)
            balances_raw = cursor.fetchall()
            # Organize balances for easy lookup: {account_id: {month: balance}}
            monthly_balances_dict: Dict[str, Dict[str, Decimal]] = {}
            for row in balances_raw:
                acc_id = row['account_id']
                month = row['month']
                balance = row['closing_balance']
                if acc_id not in monthly_balances_dict:
                    monthly_balances_dict[acc_id] = {}
                monthly_balances_dict[acc_id][month] = balance
            logger.debug("Fetched and organized monthly balances.")
    
    
            # Process each account
            for account_row in accounts_raw:
                account_id = account_row['id']
                account_name = account_row['name']
                current_balance = account_row['balance'] # This is the live balance
    
                logger.debug(f"Processing account: {account_id} ({account_name})")
    
                # Prepare monthly details dictionary
                monthly_details: Dict[str, models.MonthlyDetail] = {}
    
                # Populate details for previous months
                for month_key in previous_months_keys:
                    closing_balance = monthly_balances_dict.get(account_id, {}).get(month_key)
                    interest_rate = interest_rates_dict.get(month_key)
                    # Interest calculation for past months depends on stored balance, not live data
                    # Assuming interest was already calculated and stored if needed,
                    # or we calculate based on closing balance if that's the requirement.
                    # For simplicity, let's just report the stored balance and rate.
                    # If interest earned needs to be shown, it should ideally be stored too.
                    monthly_details[month_key] = models.MonthlyDetail(
                        closing_balance=closing_balance,
                        interest_rate=interest_rate
                        # interest_earned=... # Requires more complex logic or stored data
                    )
                    logger.debug(f"  Month {month_key}: Balance={closing_balance}, Rate={interest_rate}")
    
    
                # Calculate details for the current month (using service function)
                current_month_rate = interest_rates_dict.get(current_month_str)
                # <<< FIX: Pass the cursor, not the connection, if the service needs it >>>
                # Or better, pass only the necessary data (account_id, current_month_str, conn/cursor)
                # Assuming calculate_interest_for_month now accepts conn or cursor if needed
                # Let's assume it only needs data for now, adjust if service needs DB access
                # current_interest_earned = services.calculate_interest_for_month(
                #     conn=conn, # Or cursor=cursor, or just account_id=account_id
                #     account_id=account_id,
                #     month_str=current_month_str,
                #     current_rate_decimal=current_month_rate # Pass rate if available
                # )
                # Simplified: For display, show current balance and rate. Actual interest calculation
                # might happen elsewhere (e.g., end-of-month process).
                monthly_details[current_month_str] = models.MonthlyDetail(
                    closing_balance=current_balance, # Show live balance for current month display
                    interest_rate=current_month_rate,
                    # interest_earned=current_interest_earned # If calculated
                )
                logger.debug(f"  Current Month {current_month_str}: LiveBalance={current_balance}, Rate={current_month_rate}")
    
    
                # Create the final AccountDetails object
                account_detail = models.AccountDetails(
                    id=account_id,
                    name=account_name,
                    balance=current_balance, # Live balance
                    monthly_details=monthly_details
                )
                accounts_details.append(account_detail)
    
            logger.info(f"Successfully prepared details for {len(accounts_details)} accounts.")
            logger.info("<<< EXITING get_accounts_list SUCCESSFULLY") # <<< Лог успешного выхода
            return accounts_details
        except sqlite3.Error as e:
            logger.error(f"!!! Database error in get_accounts_list: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Database error fetching accounts: {e}")
        except Exception as e:
            logger.exception(f"!!! Unexpected error in get_accounts_list: {e}") # Используйте exception для traceback
            raise HTTPException(status_code=500, detail=f"Internal server error while fetching accounts: {e}")
        finally:
            logger.debug("--- FINISHING get_accounts_list request ---") # <<< Лог завершения (даже при ошибке)

    except sqlite3.Error as e:
        logger.error(f"Database error while fetching account list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error fetching accounts: {e}")
    except Exception as e:
        # Используйте logger.exception для автоматического добавления traceback
        logger.exception(f"Unexpected error while fetching account list: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error while fetching accounts: {e}")


# --- Endpoint to Get Single Account Details ---
@router.get("/{account_id}", response_model=models.AccountDB) # Use router, relative path "{account_id}"
async def get_account_details(account_id: str, conn: sqlite3.Connection = Depends(get_db)):
    logger.info(f"Fetching details for account: {account_id}")
    try:
        cursor = conn.execute("SELECT id, name, balance FROM accounts WHERE id = ?", (account_id,))
        account_row = cursor.fetchone()

        if account_row is None:
            logger.warning(f"Account not found: {account_id}")
            raise HTTPException(status_code=404, detail="Account not found")

        try:
            account_dict = dict(account_row)
            logger.debug(f"Fetched account row as dict: {account_dict}")
            validated_account = models.AccountDB.model_validate(account_dict)
            logger.debug(f"Validated account data for response: {validated_account}")
            return validated_account
        except Exception as validation_err:
            logger.error(f"Pydantic validation failed for account {account_id}: {validation_err}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to validate account data for response.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching account {account_id}: {e}", exc_info=True)
        error_detail = f"Internal server error while fetching account details: {str(e)}"
        raise HTTPException(status_code=500, detail=error_detail)


# --- Endpoint to Update Account Name ---
@router.put("/{account_id}", response_model=models.AccountDB) # Use router
async def update_account_name(account_id: str, account_update: models.AccountUpdate, conn: sqlite3.Connection = Depends(get_db)):
    """Обновление имени счета."""
    logger.info(f"Attempting to update name for account: {account_id}")
    new_name = account_update.name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Account name cannot be empty")
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE accounts SET name = ? WHERE id = ?",
            (new_name, account_id)
        )
        if cursor.rowcount == 0:
            logger.warning(f"Attempted to update non-existent account: {account_id}")
            raise HTTPException(status_code=404, detail="Account not found")
        conn.commit()
        logger.info(f"Account name updated for: {account_id}")

        # Fetch and return the updated account
        cursor.execute("SELECT id, name, balance FROM accounts WHERE id = ?", (account_id,))
        updated_account_row = cursor.fetchone()
        if updated_account_row:
             try:
                 account_dict = dict(updated_account_row)
                 validated_account = models.AccountDB.model_validate(account_dict)
                 return validated_account
             except Exception as validation_err:
                 logger.error(f"Pydantic validation failed for updated account {account_id}: {validation_err}", exc_info=True)
                 raise HTTPException(status_code=500, detail="Failed to validate updated account data for response.")
        else:
             # This case should ideally not happen if the update was successful
             logger.error(f"CRITICAL: Failed to fetch updated account {account_id} after successful update")
             raise HTTPException(status_code=500, detail="Failed to retrieve updated account.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating account {account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# --- Endpoint to Delete Account ---
@router.delete("/{account_id}", status_code=200) # Use router
async def delete_account_endpoint(account_id: str, conn: sqlite3.Connection = Depends(get_db)):
    """Удаление счета и всех связанных данных (транзакции, история)."""
    logger.info(f"Attempting to delete account: {account_id}")
    try:
        # Assuming ON DELETE CASCADE is set up in the database schema for
        # transactions and monthly_balances referencing accounts.id.
        # If not, you must delete from child tables first.
        cursor = conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        if cursor.rowcount == 0:
            logger.warning(f"Attempted to delete non-existent account: {account_id}")
            raise HTTPException(status_code=404, detail="Account not found")
        conn.commit()
        logger.info(f"Account deleted successfully: {account_id}")
        return {"message": "Account deleted successfully"}
    except sqlite3.IntegrityError as e:
         # This might happen if ON DELETE CASCADE is not set and there are related records
         logger.error(f"Integrity error deleting account {account_id}, possibly due to related records: {e}", exc_info=True)
         raise HTTPException(status_code=409, detail="Cannot delete account, related records exist.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting account {account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# --- Endpoint to Get Transactions for a Specific Account ---
# Note: This logically relates to transactions, but follows the /accounts/{id}/transactions URL structure.
@router.get("/{account_id}/transactions", response_model=List[models.TransactionDB]) # Use router
async def get_account_transactions_endpoint(account_id: str, limit: Optional[int] = None, conn: sqlite3.Connection = Depends(get_db)):
    logger.info(f"Fetching transactions for account: {account_id}, limit: {limit}")
    try:
        # Check if account exists
        cursor_check = conn.execute("SELECT id FROM accounts WHERE id = ?", (account_id,))
        if not cursor_check.fetchone():
             logger.warning(f"Attempted to fetch transactions for non-existent account: {account_id}")
             raise HTTPException(status_code=404, detail="Account not found")

        query = "SELECT * FROM transactions WHERE account_id = ? ORDER BY date DESC"
        params: list = [account_id]
        if limit is not None and limit > 0:
            query += " LIMIT ?"
            params.append(limit)

        cursor_transactions = conn.execute(query, params)
        transaction_rows = cursor_transactions.fetchall()
        logger.info(f"Found {len(transaction_rows)} transactions for account {account_id}")

        transactions_list = []
        for row in transaction_rows:
            try:
                transaction_dict = dict(row)
                validated_transaction = models.TransactionDB.model_validate(transaction_dict)
                transactions_list.append(validated_transaction)
            except Exception as validation_err:
                 logger.error(f"Pydantic validation failed for transaction row {dict(row)}: {validation_err}", exc_info=True)
                 # Fail fast if validation fails for any transaction in the list
                 raise HTTPException(status_code=500, detail=f"Failed to validate transaction data: {validation_err}")

        return transactions_list

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching transactions for account {account_id}: {e}", exc_info=True)
        error_detail = f"Internal server error while fetching transactions: {str(e)}"
        raise HTTPException(status_code=500, detail=error_detail)