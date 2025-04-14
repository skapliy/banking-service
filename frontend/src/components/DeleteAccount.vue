<template>
  <button class="delete-button" @click="showConfirmationModal">
    ✖
  </button>

  <!-- Модальное окно -->
  <div v-if="isModalVisible" class="confirmation-modal">
    <div class="modal-content">
      <p>Вы уверены, что хотите удалить счет?</p>
      <div class="modal-actions">
        <button @click="handleDelete">Да</button>
        <button @click="isModalVisible = false">Нет</button>
      </div>
    </div>
  </div>
</template>

<script>
import axios from '@/axios-config';

export default {
  props: {
    accountId: {
      type: String,
      required: true,
      validator: (value) => value.trim() !== '',
    },
  },
  data() {
    return {
      isModalVisible: false, // Добавлено состояние модального окна
    };
  },
  methods: {
    showConfirmationModal() {
      this.isModalVisible = true; // Метод для показа модального окна
    },
    async handleDelete() {
      this.isModalVisible = false; // Закрываем модальное окно
      try {
        console.log('Отправка запроса на удаление счета ID:', this.accountId);
        const response = await axios.delete(`/api/accounts/${this.accountId}`);
        if (response.status === 200) {
          console.log('Счет успешно удален:', response.data);
          this.$emit('deleted');
        }
      } catch (error) {
        console.error('Ошибка при удалении счета:', error);
        alert(`Ошибка удаления: ${error.response?.data?.detail || error.message}`);
      }
    },
  },
};
</script>

<style scoped>
.delete-button {
  background: none;
  border: 1px solid #dc3545;
  color: #dc3545;
  border-radius: 4px;
  padding: 6px 12px;
  cursor: pointer;
  margin: 0 4px;
  font-size: 1.1em;
  transition: background-color 0.2s, color 0.2s;
}

.delete-button:hover {
  background-color: #dc3545;
  color: white;
}

.delete-button:active {
  transform: scale(0.98);
}

/* Стили для модального окна */
.confirmation-modal {
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
  text-align: center;
}

.modal-actions button {
  margin: 10px;
  padding: 8px 16px;
  cursor: pointer;
}
</style>