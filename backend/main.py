# Standard libraries (keep these)
import logging # <<< ADD THIS LINE
from datetime import datetime, timedelta, date # Keep needed ones
from decimal import Decimal, ROUND_HALF_UP # <<< Import ROUND_HALF_UP directly from decimal
from typing import List, Dict, Optional, Union # Keep needed ones

# Third-party libraries (keep these)
from fastapi import FastAPI, HTTPException, File, UploadFile, Depends # Keep needed ones
from fastapi.middleware.cors import CORSMiddleware # Keep
from fastapi.responses import JSONResponse # Keep if used elsewhere
from pydantic import BaseModel, Field # Keep if used elsewhere
from pydantic_settings import BaseSettings # Keep
from fastapi import Request
from fastapi.responses import JSONResponse
import sqlite3 # Или другой тип ошибки

# --- Project Modules ---
# Import settings first to ensure logging is configured early
from .settings import settings, logger # Keep
# <<< REMOVE ROUND_HALF_UP from this import >>>
from .database import init_db, get_db, TWO_PLACES # Keep get_db and constants if used by other routers
# --- REMOVE accounts from here if it was imported ---
from .routers import transactions, interest_rates # Keep other routers
# --- ADD import for the new accounts router ---
from .routers import accounts # <<< ADD THIS LINE

# --- Settings Management ---
# ... (Settings class definition should be in settings.py) ...

# --- Logging Configuration ---
# ... (Logging setup should use the imported 'settings' instance) ...
# Now this line will work because 'logging' is imported
logger = logging.getLogger(__name__)

# --- FastAPI App and CORS ---
app = FastAPI(
    title="Banking Service API",
    version="1.0.0",
    description="API for managing bank accounts, transactions, and interest calculations."
)

# <<< ADD CORS MIDDLEWARE CONFIGURATION HERE >>>
# Define the origins allowed to access your API
# Use "*" for development to allow all origins, or specify your frontend origin
origins = [
    "http://localhost:8080",  # Example: Common local frontend dev server
    "http://127.0.0.1:8080", # Example: Another local frontend dev server
    "http://172.16.173.94:8080", # Your specific frontend origin from the error
    # Add any other origins you need to allow
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of allowed origins
    allow_credentials=True, # Allow cookies
    allow_methods=["*"],    # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],    # Allow all headers
)
# <<< END OF CORS MIDDLEWARE CONFIGURATION >>>


# --- Database Configuration & Initialization ---
# ... (DATABASE_URL, IS_SQLITE, adapt_decimal, register_adapter, init_db call) ...

# --- Pydantic Models ---
# --- MOVE ALL Pydantic models (AccountCreate, AccountDB, etc.) to backend/models.py ---
# <<< REMOVE ALL Pydantic model definitions from here >>>

# --- Helper Functions / Services ---
# --- MOVE helper functions (like calculate_interest_for_month) to backend/services.py ---
# <<< REMOVE helper function definitions from here >>>


# --- API Endpoints ---

# --- REMOVE ALL @app.post("/api/accounts", ...), @app.get("/api/accounts", ...), etc. ---
# <<< REMOVE create_account function definition >>>
# <<< REMOVE get_accounts_list function definition >>>
# <<< REMOVE get_account_details function definition >>>
# <<< REMOVE update_account_name function definition >>>
# <<< REMOVE delete_account_endpoint function definition >>>
# <<< REMOVE get_account_transactions_endpoint function definition >>>

# --- KEEP Endpoints for Transactions (if they are still here) ---
# @app.post("/api/transactions", ...)
# ... etc ...
# --- Ideally, move these to backend/routers/transactions.py ---

# --- KEEP Endpoints for Interest Rates (if they are still here) ---
# @app.get("/api/interest-rate", ...)
# @app.put("/api/interest-rate/{month}", ...)
# @app.post("/api/admin/calculate-monthly-balances/{month}", ...)
# --- Ideally, move these to backend/routers/interest_rates.py ---

# --- KEEP Endpoints for File Uploads (if they are still here) ---
# @app.post("/api/admin/upload-transactions", ...)
# --- Ideally, move this to a separate admin router or transactions router ---


# --- Include Routers ---
logger.info("Including API routers...")
app.include_router(accounts.router) # <<< ADD THIS LINE
app.include_router(transactions.router) # Keep if using transactions router
app.include_router(interest_rates.router) # Keep if using interest_rates router
# --- Include other routers if you create them (e.g., admin) ---
logger.info("Routers included successfully.")


# --- Root Endpoint ---
@app.get("/", tags=["Root"])
def read_root():
    """Provides a simple welcome message."""
    logger.info("Root endpoint accessed.")
    return {"message": "Welcome to Banking Service API V1.0"}

# --- Optional: Add startup/shutdown events if needed ---
# ... (startup/shutdown events) ...

# --- Main execution block (for direct run, though uvicorn is preferred) ---
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting application directly using uvicorn...")
    # Use the format expected by uvicorn when running directly
    # Note: reload doesn't work reliably this way. Use terminal command.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) # Keep reload=True if desired for this direct run method


@app.exception_handler(sqlite3.Error)
async def sqlite_exception_handler(request: Request, exc: sqlite3.Error):
    logger.error(f"Caught SQLite error: {exc}", exc_info=True) # Логируем полную ошибку
    # Возвращаем клиенту общее сообщение
    return JSONResponse(
        status_code=500,
        content={"message": f"An internal database error occurred: {exc}"}, # Осторожно с выводом деталей!
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Caught generic exception: {exc}", exc_info=True) # This logs the real error
    # This is the response you are seeing:
    return JSONResponse(
        status_code=500,
        content={"message": "An unexpected internal server error occurred."},
    )
