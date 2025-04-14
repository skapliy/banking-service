from datetime import datetime, timedelta
import uuid
import requests

# Базовый URL API
BASE_URL = "http://localhost:8000"

def create_account(name, initial_balance):
    """Создание нового счета"""
    account_data = {
        "id": str(uuid.uuid4()),  # Добавляем ID при создании
        "name": name,
        "balance": initial_balance,
        "monthly_balances": {},
        "interest_rates": {}
    }
    response = requests.post(f"{BASE_URL}/api/accounts", json=account_data)
    if response.status_code == 200:
        print(f"Создан счет: {name}")
        return account_data  # Возвращаем данные, которые мы отправили
    else:
        print(f"Ошибка при создании счета: {response.text}")
        return None

def add_transaction(account_id, amount, date, comment=""):
    """Добавление транзакции"""
    transaction_data = {
        "id": str(uuid.uuid4()),
        "account_id": account_id,
        "amount": amount,
        "date": date,
        "type": "deposit" if amount > 0 else "withdrawal"
    }
    response = requests.post(f"{BASE_URL}/api/accounts/{account_id}/transactions", json=transaction_data)
    if response.status_code == 200:
        print(f"Добавлена транзакция для счета {account_id}: {amount}")
        return True
    else:
        print(f"Ошибка при добавлении транзакции: {response.text}")
        return False

def set_interest_rate(month, rate):
    """Установка процентной ставки"""
    rate_data = {
        "month": month,
        "rate": rate
    }
    response = requests.post(f"{BASE_URL}/api/interest-rates", json=rate_data)
    if response.status_code == 200:
        print(f"Установлена ставка {rate}% за {month}")
        return True
    else:
        print(f"Ошибка при установке ставки: {response.text}")
        return False

def seed_database():
    """Заполнение базы данных тестовыми данными"""
    print("Создание счетов...")
    accounts = []
    for account_data in [
        ("Основной счет", 10000.0),
        ("Накопительный счет", 5000.0),
        ("Кредитный счет", -20000.0)
    ]:
        account = create_account(*account_data)
        if account:
            accounts.append(account)
    
    if not accounts:
        print("Не удалось создать счета. Прерываем заполнение базы.")
        return
    
    print("\nУстановка процентных ставок...")
    current_date = datetime.now()
    for i in range(6):
        month_date = current_date - timedelta(days=30*i)
        month_str = month_date.strftime("%Y-%m")
        rate = 5.0 + (i % 4) * 1.0
        set_interest_rate(month_str, rate)
    
    print("\nДобавление транзакций...")
    for account in accounts:
        print(f"\nОбработка счета: {account['name']}")
        for i in range(6):
            month_date = current_date - timedelta(days=30*i)
            month_str = month_date.strftime("%Y-%m")
            
            for j in range(3):
                transaction_date = month_date - timedelta(days=j*10)
                date_str = transaction_date.strftime("%Y-%m-%d")
                
                if "Основной" in account['name']:
                    amount = 1000.0 * (j + 1)
                elif "Накопительный" in account['name']:
                    amount = 500.0 * (j + 1)
                else:  # Кредитный счет
                    amount = -2000.0 * (j + 1)
                
                add_transaction(
                    account['id'],
                    amount,
                    date_str,
                    f"Транзакция {j+1} за {month_str}"
                )

if __name__ == "__main__":
    print("Начинаем заполнение базы данных...")
    seed_database()
    print("\nЗаполнение базы данных завершено!") 