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
          :disabled="loading"
          placeholder="Например, Основной счет"
        />
      </div>
      <div class="form-group">
        <label for="initial-balance">Начальный баланс (необязательно)</label>
        <input
          type="number"
          id="initial-balance"
          v-model.number="initialBalance"
          step="0.01"
          :disabled="loading"
          placeholder="0.00"
        />
      </div>

      <p v-if="error" class="error-message">{{ error }}</p> <!-- Display error message -->

      <div class="form-actions">
        <button type="submit" :disabled="loading">
          {{ loading ? 'Создание...' : 'Создать счет' }}
        </button>
         <button type="button" @click="$emit('close')" :disabled="loading">Отмена</button>
      </div>
    </form>
  </div>
</template>

<script>
import axios from '../axios-config'; // Use configured instance

export default {
  name: 'CreateAccount',
  data() {
    return {
      name: '',
      initialBalance: 0,
      loading: false,
      error: null, // Add error state
    };
  },
  methods: {
    async submitAccount() {
      this.loading = true;
      this.error = null; // Reset error

      const accountData = {
        name: this.name,
        initial_balance: this.initialBalance || 0, // Send 0 if null/undefined
      };

      try {
        await axios.post('/api/accounts', accountData);
        this.$emit('account-created'); // Emit success
      } catch (err) {
         console.error('Error creating account:', err); // Keep console error for debugging
         // Set user-friendly error message
         this.error = err.response?.data?.detail || err.message || 'Не удалось создать счет.';
        // alert('Ошибка при создании счета: ' + (err.response?.data?.detail || err.message)); // Remove alert
      } finally {
        this.loading = false;
      }
    },
  },
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

.error-message {
  color: #dc3545;
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
  padding: 10px 15px;
  margin-top: 15px;
  margin-bottom: 15px;
  font-size: 0.9em;
  text-align: center;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

 .form-actions button {
  padding: 8px 15px;
  border-radius: 4px;
  cursor: pointer;
  border: 1px solid transparent;
}

.form-actions button[type="submit"] {
  background-color: #198754; /* Bootstrap success */
  color: white;
  border-color: #198754;
}
.form-actions button[type="submit"]:disabled {
  background-color: #6c757d;
  border-color: #6c757d;
  cursor: not-allowed;
}

.form-actions button[type="button"] {
  background-color: #6c757d; /* Bootstrap secondary */
  color: white;
  border-color: #6c757d;
}
 .form-actions button[type="button"]:disabled {
   opacity: 0.65;
   cursor: not-allowed;
 }
</style>