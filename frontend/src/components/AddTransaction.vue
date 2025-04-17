<template>
  <div class="add-transaction">
    <form @submit.prevent="submitTransaction">
      <div class="form-group">
        <label for="amount">Сумма</label>
        <input
          type="number"
          id="amount"
          v-model="amount"
          step="0.01"
          required
          class="form-control"
        >
      </div>
      
      <div class="form-group">
        <label for="date">Дата</label>
        <input
          type="date"
          id="date"
          v-model="date"
          required
          class="form-control"
        >
      </div>
      
      <div class="form-group">
        <label for="comment">Комментарий</label>
        <input
          type="text"
          id="comment"
          v-model="comment"
          class="form-control"
          placeholder="Необязательно"
        >
      </div>
      
      <div class="form-actions">
        <button type="submit" class="submit-button" :disabled="!amount">
          Добавить
        </button>
        <button type="button" class="cancel-button" @click="closeModal">
          Отмена
        </button>
      </div>
    </form>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'AddTransaction',
  props: {
    accountId: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      amount: '',
      date: new Date().toISOString().split('T')[0],
      comment: ''
    };
  },
  methods: {
    async submitTransaction() {
      try {
        const transactionData = {
          account_id: this.accountId,
          amount: parseFloat(this.amount),
          date: this.date,
          comment: this.comment
        };
        await axios.post('/api/transactions', transactionData);
        this.$emit('transaction-added');
        this.resetForm();
      } catch (error) {
        alert('Ошибка при добавлении транзакции: ' + (error.response?.data?.detail || error.message));
      }
    },
    resetForm() {
      this.amount = '';
      this.date = new Date().toISOString().split('T')[0];
      this.comment = '';
    },
    closeModal() {
      this.$emit('close');
      this.resetForm();
    }
  }
};
</script>

<style scoped>
.add-transaction {
  padding: 20px;
  max-width: 100%;
  box-sizing: border-box;
}

.form-group {
  margin-bottom: 15px;
  width: 100%;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  color: #495057;
}

.form-control {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 16px;
  box-sizing: border-box;
  max-width: 100%;
}

input[type="date"].form-control {
  min-width: 0;
  width: 100%;
}

.form-control:focus {
  border-color: #80bdff;
  outline: 0;
  box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}

.form-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.submit-button, .cancel-button {
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  border: none;
  flex: 0 0 auto;
}

.submit-button {
  background-color: #28a745;
  color: white;
}

.submit-button:hover {
  background-color: #218838;
}

.submit-button:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.cancel-button {
  background-color: #6c757d;
  color: white;
}

.cancel-button:hover {
  background-color: #5a6268;
}

@media (max-width: 480px) {
  .form-actions {
    flex-direction: column;
    width: 100%;
  }
  
  .submit-button, .cancel-button {
    width: 100%;
    margin-bottom: 8px;
  }
}
</style>
