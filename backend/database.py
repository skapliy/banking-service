import sqlite3
import os
import logging
from contextlib import contextmanager
from decimal import Decimal
from .settings import settings

logger = logging.getLogger(__name__)

DATABASE_URL = settings.database_url
IS_SQLITE = DATABASE_URL.startswith("sqlite")
TWO_PLACES = Decimal("0.01")

# Адаптеры для Decimal в SQLite
def adapt_decimal(d: Decimal) -> str:
    """Adapts Decimal to string for SQLite."""
    return str(d)

def convert_decimal(b: bytes) -> Decimal:
    """Converts string from SQLite back to Decimal."""
    return Decimal(b.decode())

# Register adapters only if using SQLite
if IS_SQLITE:
    sqlite3.register_adapter(Decimal, adapt_decimal)
    sqlite3.register_converter("DECIMAL", convert_decimal)
    logger.info("Registered Decimal adapters for SQLite.")

def init_db():
    """Initializes the database schema if using SQLite."""
    logger.info(f"Attempting database initialization using URL: {DATABASE_URL}")
    if not IS_SQLITE:
        logger.warning("Database initialization logic is specific to SQLite. Skipping.")
        return

    db_path = DATABASE_URL.split("sqlite:///")[-1]
    logger.info(f"Extracted SQLite database path: {db_path}")

    if db_path == ':memory:':
        logger.info("Using in-memory SQLite database.")
    else:
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"Ensured database directory exists: {db_dir}")
            except OSError as e:
                 logger.error(f"Failed to create database directory '{db_dir}': {e}", exc_info=True)
                 raise

    try:
        # Add check_same_thread=False to allow SQLite to be used across threads
        with sqlite3.connect(
            db_path, 
            detect_types=sqlite3.PARSE_DECLTYPES,
            check_same_thread=False
        ) as conn:
            cursor = conn.cursor()
            # Create Accounts Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    balance DECIMAL(18, 2) NOT NULL DEFAULT 0.00
                )
            """)
            # Create Transactions Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    amount DECIMAL(18, 2) NOT NULL,
                    date TEXT NOT NULL, -- Format 'YYYY-MM-DD HH:MM:SS'
                    comment TEXT,
                    FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_account_date ON transactions (account_id, date);")
            # Create Interest Rates Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interest_rates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rate DECIMAL(5, 2) NOT NULL,
                    month TEXT NOT NULL UNIQUE -- Format 'YYYY-MM'
                )
            """)
            # Create Monthly Balances Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS monthly_balances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT NOT NULL,
                    month TEXT NOT NULL, -- Format 'YYYY-MM'
                    end_balance DECIMAL(18, 2) NOT NULL,
                    interest_accrued DECIMAL(18, 2) NOT NULL DEFAULT 0.00,
                    FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE CASCADE,
                    UNIQUE(account_id, month)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_monthly_balances_account_month ON monthly_balances (account_id, month);")
            conn.commit()
            logger.info("Database schema initialized/verified successfully.")
    except sqlite3.Error as e:
        logger.error(f"SQLite error during DB initialization at path '{db_path}': {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error during DB initialization at path '{db_path}': {e}", exc_info=True)
        raise

def get_db():
    """FastAPI dependency to get a DB connection per request."""
    conn = None
    db_path = DATABASE_URL.replace("sqlite:///", "")
    
    try:
        # Ensure directory exists
        if db_path != ":memory:":
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                logger.info(f"Database directory '{db_dir}' not found, creating it.")
                os.makedirs(db_dir, exist_ok=True)

        logger.debug(f"Attempting to connect to SQLite DB at: {db_path}")
        
        # The critical fix: add check_same_thread=False to allow cross-thread usage
        conn = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES,
            check_same_thread=False  # This is the key change
        )
        conn.row_factory = sqlite3.Row
        logger.debug(f"SQLite DB Connection Opened to: {db_path}")
        
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Error connecting to database at {db_path}: {e}", exc_info=True)
        raise
    finally:
        if conn:
            try:
                conn.close()
                logger.debug(f"SQLite DB Connection Closed for: {db_path}")
            except sqlite3.Error as e:
                logger.error(f"Error closing DB connection for {db_path}: {e}", exc_info=True)

# Keep the contextmanager version if it's used elsewhere in your code
@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = None
    db_path = DATABASE_URL.replace("sqlite:///", "")
    
    try:
        conn = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        yield conn
    finally:
        if conn:
            conn.close()