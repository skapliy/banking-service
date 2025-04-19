# --- FastAPI Core ---
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- Project Modules ---
# Import settings first to ensure logging is configured early
from .settings import settings, logger
from .database import init_db # Import only the init function
from .routers import accounts, transactions, interest_rates # Import routers

# --- FastAPI App Setup ---
app = FastAPI(
    title="Banking Service API",
    version="1.0.0",
    description="API for managing bank accounts, transactions, and interest calculations."
)

# --- CORS Middleware ---
logger.info(f"Configuring CORS for origins: {settings.allowed_origins}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], # Added OPTIONS
    allow_headers=["*"], # Allow all standard headers
)

# --- Database Initialization ---
# Call init_db on startup to ensure tables exist
try:
    init_db()
except Exception as e:
    logger.critical(f"Database initialization failed: {e}. Application might not function correctly.", exc_info=True)
    # Depending on severity, you might want to exit here
    # import sys
    # sys.exit(1)

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

# --- Optional: Add startup/shutdown events if needed ---
# @app.on_event("startup")
# async def startup_event():
#     logger.info("Application startup...")
#     # Perform any startup tasks like connecting to external services

# @app.on_event("shutdown")
# def shutdown_event():
#     logger.info("Application shutdown.")
#     # Perform cleanup tasks

# --- Main execution block (for direct run, though uvicorn is preferred) ---
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting application directly using uvicorn...")
    # Note: Uvicorn reload doesn't work well with __main__ block.
    # Use `uvicorn main:app --reload` from the terminal instead.
    uvicorn.run(app, host="0.0.0.0", port=8000)
