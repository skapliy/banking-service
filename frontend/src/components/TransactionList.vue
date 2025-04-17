<template>
  <div class="transaction-list">
    <div class="header">
      <h3>{{ accountName }}</h3>
    </div>

    <div v-if="loading" class="loading">Загрузка...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="transactions.length === 0" class="no-transactions">Нет транзакций</div>

    <div v-else class="transactions-table-container">
      <table class="transactions-table">
        <thead>
          <tr>
            <th>Дата</th>
            <th>Сумма</th>
            <th>Комментарий</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="tx in transactions" :key="tx.id">

            <template v-if="editingTransactionId !== tx.id">
              <td>{{ formatDateForDisplay(tx.date) }}</td>
              <td :class="{ 'deposit': tx.amount > 0, 'withdrawal': tx.amount < 0 }">
                  {{ formatCurrency(tx.amount)}} 
              </td>
              <td>{{ tx.comment }}</td>
              <td>
                <template v-if="tx.comment !== 'Начальный остаток'">
                  <button @click="startEdit(tx)" title="Редактировать" class="edit-btn">✏️</button>
                  <button @click="confirmDelete(tx.id)" title="Удалить" class="delete-btn">🗑️</button>
                </template>
              </td>
            </template>

            <template v-else>
              <td>
                <input type="date" v-model="editData.date" class="edit-input edit-date">
              </td>
              <td>
                <input type="number" step="0.01" v-model.number="editData.amount" class="edit-input edit-amount">
              </td>
              <td>
                <input type="text" v-model="editData.comment" class="edit-input edit-comment" placeholder="Комментарий">
              </td>
              <td>
                <button @click="saveEdit(tx.id)" title="Сохранить" class="save-btn">✔️</button>
                <button @click="cancelEdit" title="Отмена" class="cancel-btn">❌</button>
              </td>
            </template>

          </tr>
        </tbody>
      </table>
    </div>
    <p v-if="actionError" class="error action-error">{{ actionError }}</p>
  </div>
</template>

<script>
import axios from '../axios-config'; // Убедитесь, что путь правильный

export default {
  name: 'TransactionList', // Добавим имя компоненту
  props: {
    accountId: {
      type: String,
      required: true
    },
    accountName: {
      type: String,
      required: true
    }
    // interestRate: Number // Можно передавать ставку пропсом из AccountList, если нужно
  },
  data() {
    return {
      transactions: [],
      loading: true,
      error: null, // Ошибка загрузки
      actionError: null, // Ошибка при редактировании/удалении
      // interestRate: 0, // Получаем из accountId запросом или через props

      // --- Состояние для редактирования ---
      editingTransactionId: null, // ID транзакции в режиме редактирования
      editData: {               // Временные данные для полей ввода
        amount: 0,
        date: '', // Формат YYYY-MM-DD
        comment: ''
      },
      originalTransactionData: null // Храним оригинал для сравнения и отмены
      // --- Конец состояния для редактирования ---
    };
  },
  methods: {
    // --- Загрузка данных ---
    async fetchTransactions() {
      this.loading = true;
      this.error = null;
      this.actionError = null; // Сбрасываем ошибки действий
      console.log(`Workspaceing transactions for account ${this.accountId}`);
      try {
        // Загружаем только транзакции, ставка не нужна здесь (есть в AccountList)
        const response = await axios.get(`/api/accounts/${this.accountId}/transactions`);
        // Сортируем по дате от старых к новым для вида "выписки"
        this.transactions = response.data.sort((a, b) => new Date(a.date) - new Date(b.date));
        console.log("Transactions loaded:", this.transactions);
      } catch (error) {
        console.error("Error fetching transactions:", error);
        this.error = 'Ошибка загрузки транзакций: ' + (error.response?.data?.detail || error.message);
        this.transactions = []; // Очищаем на случай ошибки
      } finally {
        this.loading = false;
      }
    },

    // --- Форматирование ---
    formatDateForDisplay(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        // Формат для отображения
        return date.toLocaleDateString('ru-RU', {
          year: 'numeric', month: 'numeric', day: 'numeric' // Краткий формат даты
        });
    },
    formatDateForInput(dateString) {
        if (!dateString) return '';
        // Преобразуем 'YYYY-MM-DD HH:MM:SS' в 'YYYY-MM-DD' для input type="date"
        return dateString.substring(0, 10);
    },
    formatCurrency(amount) {
        const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
        if (numAmount === undefined || numAmount === null || isNaN(numAmount)) return '0.00'; // Или "-"
        return new Intl.NumberFormat('ru-RU', {
            style: 'decimal',                          // Обычный числовой формат
            minimumFractionDigits: 2,                  // Всегда отображаем 2 знака после запятой
            maximumFractionDigits: 2,                  // Максимум 2 знака после запятой
            useGrouping: true                          // Включаем группировку разрядов (1 234 567,89)
        }).format(numAmount);
    },

    // --- Методы Редактирования ---
    startEdit(transaction) {
      console.log("Starting edit for:", transaction);
      this.originalTransactionData = { ...transaction }; // Копируем оригинал
      this.editingTransactionId = transaction.id;
      // Преобразуем данные для формы
      this.editData.amount = parseFloat(transaction.amount);
      this.editData.date = this.formatDateForInput(transaction.date); // YYYY-MM-DD
      this.editData.comment = transaction.comment || ''; // Пустая строка если null
      this.actionError = null; // Сбрасываем ошибку
    },
    cancelEdit() {
      this.editingTransactionId = null;
      this.originalTransactionData = null; // Очищаем оригинал
      this.actionError = null;
    },
    async saveEdit(txId) {
      if (!this.editingTransactionId || this.editingTransactionId !== txId) return;
      this.actionError = null;

      // Формируем payload ТОЛЬКО с измененными данными
      const payload = {};
      const originalAmount = parseFloat(this.originalTransactionData.amount).toFixed(2);
      const editedAmount = parseFloat(this.editData.amount).toFixed(2);
      const originalDate = this.formatDateForInput(this.originalTransactionData.date);
      const editedDate = this.editData.date;
      const originalComment = this.originalTransactionData.comment || '';
      const editedComment = this.editData.comment || '';

      if (originalAmount !== editedAmount) {
         // Валидация суммы (если нужно)
        if (isNaN(parseFloat(this.editData.amount))) {
             this.actionError = "Некорректная сумма"; return;
        }
        payload.amount = parseFloat(this.editData.amount);
      }
      if (originalDate !== editedDate) {
         // Валидация даты
         if (!this.editData.date || isNaN(new Date(this.editData.date).getTime())) {
              this.actionError = "Некорректная дата"; return;
         }
         if (new Date(this.editData.date) > new Date()) {
              this.actionError = "Дата не может быть в будущем"; return;
         }
        payload.date = this.editData.date; // Отправляем YYYY-MM-DD
      }
      if (originalComment !== editedComment) {
        payload.comment = editedComment; // Отправляем новый коммент (может быть пустой строкой)
      }

      // Если ничего не изменилось, просто отменяем редактирование
      if (Object.keys(payload).length === 0) {
        this.cancelEdit();
        return;
      }

      console.log(`Saving transaction ${txId} with payload:`, payload);
      try {
        await axios.put(`/api/transactions/${txId}`, payload);
        this.cancelEdit(); // Выход из режима редактирования
        await this.fetchTransactions(); // Обновляем список транзакций
        this.$emit('transactions-updated'); // <<--- СООБЩАЕМ РОДИТЕЛЮ!
        console.log(`Transaction ${txId} saved.`);
      } catch (err) {
        console.error("Error saving transaction:", err);
        this.actionError = "Ошибка сохранения: " + (err.response?.data?.detail || err.message);
      }
    },

    // --- Метод Удаления ---
    async confirmDelete(txId) {
       this.actionError = null;
      if (confirm(`Удалить транзакцию ID: ${txId}? \n\nВНИМАНИЕ: Это действие необратимо и изменит баланс счета!`)) {
        console.log(`Attempting to delete transaction ${txId}`);
        try {
            await axios.delete(`/api/transactions/${txId}`);
            console.log(`Transaction ${txId} deleted.`);
            await this.fetchTransactions(); // Обновляем список транзакций
            this.$emit('transactions-updated'); // <<--- СООБЩАЕМ РОДИТЕЛЮ!
         } catch (err) {
             console.error("Error deleting transaction:", err);
             // Отображаем ошибку пользователю
             this.actionError = "Ошибка удаления: " + (err.response?.data?.detail || err.message);
             // Не скрываем ошибку сразу, даем пользователю увидеть
         }
      }
    }
  },
  watch: {
     // Перезагружаем транзакции при смене ID аккаунта
    accountId: {
        immediate: true, // Загрузить сразу при создании/показе компонента
        handler(newId) {
            if (newId) {
                this.fetchTransactions();
            } else {
                this.transactions = [];
            }
        }
    }
  }
};
</script>

<style scoped>
/* Общие стили компонента TransactionList */
.transaction-list {
  /* Убираем стили контейнера, так как он встраивается */
  background-color: transparent;
  border-radius: 0;
  padding: 0;
  box-shadow: none;
  max-width: 100%;
  margin: 0;
}

/* Заголовок внутри TransactionList (можно скрыть, если имя счета видно в AccountList) */
.header {
  /* display: none; */ /* Раскомментируйте, чтобы скрыть */
  margin-bottom: 5px;
  padding-bottom: 5px;
  border-bottom: none; /* Линия не нужна, если скрыт или если есть рамка у контейнера таблицы */
}
.header h3 {
  margin: 0;
  font-size: 1.0em; /* Можно сделать чуть меньше, если заголовок остается */
  font-weight: 600;
  color: #333;
}

/* Сообщения о статусе загрузки */
.loading, .error, .no-transactions {
  text-align: center;
  padding: 15px;
  font-size: 0.95em;
  color: #6c757d; /* Более нейтральный цвет для информации */
}
.error, .action-error { /* Ошибки выделяем */
  color: #dc3545;
}
.action-error {
  font-size: 0.9em;
  text-align: center;
  margin-top: 10px;
}

/* Контейнер таблицы с прокруткой */
.transactions-table-container {
  max-height: 350px;   /* Макс. высота ~10 строк, ПОДБЕРИТЕ ТОЧНЕЕ под высоту строки */
  overflow-y: auto;    /* Включаем скролл, если строк больше */
  padding-right: 5px;  /* Небольшой отступ справа для скроллбара */
  /* border-top: 1px solid #eee; */ /* Рамка сверху, если нужно визуально отделить от заголовка (если он есть) */
}

/* Стили самой таблицы */
.transactions-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9em;
}

/* Заголовки таблицы (прилипающие) */
.transactions-table th {
    background-color: #f8f9fa; /* Светлый фон для заголовков */
    font-weight: 600;
    padding: 8px 10px;
    text-align: left;
    vertical-align: middle;
    position: sticky;   /* Заголовок остается при прокрутке */
    top: 0;             /* Прилипает к верху контейнера .transactions-table-container */
    z-index: 1;
    border-bottom: 2px solid #dee2e6; /* Более заметная нижняя граница для заголовков */
}

/* Ячейки таблицы */
.transactions-table td {
    border-bottom: 1px solid #eee; /* Разделитель строк */
    padding: 8px 10px;
    text-align: left;
    vertical-align: middle;
}

/* Стилизация отдельных столбцов */
.transactions-table td:nth-child(2) { /* Сумма */
    text-align: right;
    font-weight: 500;
    min-width: 100px; /* Чтобы сумма не переносилась */
    white-space: nowrap;
}
.transactions-table td:nth-child(3) { /* Комментарий */
    color: #555;
    word-break: break-word; /* Перенос длинных комментариев */
    min-width: 150px; /* Дать больше места комментарию */
}
.transactions-table td:nth-child(4) { /* Действия */
    text-align: center;
    white-space: nowrap; /* Кнопки в одну строку */
    width: 80px; /* Фиксированная ширина для кнопок */
}

/* Стили для кнопок действий (редактировать, удалить, сохранить, отмена) */
.transactions-table button {
    background: none;
    border: none;
    cursor: pointer;
    padding: 2px 4px;
    margin: 0 2px;
    font-size: 1.1em; /* Размер иконок */
    border-radius: 3px;
    vertical-align: middle; /* Выравнивание иконок по центру строки */
    transition: background-color 0.15s ease-in-out; /* Плавность при наведении */
}
.transactions-table button:hover {
    background-color: #e9ecef; /* Фон при наведении чуть темнее */
}
.edit-btn { color: #007bff; }
.delete-btn { color: #dc3545; }
.save-btn { color: #28a745; }
.cancel-btn { color: #6c757d; }

/* Стили для полей ввода в режиме редактирования */
.edit-input {
    width: 100%;
    padding: 4px 6px;
    border: 1px solid #ccc;
    border-radius: 3px;
    font-size: inherit; /* Наследуем размер шрифта ячейки */
    box-sizing: border-box; /* Учитываем padding и border в ширине */
}
.edit-amount {
    text-align: right;
}
.edit-date {
    min-width: 130px; /* Чтобы влез виджет календаря */
}
/* Улучшение вида input-ов */
.edit-input:focus {
    outline: none;
    border-color: #80bdff;
    box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}

/* Стили для сумм (пополнение/снятие) */
.deposit { color: #198754; } /* Более современный зеленый */
.withdrawal { color: #dc3545; }

/* Стили скроллбара (опционально, WebKit браузеры) */
.transactions-table-container::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
.transactions-table-container::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 3px;
}
.transactions-table-container::-webkit-scrollbar-thumb {
    background: #aaa;
    border-radius: 3px;
}
.transactions-table-container::-webkit-scrollbar-thumb:hover {
    background: #888;
}
</style>