import sqlite3

def check_database():
    try:
        # Подключение к БД
        conn = sqlite3.connect('banking.db')
        conn.row_factory = sqlite3.Row
        
        # Проверка таблицы accounts
        cursor = conn.execute("SELECT COUNT(*) as count FROM accounts")
        accounts_count = cursor.fetchone()['count']
        print(f"Количество счетов в БД: {accounts_count}")
        
        if accounts_count > 0:
            # Вывод первых 5 счетов
            cursor = conn.execute("SELECT id, name, balance FROM accounts LIMIT 5")
            accounts = cursor.fetchall()
            print("\nПримеры счетов:")
            for account in accounts:
                print(f"ID: {account['id']}, Имя: {account['name']}, Баланс: {account['balance']}")
        
        # Проверка других таблиц
        tables = ['transactions', 'interest_rates', 'monthly_balances']
        for table in tables:
            cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = cursor.fetchone()['count']
            print(f"Количество записей в таблице {table}: {count}")
        
        conn.close()
        print("\nПроверка БД завершена успешно.")
    except Exception as e:
        print(f"Ошибка при проверке БД: {e}")

if __name__ == "__main__":
    check_database()