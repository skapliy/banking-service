<template>
  <div class="delete-account-wrapper">
    <button
      class="action-button delete-button"
      @click="showConfirmationModal"
      title="Удалить счет"
      :disabled="loading"
    >
      ✖
    </button>

    <!-- Confirmation Modal -->
    <div v-if="showModal" class="modal">
      <div class="modal-content small">
        <div class="modal-header">
          <h3>Подтверждение удаления</h3>
          <button @click="closeModal" class="close-button" :disabled="loading">&times;</button>
        </div>
        <div class="modal-body">
          <p>Вы уверены, что хотите удалить этот счет? Это действие необратимо.</p>

          <p v-if="error" class="error-message">{{ error }}</p> <!-- Display error message -->

        </div>
        <div class="modal-footer">
          <button @click="deleteAccount" class="confirm-delete-button" :disabled="loading">
            {{ loading ? 'Удаление...' : 'Удалить' }}
          </button>
          <button @click="closeModal" class="cancel-button" :disabled="loading">Отмена</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from '@/axios-config'; // Use configured instance

export default {
  name: 'DeleteAccount',
  props: {
    accountId: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      showModal: false,
      loading: false,
      error: null, // Add error state
    };
  },
  methods: {
    showConfirmationModal() {
      this.error = null; // Reset error when opening modal
      this.showModal = true;
    },
    closeModal() {
      if (!this.loading) {
        this.showModal = false;
        this.error = null; // Clear error on close
      }
    },
    async deleteAccount() {
      this.loading = true;
      this.error = null; // Reset error on new attempt

      try {
        await axios.delete(`/api/accounts/${this.accountId}`);
        // console.log('Account deleted successfully'); // Remove console.log
        this.$emit('deleted'); // Notify parent component
        this.closeModal();
      } catch (err) {
        // console.error('Error deleting account:', err); // Remove console.error
        const errorMessage = err.response?.data?.detail || err.message || 'Не удалось удалить счет.';
        this.error = errorMessage; // Set error message for display in modal
        this.$emit('error', `Ошибка при удалении счета ${this.accountId}: ${errorMessage}`); // Emit error for parent logging
        // alert('Ошибка при удалении счета: ' + (err.response?.data?.detail || err.message)); // Remove alert
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<style scoped>
.delete-account-wrapper {
  display: inline-block; /* Keep button layout consistent */
}

/* Styles for the modal (similar to AccountList) */
.modal {
  position: fixed;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1001; /* Ensure it's above other modals if needed */
  padding: 15px;
  box-sizing: border-box;
}

.modal-content {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 40px);
  overflow: hidden; /* Prevent body scroll */
  width: 100%;
}

.modal-content.small {
   max-width: 450px; /* Adjust width as needed */
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 15px;
  border-bottom: 1px solid #dee2e6;
  flex-shrink: 0;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.2rem;
  font-weight: 600;
}

.close-button {
  background: none;
  border: none;
  font-size: 1.6rem;
  font-weight: bold;
  color: #6c757d;
  cursor: pointer;
  padding: 0 5px;
  line-height: 1;
}
.close-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.modal-body {
  padding: 20px 15px;
  overflow-y: auto; /* Scroll if content overflows */
}

.modal-body p {
  margin-top: 0;
  margin-bottom: 1rem;
}

.error-message {
  color: #dc3545;
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
  padding: 10px 15px;
  margin-top: 15px;
  font-size: 0.9em;
  text-align: center;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 12px 15px;
  border-top: 1px solid #dee2e6;
  flex-shrink: 0;
}

.modal-footer button {
   padding: 8px 15px;
   border-radius: 4px;
   cursor: pointer;
   border: 1px solid transparent;
   font-weight: 500;
}
.modal-footer button:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.confirm-delete-button {
  background-color: #dc3545; /* Bootstrap danger */
  color: white;
  border-color: #dc3545;
}

.cancel-button {
   background-color: #6c757d; /* Bootstrap secondary */
   color: white;
   border-color: #6c757d;
}

/* Inherit action-button styles if needed, or define specific ones */
.action-button {
  /* ... styles from AccountList.vue if needed ... */
  /* Example: */
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 5px;
  font-size: 1.4em;
  line-height: 1;
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s, border-color 0.2s;
  border: 1px solid;
  background-color: #fff;
  padding: 0;
  vertical-align: middle;
}
.action-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-button.delete-button {
  border-color: #dc3545;
  color: #dc3545;
}
.action-button.delete-button:hover:not(:disabled) {
  background-color: #dc3545;
  color: white;
}
</style>