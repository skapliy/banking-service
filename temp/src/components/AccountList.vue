<template>
  <div class="accounts-container">
    <div class="header-row">
      <h2>Список счетов</h2>
      <button class="create-account-button" @click="showCreateAccount">
        <span class="plus-icon">+</span>
      </button>
    </div>
    
    <div v-if="loading" class="loading">
      Загрузка счетов...
    </div>
    
    <div v-else-if="error" class="error">
      {{ error }}
    </div>
    
    <div v-else>
      <table class="accounts-table">
        <thead>
          <tr>
            <th>Название счета</th>
            <th>Текущий баланс</th>
            <th v-for="month in months" :key="month">{{ formatMonthName(month) }}</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="account in accounts" :key="account.id">
            <td>
              <span class="account-name" @click="showTransactions(account.id, account.name)">
                {{ account.name }}
              </span>
            </td>
            <td :class="{ 'negative': account.balance < 0 }">
              {{ formatBalance(account.balance) }}
              <div class="capitalization" v-if="currentMonth">
                <div class="capitalization-amount">
                  {{ formatBalance(calculateCapitalizedBalance(account)) }}
                </div>
              </div>
            </td>
            <td v-for="month in months" :key="month" 
                :class="{ 'negative': (account.monthly_balances?.[month] || 0) < 0 }">
              {{ formatBalance(account.monthly_balances?.[month]) }}
              <div class="interest-rate" v-if="account.interest_rates?.[month]">
                {{ account.interest_rates[month] }}%
              </div>
            </td>
            <td class="actions">
              <button 
                class="action-button" 
                @click="showTransactions(account.id, account.name)"
                title="История транзакций"
              >
                📖
              </button>
              <button 
                class="action-button" 
                @click="showAddTransaction(account.id)"
                title="Добавить транзакцию"
              >
                ±
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Модальное окно для транзакций -->
      <div v-if="selectedAccount && !showingAddTransaction && !showingCreateAccount" class="modal">
        <div class="modal-content">
          <div class="modal-header">
            <h3>{{ selectedAccount.name }}</h3>
            <button @click="selectedAccount = null" class="close-button">&times;</button>
          </div>
          <TransactionList 
            :account-id="selectedAccount.id"
            :account-name="selectedAccount.name"
            @close="selectedAccount = null"
          />
        </div>
      </div>

      <!-- Модальное окно для добавления транзакции -->
      <div v-if="showingAddTransaction" class="modal">
        <div class="modal-content">
          <div class="modal-header">
            <h3>Новая транзакция: {{ selectedAccount?.name }}</h3>
            <button @click="closeAddTransaction" class="close-button">&times;</button>
          </div>
          <AddTransaction
            v-if="selectedAccount"
            :account-id="selectedAccount.id"
            @transaction-added="onTransactionAdded"
            @close="closeAddTransaction"
          />
        </div>
      </div>

      <!-- Модальное окно для создания счета -->
      <div v-if="showingCreateAccount" class="modal">
        <div class="modal-content">
          <div class="modal-header">
            <h3>Создать новый счет</h3>
            <button @click="closeCreateAccount" class="close-button">&times;</button>
          </div>
          <CreateAccount 
            @account-created="onAccountCreated" 
            @close="closeCreateAccount"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.accounts-container {
  padding: 20px;
}

.accounts-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
  background: white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.accounts-table th,
.accounts-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.accounts-table th {
  background-color: #f8f9fa;
  font-weight: 600;
  color: #495057;
}

.accounts-table td {
  vertical-align: top;
}

.negative {
  color: #dc3545;
}

.interest-rate {
  font-size: 0.8em;
  color: #6c757d;
  margin-top: 4px;
}

.action-button {
  margin: 0 4px;
  padding: 6px 12px;
  border: 1px solid #007bff;
  background-color: white;
  color: #007bff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1.1em;
  min-width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.action-button:hover {
  background-color: #007bff;
  color: white;
}

.modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 20px;
  border-radius: 8px;
  width: 80%;
  max-width: 800px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.close-button {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
}

.close-button:hover {
  color: #333;
}

.loading {
  text-align: center;
  padding: 20px;
  color: #666;
}

.error {
  color: #dc3545;
  padding: 20px;
  text-align: center;
}

.capitalization {
  margin-top: 4px;
  font-size: 0.85em;
}

.capitalization-amount {
  font-weight: 500;
  color: #28a745;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.create-account-button {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid #6c757d;
  background: white;
  color: #6c757d;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.create-account-button:hover {
  background: #6c757d;
  color: white;
}

.plus-icon {
  font-size: 20px;
  line-height: 1;
}

.account-name {
  cursor: pointer;
  color: #007bff;
  text-decoration: none;
}

.account-name:hover {
  text-decoration: underline;
}
</style>

<script>
import axios from 'axios';
import TransactionList from './TransactionList.vue';
import AddTransaction from './AddTransaction.vue';
import CreateAccount from './CreateAccount.vue';

export default {
  name: 'AccountList',
  components: {
    TransactionList,
    AddTransaction,
    CreateAccount
  },
  data() {
    return {
      accounts: [],
      months: [],
      loading: true,
      error: null,
      selectedAccount: null,
      showingAddTransaction: false,
      showingCreateAccount: false,
      currentMonth: null
    };
  },
  methods: {
    formatBalance(amount) {
      if (amount === undefined || amount === null) return '-';
      return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'RUB'
      }).format(amount);
    },
    formatMonthName(monthStr) {
      const [year, month] = monthStr.split('-');
      const date = new Date(year, parseInt(month) - 1);
      return date.toLocaleString('ru-RU', { month: 'long', year: 'numeric' });
    },
    showTransactions(accountId, accountName) {
      this.selectedAccount = { id: accountId, name: accountName };
      this.showingAddTransaction = false;
      this.showingCreateAccount = false;
    },
    showAddTransaction(accountId) {
      this.selectedAccount = { id: accountId };
      this.showingAddTransaction = true;
      this.showingCreateAccount = false;
    },
    showCreateAccount() {
      this.showingCreateAccount = true;
      this.showingAddTransaction = false;
      this.selectedAccount = null;
    },
    closeCreateAccount() {
      this.showingCreateAccount = false;
    },
    async onTransactionAdded() {
      this.showingAddTransaction = false;
      this.selectedAccount = null;
      await this.loadAccounts();
    },
    closeAddTransaction() {
      this.showingAddTransaction = false;
      this.selectedAccount = null;
    },
    calculateCapitalizedBalance(account) {
      if (!this.currentMonth || !account.interest_rates[this.currentMonth]) {
        return account.balance;
      }
      const rate = account.interest_rates[this.currentMonth] / 100;
      const monthlyRate = rate / 12;
      return account.balance * (1 + monthlyRate);
    },
    async onAccountCreated() {
      this.showingCreateAccount = false;
      await this.loadAccounts();
    },
    async loadAccounts() {
      try {
        const response = await axios.get('/api/accounts');
        this.accounts = response.data.map(account => ({
          ...account,
          monthly_balances: account.monthly_balances || {},
          interest_rates: account.interest_rates || {}
        }));
        
        // Получаем список всех месяцев из всех счетов
        const allMonths = new Set();
        this.accounts.forEach(account => {
          if (account.monthly_balances) {
            Object.keys(account.monthly_balances).forEach(month => allMonths.add(month));
          }
        });
        
        // Если нет исторических данных, создаем список последних 6 месяцев
        if (allMonths.size === 0) {
          const now = new Date();
          for (let i = 0; i < 6; i++) {
            const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
            const monthStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
            allMonths.add(monthStr);
            
            // Инициализируем месячные балансы для каждого счета
            this.accounts.forEach(account => {
              if (!account.monthly_balances[monthStr]) {
                account.monthly_balances[monthStr] = account.balance;
              }
            });
          }
        }
        
        this.months = Array.from(allMonths).sort().reverse();
        this.currentMonth = this.months[0]; // Первый месяц в списке - текущий
        this.error = null;
      } catch (error) {
        this.error = 'Ошибка при загрузке счетов: ' + (error.response?.data?.detail || error.message);
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