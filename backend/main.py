from fastapi import FastAPI, HTTPException, File, UploadFile, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from typing import List, Dict, Optional
import csv
import io
import uuid
from datetime import datetime, timedelta
import logging
import sqlite3
import os
from contextlib import contextmanager
import calendar

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding='utf-8'),  # Указываем кодировку для файла логов
        logging.StreamHandler()          # Логи выводятся в консоль
    ]
)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins during development
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
    month: str  # Format: YYYY-MM
    balance: float
    interest_rate: float

class Account(BaseModel):
    id: str
    name: str
    balance: float
    initial_balance: float
    interest_rate: float = 0.0
    history: List[Transaction] = []
    monthly_balances: Dict[str, MonthlyBalance] = {}
    interest_rates: Dict[str, float] = {}

class AccountUpdate(BaseModel):
    name: str
    balance: float

class InterestRate(BaseModel):
    rate: float

# Global variables for interest rate
global_interest_rate = 0.0

# In-memory storage
accounts = {}
transactions = []
interest_rates = {}

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
            
            # Получаем транзакции за последние 3 месяца для каждого счета
            three_months_ago = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
            
            for account in accounts:
                # Получаем транзакции для счета
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
                
                # Рассчитываем месячные балансы и получаем процентные ставки
                monthly_balances = {}
                current_date = datetime.now()
                for i in range(3):
                    month_date = current_date - timedelta(days=30 * i)
                    month_key = month_date.strftime("%Y-%m")
                    
                    # Получаем процентную ставку для месяца
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

@app.get("/api/accounts/{account_id}")
async def get_account(account_id: str):
    """Get account by ID"""
    try:
        with get_db() as conn:
            cursor = conn.execute(
                "SELECT * FROM accounts WHERE id = ?",
                (account_id,)
            )
            account = cursor.fetchone()
            if account is None:
                raise HTTPException(status_code=404, detail="Account not found")
            return JSONResponse(
                content=dict(account),
                headers={"Content-Type": "application/json; charset=utf-8"}
            )
    except sqlite3.Error as e:
        logging.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")

@app.post("/api/accounts")
async def create_account(account: AccountUpdate):
    """Create a new account"""
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

            # Получаем созданный аккаунт
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
            # Проверяем существование счета
            cursor = conn.execute(
                "SELECT * FROM accounts WHERE id = ?",
                (transaction.account_id,)
            )
            account = cursor.fetchone()
            if account is None:
                raise HTTPException(status_code=404, detail="Account not found")
            
            # Проверяем дату
            transaction_date = datetime.strptime(transaction.date, "%Y-%m-%d").date()
            today = datetime.now().date()
            if transaction_date > today:
                raise HTTPException(status_code=400, detail="Transaction date cannot be in the future")
            
            # Создаем транзакцию
            transaction_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO transactions (id, account_id, amount, date, comment) VALUES (?, ?, ?, ?, ?)",
                (transaction_id, transaction.account_id, transaction.amount, transaction.date, transaction.comment)
            )
            
            # Обновляем баланс счета
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
        if rate.rate < 0:
            raise HTTPException(status_code=400, detail="Interest rate cannot be negative")
            
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
def capitalize_interest():
    global global_interest_rate
    try:
        with get_db() as conn:
            cursor = conn.execute("SELECT id, balance FROM accounts")
            accounts = cursor.fetchall()
            
            for account in accounts:
                interest = account['balance'] * global_interest_rate
                new_balance = account['balance'] + interest
                
                conn.execute(
                    "UPDATE accounts SET balance = ? WHERE id = ?",
                    (new_balance, account['id'])
                )
                
                # Записываем начисление процентов как транзакцию
                transaction_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO transactions (id, account_id, amount, type, date) VALUES (?, ?, ?, ?, ?)",
                    (transaction_id, account['id'], interest, 'interest', datetime.now().strftime('%Y-%m-%d'))
                )
            
            conn.commit()
            return {"message": "Interest capitalized successfully"}
    except sqlite3.Error as e:
        logging.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")

@app.get("/api/accounts/history")
def get_accounts_history():
    try:
        logging.debug("Fetching accounts history")
        today = datetime.now()
        last_three_months = [(today - timedelta(days=30 * i)).strftime("%Y-%m") for i in range(1, 4)]
        
        accounts_history = []
        for account in accounts.values():
            history_data = {}
            for month in last_three_months:
                record = next((h for h in account.history if h["date"].startswith(month)), None)
                history_data[month] = record["balance"] if record else "Нет данных"
            
            current_month = today.strftime("%Y-%m")
            current_record = next((h for h in account.history if h["date"].startswith(current_month)), None)
            current_balance = current_record["balance"] if current_record else account.balance
            interest_amount = current_balance * (global_interest_rate / 100)
            
            accounts_history.append({
                "id": account.id,
                "name": account.name,
                "history": history_data,
                "current_month": {
                    "balance": current_balance,
                    "balance_with_interest": current_balance + interest_amount
                }
            })
        
        logging.info("Accounts history fetched successfully")
        return accounts_history
    except Exception as e:
        logging.error(f"Error fetching accounts history: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/accounts/upload")
async def upload_accounts(file: UploadFile = File(...)):
    try:
        logging.debug(f"Received file: {file.filename}")
        if not file.content_type.startswith("text/csv"):
            raise HTTPException(status_code=400, detail="Invalid file type. Only CSV files are allowed.")
        
        content = await file.read()
        decoded_content = content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(decoded_content))
        
        created_accounts = []
        for row in reader:
            logging.debug(f"Processing row: {row}")
            if "name" not in row or "balance" not in row:
                raise HTTPException(status_code=400, detail=f"Missing required fields in row: {row}")
            
            # Проверяем корректность данных
            try:
                name = row["name"].strip()
                balance = float(row["balance"].strip())
            except ValueError:
                logging.warning(f"Skipping invalid row: {row}")
                continue
            
            if not name:
                logging.warning(f"Skipping row with empty name: {row}")
                continue
            if balance < 0:
                logging.warning(f"Skipping row with negative balance: {row}")
                continue
            
            account_id = str(uuid.uuid4())
            account = Account(
                id=account_id,
                name=name,
                balance=balance,
                initial_balance=balance
            )
            accounts[account_id] = account
            created_accounts.append(account)
        
        logging.info(f"Accounts uploaded successfully: {[a.dict() for a in created_accounts]}")
        return {"message": "Accounts uploaded successfully", "accounts": [account.dict() for account in created_accounts]}
    except Exception as e:
        logging.error(f"Error uploading accounts: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/accounts/report")
def get_account_report(account_id: str, date: str):
    try:
        logging.debug(f"Fetching account report for account_id={account_id}, date={date}")
        if account_id not in accounts:
            raise HTTPException(status_code=404, detail="Account not found")
        
        account = accounts[account_id]
        report_date = datetime.strptime(date, "%Y-%m-%d")
        
        closest_record = None
        for record in account.history:
            record_date = datetime.strptime(record["date"], "%Y-%m-%d")
            if record_date <= report_date and (not closest_record or record_date > closest_record["date"]):
                closest_record = record
        
        logging.info(f"Account report fetched successfully for account_id={account_id}")
        return {
            "date": date,
            "balance": closest_record["balance"] if closest_record else "Нет данных",
            "transactions": [t for t in transactions if t.account_id == account_id]
        }
    except Exception as e:
        logging.error(f"Error fetching account report: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/api/accounts/{account_id}")
async def update_account(account_id: str, account_update: AccountUpdate):
    try:
        with get_db() as conn:
            cursor = conn.execute(
                "SELECT * FROM accounts WHERE id = ?",
                (account_id,)
            )
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Account not found")

            conn.execute(
                "UPDATE accounts SET name = ? WHERE id = ?",
                (account_update.name, account_id)
            )
            conn.commit()

            # Получаем обновленный аккаунт
            cursor = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
            updated_account = dict(cursor.fetchone())
            
            return JSONResponse(
                content=updated_account,
                headers={"Content-Type": "application/json; charset=utf-8"}
            )
    except sqlite3.Error as e:
        logging.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")

def get_last_three_months():
    current_date = datetime.now()
    months = []
    for i in range(3, -1, -1):
        date = current_date - timedelta(days=30*i)
        months.append(date.strftime("%Y-%m"))
    return months

def calculate_future_balance(account: Account) -> float:
    current_date = datetime.now()
    days_in_month = calendar.monthrange(current_date.year, current_date.month)[1]
    days_remaining = days_in_month - current_date.day
    
    daily_interest = account.interest_rate / 365
    future_balance = account.balance * (1 + daily_interest) ** days_remaining
    
    return round(future_balance, 2)

def update_monthly_balance(account: Account):
    current_month = datetime.now().strftime("%Y-%m")
    if current_month not in account.monthly_balances:
        account.monthly_balances[current_month] = MonthlyBalance(
            month=current_month,
            balance=account.balance,
            interest_rate=account.interest_rate
        )
    else:
        account.monthly_balances[current_month].balance = account.balance
        account.monthly_balances[current_month].interest_rate = account.interest_rate

@app.get("/api/accounts/{account_id}/transactions")
async def get_account_transactions(account_id: str, limit: Optional[int] = None):
    """Get transactions for a specific account"""
    try:
        with get_db() as conn:
            # Проверяем существование счета
            cursor = conn.execute("SELECT id FROM accounts WHERE id = ?", (account_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Account not found")
            
            # Получаем транзакции из базы данных
            query = """
                SELECT * FROM transactions 
                WHERE account_id = ? 
                ORDER BY date DESC
            """
            params = [account_id]
            
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor = conn.execute(query, params)
            transactions = [dict(row) for row in cursor.fetchall()]
            
            return JSONResponse(
                content=transactions,
                headers={"Content-Type": "application/json; charset=utf-8"}
            )
            
    except sqlite3.Error as e:
        logging.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logging.error(f"Error getting transactions: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")