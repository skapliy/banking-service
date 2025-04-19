from pydantic import BaseModel, Field
from decimal import Decimal
from typing import List, Dict, Optional

# --- Account Models ---
class AccountBase(BaseModel):
    name: str

# Add or update the AccountCreate model
# Update the AccountCreate model to match the frontend's field names
class AccountCreate(BaseModel):
    name: str
    initial_balance: Decimal  # Changed from 'balance' to 'initial_balance'
    interest_rate: Optional[Decimal] = None

class AccountUpdate(AccountBase):
    pass # Только имя можно менять

class AccountDB(AccountBase):
    id: str
    balance: Decimal

    class Config:
        from_attributes = True # For compatibility with ORM-like objects (sqlite3.Row)

# --- Transaction Models ---
class TransactionBase(BaseModel):
    amount: Decimal
    comment: Optional[str] = None

class TransactionCreate(TransactionBase):
    account_id: str
    date: Optional[str] = None # YYYY-MM-DD, defaults to current if None

class TransactionUpdate(BaseModel):
    amount: Optional[Decimal] = None
    date: Optional[str] = None # YYYY-MM-DD
    comment: Optional[str] = None

class TransactionDB(TransactionBase):
    id: str
    account_id: str
    date: str # Stored as 'YYYY-MM-DD HH:MM:SS' string

    class Config:
        from_attributes = True

# --- Interest Rate Models ---
class InterestRate(BaseModel):
    rate: Decimal # Percentage (e.g., 15.0 for 15%)

# --- Reporting/Detail Models ---
class PreviousMonthData(BaseModel):
    end_balance: Optional[Decimal] = None
    interest_accrued: Optional[Decimal] = None

class CurrentPeriodData(BaseModel):
    start_balance: Decimal
    current_balance: Decimal
    projected_interest: Decimal
    projected_eom_balance: Decimal

# Add this MonthlyDetail model to your models.py file
# Place it with your other Pydantic models

from decimal import Decimal
from typing import Dict, Optional
from pydantic import BaseModel, Field

class MonthlyDetail(BaseModel):
    """Monthly account details including balance and interest rate."""
    closing_balance: Optional[Decimal] = None
    interest_rate: Optional[Decimal] = None
    interest_earned: Optional[Decimal] = None

# Make sure your AccountDetails model includes the monthly_details field
class AccountDetails(AccountDB):
    """Extended account information with monthly details."""
    monthly_details: Dict[str, MonthlyDetail] = Field(default_factory=dict)
    current_period: CurrentPeriodData
    current_interest_rate: Optional[Decimal] = None # Add this field to hold the current rate
    # Make these fields optional with default values
    previous_months: Optional[Dict[str, Optional[PreviousMonthData]]] = Field(default_factory=dict)
    current_period: Optional[CurrentPeriodData] = None