<template>
  <div class="add-interest">
    <h2>Начислить проценты</h2>
    <form @submit.prevent="submitInterest">
      <div>
        <label for="rate">Процентная ставка:</label>
        <input type="number" id="rate" v-model="rate" step="0.01" required>
      </div>
      <button type="submit">Начислить проценты</button>
    </form>
  </div>
</template>

<script>
import axios from '../axios-config';

export default {
  data() {
    return {
      rate: 0
    };
  },
  methods: {
    async submitInterest() {
      try {
        await axios.post('/api/interest-rate', this.rate);
        await axios.post('/api/capitalize-interest');
        alert('Проценты успешно начислены');
        this.rate = 0;
        // Обновляем список счетов
        this.$emit('interest-added');
      } catch (error) {
        alert('Ошибка при начислении процентов: ' + error.response?.data?.detail || error.message);
      }
    }
  }
};
</script>

<style scoped>
.add-interest {
  max-width: 500px;
  margin: 0 auto;
  padding: 20px;
}

form div {
  margin-bottom: 15px;
}

label {
  display: block;
  margin-bottom: 5px;
}

input {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

button {
  background-color: #007bff;
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

button:hover {
  background-color: #0056b3;
}
</style> 