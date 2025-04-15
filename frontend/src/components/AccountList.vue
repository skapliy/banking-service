<template>
  <div class="accounts-container">
    <div class="header-row">
      <h2>Список счетов</h2>
      <button class="create-account-button" @click="showCreateAccount" title="Создать новый счет">
        <span class="plus-icon">+</span>
      </button>
    </div>

    <div v-if="loading" class="loading">
      Загрузка счетов...
    </div>

    <div v-else-if="error" class="error">
      Ошибка при загрузке данных: {{ error }}
    </div>

    <div v-else>
      <table class="accounts-table">
        <thead>
          <tr>
            <th>Счет</th>
            <th v-for="monthKey in lastThreeMonths" :key="monthKey">{{ formatMonthYear(monthKey) }}</th>
            <th>Баланс / Прогноз</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="account in accounts" :key="account.id">
            <td>
              <span
                class="account-name clickable"
                @click="showTransactions(account.id, account.name)"
                :title="`Показать транзакции для ${account.name}`"
              >
                {{ account.name }}
                <span
                  v-if="account.current_interest_rate !== undefined && account.current_interest_rate !== null"
                  class="interest-rate-label"
                  :title="`Текущая ставка: ${account.current_interest_rate}%`"
                >
                  ({{ account.current_interest_rate }}%)
                </span>
                 <span v-else class="interest-rate-label" title="Ставка не установлена">
                  (-%)
                </span>
              </span>
            </td>

            <td
              v-for="monthKey in lastThreeMonths"
              :key="monthKey"
              class="historical-cell"
            >
              <div class="monthly-data" v-if="account.previous_months[monthKey]">
                <div class="balance" title="Остаток на конец месяца">
                  {{ formatBalance(account.previous_months[monthKey].end_balance) }}
                </div>
                <div class="interest" title="Начислено процентов за месяц">
                  +{{ formatBalance(account.previous_months[monthKey].interest_accrued) }}
                </div>
              </div>
              <div v-else class="monthly-data-na">
                -
              </div>
            </td>

            <td :class="{ 'negative': account.current_period.current_balance < 0 }">
              <div class="balance-container">
                <div class="actual-balance" title="Текущий фактический баланс">
                    {{ formatBalance(account.current_period.current_balance) }}
                </div>
              <div
               class="projected-balance"
                :title="`Прогноз на конец ${formatMonthYear(currentMonthStr)} с учетом процентов (${formatValueForTitle(account.current_period.projected_interest)} ₽)`"
             >
               {{ formatBalance(account.current_period.projected_eom_balance) }}
             </div>
                
              </div>
            </td>

            <td class="actions">
               <button
                class="action-button rate-button"
                @click="showChangeRateModal(account)"
                title="Изменить процентную ставку текущего месяца"
              >
                %
              </button>
              <button
                class="action-button transaction-button"
                @click="showAddTransaction(account.id, account.name)"
                title="Добавить транзакцию"
              >
                ±
              </button>
               <DeleteAccount
                :account-id="account.id"
                @deleted="loadAccounts"
              />
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="showingTransactionList" class="modal">
        <div class="modal-content wide">
          <div class="modal-header">
            <h3>Транзакции: {{ selectedAccountForModal?.name }}</h3>
            <button @click="closeTransactionList" class="close-button">&times;</button>
          </div>
          <TransactionList
            v-if="selectedAccountForModal"
            :account-id="selectedAccountForModal.id"
            :account-name="selectedAccountForModal.name"
            @close="closeTransactionList"
          />
        </div>
      </div>

      <div v-if="showingAddTransaction" class="modal">
        <div class="modal-content">
          <div class="modal-header">
            <h3>Новая транзакция: {{ selectedAccountForModal?.name }}</h3>
            <button @click="closeAddTransaction" class="close-button">&times;</button>
          </div>
          <AddTransaction
            v-if="selectedAccountForModal"
            :account-id="selectedAccountForModal.id"
            @transaction-added="onActionComplete"
            @close="closeAddTransaction"
          />
        </div>
      </div>

      <div v-if="showingCreateAccount" class="modal">
        <div class="modal-content">
          <div class="modal-header">
            <h3>Создать новый счет</h3>
            <button @click="closeCreateAccount" class="close-button">&times;</button>
          </div>
          <CreateAccount
            @account-created="onActionComplete"
            @close="closeCreateAccount"
          />
        </div>
      </div>

      <div v-if="showingChangeRateModal" class="modal">
        <div class="modal-content small">
           <div class="modal-header">
            <h3>Ставка за {{ formatMonthYear(currentMonthStr) }} для {{ accountToChangeRate?.name }}</h3>
            <button @click="closeChangeRateModal" class="close-button">&times;</button>
          </div>
          <div class="change-rate-form">
             <label :for="'rate-input-' + accountToChangeRate?.id">Новая ставка (%):</label>
             <input
                type="number"
                :id="'rate-input-' + accountToChangeRate?.id"
                v-model.number="newInterestRate"
                min="0"
                step="0.01"
                placeholder="Например, 15.00"
              />
              <div class="modal-actions">
                <button @click="saveInterestRate" class="save-button">Сохранить</button>
                <button @click="closeChangeRateModal" class="cancel-button">Отмена</button>
              </div>
               <p v-if="rateChangeError" class="error">{{ rateChangeError }}</p>
          </div>
          </div>
      </div>

    </div>
  </div>
</template>

<style scoped>
/* ... ваши существующие стили ... */

/* Дополнительные или измененные стили */
.accounts-table th,
.accounts-table td {
  padding: 10px 12px; /* Немного уменьшим паддинг */
  vertical-align: middle; /* Выравниваем по центру вертикально */
}

.interest-rate-label {
  font-size: 0.8em; /* Чуть меньше */
  color: #6c757d;
  margin-left: 5px;
  font-weight: normal; /* Сделаем обычным */
}

.historical-cell {
  min-width: 100px; /* Можно настроить */
  text-align: right; /* Выравниваем числа вправо */
}
.monthly-data .balance {
    font-weight: 500;
}
.monthly-data .interest {
    font-size: 0.85em;
    color: #28a745; /* Зеленый для процентов */
}
.monthly-data-na {
    color: #aaa;
    text-align: center;
}

.balance-container {
  display: flex;
  flex-direction: column;
  gap: 2px; /* Меньше разрыв */
  text-align: right; /* Выравниваем числа вправо */
}
.actual-balance {
    font-weight: 600; /* Текущий баланс жирнее */
}
.projected-balance {
  font-size: 0.9em;
  color: #007bff; /* Синий для прогноза */
}

.actions {
    text-align: center; /* Центрируем кнопки */
    white-space: nowrap; /* Запрещаем перенос кнопок */
}

/* Внутри <style scoped> файла AccountList.vue */

/* ---> ИЗМЕНЕНИЕ: Добавляем :deep() к БАЗОВОМУ классу <--- */
/* Это должно заставить размер и отступы примениться и к кнопкам в дочерних компонентах */
:deep(.action-button) {
  /* Основные для размера и выравнивания */
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;            /* Жесткая ширина */
  height: 32px;           /* Жесткая высота */
  padding: 0;             /* Убедитесь, что padding 0 */
  box-sizing: border-box;  /* Важно */

  /* Вспомогательные для внешнего вида */
  margin: 0 3px;
  border: 1px solid;
  border-radius: 4px;
  background-color: white;
  font-size: 1.1em;
  font-weight: bold;
  line-height: 1;
  text-align: center;
  vertical-align: middle;
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s;
  overflow: hidden;
}
/* ---> КОНЕЦ ИЗМЕНЕНИЯ <--- */


/* Стили для кнопки изменения ставки (%) - БЕЗ :deep(), т.к. кнопка в этом же компоненте */
.action-button.rate-button {
  border-color: #ffc107;
  color: #ffc107;
}
.action-button.rate-button:hover {
  background-color: #ffc107;
  color: white;
}

/* Стили для кнопки добавления транзакции (±) - БЕЗ :deep() */
.action-button.transaction-button {
  border-color: #17a2b8;
  color: #17a2b8;
}
.action-button.transaction-button:hover {
  background-color: #17a2b8;
  color: white;
}

/* Стили для кнопки удаления (X/±) - :deep() НУЖЕН, т.к. кнопка в DeleteAccount.vue */
:deep(.action-button.delete-button) {
  border-color: #dc3545;
  color: #dc3545;
}
:deep(.action-button.delete-button:hover) {
  background-color: #dc3545;
  color: white;
}

/* ... остальные стили ... */

.modal-content.wide {
    max-width: 90%; /* Шире для списка транзакций */
}
.modal-content.small {
    max-width: 400px; /* Узкое для изменения ставки */
}
.change-rate-form {
    display: flex;
    flex-direction: column;
    gap: 15px;
}
.change-rate-form label {
    margin-bottom: -10px;
    font-weight: 500;
}
.change-rate-form input {
    padding: 8px;
    border: 1px solid #ccc;
    border-radius: 4px;
}
.change-rate-form .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 10px;
}
.change-rate-form .save-button, .change-rate-form .cancel-button {
    padding: 8px 15px;
    border-radius: 4px;
    cursor: pointer;
}
.change-rate-form .save-button {
    background-color: #28a745;
    color: white;
    border: none;
}
.change-rate-form .cancel-button {
    background-color: #6c757d;
    color: white;
    border: none;
}
.change-rate-form .error {
    color: #dc3545;
    font-size: 0.9em;
    margin-top: -5px;
}

</style>

<script>
import axios from 'axios';
import TransactionList from './TransactionList.vue'; // Предполагаем, что этот компонент существует
import AddTransaction from './AddTransaction.vue';   // Предполагаем, что этот компонент существует
import CreateAccount from './CreateAccount.vue';     // Предполагаем, что этот компонент существует
import DeleteAccount from './DeleteAccount.vue';     // Предполагаем, что этот компонент существует
// import ChangeInterestRate from './ChangeInterestRate.vue'; // Опционально, если выносить в отдельный компонент

export default {
  name: 'AccountList',
  components: {
    TransactionList,
    AddTransaction,
    CreateAccount,
    DeleteAccount,
    // ChangeInterestRate // Раскомментировать, если используется отдельный компонент
  },
  data() {
    return {
      accounts: [], // Будет содержать объекты AccountDetails из API
      loading: true,
      error: null,
      // --- Состояния модальных окон ---
      showingTransactionList: false,
      showingAddTransaction: false,
      showingCreateAccount: false,
      showingChangeRateModal: false,
      // --- Данные для модальных окон ---
      selectedAccountForModal: null, // Для показа транзакций и добавления
      accountToChangeRate: null,     // Для изменения ставки
      newInterestRate: null,         // V-model для инпута ставки
      rateChangeError: null,         // Ошибка при сохранении ставки
    };
  },

  computed: {
    /**
     * Возвращает массив строк с ключами 3-х предыдущих месяцев (относительно текущего).
     * Пример: если сейчас апрель 2025, вернет ["2025-01", "2025-02", "2025-03"]
     */
    lastThreeMonths() {
      const months = [];
      const today = new Date();
      for (let i = 3; i >= 1; i--) { // Идем назад на 3, 2, 1 месяц
        // new Date(year, monthIndex (0-11), day)
        const d = new Date(today.getFullYear(), today.getMonth() - i, 1);
        const monthStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
        months.push(monthStr);
      }
      console.log("Previous months keys:", months); // Для отладки
      return months;
    },
    /**
     * Возвращает строку текущего месяца в формате YYYY-MM.
     */
    currentMonthStr() {
        const today = new Date();
        return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`;
    }
  },

  methods: {
    /**
     * Форматирует число как валюту RUB.
     */
    formatBalance(amount) {
      // Преобразуем в число, если это строка (API может вернуть Decimal как строку)
      const numAmount = (typeof amount === 'string') ? parseFloat(amount) : amount;
      if (numAmount === undefined || numAmount === null || isNaN(numAmount)) return '-';
      return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'RUB',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(numAmount);
    },

    /**
     * Форматирует ключ месяца "YYYY-MM" в "Месяц Год".
     */
    formatMonthYear(monthKey) {
        if (!monthKey || !monthKey.includes('-')) return monthKey; // Возвращаем как есть, если формат неверный
        try {
            const [year, month] = monthKey.split('-');
            // В JS месяцы 0-11, поэтому month - 1
            const date = new Date(parseInt(year), parseInt(month) - 1, 1);
            return date.toLocaleString('ru-RU', { month: 'long', year: 'numeric' });
        } catch (e) {
            console.error("Error formatting month key:", monthKey, e);
            return monthKey; // Возвращаем исходный ключ при ошибке
        }
    },

    /**
     * Безопасно форматирует число (полученное как строка или число) для title атрибута.
     * @param {*} value Значение для форматирования (может быть строкой, числом, null)
     * @returns {string} Отформатированная строка (e.g., "22.50") или дефолтное значение.
     */
     formatValueForTitle(value) {
        const num = parseFloat(value); // Преобразуем в число
        if (isNaN(num)) {
             // Возвращаем дефолтное значение, если не число
            return '0.00'; // или '-', или 'н/д'
        }
        return num.toFixed(2); // Форматируем число
    },

    /**
     * Получает отформатированный баланс на конец месяца для счета и ключа месяца.
     */
    getHistoricalBalance(account, monthKey) {
      const monthData = account.previous_months?.[monthKey];
      // Проверяем наличие данных и самого значения end_balance
      return (monthData && monthData.end_balance !== null && monthData.end_balance !== undefined)
             ? this.formatBalance(monthData.end_balance)
             : "-";
    },

    /**
     * Получает отформатированные проценты, начисленные за месяц, для счета и ключа месяца.
     */
    getHistoricalInterest(account, monthKey) {
      const monthData = account.previous_months?.[monthKey];
       // Проверяем наличие данных и самого значения interest_accrued
      return (monthData && monthData.interest_accrued !== null && monthData.interest_accrued !== undefined)
             ? this.formatBalance(monthData.interest_accrued)
             : "-";
    },

    // --- Управление Модальными Окнами ---
    showTransactions(accountId, accountName) {
      this.selectedAccountForModal = { id: accountId, name: accountName };
      this.showingTransactionList = true;
      this.showingAddTransaction = false;
      this.showingCreateAccount = false;
      this.showingChangeRateModal = false;
    },
     closeTransactionList() {
       this.showingTransactionList = false;
       this.selectedAccountForModal = null;
    },

    showAddTransaction(accountId, accountName) { // Добавим имя для заголовка
      // Ищем полный объект аккаунта, чтобы показать имя в заголовке
      this.selectedAccountForModal = this.accounts.find(acc => acc.id === accountId) || { id: accountId, name: accountName || 'Счет' };
      this.showingAddTransaction = true;
      this.showingTransactionList = false;
      this.showingCreateAccount = false;
      this.showingChangeRateModal = false;
    },
    closeAddTransaction() {
      this.showingAddTransaction = false;
       this.selectedAccountForModal = null;
    },

    showCreateAccount() {
      this.showingCreateAccount = true;
      this.showingTransactionList = false;
      this.showingAddTransaction = false;
      this.showingChangeRateModal = false;
      this.selectedAccountForModal = null;
    },
    closeCreateAccount() {
      this.showingCreateAccount = false;
    },

    showChangeRateModal(account) {
        this.accountToChangeRate = account;
        // Устанавливаем текущую ставку в инпут (или null, если не задана)
        this.newInterestRate = account.current_interest_rate !== null ? account.current_interest_rate : null;
        this.rateChangeError = null; // Сбрасываем ошибку
        this.showingChangeRateModal = true;
        this.showingTransactionList = false;
        this.showingAddTransaction = false;
        this.showingCreateAccount = false;
    },
     closeChangeRateModal() {
        this.showingChangeRateModal = false;
        this.accountToChangeRate = null;
        this.newInterestRate = null;
         this.rateChangeError = null;
    },

    // --- Обработчики после действий ---
    async onActionComplete() {
      // Вызывается после добавления транзакции или создания счета
      this.closeAddTransaction();
      this.closeCreateAccount();
      await this.loadAccounts(); // Перезагружаем список
    },

    // --- Сохранение Ставки ---
     async saveInterestRate() {
        if (this.newInterestRate === null || this.newInterestRate === undefined || this.newInterestRate < 0) {
            this.rateChangeError = "Пожалуйста, введите корректную неотрицательную ставку.";
            return;
        }
        if (!this.accountToChangeRate) return;

        this.rateChangeError = null; // Сброс ошибки перед запросом
        const ratePayload = { rate: this.newInterestRate };
        const monthToUpdate = this.currentMonthStr; // Получаем текущий месяц YYYY-MM

        try {
            console.log(`Sending PUT to /api/interest-rate/${monthToUpdate} with payload:`, ratePayload);
            await axios.put(`/api/interest-rate/${monthToUpdate}`, ratePayload);
            this.closeChangeRateModal();
            await this.loadAccounts(); // Обновляем список, чтобы увидеть новую ставку
        } catch (error) {
            console.error("Error updating interest rate:", error);
            this.rateChangeError = 'Ошибка при сохранении ставки: ' + (error.response?.data?.detail || error.message);
        }
    },

    // --- Загрузка Данных ---
    async loadAccounts() {
      this.loading = true; // Устанавливаем флаг загрузки
      this.error = null;   // Сбрасываем предыдущие ошибки
      console.log("Loading accounts from /api/accounts");
      try {
        const response = await axios.get('/api/accounts');
        console.log("API Response:", response.data); // Отладка ответа API

        // Используем данные напрямую, так как бэкенд теперь возвращает нужную структуру
        this.accounts = response.data;

        // Проверка структуры полученных данных (для отладки)
        if (this.accounts.length > 0) {
            console.log("First account structure:", this.accounts[0]);
            console.log("Previous months data for first account:", this.accounts[0].previous_months);
            console.log("Current period data for first account:", this.accounts[0].current_period);
        }


      } catch (error) {
         console.error("Error loading accounts:", error);
         // Устанавливаем сообщение об ошибке для отображения пользователю
        this.error = (error.response?.data?.detail || error.message || 'Неизвестная ошибка сети');
        this.accounts = []; // Очищаем список при ошибке
      } finally {
        this.loading = false; // Снимаем флаг загрузки в любом случае
      }
    }
  },
  // --- Хук Жизненного Цикла ---
  async created() {
    // Загружаем данные при создании компонента
    await this.loadAccounts();
  }
};
</script>