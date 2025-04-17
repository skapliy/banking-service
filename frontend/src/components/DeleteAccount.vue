<template>
  <div class="delete-account-wrapper">
    <button
      class="action-button delete-button"
      @click="showConfirmationModal"
      title="Удалить счет"
    >
      ✖
    </button>
    
    <teleport to="body">
      <div v-if="isModalVisible" class="confirmation-modal">
        <div class="modal-content">
          <h3>Удаление счета</h3>
          <p>Вы уверены, что хотите удалить этот счет?</p>
          <p class="warning-text">Это действие нельзя отменить.</p>
          <div class="modal-actions">
            <button class="delete-btn" @click="handleDelete">Удалить</button>
            <button class="cancel-btn" @click="isModalVisible = false">Отмена</button>
          </div>
        </div>
      </div>
    </teleport>
  </div>
</template>

<script>
import axios from '@/axios-config';

export default {
  name: 'DeleteAccount',
  props: {
    accountId: {
      type: String,
      required: true,
      validator: (value) => value.trim() !== '',
    },
  },
  emits: ['deleted'], // Добавлено объявление эмитируемых событий
  data() {
    return {
      isModalVisible: false,
      isDeleting: false, // Добавлено состояние для отслеживания процесса удаления
    };
  },
  methods: {
    showConfirmationModal() {
      this.isModalVisible = true;
    },
    async handleDelete() {
      if (this.isDeleting) return; // Предотвращаем повторные нажатия
      
      this.isDeleting = true;
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
      } finally {
        this.isDeleting = false;
        this.isModalVisible = false;
      }
    },
  },
};
</script>

<style scoped>
.delete-account-wrapper {
  display: inline-block; /* Важно для правильного позиционирования кнопки-триггера */
  vertical-align: middle; /* Выравнивание по вертикали с другими кнопками */
}

/* Стили для модального окна подтверждения */
.confirmation-modal {
  position: fixed;
  inset: 0; /* Аналог top/left/right/bottom = 0 */
  background: rgba(0, 0, 0, 0.6); /* Немного темнее фон */
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1050; /* Убедимся, что выше других элементов */
  padding: 15px; /* Отступы от краев экрана */
  box-sizing: border-box;
}

.modal-content {
  background: white;
  padding: 25px 30px; /* Увеличены внутренние отступы */
  border-radius: 8px;
  text-align: center;
  width: 95%; /* Ширина для мобильных */
  max-width: 420px; /* Максимальная ширина */
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2); /* Немного выразительнее тень */
  display: flex; /* Используем flex для управления высотой */
  flex-direction: column;
  max-height: calc(100vh - 40px); /* Макс. высота с учетом отступов */
  overflow-y: auto; /* Скролл, если контент высокий */
}

.modal-content h3 {
  margin-top: 0;
  margin-bottom: 15px; /* Отступ под заголовком */
  color: #343a40; /* Темнее цвет заголовка */
  font-size: 1.3rem;
  font-weight: 600;
}

.modal-content p {
    margin-bottom: 10px;
    color: #495057; /* Цвет основного текста */
    line-height: 1.5;
}

.warning-text {
  color: #dc3545;
  font-weight: 500; /* Слегка жирнее */
  font-size: 0.95em;
  margin-bottom: 25px; /* Больше отступ перед кнопками */
}

.modal-actions {
  display: flex;
  justify-content: center; /* Центрируем кнопки */
  gap: 15px; /* Больше расстояние между кнопками */
  margin-top: 20px;
  flex-wrap: wrap; /* Разрешаем перенос кнопок */
}

.modal-actions button {
  padding: 10px 20px; /* Увеличены паддинги для удобства нажатия */
  cursor: pointer;
  border: none;
  border-radius: 5px; /* Скругление как у других кнопок */
  font-weight: 500;
  font-size: 0.95rem;
  transition: background-color 0.2s, opacity 0.2s;
  min-width: 100px; /* Минимальная ширина кнопки */
}

/* Стилизация кнопки подтверждения удаления */
.delete-btn {
  background-color: #dc3545;
  color: white;
}
.delete-btn:hover {
  background-color: #c82333;
}
.delete-btn:disabled { /* Стиль для неактивной кнопки во время удаления */
    background-color: #e48a93;
    cursor: not-allowed;
}


/* Стилизация кнопки отмены */
.cancel-btn {
  background-color: #6c757d;
  color: white;
}
.cancel-btn:hover {
  background-color: #5a6268;
}

/* Кнопка-триггер (крестик) - СТИЛИ ЗАДАЮТСЯ ИЗ РОДИТЕЛЯ ЧЕРЕЗ :deep() */
/* Оставляем пустым или удаляем */
/* .action-button.delete-button { } */

/* Адаптация для очень маленьких экранов */
@media (max-width: 400px) {
    .modal-content {
        padding: 20px 20px; /* Уменьшаем паддинги */
    }
    .modal-actions {
        flex-direction: column; /* Кнопки друг под другом */
        gap: 10px;
        align-items: stretch; /* Растянуть кнопки по ширине */
    }
     .modal-actions button {
         width: 100%; /* Кнопки на всю ширину */
     }
}

</style>