<template>
  <div class="create-account">
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
  max-width: 100%; /* Ограничиваем максимальную ширину */
  box-sizing: border-box; /* Учитываем padding в общей ширине */
}

h2 {
  margin-top: 0;
  margin-bottom: 20px;
  font-size: 1.5rem;
}

.form-group {
  margin-bottom: 15px;
  width: 100%; /* Устанавливаем ширину группы формы */
  box-sizing: border-box; /* Учитываем padding в общей ширине */
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
  box-sizing: border-box; /* Важно! Учитываем padding в общей ширине */
  max-width: 100%; /* Предотвращаем выход за границы */
}

.form-control:focus {
  border-color: #80bdff;
  outline: 0;
  box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}

input[type="number"].form-control {
  min-width: 0;
  width: 100%;
  -moz-appearance: textfield;
  appearance: textfield;
}

input[type="number"].form-control::-webkit-outer-spin-button,
input[type="number"].form-control::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

input[type="date"].form-control {
  min-width: 0;
  width: 100%;
}

.form-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
  flex-wrap: wrap; /* Позволяет кнопкам переноситься на новую строку при необходимости */
  justify-content: flex-end; /* Выравнивание кнопок по правому краю */
}

.submit-button, .cancel-button {
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  border: none;
  flex: 0 0 auto; /* Предотвращает сжатие кнопок */
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

/* Медиа-запрос для маленьких экранов */
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