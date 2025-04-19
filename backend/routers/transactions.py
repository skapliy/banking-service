import logging
import sqlite3
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends

from .. import models, services # Use relative imports
from ..database import get_db, TWO_PLACES
from ..settings import logger # Use logger from settings

router = APIRouter(
    prefix="/api", # Prefix for all routes in this router
    tags=["transactions"], # Tag for OpenAPI documentation
)

@router.post("/transactions", status_code=201)
async def create_transaction_endpoint(transaction_in: models.TransactionCreate, conn: sqlite3.Connection = Depends(get_db)):
    """Creates a new transaction and updates the account balance."""
    logger.info(f"Attempting to create transaction for account: {transaction_in.account_id}")
    account_id = transaction_in.account_id
    amount = transaction_in.amount.quantize(TWO_PLACES, services.ROUND_HALF_UP)
    comment = transaction_in.comment.strip() if transaction_in.comment else None

    # Determine transaction date
    transaction_dt = datetime.now()
    if transaction_in.date:
        try:
            transaction_date_part = datetime.strptime(transaction_in.date, '%Y-%m-%d').date()
            if transaction_date_part > date.today():
                raise HTTPException(status_code=400, detail="Transaction date cannot be in the future")
            transaction_dt = datetime.combine(transaction_date_part, datetime.now().time())
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    transaction_date_str = transaction_dt.strftime('%Y-%m-%d %H:%M:%S')

    try:
        # Check if account exists
        cursor_check = conn.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
        account = cursor_check.fetchone()
        if account is None:
            logger.warning(f"Transaction attempt for non-existent account: {account_id}")
            raise HTTPException(status_code=404, detail="Account not found")

        # Insert transaction
        transaction_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO transactions (id, account_id, amount, date, comment)
               VALUES (?, ?, ?, ?, ?)""",
            (transaction_id, account_id, amount, transaction_date_str, comment)
        )

        # Update account balance atomically
        conn.execute(
            "UPDATE accounts SET balance = balance + ? WHERE id = ?",
            (amount, account_id)
        )
        conn.commit()

        # Get new balance for response
        cursor_balance = conn.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
        new_balance = cursor_balance.fetchone()['balance']

        logger.info(f"Transaction {transaction_id} created for account {account_id}. New balance: {new_balance}")
        return {
            "message": "Transaction successful",
            "transaction_id": transaction_id,
            "new_balance": new_balance
        }
    except HTTPException:
        raise # Re-raise HTTP exceptions
    except sqlite3.Error as db_err:
         logger.error(f"Database error creating transaction for account {account_id}: {db_err}", exc_info=True)
         conn.rollback()
         raise HTTPException(status_code=500, detail=f"Database error: {db_err}")
    except Exception as e:
        logger.error(f"Unexpected error creating transaction for account {account_id}: {e}", exc_info=True)
        conn.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/accounts/{account_id}/transactions", response_model=List[models.TransactionDB])
async def get_account_transactions_endpoint(account_id: str, limit: Optional[int] = None, conn: sqlite3.Connection = Depends(get_db)):
    """Gets a list of transactions for a specific account."""
    logger.info(f"Fetching transactions for account: {account_id}, limit: {limit}")
    try:
        # Check if account exists
        cursor_check = conn.execute("SELECT id FROM accounts WHERE id = ?", (account_id,))
        if not cursor_check.fetchone():
            raise HTTPException(status_code=404, detail="Account not found")

        query = "SELECT * FROM transactions WHERE account_id = ? ORDER BY date DESC"
        params: list = [account_id]
        if limit is not None and limit > 0:
            query += " LIMIT ?"
            params.append(limit)

        cursor_transactions = conn.execute(query, params)
        transaction_rows = cursor_transactions.fetchall()
        logger.info(f"Found {len(transaction_rows)} transactions for account {account_id}")

        # Validate and convert rows to Pydantic models
        transactions_list = [models.TransactionDB.model_validate(dict(row)) for row in transaction_rows]
        return transactions_list

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching transactions for account {account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while fetching transactions")


@router.put("/transactions/{transaction_id}", status_code=200)
async def update_transaction_endpoint(transaction_id: str, transaction_update: models.TransactionUpdate, conn: sqlite3.Connection = Depends(get_db)):
    """Updates an existing transaction's amount, date, or comment."""
    logger.info(f"Attempting to update transaction: {transaction_id}")

    if not any([transaction_update.amount is not None, transaction_update.date, transaction_update.comment]):
         raise HTTPException(status_code=400, detail="No update data provided.")

    try:
        # Get original transaction details
        cursor_orig = conn.execute("SELECT account_id, amount, date FROM transactions WHERE id = ?", (transaction_id,))
        original_transaction = cursor_orig.fetchone()
        if not original_transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")

        original_amount = Decimal(original_transaction['amount'])
        account_id = original_transaction['account_id']
        new_amount = transaction_update.amount.quantize(TWO_PLACES, services.ROUND_HALF_UP) if transaction_update.amount is not None else original_amount
        amount_diff = new_amount - original_amount

        # Validate and prepare new date if provided
        new_date_str = original_transaction['date'] # Default to original
        if transaction_update.date:
            try:
                new_date_part = datetime.strptime(transaction_update.date, '%Y-%m-%d').date()
                if new_date_part > date.today():
                    raise HTTPException(status_code=400, detail="Transaction date cannot be in the future")
                # Keep original time part if only date is updated
                original_dt = datetime.fromisoformat(original_transaction['date'])
                new_dt = datetime.combine(new_date_part, original_dt.time())
                new_date_str = new_dt.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

        # Prepare update query parts
        update_fields = []
        update_params = []
        if transaction_update.amount is not None:
            update_fields.append("amount = ?")
            update_params.append(new_amount)
        if transaction_update.date:
            update_fields.append("date = ?")
            update_params.append(new_date_str)
        if transaction_update.comment is not None: # Allow empty string comment
            update_fields.append("comment = ?")
            update_params.append(transaction_update.comment.strip())

        update_query = f"UPDATE transactions SET {', '.join(update_fields)} WHERE id = ?"
        update_params.append(transaction_id)

        # Execute transaction update
        conn.execute(update_query, tuple(update_params))

        # Update account balance if amount changed
        if amount_diff != Decimal('0.00'):
            conn.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount_diff, account_id))

        conn.commit()
        logger.info(f"Transaction {transaction_id} updated successfully.")
        return {"message": "Transaction updated successfully"}

    except HTTPException:
        raise
    except sqlite3.Error as db_err:
        logger.error(f"Database error updating transaction {transaction_id}: {db_err}", exc_info=True)
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {db_err}")
    except Exception as e:
        logger.error(f"Unexpected error updating transaction {transaction_id}: {e}", exc_info=True)
        conn.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/transactions/{transaction_id}", status_code=200)
async def delete_transaction_endpoint(transaction_id: str, conn: sqlite3.Connection = Depends(get_db)):
    """Deletes a transaction and adjusts the account balance."""
    logger.info(f"Attempting to delete transaction: {transaction_id}")
    try:
        # Get transaction details before deleting
        cursor_get = conn.execute("SELECT account_id, amount FROM transactions WHERE id = ?", (transaction_id,))
        transaction = cursor_get.fetchone()
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")

        account_id = transaction['account_id']
        amount_to_revert = Decimal(transaction['amount']) * -1 # Amount to adjust balance by

        # Delete the transaction
        cursor_del = conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        if cursor_del.rowcount == 0:
             # Should not happen if fetch worked, but good practice
             raise HTTPException(status_code=404, detail="Transaction not found during delete.")

        # Adjust account balance
        conn.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount_to_revert, account_id))

        conn.commit()
        logger.info(f"Transaction {transaction_id} deleted successfully. Balance adjusted for account {account_id}.")
        return {"message": "Transaction deleted successfully"}

    except HTTPException:
        raise
    except sqlite3.Error as db_err:
        logger.error(f"Database error deleting transaction {transaction_id}: {db_err}", exc_info=True)
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {db_err}")
    except Exception as e:
        logger.error(f"Unexpected error deleting transaction {transaction_id}: {e}", exc_info=True)
        conn.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")