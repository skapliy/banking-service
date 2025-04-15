<template>
  <div class="create-account">
    <h2>Создать счет</h2>
    <form @submit.prevent="submitAccount">
      <div class="form-group">
        <label for="name">Название счета</label>
        <input
          type="text"
          id="name"
          v-model="name"
          required
          class="form-control"
        >
      </div>
      
      <div class="form-group">
        <label for="balance">Начальный баланс</label>
        <input
          type="number"
          id="balance"
          v-model="balance"
          step="0.01"
          required
          class="form-control"
        >
      </div>

      <div class="form-group">
        <label for="interest-rate">Процентная ставка (%)</label>
        <input
          type="number"
          id="interest-rate"
          v-model="interestRate"
          step="0.01"
          min="0"
          max="100"
          required
          class="form-control"
        >
      </div>
      
      <div class="form-actions">
        <button type="submit" class="submit-button" :disabled="!isFormValid">
          Создать
        </button>
        <button type="button" class="cancel-button" @click="$emit('close')">
          Отмена
        </button>
      </div>
    </form>
  </div>
</template>

<script>
import axios from '../axios-config';

export default {
  name: 'CreateAccount',
  data() {
    return {
      name: '',
      balance: '',
      interestRate: 0.0
    };
  },
  computed: {
    isFormValid() {
      return this.name && this.balance && this.interestRate !== '';
    }
  },
  methods: {
    async submitAccount() {
      try {
        const accountData = {
          name: this.name,
          balance: parseFloat(this.balance),
          interest_rate: parseFloat(this.interestRate)
        };

        await axios.post('/api/accounts', accountData);
        this.$emit('account-created');
        this.resetForm();
      } catch (error) {
        alert('Ошибка при создании счета: ' + (error.response?.data?.detail || error.message));
      }
    },
    resetForm() {
      this.name = '';
      this.balance = '';
      this.interestRate = '0.0';
    }
  }
};
</script>

<style scoped>
.create-account {
  padding: 20px;
}

.form-group {
  margin-bottom: 15px;
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
}

.submit-button {
  background-color: #28a745;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
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
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
}

.cancel-button:hover {
  background-color: #5a6268;
}
</style>