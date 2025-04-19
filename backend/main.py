# Standard libraries (keep these)
import logging
from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional, Union

# Third-party libraries (keep these)
from fastapi import FastAPI, HTTPException, File, UploadFile, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import sqlite3

# --- Project Modules ---
from .settings import settings, logger
from .database import init_db, get_db, TWO_PLACES
from .routers import transactions, interest_rates, accounts

# --- FastAPI App and CORS ---
app = FastAPI(
    title="Banking Service API",
    version="1.0.0",
    description="API for managing bank accounts, transactions, and interest calculations."
)

# Define the origins allowed to access your API
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:8081",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:8081",
    "http://172.16.173.94:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# Инициализация при старте
@app.on_event("startup")
def startup_db_client():
    """Initialize database on application startup"""
    logger.info("Initializing database on startup...")
    init_db()
    logger.info("Database initialization complete.")

# --- Include Routers ---
logger.info("Including API routers...")
app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(interest_rates.router)
logger.info("Routers included successfully.")

# --- Root Endpoint ---
@app.get("/", tags=["Root"])
def read_root():
    """Provides a simple welcome message."""
    logger.info("Root endpoint accessed.")
    return {"message": "Welcome to Banking Service API V1.0"}

@app.get("/api/health")
async def health_check():
    """Check if the application and database are working"""
    try:
        # Use the get_db dependency properly
        conn = None
        for db in get_db():  # This will properly handle the connection lifecycle
            conn = db
            # Try a simple query
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            if result and result[0] == 1:
                return {"status": "healthy", "database": "connected"}
            return {"status": "unhealthy", "database": "error"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

@app.exception_handler(sqlite3.Error)
async def sqlite_exception_handler(request: Request, exc: sqlite3.Error):
    logger.error(f"Caught SQLite error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": f"An internal database error occurred: {exc}"},
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Caught generic exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "An unexpected internal server error occurred."},
    )

# --- Main execution block (for direct run, though uvicorn is preferred) ---
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting application directly using uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
