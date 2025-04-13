from fastapi import FastAPI, HTTPException, File, UploadFile, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import csv
import io
import uuid
from datetime import datetime, timedelta
import logging
import sqlite3
import calendar
import asyncio
from contextlib import contextmanager

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DATABASE_URL = "banking.db"

# Database initialization
def init_db():
    with sqlite3.connect(DATABASE_URL) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                balance REAL NOT NULL DEFAULT 0.0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                comment TEXT,
                FOREIGN KEY (account_id) REFERENCES accounts (id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS interest_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rate REAL NOT NULL,
                month TEXT NOT NULL,
                UNIQUE(month)
            )
        """)
        # Инициализируем текущую процентную ставку
        current_month = datetime.now().strftime("%Y-%m")
        conn.execute("""
            INSERT OR IGNORE INTO interest_rates (rate, month) VALUES (0.0, ?)
        """, (current_month,))
        conn.commit()

# Initialize database on startup
init_db()

@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE_URL)
    try:
        conn.row_factory = sqlite3.Row
        yield conn
    finally:
        conn.close()

# Data models
class Transaction(BaseModel):
    account_id: str
    amount: float
    date: str
    comment: Optional[str] = None

class MonthlyBalance(BaseModel):
    month: str
    balance: float

class AccountUpdate(BaseModel):
    name: str
    balance: float

class InterestRate(BaseModel):
    rate: float

@app.get("/")
def read_root():
    logging.info("Root endpoint accessed")
    return {"message": "Welcome to Banking Service API"}

@app.get("/api/accounts")
async def get_accounts():
    try:
        with get_db() as conn:
            cursor = conn.execute("SELECT * FROM accounts")
            accounts = [dict(row) for row in cursor.fetchall()]
            three_months_ago = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
            for account in accounts:
                cursor = conn.execute(
                    """
                    SELECT * FROM transactions 
                    WHERE account_id = ? AND date >= ?
                    ORDER BY date DESC
                    """,
                    (account['id'], three_months_ago)
                )
                transactions = [dict(row) for row in cursor.fetchall()]
                account['transactions'] = transactions
                monthly_balances = {}
                current_date = datetime.now()
                for i in range(3):
                    month_date = current_date - timedelta(days=30 * i)
                    month_key = month_date.strftime("%Y-%m")
                    cursor = conn.execute(
                        "SELECT rate FROM interest_rates WHERE month = ?",
                        (month_key,)
                    )
                    rate_result = cursor.fetchone()
                    interest_rate = rate_result['rate'] if rate_result else 0.0
                    cursor = conn.execute(
                        """
                        SELECT SUM(amount) as total
                        FROM transactions
                        WHERE account_id = ? 
                        AND strftime('%Y-%m', date) = ?
                        """,
                        (account['id'], month_key)
                    )
                    result = cursor.fetchone()
                    monthly_balance = float(result['total'] or 0)
                    monthly_balances[month_key] = {
                        'balance': monthly_balance,
                        'interest_rate': interest_rate
                    }
                account['monthly_balances'] = monthly_balances
            return JSONResponse(
                content=accounts,
                headers={"Content-Type": "application/json; charset=utf-8"}
            )
    except sqlite3.Error as e:
        logging.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")

@app.post("/api/accounts")
async def create_account(account: AccountUpdate):
    try:
        if not account.name:
            raise HTTPException(status_code=400, detail="Name is required")
        if account.balance < 0:
            raise HTTPException(status_code=400, detail="Balance cannot be negative")
        account_id = str(uuid.uuid4())
        with get_db() as conn:
            conn.execute(
                "INSERT INTO accounts (id, name, balance) VALUES (?, ?, ?)",
                (account_id, account.name, float(account.balance))
            )
            conn.commit()
            cursor = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
            new_account = dict(cursor.fetchone())
            logging.info(f"Account created successfully: {new_account}")
            return JSONResponse(
                content=new_account,
                headers={"Content-Type": "application/json; charset=utf-8"}
            )
    except sqlite3.Error as e:
        logging.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logging.error(f"Error creating account: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/transactions")
async def create_transaction(transaction: Transaction):
    try:
        with get_db() as conn:
            cursor = conn.execute(
                "SELECT * FROM accounts WHERE id = ?",
                (transaction.account_id,)
            )
            account = cursor.fetchone()
            if account is None:
                raise HTTPException(status_code=404, detail="Account not found")
            transaction_date = datetime.strptime(transaction.date, "%Y-%m-%d").date()
            today = datetime.now().date()
            if transaction_date > today:
                raise HTTPException(status_code=400, detail="Transaction date cannot be in the future")
            transaction_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO transactions (id, account_id, amount, date, comment) VALUES (?, ?, ?, ?, ?)",
                (transaction_id, transaction.account_id, transaction.amount, transaction.date, transaction.comment)
            )
            new_balance = float(account['balance']) + transaction.amount
            conn.execute(
                "UPDATE accounts SET balance = ? WHERE id = ?",
                (new_balance, transaction.account_id)
            )
            conn.commit()
            return {
                "message": "Transaction successful",
                "new_balance": new_balance
            }
    except sqlite3.Error as e:
        logging.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/interest-rate")
async def get_interest_rate(month: str = None):
    try:
        with get_db() as conn:
            if month is None:
                month = datetime.now().strftime("%Y-%m")
            cursor = conn.execute(
                "SELECT rate FROM interest_rates WHERE month = ?",
                (month,)
            )
            result = cursor.fetchone()
            return {"rate": result['rate'] if result else 0.0}
    except sqlite3.Error as e:
        logging.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")

@app.put("/api/interest-rate")
async def update_interest_rate(rate: InterestRate, month: str = None):
    try:
        with get_db() as conn:
            if month is None:
                month = datetime.now().strftime("%Y-%m")
            conn.execute("""
                INSERT INTO interest_rates (rate, month)
                VALUES (?, ?)
                ON CONFLICT(month) DO UPDATE SET rate = excluded.rate
            """, (rate.rate, month))
            conn.commit()
            return {"message": "Interest rate updated successfully"}
    except sqlite3.Error as e:
        logging.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")

@app.post("/api/capitalize-interest")
async def capitalize_interest():
    try:
        with get_db() as conn:
            current_rate = get_current_interest_rate(conn) / 100
            cursor = conn.execute("SELECT id, balance FROM accounts")
            accounts = cursor.fetchall()
            for account in accounts:
                interest = account['balance'] * current_rate
                new_balance = account['balance'] + interest
                conn.execute(
                    "UPDATE accounts SET balance = ? WHERE id = ?",
                    (new_balance, account['id'])
                )
            conn.commit()
            return {"message": "Interest capitalized successfully"}
    except sqlite3.Error as e:
        logging.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")

def get_current_interest_rate(conn, month=None):
    if month is None:
        month = datetime.now().strftime("%Y-%m")
    cursor = conn.execute(
        "SELECT rate FROM interest_rates WHERE month = ?",
        (month,)
    )
    result = cursor.fetchone()
    return result['rate'] if result else 0.0

@app.on_event("startup")
async def start_scheduled_tasks():
    asyncio.create_task(scheduled_tasks())

@app.on_event("shutdown")
async def stop_scheduled_tasks():
    pass

async def scheduled_tasks():
    while True:
        now = datetime.now()
        if now.day == 1 and now.hour == 0:
            try:
                logging.info("Running scheduled monthly balance update")
                await update_monthly_balances()
                logging.info("Monthly balance update completed")
            except Exception as e:
                logging.error(f"Error in scheduled monthly balance update: {str(e)}")
        if now.day == 1 and now.hour == 1:
            try:
                logging.info("Running scheduled interest calculation")
                last_month = (now - timedelta(days=1)).strftime("%Y-%m")
                await calculate_all_interest(last_month)
                logging.info("Interest calculation completed")
            except Exception as e:
                logging.error(f"Error in scheduled interest calculation: {str(e)}")
        await asyncio.sleep(3600)

@app.post("/api/accounts/update-monthly-balances")
async def update_monthly_balances():
    try:
        current_month = datetime.now().strftime("%Y-%m")
        results = []
        with get_db() as conn:
            cursor = conn.execute("SELECT * FROM accounts")
            accounts = cursor.fetchall()
            for account in accounts:
                account_id = account['id']
                balance = float(account['balance'])
                cursor = conn.execute(
                    "SELECT * FROM monthly_balances WHERE account_id = ? AND month = ?",
                    (account_id, current_month)
                )
                existing = cursor.fetchone()
                if existing:
                    conn.execute(
                        "UPDATE monthly_balances SET balance = ? WHERE account_id = ? AND month = ?",
                        (balance, account_id, current_month)
                    )
                else:
                    conn.execute(
                        "INSERT INTO monthly_balances (account_id, month, balance) VALUES (?, ?, ?)",
                        (account_id, current_month, balance)
                    )
                results.append({
                    "account_id": account_id,
                    "month": current_month,
                    "balance": balance
                })
            conn.commit()
        return {"updated": len(results), "balances": results}
    except sqlite3.Error as e:
        logging.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")

@app.post("/api/calculate-all-interest")
async def calculate_all_interest(background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(process_all_interest)
        return {"message": "Interest calculation started in background"}
    except Exception as e:
        logging.error(f"Error starting interest calculation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def process_all_interest():
    try:
        with get_db() as conn:
            current_rate = get_current_interest_rate(conn) / 100
            cursor = conn.execute("SELECT id, balance FROM accounts")
            accounts = cursor.fetchall()
            for account in accounts:
                interest = account['balance'] * current_rate
                new_balance = account['balance'] + interest
                conn.execute(
                    "UPDATE accounts SET balance = ? WHERE id = ?",
                    (new_balance, account['id'])
                )
            conn.commit()
    except Exception as e:
        logging.error(f"Error calculating interest: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")