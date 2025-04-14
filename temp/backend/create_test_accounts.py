import requests
import random
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

# Список тестовых счетов с кириллическими названиями
test_accounts = [
    {"name": "Основной счет", "balance": 50000.00},
    {"name": "Накопительный счет", "balance": 150000.00},
    {"name": "Кредитный счет", "balance": -25000.00},
    {"name": "Валютный счет", "balance": 75000.00},
    {"name": "Пенсионный счет", "balance": 300000.00},
    {"name": "Инвестиционный счет", "balance": 200000.00},
    {"name": "Сберегательный счет", "balance": 100000.00},
    {"name": "Корпоративный счет", "balance": 500000.00},
    {"name": "Счет для путешествий", "balance": 25000.00},
    {"name": "Счет для обучения", "balance": 150000.00}
]

def create_account(account_data):
    try:
        response = requests.post(
            f"{BASE_URL}/api/accounts",
            json=account_data,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            print(f"Счет '{account_data['name']}' успешно создан")
            return response.json()
        else:
            print(f"Ошибка при создании счета '{account_data['name']}': {response.text}")
    except Exception as e:
        print(f"Ошибка при создании счета '{account_data['name']}': {str(e)}")

def create_test_transactions(account_id, account_name, initial_balance):
    # Создаем транзакции за последние 3 месяца
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    current_date = start_date
    current_balance = initial_balance
    
    while current_date <= end_date:
        # Создаем случайную транзакцию
        amount = random.uniform(-10000, 10000)
        if current_balance + amount < 0:  # Не допускаем отрицательный баланс
            amount = -current_balance
        
        transaction_data = {
            "account_id": account_id,
            "amount": round(amount, 2),
            "date": current_date.strftime("%Y-%m-%d"),
            "comment": f"Тестовая транзакция для {account_name}"
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/transactions",
                json=transaction_data,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                current_balance += amount
                print(f"Транзакция для счета '{account_name}' создана: {amount} руб.")
            else:
                print(f"Ошибка при создании транзакции: {response.text}")
        except Exception as e:
            print(f"Ошибка при создании транзакции: {str(e)}")
        
        # Переходим к следующему дню
        current_date += timedelta(days=1)

def main():
    print("Создание тестовых счетов...")
    for account in test_accounts:
        result = create_account(account)
        if result and 'id' in result:
            print(f"Создание транзакций для счета '{account['name']}'...")
            create_test_transactions(result['id'], account['name'], account['balance'])
    
    print("Тестовые данные успешно созданы!")

if __name__ == "__main__":
    main() 