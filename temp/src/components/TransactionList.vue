<template>
  <div class="transaction-list">
    <div class="header">
      <h3>{{ accountName }} ({{ interestRate }}%)</h3>
    </div>
    
    <div v-if="loading" class="loading">Загрузка...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="transactions.length === 0" class="no-transactions">Нет транзакций</div>
    <div v-else class="transactions">
      <div v-for="transaction in transactions" :key="transaction.id" class="transaction-item">
        <div class="transaction-date">{{ formatDate(transaction.date) }}</div>
        <div class="transaction-amount" :class="{ 'deposit': transaction.amount > 0, 'withdrawal': transaction.amount < 0 }">
          {{ formatAmount(transaction.amount) }}
        </div>
        <div class="transaction-comment" v-if="transaction.comment">
          {{ transaction.comment }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from '../axios-config';

export default {
  props: {
    accountId: {
      type: String,
      required: true
    },
    accountName: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      transactions: [],
      loading: true,
      error: null,
      interestRate: 0
    };
  },
  async created() {
    try {
      const [transactionsResponse, accountResponse] = await Promise.all([
        axios.get(`/api/accounts/${this.accountId}/transactions`),
        axios.get(`/api/accounts/${this.accountId}`)
      ]);
      this.transactions = transactionsResponse.data;
      this.interestRate = accountResponse.data.interest_rate || 0;
    } catch (error) {
      this.error = 'Ошибка при загрузке транзакций: ' + (error.response?.data?.detail || error.message);
    } finally {
      this.loading = false;
    }
  },
  methods: {
    formatDate(dateString) {
      const date = new Date(dateString);
      return date.toLocaleDateString('ru-RU', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    },
    formatAmount(amount) {
      return parseFloat(amount).toFixed(2);
    }
  }
};
</script>

<style scoped>
.transaction-list {
  background-color: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  max-width: 800px;
  margin: 0 auto;
}

.header {
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
}

.header h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
}

.loading, .error, .no-transactions {
  text-align: center;
  padding: 20px;
  font-size: 16px;
}

.error {
  color: #dc3545;
}

.transactions {
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 10px;
}

.transactions::-webkit-scrollbar {
  width: 8px;
}

.transactions::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.transactions::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 4px;
}

.transactions::-webkit-scrollbar-thumb:hover {
  background: #555;
}

.transaction-item {
  display: flex;
  align-items: center;
  padding: 12px;
  border-bottom: 1px solid #eee;
  transition: background-color 0.2s;
}

.transaction-item:hover {
  background-color: #f8f9fa;
}

.transaction-item:last-child {
  border-bottom: none;
}

.transaction-date {
  color: #666;
  font-size: 14px;
  width: 200px;
  white-space: nowrap;
}

.transaction-amount {
  font-weight: 500;
  font-size: 16px;
  width: 120px;
  text-align: right;
  padding: 0 20px;
}

.transaction-amount.deposit {
  color: #28a745;
}

.transaction-amount.withdrawal {
  color: #dc3545;
}

.transaction-comment {
  color: #666;
  font-size: 14px;
  flex: 1;
  word-break: break-word;
  padding-left: 20px;
  border-left: 1px solid #eee;
}
</style> 