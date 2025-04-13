<template>
  <div class="interest-rate-manager">
    <h3>Управление процентными ставками</h3>
    <div class="current-rate">
      <label>Месяц:</label>
      <select v-model="selectedMonth" @change="loadRate">
        <option v-for="month in months" :key="month" :value="month">
          {{ formatMonthName(month) }}
        </option>
      </select>
      <div class="rate-input">
        <label>Процентная ставка:</label>
        <input 
          type="number" 
          v-model="currentRate" 
          step="0.01" 
          min="0" 
          max="100"
          @change="updateGlobalRate"
        >
        <span class="percent">%</span>
      </div>
    </div>
    <div class="rate-info">
      <p>Установленная ставка будет применена к выбранному месяцу для расчета остатков</p>
    </div>
  </div>
</template>

<script>
import axios from '../axios-config';

export default {
  data() {
    return {
      currentRate: 0.0,
      selectedMonth: new Date().toISOString().slice(0, 7), // YYYY-MM
      months: []
    };
  },
  async created() {
    await this.loadMonths();
    await this.loadRate();
  },
  methods: {
    formatMonthName(month) {
      const [year, monthNum] = month.split('-');
      const date = new Date(year, monthNum - 1);
      return date.toLocaleString('ru-RU', { month: 'long', year: 'numeric' });
    },
    async loadMonths() {
      const currentDate = new Date();
      this.months = Array.from({length: 3}, (_, i) => {
        const d = new Date(currentDate.getFullYear(), currentDate.getMonth() - i, 1);
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
      }).reverse();
    },
    async loadRate() {
      try {
        const response = await axios.get(`/api/interest-rate?month=${this.selectedMonth}`);
        this.currentRate = response.data.rate;
      } catch (error) {
        console.error('Ошибка при загрузке процентной ставки:', error);
      }
    },
    async updateGlobalRate() {
      try {
        await axios.put(`/api/interest-rate?month=${this.selectedMonth}`, { rate: this.currentRate });
        this.$emit('rate-updated', { month: this.selectedMonth, rate: this.currentRate });
      } catch (error) {
        console.error('Ошибка при обновлении процентной ставки:', error);
      }
    }
  }
};
</script>

<style scoped>
.interest-rate-manager {
  background-color: #fff;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

h3 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #333;
}

.current-rate {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-bottom: 10px;
}

.rate-input {
  display: flex;
  align-items: center;
  gap: 10px;
}

select {
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  max-width: 200px;
}

input {
  width: 80px;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.percent {
  color: #666;
}

.rate-info {
  font-size: 14px;
  color: #666;
  margin-top: 10px;
}
</style> 