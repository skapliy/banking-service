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
      
      <p v-if="error" class="error-message">{{ error }}</p> <!-- Display error message -->

      <div class="form-actions">
        <button type="submit" :disabled="loading">
          {{ loading ? 'Добавление...' : 'Добавить' }}
        </button>
        <button type="button" @click="$emit('close')" :disabled="loading">Отмена</button>
      </div>
    </form>
  </div>
</template>

<script>
// import axios from 'axios'; // Remove direct import
import axios from '../axios-config'; // Use configured instance

export default {
  name: 'AddTransaction',
  props: {
    accountId: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      amount: null,
      date: new Date().toISOString().slice(0, 10), // Default to today
      comment: '',
      loading: false,
      error: null, // Add error state
    };
  },
  methods: {
    async submitTransaction() {
      this.loading = true;
      this.error = null; // Reset error on new submission

      const transactionData = {
        account_id: this.accountId,
        amount: this.amount,
        date: this.date,
        comment: this.comment || null, // Send null if empty
      };

      try {
        // Use the configured axios instance (relative path is correct)
        await axios.post('/api/transactions', transactionData);
        this.$emit('transaction-added'); // Emit success event
        // Optionally reset form or close modal via another event
        // this.resetForm(); // Example reset
      } catch (err) {
        console.error('Error adding transaction:', err); // Keep console error for debugging
        // Set user-friendly error message
        this.error = err.response?.data?.detail || err.message || 'Не удалось добавить транзакцию. Пожалуйста, проверьте введенные данные.';
        // alert('Ошибка при добавлении транзакции: ' + (err.response?.data?.detail || err.message)); // Remove alert
      } finally {
        this.loading = false;
      }
    },
    // Optional: Method to reset form fields
    // resetForm() {
    //   this.amount = null;
    //   this.date = new Date().toISOString().slice(0, 10);
    //   this.comment = '';
    //   this.error = null;
    // }
  },
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

.error-message {
  color: #dc3545; /* Bootstrap danger color */
  background-color: #f8d7da; /* Light red background */
  border: 1px solid #f5c6cb; /* Reddish border */
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
