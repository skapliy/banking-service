<template>
  <div class="accounts-container">
    <!-- Шапка с кнопками -->
    <div class="header-row">
      <h2 class="page-title">Счета</h2>
      <div class="action-buttons">
        <button
          class="action-button create-button"
          @click="showCreateAccount"
          title="Создать новый счет"
        >
          +
        </button>
        <button
          class="action-button rate-button"
          title="Установить ставку на текущий месяц"
          @click="showGlobalRateModal"
        >
          %
        </button>
      </div>
    </div>

    <!-- Состояния загрузки и ошибки -->
    <div v-if="loading" class="loading">Загрузка счетов...</div>
    <div v-else-if="error" class="error">
      Ошибка при загрузке данных: {{ error }}
    </div>

    <!-- Основной контент -->
    <div v-else>
      <!-- Мобильный вид (карточки) -->
      <div class="accounts-mobile">
        <div 
          v-for="account in accounts" 
          :key="account.id"
          class="account-card"
        >
          <div class="account-header" @click="toggleTransactions(account.id)">
            <div class="account-name-container">
              <span class="account-name">
                {{ account.name }}
                <span
                  v-if="account.current_interest_rate !== undefined && account.current_interest_rate !== null"
                  class="interest-rate-label"
                >
                  ({{ account.current_interest_rate }}%)
                </span>
                <span v-else class="interest-rate-label">(--%)</span>
              </span>
              <span class="expand-icon">
                {{ expandedAccountId === account.id ? "▲" : "▼" }}
              </span>
            </div>
            
            <div class="balance-container">
              <div 
                class="actual-balance" 
                :class="{ negative: account.current_period && account.current_period.current_balance < 0 }"
              >
                {{ formatBalance(account.current_period.current_balance) }}
              </div>
              <div class="projected-balance">
                {{ formatBalance(account.current_period.projected_eom_balance) }}
              </div>
            </div>
          </div>
          
          <div class="account-actions">
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
          </div>
          
          <!-- Исторические данные (свернуты по умолчанию) -->
          <div class="history-section" v-if="expandedAccountId === account.id">
            <div class="history-title">История за последние 3 месяца:</div>
            <div class="history-grid">
              <div 
                v-for="monthKey in lastThreeMonths" 
                :key="monthKey"
                class="month-card"
              >
                <div class="month-name">{{ formatMonthYear(monthKey) }}</div>
                <div 
                  v-if="account.previous_months && account.previous_months[monthKey]"
                  class="month-data"
                >
                  <div class="balance">
                    {{ formatBalance(account.previous_months[monthKey].end_balance) }}
                  </div>
                  <div class="interest">
                    +{{ formatBalance(account.previous_months[monthKey].interest_accrued) }}
                  </div>
                </div>
                <div v-else class="month-data-na">-</div>
              </div>
            </div>
          </div>
          
          <!-- Транзакции (если развернуты) -->
          <div 
            v-if="expandedAccountId === account.id"
            class="transactions-wrapper"
          >
            <TransactionList
              :account-id="account.id"
              :account-name="account.name"
              @transactions-updated="handleTransactionsUpdate"
              :key="`${account.id}-tx`"
            />
          </div>
        </div>
        
        <!-- Итоговая карточка -->
        <div class="account-card totals-card">
          <div class="account-header">
            <span class="account-name">Итого:</span>
            <div class="balance-container">
              <div class="actual-balance">
                {{ formatBalance(currentPeriodTotals.totalCurrentBalance) }}
              </div>
              <div class="projected-balance">
                {{ formatBalance(currentPeriodTotals.totalProjectedEomBalance) }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Десктопный вид (таблица) - скрыт на мобильных -->
      <div class="accounts-desktop">
        <table class="accounts-table">
          <thead>
            <tr>
              <th>Счет</th>
              <th v-for="monthKey in lastThreeMonths" :key="monthKey">
                {{ formatMonthYear(monthKey) }}
              </th>
              <th>Баланс / Прогноз</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="account in accounts" :key="account.id">
              <tr>
                <td>
                  <span
                    class="account-name clickable"
                    @click="toggleTransactions(account.id)"
                    :title="`${expandedAccountId === account.id ? 'Скрыть' : 'Показать'} транзакции для ${account.name}`"
                    :class="{ expanded: expandedAccountId === account.id }"
                  >
                    {{ account.name }}
                    <span
                      v-if="account.current_interest_rate !== undefined && account.current_interest_rate !== null"
                      class="interest-rate-label"
                      :title="`Текущая ставка: ${account.current_interest_rate}%`"
                    >
                      ({{ account.current_interest_rate }}%)
                    </span>
                    <span
                      v-else
                      class="interest-rate-label"
                      title="Ставка не установлена"
                    >
                      (-%)
                    </span>
                    <span class="expand-icon">{{
                      expandedAccountId === account.id ? "▲" : "▼"
                    }}</span>
                  </span>
                </td>
                <td
                  v-for="monthKey in lastThreeMonths"
                  :key="monthKey"
                  class="historical-cell"
                >
                  <div
                    class="monthly-data"
                    v-if="account.previous_months && account.previous_months[monthKey]"
                  >
                    <div class="balance" title="Остаток на конец месяца">
                      {{ formatBalance(account.previous_months[monthKey].end_balance) }}
                    </div>
                    <div class="interest" title="Начислено процентов за месяц">
                      +{{ formatBalance(account.previous_months[monthKey].interest_accrued) }}
                    </div>
                  </div>
                  <div v-else class="monthly-data-na">-</div>
                </td>
                <td
                  :class="{ negative: account.current_period && account.current_period.current_balance < 0 }"
                >
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
              <tr
                v-if="expandedAccountId === account.id"
                class="transaction-details-row"
              >
                <td :colspan="lastThreeMonths.length + 3">
                  <div class="details-wrapper" :style="{ maxHeight: expandedAccountId === account.id ? '1000px' : '0px' }">
                    <TransactionList
                      :account-id="account.id"
                      :account-name="account.name"
                      @transactions-updated="handleTransactionsUpdate"
                      :key="`${account.id}-tx`"
                    />
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
          <tfoot>
            <tr class="totals-row">
              <td><strong>Итого:</strong></td>
              <td
                v-for="monthKey in lastThreeMonths"
                :key="`${monthKey}-total`"
                class="historical-cell totals-cell"
              >
                <div v-if="totalsByMonth[monthKey]" class="monthly-data">
                  <div class="balance" title="Сумма остатков на конец месяца">
                    {{ formatBalance(totalsByMonth[monthKey].totalEndBalance) }}
                  </div>
                  <div
                    class="interest"
                    title="Сумма начисленных процентов за месяц"
                  >
                    +{{ formatBalance(totalsByMonth[monthKey].totalInterestAccrued) }}
                  </div>
                </div>
                <div v-else class="monthly-data-na">-</div>
              </td>
              <td class="totals-cell">
                <div class="balance-container">
                  <div class="actual-balance" title="Сумма текущих балансов">
                    {{ formatBalance(currentPeriodTotals.totalCurrentBalance) }}
                  </div>
                  <div
                    class="projected-balance"
                    title="Сумма прогнозируемых балансов на конец месяца"
                  >
                    {{ formatBalance(currentPeriodTotals.totalProjectedEomBalance) }}
                  </div>
                </div>
              </td>
              <td></td>
            </tr>
          </tfoot>
        </table>
      </div>

      <!-- Модальные окна -->
      <!-- Модальное окно добавления транзакции -->
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

      <!-- Модальное окно создания счета -->
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

      <!-- Модальное окно изменения глобальной ставки -->
      <div v-if="showingGlobalRateModal" class="modal">
        <div class="modal-content small">
          <div class="modal-header">
            <h3>Ставка за {{ formatMonthYear(currentMonthStr) }}</h3>
            <button @click="closeGlobalRateModal" class="close-button">&times;</button>
          </div>
          <div class="change-rate-form">
            <label for="global-rate-input">Новая ставка (%):</label>
            <input
              type="number"
              id="global-rate-input"
              v-model.number="newInterestRate"
              min="0"
              step="0.01"
              placeholder="Например, 15.00"
            />
            <div class="modal-actions">
              <button @click="saveGlobalInterestRate" class="save-button">Сохранить</button>
              <button @click="closeGlobalRateModal" class="cancel-button">Отмена</button>
            </div>
            <p v-if="rateChangeError" class="error">{{ rateChangeError }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* === Общие стили и адаптивность === */
.accounts-container {
  padding: 10px;
  max-width: 100%;
  overflow-x: hidden;
}

.loading, .error {
  text-align: center;
  padding: 15px;
  font-size: 1em;
  margin: 10px 0;
}

.error {
  color: #dc3545;
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  flex-wrap: wrap;
}

.page-title {
  margin: 0;
  font-size: 1.5rem;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

/* === Мобильный вид (карточки) === */
.accounts-mobile {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.account-card {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  padding: 12px;
  border: 1px solid #e0e0e0;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  flex-wrap: wrap;
}

.page-title {
  margin: 0;
  font-size: 1.5rem;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

/* === Мобильный вид (карточки) === */
.accounts-mobile {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.account-card {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  padding: 12px;
  border: 1px solid #e0e0e0;
}

.totals-card {
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
}

.account-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  padding-bottom: 8px;
}

.account-name-container {
  display: flex;
  align-items: center;
  gap: 5px;
}

.account-name {
  font-weight: 600;
  font-size: 1.1em;
}

.interest-rate-label {
  font-size: 0.8em;
  color: #6c757d;
  font-weight: normal;
}

.expand-icon {
  font-size: 0.8em;
  color: #888;
  margin-left: 5px;
}

.balance-container {
  text-align: right;
}

.actual-balance {
  font-weight: 600;
  font-size: 1.1em;
}

.actual-balance.negative {
  color: #dc3545;
}

.projected-balance {
  font-size: 0.9em;
  color: #0d6efd;
}

.account-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #eee;
}

/* История счета в мобильном виде */
.history-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #e0e0e0;
}

.history-title {
  font-size: 0.9em;
  color: #6c757d;
  margin-bottom: 8px;
}

.history-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.month-card {
  background-color: #f8f9fa;
  border-radius: 6px;
  padding: 8px;
  text-align: center;
}

.month-name {
  font-size: 0.8em;
  color: #495057;
  margin-bottom: 5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.month-data {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.month-data .balance {
  font-weight: 500;
  font-size: 0.9em;
}

.month-data .interest {
  font-size: 0.8em;
  color: #198754;
}

.month-data-na {
  color: #adb5bd;
  font-style: italic;
}

/* Транзакции в мобильном виде */
.transactions-wrapper {
  margin-top: 15px;
  border-top: 1px solid #dee2e6;
  padding-top: 15px;
}

/* === Десктопный вид (таблица) === */
.accounts-desktop {
  display: none; /* Скрыт на мобильных */
}

.accounts-table {
  width: 100%;
  border-collapse: collapse;
}

.accounts-table th,
.accounts-table td {
  padding: 10px 12px;
  vertical-align: middle;
  border-bottom: 1px solid #dee2e6;
}

.accounts-table th {
  background-color: #f8f9fa;
  font-weight: 600;
  text-align: left;
  white-space: nowrap;
}

.accounts-table th:nth-child(1) { text-align: left; }
.accounts-table th:nth-child(n+2) { text-align: right; }
.accounts-table th:last-child { text-align: center; }

/* Стили для кнопок действий */
.action-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  border: 1px solid;
  border-radius: 4px;
  background-color: #fff;
  font-size: 1.4em;
  line-height: 1;
  text-align: center;
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s;
}

.action-button.create-button {
  border-color: #198754;
  color: #198754;
}

.action-button.create-button:hover {
  background-color: #198754;
  color: white;
}

.action-button.rate-button {
  border-color: #ffc107;
  color: #ffc107;
}

.action-button.rate-button:hover {
  background-color: #ffc107;
  color: white;
}

.action-button.transaction-button {
  border-color: #0dcaf0;
  color: #0dcaf0;
}

.action-button.transaction-button:hover {
  background-color: #0dcaf0;
  color: white;
}

:deep(.action-button.delete-button) {
  border-color: #dc3545;
  color: #dc3545;
}

:deep(.action-button.delete-button:hover) {
  background-color: #dc3545;
  color: white;
}

/* === Модальные окна === */
.modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  position: relative;
}

.modal-content.small {
  max-width: 350px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  border-bottom: 1px solid #dee2e6;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.2rem;
}

.close-button {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #6c757d;
}

.change-rate-form {
  display: flex;
  flex-direction: column;
  gap: 15px;
  padding: 15px;
}

.change-rate-form label {
  font-weight: 500;
}

.change-rate-form input {
  padding: 10px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 1em;
}

.change-rate-form .modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 10px;
}

.change-rate-form .save-button,
.change-rate-form .cancel-button {
  padding: 8px 15px;
  border-radius: 4px;
  cursor: pointer;
  border: none;
  font-weight: 500;
}

.change-rate-form .save-button {
  background-color: #198754;
  color: white;
}

.change-rate-form .cancel-button {
  background-color: #6c757d;
  color: white;
}

.change-rate-form .error {
  color: #dc3545;
  font-size: 0.9em;
  text-align: center;
}

/* === Медиа-запросы для адаптивности === */
@media (min-width: 768px) {
  .accounts-container {
    padding: 20px;
  }
  
  .accounts-mobile {
    display: none; /* Скрываем карточки на десктопе */
  }
  
  .accounts-desktop {
    display: block; /* Показываем таблицу на десктопе */
  }
  
  .modal-content {
    width: auto;
    min-width: 500px;
  }
}

/* Для очень маленьких экранов */
@media (max-width: 360px) {
  .history-grid {
    grid-template-columns: repeat(2, 1fr); /* 2 колонки вместо 3 */
  }
  
  .account-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .balance-container {
    align-self: flex-end;
  }
}
</style>  


<script>
import axios from 'axios';
import TransactionList from './TransactionList.vue';
import AddTransaction from './AddTransaction.vue';
import CreateAccount from './CreateAccount.vue';
import DeleteAccount from './DeleteAccount.vue';

export default {
  name: 'AccountList',
  components: {
    TransactionList,
    AddTransaction,
    CreateAccount,
    DeleteAccount,
  },
  data() {
    return {
      accounts: [],
      loading: true,
      error: null,
      showingAddTransaction: false,
      showingCreateAccount: false,
      showingGlobalRateModal: false,
      expandedAccountId: null, // ID аккаунта, чьи транзакции сейчас показаны
      selectedAccountForModal: null, // Для модальных окон
      newInterestRate: null,
      rateChangeError: null,
    };
  },
  computed: {
    /**
     * Возвращает массив строк с ключами 3-х предыдущих месяцев (относительно текущего).
     */
    lastThreeMonths() {
      const months = [];
      const today = new Date();
      for (let i = 3; i >= 1; i--) {
        const d = new Date(today.getFullYear(), today.getMonth() - i, 1);
        const monthStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
        months.push(monthStr);
      }
      return months;
    },
    
    /**
     * Возвращает строку текущего месяца в формате YYYY-MM.
     */
    currentMonthStr() {
      const today = new Date();
      return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`;
    },
    
    /**
     * Рассчитывает общие суммы для текущего периода.
     */
    currentPeriodTotals() {
      return this.accounts.reduce((totals, account) => {
        // Суммируем текущий баланс
        const currentBalance = parseFloat(account.current_period?.current_balance || 0);
        totals.totalCurrentBalance += isNaN(currentBalance) ? 0 : currentBalance;
        
        // Суммируем прогнозируемый баланс
        const projectedBalance = parseFloat(account.current_period?.projected_eom_balance || 0);
        totals.totalProjectedEomBalance += isNaN(projectedBalance) ? 0 : projectedBalance;
        
        return totals;
      }, { totalCurrentBalance: 0, totalProjectedEomBalance: 0 });
    },
    
    /**
     * Рассчитывает общие суммы для каждого из предыдущих месяцев.
     */
    totalsByMonth() {
      const monthlyTotals = {};
      
      // Инициализируем объект для каждого месяца из заголовков
      this.lastThreeMonths.forEach(monthKey => {
        monthlyTotals[monthKey] = { totalEndBalance: 0, totalInterestAccrued: 0 };
      });
      
      // Проходим по всем счетам
      this.accounts.forEach(account => {
        // Проходим по месяцам, для которых есть ключи в итогах
        this.lastThreeMonths.forEach(monthKey => {
          const monthData = account.previous_months?.[monthKey];
          if (monthData) {
            // Суммируем баланс на конец месяца
            const endBalance = parseFloat(monthData.end_balance || 0);
            monthlyTotals[monthKey].totalEndBalance += isNaN(endBalance) ? 0 : endBalance;
            
            // Суммируем начисленные проценты
            const interestAccrued = parseFloat(monthData.interest_accrued || 0);
            monthlyTotals[monthKey].totalInterestAccrued += isNaN(interestAccrued) ? 0 : interestAccrued;
          }
        });
      });
      
      // Округляем итоговые суммы до 2 знаков после запятой
      Object.keys(monthlyTotals).forEach(monthKey => {
        monthlyTotals[monthKey].totalEndBalance = parseFloat(monthlyTotals[monthKey].totalEndBalance.toFixed(2));
        monthlyTotals[monthKey].totalInterestAccrued = parseFloat(monthlyTotals[monthKey].totalInterestAccrued.toFixed(2));
      });
      
      return monthlyTotals;
    }
  },
  methods: {
    /**
     * Форматирует число как валюту без символа валюты.
     */
    formatBalance(amount) {
      const numAmount = (typeof amount === 'string') ? parseFloat(amount) : amount;
      if (numAmount === undefined || numAmount === null || isNaN(numAmount)) return '-';
      
      return new Intl.NumberFormat('ru-RU', {
        style: 'decimal',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
        useGrouping: true
      }).format(numAmount);
    },
    
    /**
     * Обработчик обновления транзакций
     */
    handleTransactionsUpdate() {
      this.loadAccounts();
    },
    
    /**
     * Форматирует ключ месяца "YYYY-MM" в "Месяц".
     */
    formatMonthYear(monthKey) {
      if (!monthKey || !monthKey.includes('-')) return monthKey;
      
      try {
        const [year, month] = monthKey.split('-');
        const date = new Date(parseInt(year), parseInt(month) - 1, 1);
        return date.toLocaleString('ru-RU', { month: 'long' });
      } catch (e) {
        console.error("Error formatting month key:", monthKey, e);
        return monthKey;
      }
    },
    
    /**
     * Форматирует число для title атрибута.
     */
    formatValueForTitle(value) {
      const num = parseFloat(value);
      if (isNaN(num)) {
        return '0.00';
      }
      return num.toFixed(2);
    },
    
    /**
     * Переключает отображение транзакций для счета
     */
    toggleTransactions(accountId) {
      this.expandedAccountId = this.expandedAccountId === accountId ? null : accountId;
    },
    
    /**
     * Показывает модальное окно добавления транзакции
     */
    showAddTransaction(accountId, accountName) {
      this.selectedAccountForModal = this.accounts.find(acc => acc.id === accountId) || 
                                    { id: accountId, name: accountName || 'Счет' };
      this.showingAddTransaction = true;
      this.showingCreateAccount = false;
      this.showingGlobalRateModal = false;
    },
    
    /**
     * Закрывает модальное окно добавления транзакции
     */
    closeAddTransaction() {
      this.showingAddTransaction = false;
      this.selectedAccountForModal = null;
    },
    
    /**
     * Показывает модальное окно создания счета
     */
    showCreateAccount() {
      this.showingCreateAccount = true;
      this.showingAddTransaction = false;
      this.showingGlobalRateModal = false;
      this.selectedAccountForModal = null;
    },
    
    /**
     * Закрывает модальное окно создания счета
     */
    closeCreateAccount() {
      this.showingCreateAccount = false;
    },
    
    /**
     * Показывает модальное окно изменения глобальной ставки
     */
    showGlobalRateModal() {
      this.fetchCurrentMonthRate();
      this.rateChangeError = null;
      this.showingGlobalRateModal = true;
      this.showingAddTransaction = false;
      this.showingCreateAccount = false;
    },
    
    /**
     * Закрывает модальное окно изменения глобальной ставки
     */
    closeGlobalRateModal() {
      this.showingGlobalRateModal = false;
      this.newInterestRate = null;
      this.rateChangeError = null;
    },
    
    /**
     * Получает текущую ставку месяца для предзаполнения поля
     */
    async fetchCurrentMonthRate() {
      try {
         const response = await axios.get(`/api/interest-rate/${this.currentMonthStr}`);
        if (response.data && response.data.rate !== undefined) {
          this.newInterestRate = response.data.rate;
        } else {
          this.newInterestRate = null;
        }
      } catch (error) {
        console.error("Error fetching current month rate:", error);
        this.newInterestRate = null;
      }
    },
    
    /**
     * Обработчик после добавления транзакции или создания счета
     */
    async onActionComplete() {
      this.closeAddTransaction();
      this.closeCreateAccount();
      await this.loadAccounts();
    },
    
    /**
     * Сохраняет глобальную процентную ставку
     */
    async saveGlobalInterestRate() {
      if (this.newInterestRate === null || this.newInterestRate === undefined || this.newInterestRate < 0) {
        this.rateChangeError = "Пожалуйста, введите корректную неотрицательную ставку.";
        return;
      }
      
      this.rateChangeError = null;
      const ratePayload = { rate: this.newInterestRate };
      const monthToUpdate = this.currentMonthStr;
      
      try {
        await axios.put(`/api/interest-rate/${monthToUpdate}`, ratePayload);
        this.closeGlobalRateModal();
        await this.loadAccounts();
      } catch (error) {
        console.error("Error updating global interest rate:", error);
        this.rateChangeError = 'Ошибка при сохранении ставки: ' + 
                              (error.response?.data?.detail || error.message);
      }
    },
    
    /**
     * Загружает список счетов с сервера
     */
    async loadAccounts() {
      this.loading = true;
      this.error = null;
      
      try {
        const response = await axios.get('/api/accounts');
        this.accounts = response.data;
      } catch (error) {
        console.error("Error loading accounts:", error);
        this.error = (error.response?.data?.detail || error.message || 'Неизвестная ошибка сети');
        this.accounts = [];
      } finally {
        this.loading = false;
      }
    }
  },
  async created() {
    await this.loadAccounts();
  }
};
</script>