from pydantic import BaseModel, Field
from decimal import Decimal
from typing import List, Dict, Optional

# --- Account Models ---
class AccountBase(BaseModel):
    name: str

class AccountCreate(AccountBase):
    balance: Decimal # Начальный баланс
    interest_rate: Optional[Decimal] = None # Опциональная ставка при создании

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

class AccountDetails(AccountDB):
    current_interest_rate: Optional[Decimal] = None
    previous_months: Dict[str, Optional[PreviousMonthData]] # {"YYYY-MM": PreviousMonthData | null}
    current_period: CurrentPeriodData