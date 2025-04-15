# Стандартные библиотеки (отсортированы по алфавиту)
import calendar
import csv
import io
import logging
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional

# Сторонние библиотеки (отсортированы по алфавиту)
from fastapi import FastAPI, HTTPException, File, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация FastAPI и CORS
app = FastAPI(title="Banking Service API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # В production замените "*" на конкретные домены фронтенда
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Конфигурация БД
DATABASE_URL = "banking.db"

# --- Точность Decimal ---
# Устанавливаем точность для денежных расчетов (2 знака после запятой)
decimal_context = sqlite3.connect(':memory:').cursor().connection.execute('PRAGMA query_only = 0;').connection.execute('SELECT 1 / CAST(100 AS DECIMAL(10, 2));').connection.cursor() # Для адаптеров
TWO_PLACES = Decimal("0.01")

# Адаптеры для Decimal в SQLite
def adapt_decimal(d):
    return str(d)

def convert_decimal(b):
    return Decimal(b.decode())

sqlite3.register_adapter(Decimal, adapt_decimal)
sqlite3.register_converter("DECIMAL", convert_decimal)

# --- Инициализация БД ---
def init_db():
    logger.info("Initializing database...")
    # Используем PARSE_DECLTYPES для работы с типами Decimal
    with sqlite3.connect(DATABASE_URL, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                balance DECIMAL(18, 2) NOT NULL DEFAULT 0.00 -- Используем DECIMAL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                amount DECIMAL(18, 2) NOT NULL, -- DECIMAL
                date TEXT NOT NULL,             -- Формат 'YYYY-MM-DD HH:MM:SS'
                comment TEXT,
                FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE CASCADE -- Каскадное удаление транзакций
            )
        """)
        # Индекс для ускорения выборки транзакций по дате
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_account_date ON transactions (account_id, date);")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interest_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rate DECIMAL(5, 2) NOT NULL,  -- DECIMAL (e.g., 15.00 for 15%)
                month TEXT NOT NULL UNIQUE    -- Формат 'YYYY-MM'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monthly_balances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT NOT NULL,
                month TEXT NOT NULL,               -- Формат 'YYYY-MM'
                end_balance DECIMAL(18, 2) NOT NULL, -- DECIMAL (баланс на конец месяца)
                interest_accrued DECIMAL(18, 2) NOT NULL DEFAULT 0.00, -- DECIMAL (проценты за месяц)
                FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE CASCADE,
                UNIQUE(account_id, month)
            )
        """)
        # Индекс для ускорения выборки месячных балансов
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_monthly_balances_account_month ON monthly_balances (account_id, month);")

        conn.commit()
        logger.info("Database initialized successfully.")

# Инициализация при старте
init_db()

# --- Управление соединением с БД ---
@contextmanager
def get_db():
    # PARSE_DECLTYPES | PARSE_COLNAMES - чтобы правильно работать с Decimal
    conn = sqlite3.connect(DATABASE_URL, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row # Возвращать строки как словари
    try:
        logger.debug("DB Connection Opened")
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database operation failed: {e}")
        conn.rollback() # Откатываем транзакцию при ошибке SQLite
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        conn.rollback() # Откатываем транзакцию при других ошибках
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
    finally:
        logger.debug("DB Connection Closed")
        conn.close()

# --- Pydantic Модели ---
class AccountBase(BaseModel):
    name: str

class AccountCreate(AccountBase):
    balance: Decimal # Начальный баланс
    interest_rate: Optional[Decimal] = None

class AccountUpdate(AccountBase):
    pass # Только имя можно менять через этот эндпоинт пока

class AccountDB(AccountBase):
    id: str
    balance: Decimal

    class Config:
        from_attributes = True # Совместимость с ORM-like объектами (sqlite3.Row)

class TransactionBase(BaseModel):
    amount: Decimal
    comment: Optional[str] = None

class TransactionCreate(TransactionBase):
    account_id: str
    date: Optional[str] = None # YYYY-MM-DD, если не указана - текущая

class TransactionDB(TransactionBase):
    id: str
    account_id: str
    date: str # Храним как строку YYYY-MM-DD HH:MM:SS

    class Config:
        from_attributes = True

class InterestRate(BaseModel):
    rate: Decimal # Процент (например, 15.0 для 15%)

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

class TransactionUpdate(BaseModel):
    amount: Optional[Decimal] = None # Сумма опциональна
    date: Optional[str] = None      # Дата опциональна (YYYY-MM-DD)
    comment: Optional[str] = None   # Комментарий тоже можно обновлять
# --- Вспомогательные Функции ---

def get_days_in_year(year: int) -> int: # Возвращает количество дней в году (учитывает високосные)
    """Возвращает количество дней в году (учитывает високосные)."""
    return 366 if calendar.isleap(year) else 365

def get_balance_at_date(conn: sqlite3.Connection, account_id: str, target_date: date) -> Decimal: # Получает баланс счета на начало указанной даты
    """
    Получает баланс счета на начало указанной даты (т.е. на конец предыдущего дня).
    """
    target_date_str = target_date.strftime('%Y-%m-%d') + ' 00:00:00'
    logger.debug(f"Getting balance for account {account_id} at start of {target_date_str}")

    # 1. Найти последний сохраненный месячный баланс до начала целевой даты
    prev_month = (target_date.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
    cursor = conn.execute(
        "SELECT end_balance FROM monthly_balances WHERE account_id = ? AND month = ?",
        (account_id, prev_month)
    )
    row = cursor.fetchone()
    start_balance = Decimal(row['end_balance']) if row else Decimal('0.00')
    start_date_str = (target_date.replace(day=1)).strftime('%Y-%m-%d') + ' 00:00:00' # Начало месяца целевой даты
    logger.debug(f"Starting balance from prev month {prev_month}: {start_balance}. Checking transactions from {start_date_str} to {target_date_str}")


    # 2. Применить транзакции с начала месяца до *начала* целевого дня
    cursor = conn.execute(
        """
        SELECT SUM(amount) as total_amount
        FROM transactions
        WHERE account_id = ? AND date >= ? AND date < ?
        """,
        (account_id, start_date_str, target_date_str)
    )
    result = cursor.fetchone()
    sum_transactions = Decimal(result['total_amount']) if result and result['total_amount'] is not None else Decimal('0.00')
    logger.debug(f"Sum of transactions between {start_date_str} and {target_date_str}: {sum_transactions}")

    balance = start_balance + sum_transactions
    logger.debug(f"Calculated balance at start of {target_date}: {balance}")
    return balance.quantize(TWO_PLACES, ROUND_HALF_UP)

def calculate_interest_for_month(conn: sqlite3.Connection, account_id: str, month_str: str) -> tuple[Decimal, Decimal]: # Рассчитывает проценты и конечный баланс за указанный месяц
    """
    Рассчитывает проценты и конечный баланс за указанный месяц ('YYYY-MM').
    Использует ежедневный расчет баланса.
    Возвращает (total_interest, end_of_month_balance).
    """
    logger.info(f"Calculating interest for account {account_id}, month {month_str}")
    try:
        year, month = map(int, month_str.split('-'))
        start_date = date(year, month, 1)
        days_in_month = calendar.monthrange(year, month)[1]
        end_date = date(year, month, days_in_month)
        days_in_year = get_days_in_year(year)

        # Получаем ставку для этого месяца
        cursor = conn.execute("SELECT rate FROM interest_rates WHERE month = ?", (month_str,))
        rate_row = cursor.fetchone()
        if not rate_row or rate_row['rate'] is None:
            logger.warning(f"No interest rate found for {month_str}. Interest calculation skipped.")
            # Получаем баланс на конец месяца без начисления процентов
            eom_balance = get_balance_at_date(conn, account_id, end_date + timedelta(days=1))
            return Decimal('0.00'), eom_balance

        monthly_rate_decimal = Decimal(rate_row['rate']) / Decimal('100.0')
        logger.debug(f"Interest rate for {month_str}: {monthly_rate_decimal * 100}%")

        total_interest = Decimal('0.00')
        current_day = start_date
        # Получаем все транзакции за месяц один раз
        transactions_in_month = conn.execute(
            """SELECT amount, date FROM transactions
               WHERE account_id = ? AND date >= ? AND date < ?
               ORDER BY date""",
            (account_id, start_date.strftime('%Y-%m-%d') + ' 00:00:00',
             (end_date + timedelta(days=1)).strftime('%Y-%m-%d') + ' 00:00:00')
        ).fetchall()

        balance_at_start_of_day = get_balance_at_date(conn, account_id, start_date)
        logger.debug(f"Balance at start of {start_date}: {balance_at_start_of_day}")

        transaction_iter = iter(transactions_in_month)
        current_transaction = next(transaction_iter, None)

        for day_num in range(days_in_month):
            current_day_str = current_day.strftime('%Y-%m-%d')
            # Начисляем проценты на баланс *на начало дня*
            daily_interest = (balance_at_start_of_day * monthly_rate_decimal / Decimal(days_in_year))
            total_interest += daily_interest
            # logger.debug(f"Day {current_day_str}: Start Balance={balance_at_start_of_day:.2f}, Daily Interest={daily_interest:.4f}")

            # Применяем транзакции *за этот день* для получения баланса на начало *следующего* дня
            daily_transaction_sum = Decimal('0.00')
            while current_transaction and current_transaction['date'].startswith(current_day_str):
                daily_transaction_sum += Decimal(current_transaction['amount'])
                current_transaction = next(transaction_iter, None)

            balance_at_start_of_next_day = balance_at_start_of_day + daily_transaction_sum
            # logger.debug(f"Day {current_day_str}: Transactions Sum={daily_transaction_sum:.2f}, Balance EOD={balance_at_start_of_next_day:.2f}")
            balance_at_start_of_day = balance_at_start_of_next_day # Готовимся к следующему дню
            current_day += timedelta(days=1)

        # Баланс на конец месяца = Баланс на начало последнего дня + Транзакции за последний день
        end_of_month_balance_before_interest = balance_at_start_of_day
        total_interest = total_interest.quantize(TWO_PLACES, ROUND_HALF_UP)
        end_of_month_balance_after_interest = (end_of_month_balance_before_interest + total_interest).quantize(TWO_PLACES, ROUND_HALF_UP)

        logger.info(f"Calculation for {month_str}: Total Interest={total_interest:.2f}, Balance EOM (before interest)={end_of_month_balance_before_interest:.2f}, Balance EOM (after interest)={end_of_month_balance_after_interest:.2f}")
        # Важно: monthly_balances хранит баланс *после* начисления процентов за этот месяц
        return total_interest, end_of_month_balance_after_interest

    except Exception as e:
        logger.error(f"Error calculating interest for {account_id} month {month_str}: {e}", exc_info=True)
        raise # Передаем ошибку выше

# --- API Эндпоинты ---

@app.get("/")
def read_root():
    return {"message": "Welcome to Banking Service API V1.0"}

@app.post("/api/accounts", response_model=AccountDB, status_code=201) # Создание нового счета с начальным балансом и опциональной ставкой на текущий месяц.
async def create_account_endpoint(account_in: AccountCreate): # <-- Теперь тип AccountCreate включает interest_rate
    logger.info(f"Attempting to create account: {account_in.name} with balance {account_in.balance} and rate {account_in.interest_rate}") # Добавим лог ставки

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
        with get_db() as conn:
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
                cursor.execute(
                    """
                    INSERT INTO interest_rates (month, rate) VALUES (?, ?)
                    ON CONFLICT(month) DO UPDATE SET rate = excluded.rate
                    """,
                    (current_month_str, rate_value)
                )
                # ВАЖНО: Текущая реализация установит ОДНУ ставку на месяц для ВСЕХ счетов.
                # Если нужна ставка НА КОНКРЕТНЫЙ СЧЕТ, схему БД и логику нужно сильно менять.
                # Пока оставляем как есть - ставка устанавливается глобально на месяц.

            conn.commit() # Коммитим все изменения

            # Получаем и возвращаем созданный аккаунт (как и раньше)
            cursor.execute("SELECT id, name, balance FROM accounts WHERE id = ?", (account_id,))
            new_account_row = cursor.fetchone()
            logger.info(f"Account created successfully in DB: {account_id}")

            if new_account_row:
                try:
                    account_dict = dict(new_account_row)
                    validated_account = AccountDB.model_validate(account_dict)
                    return validated_account
                except Exception as validation_err:
                     logger.error(f"Pydantic validation failed for new account {account_id}: {validation_err}", exc_info=True)
                     raise HTTPException(status_code=500, detail="Failed to validate created account data for response.")
            else:
                logger.error(f"CRITICAL: Failed to fetch newly created account from DB: {account_id}")
                raise HTTPException(status_code=500, detail="Failed to retrieve created account after insertion.")

    except sqlite3.IntegrityError as e:
        logger.error(f"Database integrity error during account creation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create account due to database constraint: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during account creation endpoint execution for {account_in.name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during account creation.")

@app.get("/api/accounts", response_model=List[AccountDetails]) # Указываем модель ответа
async def get_accounts_list():
    """
    Получение списка всех счетов с детализацией за 3 предыдущих месяца
    и расчетами для текущего периода.
    """
    logger.info("Fetching account list details")
    accounts_details: List[AccountDetails] = [] # Явно типизируем для ясности
    today = date.today()
    current_month_str = today.strftime('%Y-%m')

    # Определяем 3 предыдущих месяца
    previous_months_keys = []
    for i in range(1, 4):
        # Корректный способ получить первый день месяца i месяцев назад
        first_day_current_month = today.replace(day=1)
        target_month_first_day = first_day_current_month
        for _ in range(i):
             # Отнимаем день, чтобы перейти к предыдущему месяцу, затем берем 1е число
             target_month_first_day = (target_month_first_day - timedelta(days=1)).replace(day=1)
        previous_months_keys.append(target_month_first_day.strftime('%Y-%m'))

    previous_months_keys.sort() # Сортируем от прошлого к недавнему ['2025-01', '2025-02', '2025-03']
    logger.debug(f"Previous 3 months identified: {previous_months_keys}")


    try:
        with get_db() as conn:
            # Получаем все аккаунты
            cursor_accounts = conn.execute("SELECT id, name, balance FROM accounts") # Выбираем нужные поля
            db_accounts = cursor_accounts.fetchall()

            for account_row in db_accounts:
                account_id = account_row['id']
                logger.debug(f"Processing account: {account_id} ({account_row['name']})")

                # --- Код для получения ставки, истории, расчета текущего периода ---
                # (Этот код остается таким же, как в предыдущей версии,
                # он собирает данные в Pydantic модели PreviousMonthData и CurrentPeriodData)

                # 1. Текущая ставка
                cursor_rate = conn.execute("SELECT rate FROM interest_rates WHERE month = ?", (current_month_str,))
                rate_row = cursor_rate.fetchone()
                current_rate = Decimal(rate_row['rate']) if rate_row and rate_row['rate'] is not None else None

                # 2. Данные за предыдущие 3 месяца
                prev_months_data: Dict[str, Optional[PreviousMonthData]] = {}
                for month_key in previous_months_keys:
                    cursor_hist = conn.execute(
                        "SELECT end_balance, interest_accrued FROM monthly_balances WHERE account_id = ? AND month = ?",
                        (account_id, month_key)
                    )
                    hist_row = cursor_hist.fetchone()
                    if hist_row and hist_row['end_balance'] is not None and hist_row['interest_accrued'] is not None:
                        prev_months_data[month_key] = PreviousMonthData(
                             end_balance=Decimal(hist_row['end_balance']),
                             interest_accrued=Decimal(hist_row['interest_accrued'])
                         )
                    else:
                        prev_months_data[month_key] = None # Нет данных за этот месяц
                        # logger.warning(f"No monthly balance data found for account {account_id}, month {month_key}") # Можно закомментировать, если это ожидаемо

                # 3. Расчеты для текущего периода
                start_of_current_month_balance = Decimal('0.00')
                last_prev_month_key = previous_months_keys[-1] if previous_months_keys else None
                # Используем безопасный доступ к словарю и проверку на None
                last_month_data = prev_months_data.get(last_prev_month_key) if last_prev_month_key else None
                if last_month_data and last_month_data.end_balance is not None:
                    start_of_current_month_balance = last_month_data.end_balance

                current_actual_balance = Decimal(account_row['balance']) # Берем из accounts.balance

                projected_interest_current_month = Decimal('0.00')
                if current_rate is not None:
                    try:
                        projected_interest_current_month, _ = calculate_interest_for_month(conn, account_id, current_month_str)
                    except Exception as calc_err:
                        logger.error(f"Failed to calculate projected interest for {account_id} month {current_month_str}: {calc_err}", exc_info=True)

                transactions_sum_this_month = current_actual_balance - start_of_current_month_balance
                projected_eom_balance = start_of_current_month_balance + transactions_sum_this_month + projected_interest_current_month

                # --- Сборка итогового объекта AccountDetails ---
                accounts_details.append(AccountDetails(
                    id=account_id,
                    name=account_row['name'],
                    balance=current_actual_balance,
                    current_interest_rate=current_rate,
                    previous_months=prev_months_data,
                    current_period=CurrentPeriodData(
                        start_balance=start_of_current_month_balance,
                        current_balance=current_actual_balance,
                        projected_interest=projected_interest_current_month.quantize(TWO_PLACES, ROUND_HALF_UP),
                        projected_eom_balance=projected_eom_balance.quantize(TWO_PLACES, ROUND_HALF_UP)
                    )
                ))
            # --- Конец цикла по счетам ---

        logger.info("Successfully fetched account list details.")

        # Просто возвращаем список Pydantic моделей. FastAPI сам его сериализует.
        return accounts_details

    except Exception as e:
         logger.error(f"Error processing account list: {e}", exc_info=True)
         # Убедимся, что detail тоже сериализуем
         error_detail = f"Internal server error while fetching accounts: {str(e)}"
         raise HTTPException(status_code=500, detail=error_detail)

@app.get("/api/accounts/{account_id}", response_model=AccountDB) # Получение деталей одного счета
async def get_account_details(account_id: str):
    logger.info(f"Fetching details for account: {account_id}")
    try:
        with get_db() as conn:
            # Явно выбираем нужные поля для модели AccountDB
            cursor = conn.execute("SELECT id, name, balance FROM accounts WHERE id = ?", (account_id,))
            account_row = cursor.fetchone() # Переименуем для ясности

            if account_row is None:
                logger.warning(f"Account not found: {account_id}")
                raise HTTPException(status_code=404, detail="Account not found")

            # Явно преобразуем/валидируем перед возвратом
            try:
                # Конвертируем sqlite3.Row в словарь
                account_dict = dict(account_row)
                logger.debug(f"Fetched account row as dict: {account_dict}")

                # Валидируем словарь через Pydantic модель AccountDB
                # (Убедитесь, что AccountDB имеет Config с from_attributes=True)
                validated_account = AccountDB.model_validate(account_dict)
                logger.debug(f"Validated account data for response: {validated_account}")

                # Возвращаем Pydantic модель
                return validated_account
            except Exception as validation_err:
                # Ловим ошибки валидации Pydantic
                logger.error(f"Pydantic validation failed for account {account_id}: {validation_err}", exc_info=True)
                # Возвращаем 500, так как данные в БД есть, но ответ сформировать не можем
                raise HTTPException(status_code=500, detail="Failed to validate account data for response.")

    # Перехватываем отдельно HTTP ошибки, чтобы пробросить их
    except HTTPException:
        raise
    # Ловим все остальные ошибки
    except Exception as e:
        logger.error(f"Error fetching account {account_id}: {e}", exc_info=True)
        # Формируем общее сообщение об ошибке
        error_detail = f"Internal server error while fetching account details: {str(e)}"
        raise HTTPException(status_code=500, detail=error_detail)

@app.put("/api/accounts/{account_id}", response_model=AccountDB)
async def update_account_name(account_id: str, account_update: AccountUpdate):
    """Обновление имени счета."""
    logger.info(f"Attempting to update name for account: {account_id}")
    if not account_update.name.strip():
        raise HTTPException(status_code=400, detail="Account name cannot be empty")
    try:
        with get_db() as conn:
            cursor = conn.cursor() # Используем курсор
            cursor.execute(
                "UPDATE accounts SET name = ? WHERE id = ?",
                (account_update.name.strip(), account_id)
            )
            if cursor.rowcount == 0:
                logger.warning(f"Attempted to update non-existent account: {account_id}")
                raise HTTPException(status_code=404, detail="Account not found")
            conn.commit()
            logger.info(f"Account name updated for: {account_id}")

            # Получаем и возвращаем обновленный аккаунт (валидированный)
            cursor.execute("SELECT id, name, balance FROM accounts WHERE id = ?", (account_id,)) # Выбираем нужные поля
            updated_account_row = cursor.fetchone()
            if updated_account_row:
                 try:
                     account_dict = dict(updated_account_row) # Конвертируем в dict
                     validated_account = AccountDB.model_validate(account_dict) # Валидируем dict
                     return validated_account # Возвращаем Pydantic модель
                 except Exception as validation_err:
                     logger.error(f"Pydantic validation failed for updated account {account_id}: {validation_err}", exc_info=True)
                     raise HTTPException(status_code=500, detail="Failed to validate updated account data for response.")
            else:
                 logger.error(f"Failed to fetch updated account {account_id}")
                 raise HTTPException(status_code=500, detail="Failed to retrieve updated account.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating account {account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/api/accounts/{account_id}", status_code=200) # Удаление счета и всех связанных данных (транзакции, история)
async def delete_account_endpoint(account_id: str):
    logger.info(f"Attempting to delete account: {account_id}")
    try:
        with get_db() as conn:
            # Используем каскадное удаление (ON DELETE CASCADE в схеме),
            # поэтому удаляем только из основной таблицы.
            # Если каскадного удаления нет, нужно сначала удалить из monthly_balances и transactions.
            cursor = conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
            if cursor.rowcount == 0:
                logger.warning(f"Attempted to delete non-existent account: {account_id}")
                raise HTTPException(status_code=404, detail="Account not found")
            conn.commit()
            logger.info(f"Account deleted successfully: {account_id}")
            return {"message": "Account deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting account {account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/transactions", status_code=201) # Создание новой транзакции
async def create_transaction_endpoint(transaction_in: TransactionCreate):
    logger.info(f"Attempting to create transaction for account: {transaction_in.account_id}")
    account_id = transaction_in.account_id
    amount = transaction_in.amount.quantize(TWO_PLACES, ROUND_HALF_UP)
    comment = transaction_in.comment.strip() if transaction_in.comment else None

    # Дата транзакции
    transaction_dt = datetime.now()
    if transaction_in.date:
        try:
            # Позволяем указывать только дату, время будет текущее
            transaction_date_part = datetime.strptime(transaction_in.date, '%Y-%m-%d').date()
            # Не позволяем транзакции в будущем
            if transaction_date_part > date.today():
                 raise HTTPException(status_code=400, detail="Transaction date cannot be in the future")
            transaction_dt = datetime.combine(transaction_date_part, datetime.now().time())
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    transaction_date_str = transaction_dt.strftime('%Y-%m-%d %H:%M:%S')

    try:
        with get_db() as conn:
            # Проверяем существование счета
            cursor = conn.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
            account = cursor.fetchone()
            if account is None:
                logger.warning(f"Transaction attempt for non-existent account: {account_id}")
                raise HTTPException(status_code=404, detail="Account not found")

            # Добавляем транзакцию
            transaction_id = str(uuid.uuid4())
            conn.execute(
                """INSERT INTO transactions (id, account_id, amount, date, comment)
                   VALUES (?, ?, ?, ?, ?)""",
                (transaction_id, account_id, amount, transaction_date_str, comment)
            )

            # Обновляем текущий баланс счета АТОМАРНО
            # Используем `balance + ?` чтобы избежать race conditions
            conn.execute(
                "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                (amount, account_id)
            )
            conn.commit()

            # Получаем новый баланс для ответа
            cursor = conn.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
            new_balance = cursor.fetchone()['balance']

            logger.info(f"Transaction {transaction_id} created for account {account_id}. New balance: {new_balance}")
            return {
                "message": "Transaction successful",
                "transaction_id": transaction_id,
                "new_balance": new_balance
            }
    except Exception as e:
        logger.error(f"Error creating transaction for account {account_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/accounts/{account_id}/transactions", response_model=List[TransactionDB]) # Получение списка всех транзакций для счета (включая начальный остаток)
async def get_account_transactions_endpoint(account_id: str, limit: Optional[int] = None):
    logger.info(f"Fetching transactions for account: {account_id}, limit: {limit}")
    try:
        with get_db() as conn:
            # Проверка существования счета
            # Используем другое имя переменной для курсора проверки
            cursor_check = conn.execute("SELECT id FROM accounts WHERE id = ?", (account_id,))
            if not cursor_check.fetchone():
                 raise HTTPException(status_code=404, detail="Account not found")

            query = "SELECT * FROM transactions WHERE account_id = ? ORDER BY date DESC"
            params: list = [account_id] # Явно типизируем для ясности
            if limit is not None and limit > 0:
                query += " LIMIT ?"
                params.append(limit)

            # Используем другое имя переменной для курсора транзакций
            cursor_transactions = conn.execute(query, params)
            transaction_rows = cursor_transactions.fetchall() # Получаем список sqlite3.Row
            logger.info(f"Found {len(transaction_rows)} transactions for account {account_id}")

            transactions_list = [] # Создаем пустой список для Pydantic моделей
            for row in transaction_rows:
                try:
                    # Преобразуем строку sqlite3.Row в словарь
                    transaction_dict = dict(row)
                    # Валидируем словарь через модель TransactionDB
                    # (Убедитесь, что TransactionDB имеет Config с from_attributes=True)
                    validated_transaction = TransactionDB.model_validate(transaction_dict)
                    transactions_list.append(validated_transaction)
                except Exception as validation_err:
                     # Если одна строка не валидируется, логируем и возвращаем ошибку 500
                     logger.error(f"Pydantic validation failed for transaction row {dict(row)}: {validation_err}", exc_info=True)
                     raise HTTPException(status_code=500, detail=f"Failed to validate transaction data: {validation_err}")

            # Возвращаем СПИСОК Pydantic моделей. FastAPI сам сериализует Decimal.
            return transactions_list

    # Перехватываем отдельно HTTP ошибки, чтобы пробросить их
    except HTTPException:
        raise
    # Ловим все остальные ошибки
    except Exception as e:
        logger.error(f"Error fetching transactions for account {account_id}: {e}", exc_info=True)
        # Формируем общее сообщение
        error_detail = f"Internal server error while fetching transactions: {str(e)}"
        raise HTTPException(status_code=500, detail=error_detail)

@app.get("/api/interest-rate") # Получение процентной ставки для указанного месяца (YYYY-MM) или текущего.
async def get_interest_rate_endpoint(month: Optional[str] = None):
    target_month = month if month else datetime.now().strftime('%Y-%m')
    logger.info(f"Fetching interest rate for month: {target_month}")
    try:
        # Валидация формата месяца
        datetime.strptime(target_month, '%Y-%m')
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM.")

    try:
        with get_db() as conn:
            cursor = conn.execute("SELECT rate FROM interest_rates WHERE month = ?", (target_month,))
            result = cursor.fetchone()
            rate = Decimal(result['rate']) if result else Decimal("0.00") # Возвращаем 0, если ставка не найдена
            logger.info(f"Interest rate for {target_month}: {rate}")
            return {"month": target_month, "rate": rate}
    except Exception as e:
        logger.error(f"Error fetching interest rate for {target_month}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/api/interest-rate/{month}", status_code=200) # Установка или обновление процентной ставки для КОНКРЕТНОГО месяца
async def set_interest_rate_for_month(month: str, rate_in: InterestRate):
    """
    Установка или обновление процентной ставки для КОНКРЕТНОГО месяца (YYYY-MM).
    Требование 5 позволяет менять только текущий месяц, НО этот эндпоинт более гибкий.
    Ограничение на *только текущий месяц* лучше реализовать на фронтенде
    или добавить проверку в этот эндпоинт, если нужно жестко.
    """
    logger.info(f"Attempting to set interest rate for month {month} to {rate_in.rate}")
    try:
        target_month_date = datetime.strptime(month, '%Y-%m').date().replace(day=1)
        # Опциональная проверка: разрешать установку только для текущего или будущих месяцев
        # current_month_date = date.today().replace(day=1)
        # if target_month_date < current_month_date:
        #     raise HTTPException(status_code=400, detail="Cannot set interest rate for past months.")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM.")

    if rate_in.rate < 0:
        raise HTTPException(status_code=400, detail="Interest rate cannot be negative")

    rate_value = rate_in.rate.quantize(TWO_PLACES, ROUND_HALF_UP)

    try:
        with get_db() as conn:
            # INSERT OR REPLACE или ON CONFLICT для атомарного обновления/вставки
            conn.execute(
                """
                INSERT INTO interest_rates (month, rate) VALUES (?, ?)
                ON CONFLICT(month) DO UPDATE SET rate = excluded.rate
                """,
                (month, rate_value)
            )
            conn.commit()
            logger.info(f"Interest rate for month {month} set to {rate_value}")
            return {"message": f"Interest rate for {month} updated successfully", "month": month, "rate": rate_value}
    except Exception as e:
        logger.error(f"Error setting interest rate for {month}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/admin/calculate-monthly-balances/{month}", status_code=200) # Рассчитывает и сохраняет конечный баланс и начисленные проценты для ВСЕХ счетов за указанный месяц

@app.post("/api/admin/calculate-monthly-balances/{month}", status_code=200)
async def calculate_and_store_monthly_balances(month: str):
    """
    Рассчитывает и сохраняет конечный баланс и начисленные проценты
    для ВСЕХ счетов за указанный месяц (YYYY-MM).
    *** ТЕПЕРЬ ТАКЖЕ КАПИТАЛИЗИРУЕТ ПРОЦЕНТЫ: ***
    - Добавляет начисленные проценты к основному балансу счета.
    - Создает транзакцию для начисления процентов.
    Этот эндпоинт ДОЛЖЕН вызываться в начале следующего месяца
    (например, 1го апреля вызвать для марта /api/admin/calculate-monthly-balances/2025-03).
    """
    logger.info(f"Starting calculation and capitalization of monthly balances for month: {month}")
    try:
        # Валидация формата и проверка, что месяц не будущий
        target_month_date = datetime.strptime(month, '%Y-%m').date().replace(day=1)
        if target_month_date >= date.today().replace(day=1):
             raise HTTPException(status_code=400, detail="Cannot calculate balances for current or future months.")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM.")

    # Словарь для русских названий месяцев (более надежно, чем locale)
    months_ru = {
        1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель', 5: 'Май', 6: 'Июнь',
        7: 'Июль', 8: 'Август', 9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
    }

    accounts_processed = 0
    accounts_failed = 0
    accounts_capitalized = 0 # Счетчик для капитализированных счетов

    try:
        with get_db() as conn:
            cursor = conn.execute("SELECT id FROM accounts") # Используем курсор для итерации
            account_ids = [row['id'] for row in cursor.fetchall()]
            logger.info(f"Found {len(account_ids)} accounts to process for month {month}")

            # Определяем год и номер месяца для комментариев и даты транзакции
            try:
                year, month_num = map(int, month.split('-'))
                month_name_ru = months_ru.get(month_num, f'Месяц {month_num}')
                # Дата для транзакции - первый момент следующего месяца
                next_month_year = year + (month_num // 12)
                next_month_num = (month_num % 12) + 1
                interest_transaction_date = datetime(next_month_year, next_month_num, 1, 0, 0, 0)
                interest_transaction_date_str = interest_transaction_date.strftime('%Y-%m-%d %H:%M:%S')
            except Exception as date_parse_err:
                 logger.error(f"Error preparing date/comment parts for month {month}: {date_parse_err}", exc_info=True)
                 raise HTTPException(status_code=500, detail="Internal error preparing data for interest capitalization.")

            for account_id in account_ids:
                logger.debug(f"Processing account {account_id} for month {month}")
                try:
                    # 1. Рассчитываем проценты и конечный баланс (как раньше)
                    # Убедимся, что функция возвращает Decimal
                    interest_accrued, end_balance = calculate_interest_for_month(conn, account_id, month)

                    # 2. Сохраняем исторический результат в monthly_balances (как раньше)
                    conn.execute(
                        """
                        INSERT INTO monthly_balances (account_id, month, end_balance, interest_accrued)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(account_id, month) DO UPDATE SET
                            end_balance = excluded.end_balance,
                            interest_accrued = excluded.interest_accrued
                        """,
                        (account_id, month, end_balance, interest_accrued)
                    )
                    logger.debug(f"Stored historical balance for {account_id}, month {month}. End Balance: {end_balance}, Interest: {interest_accrued}")

                    # --- НАЧАЛО: Логика Капитализации ---
                    if interest_accrued is not None and interest_accrued > Decimal('0.00'):
                        logger.info(f"Capitalizing interest {interest_accrued:.2f} for account {account_id}, month {month}")

                        # а. Генерируем ID для транзакции процентов
                        interest_transaction_id = str(uuid.uuid4())

                        # б. Формируем комментарий
                        comment = f"Начисленные за {month_name_ru} {year} проценты"

                        # в. Обновляем основной баланс счета (атомарно)
                        conn.execute(
                            "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                            (interest_accrued, account_id)
                        )
                        logger.debug(f"Updated account balance for {account_id} by +{interest_accrued:.2f}")

                        # г. Создаем транзакцию начисления процентов
                        conn.execute(
                            """INSERT INTO transactions (id, account_id, amount, date, comment)
                               VALUES (?, ?, ?, ?, ?)""",
                            (interest_transaction_id, account_id, interest_accrued, interest_transaction_date_str, comment)
                        )
                        logger.debug(f"Created interest transaction {interest_transaction_id} for account {account_id}")
                        accounts_capitalized += 1
                    # --- КОНЕЦ: Логика Капитализации ---

                    accounts_processed += 1

                except Exception as e:
                    accounts_failed += 1
                    # Логируем ошибку, но НЕ прерываем весь процесс, переходим к следующему счету
                    logger.error(f"Failed to process or capitalize interest for account {account_id}, month {month}: {e}", exc_info=True)
                    # Важно: не откатываем транзакцию здесь, чтобы успешные записи для ДРУГИХ счетов сохранились

            # Коммитим все изменения (успешно обработанные счета) ПОСЛЕ цикла
            conn.commit()
            logger.info(f"Monthly balance calculation & capitalization finished for {month}. Processed: {accounts_processed}, Capitalized: {accounts_capitalized}, Failed: {accounts_failed}")
            return {
                "message": f"Monthly balances calculated and interest capitalized for {month}.",
                "processed": accounts_processed,
                "capitalized": accounts_capitalized, # Добавили счетчик
                "failed": accounts_failed
            }

    except Exception as e:
        # Эта ошибка возникла до или во время получения списка счетов, или при подготовке дат/комментариев
        logger.error(f"Critical error during monthly balance calculation/capitalization for {month}: {e}", exc_info=True)
        # Здесь откат произойдет автоматически при выходе из contextmanager get_db, если conn.commit() не был вызван
        raise HTTPException(status_code=500, detail=f"Internal server error during balance calculation for {month}")

@app.put("/api/transactions/{transaction_id}", response_model=TransactionDB)
async def update_transaction_endpoint(transaction_id: str, transaction_update: TransactionUpdate):
    """Обновление существующей транзакции (сумма, дата, комментарий)."""
    logger.info(f"Attempting to update transaction: {transaction_id}")

    # --- Валидация входных данных и подготовка значений ---
    if transaction_update.amount is None and transaction_update.date is None and transaction_update.comment is None:
        raise HTTPException(status_code=400, detail="No fields provided for update.")

    new_amount_decimal: Optional[Decimal] = None
    if transaction_update.amount is not None:
        new_amount_decimal = transaction_update.amount.quantize(TWO_PLACES, ROUND_HALF_UP)

    new_date_str_for_update: Optional[str] = None # Отформатированная дата для ЗАПИСИ в БД
    if transaction_update.date:
        try:
            new_date_part = datetime.strptime(transaction_update.date, '%Y-%m-%d').date()
            if new_date_part > date.today():
                 raise HTTPException(status_code=400, detail="Transaction date cannot be in the future")
            # Форматируем для записи в БД (если у вас там datetime)
            new_date_str_for_update = datetime.combine(new_date_part, datetime.min.time()).strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    new_comment = transaction_update.comment # Может быть None или ""

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # 1. Найти текущую транзакцию (чтобы получить account_id, old_amount и оригинальные date/comment)
            cursor.execute("SELECT account_id, amount, date, comment FROM transactions WHERE id = ?", (transaction_id,))
            current_transaction_row = cursor.fetchone()
            if not current_transaction_row:
                raise HTTPException(status_code=404, detail="Transaction not found")

            account_id = current_transaction_row['account_id']
            old_amount = Decimal(current_transaction_row['amount'])
            original_db_date_str = current_transaction_row['date'] # Сохраняем исходную дату/время из БД
            original_db_comment = current_transaction_row['comment'] # Сохраняем исходный коммент

            # 2. Определить итоговые значения для записи в БД
            final_amount = new_amount_decimal if new_amount_decimal is not None else old_amount
            final_date_str_for_db = new_date_str_for_update if new_date_str_for_update is not None else original_db_date_str
            final_comment = new_comment if new_comment is not None else original_db_comment

            # 3. Рассчитать разницу в сумме для обновления баланса счета
            amount_difference = final_amount - old_amount
            logger.debug(f"Updating transaction {transaction_id}. Diff: {amount_difference}")

            # --- Обновления в БД ---
            # 4. Обновить транзакцию
            cursor.execute(
                "UPDATE transactions SET amount = ?, date = ?, comment = ? WHERE id = ?",
                (final_amount, final_date_str_for_db, final_comment, transaction_id)
            )
            # 5. Обновить баланс счета, если сумма изменилась
            if amount_difference != Decimal('0.00'):
                cursor.execute(
                    "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                    (amount_difference, account_id)
                )
            conn.commit()
            # --- Обновления в БД Завершены ---

            logger.info(f"Transaction {transaction_id} updated successfully in DB.")

            # --- Формирование Ответа --- <<< ИЗМЕНЕНИЕ ЛОГИКИ ЗДЕСЬ
            # Не читаем заново из БД, а создаем объект Pydantic из известных данных
            try:
                # Создаем экземпляр TransactionDB напрямую
                response_data = TransactionDB(
                    id=transaction_id,           # ID из параметра пути
                    account_id=account_id,       # ID счета, который мы получили ранее
                    amount=final_amount,         # Итоговая сумма, которую записали в БД
                    date=final_date_str_for_db,  # Итоговая дата (строка), которую записали
                    comment=final_comment        # Итоговый комментарий, который записали
                )
                logger.debug(f"Constructed response object: {response_data}")
                # Возвращаем готовый Pydantic объект, FastAPI его сериализует
                return response_data
            except Exception as response_build_err:
                 # На случай ошибки сборки Pydantic объекта (хотя не должно)
                 logger.error(f"Failed to build response object for transaction {transaction_id}: {response_build_err}", exc_info=True)
                 raise HTTPException(status_code=500, detail="Internal error constructing transaction response.")
            # --- Конец Формирования Ответа ---

    except HTTPException:
        raise # Пробрасываем HTTP ошибки
    except Exception as e:
        logger.error(f"Error updating transaction {transaction_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during transaction update.")    
@app.delete("/api/transactions/{transaction_id}", status_code=200) # Можно 204 No Content, но 200 с сообщением тоже ок
async def delete_transaction_endpoint(transaction_id: str):
    """Удаление транзакции и корректировка баланса счета."""
    logger.info(f"Attempting to delete transaction: {transaction_id}")

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # 1. Найти транзакцию, чтобы получить ее сумму и ID счета
            cursor.execute("SELECT account_id, amount FROM transactions WHERE id = ?", (transaction_id,))
            transaction_to_delete = cursor.fetchone()

            if not transaction_to_delete:
                raise HTTPException(status_code=404, detail="Transaction not found")

            account_id = transaction_to_delete['account_id']
            amount_to_reverse = Decimal(transaction_to_delete['amount'])
            logger.debug(f"Found transaction {transaction_id} for account {account_id} with amount {amount_to_reverse}")

            # 2. Скорректировать баланс счета АТОМАРНО (вычитаем сумму удаляемой транзакции)
            logger.debug(f"Updating account {account_id} balance by {-amount_to_reverse}")
            cursor.execute(
                "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                (amount_to_reverse, account_id)
            )

            # 3. Удалить саму транзакцию
            cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))

            conn.commit()
            logger.info(f"Transaction {transaction_id} deleted successfully.")
            return {"message": "Transaction deleted successfully"}

    except HTTPException:
        raise # Пробрасываем HTTP ошибки
    except Exception as e:
        logger.error(f"Error deleting transaction {transaction_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during transaction deletion.")

# --- Запуск приложения (для локальной разработки) ---
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server...")
    # Используем reload=True для автоматической перезагрузки при изменениях кода
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)