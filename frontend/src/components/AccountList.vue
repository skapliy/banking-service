<template>
  <div class="accounts-container">
    <!-- Шапка с кнопками -->
    <div class="header-row">
      <h2 class="page-title">Копилки</h2>
      <div class="action-buttons">
        <button
          class="action-button create-button"
          @click="showCreateAccount"
          title="Создать новый счет"
        >
          +
        </button>
        <button
          class="action-button rate-button"
          title="Установить ставку на текущий месяц"
          @click="showGlobalRateModal"
        >
          %
        </button>
    </div>
   </div> 

    <!-- Состояния загрузки и ошибки -->
    <div v-if="loading" class="loading">
      Загрузка счетов...
      <div class="debug-info" style="font-size: 0.8em; color: #999; margin-top: 10px;">
        Время начала загрузки: {{ new Date().toLocaleTimeString() }}
      </div>
    </div>

    <!-- Основной контент -->
    <div v-else>
      <!-- Мобильный вид (карточки) -->
      <div class="accounts-mobile">
        <div 
          v-for="account in accounts" 
          :key="account.id"
          class="account-card"
        >
          <div class="account-header" @click="toggleTransactions(account.id)">
            <div class="account-name-container">
              <span class="account-name">
                {{ account.name }}
                <span
                  v-if="account.current_interest_rate !== undefined && account.current_interest_rate !== null"
                  class="interest-rate-label"
                >
                  ({{ account.current_interest_rate }}%)
                </span>
                <span v-else class="interest-rate-label">(--%)</span>
              </span>
              <span class="expand-icon">
                {{ expandedAccountId === account.id ? "▲" : "▼" }}
              </span>
            </div>
            
            <div class="balance-container">
              <div 
                class="actual-balance" 
                :class="{ negative: account.current_period && account.current_period.current_balance < 0 }"
              >
                {{ formatBalance(account.current_period.current_balance) }}
              </div>
              <div class="projected-balance">
                {{ formatBalance(account.current_period.projected_eom_balance) }}
              </div>
            </div>
          </div>
          
          <div class="account-actions">
            <button
              class="action-button transaction-button"
              @click="showAddTransaction(account.id, account.name)"
              title="Добавить транзакцию"
            >
              ±
            </button>
            <DeleteAccount
              :account-id="account.id"
              @deleted="loadAccounts"
            />
          </div>
          
          <!-- Исторические данные (свернуты по умолчанию) -->
          <div class="history-section" v-if="expandedAccountId === account.id">
            <div class="history-grid">
              <div 
                v-for="monthKey in lastThreeMonths" 
                :key="monthKey"
                class="month-card"
              >
                <div class="month-name">{{ formatMonthYear(monthKey) }}</div>
                <div 
                  v-if="account.previous_months && account.previous_months[monthKey]"
                  class="month-data"
                >
                  <div class="balance">
                    {{ formatBalance(account.previous_months[monthKey].end_balance) }}
                  </div>
                  <div class="interest">
                    +{{ formatBalance(account.previous_months[monthKey].interest_accrued) }}
                  </div>
                </div>
                <div v-else class="month-data-na">-</div>
              </div>
            </div>
          </div>
          
          <!-- Транзакции (если развернуты) -->
          <div
            v-if="expandedAccountId === account.id"
            class="transactions-wrapper"
          >
            <div class="details-wrapper" :style="{ maxHeight: expandedAccountId === account.id ? '500px' : '0px' }">
                 <TransactionList
                :account-id="account.id"
                :account-name="account.name"
                @transactions-updated="handleTransactionsUpdate"
                :key="`${account.id}-tx`"
              />
            </div>
             </div>
        </div>
        
        <!-- Итоговая карточка -->
        <div class="account-card totals-card">
          <div class="account-header">
            <span class="account-name">Итого:</span>
            <div class="balance-container">
              <div class="actual-balance">
                {{ formatBalance(currentPeriodTotals.totalCurrentBalance) }}
              </div>
              <div class="projected-balance">
                {{ formatBalance(currentPeriodTotals.totalProjectedEomBalance) }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Десктопный вид (таблица) - скрыт на мобильных -->
      <div class="accounts-desktop">
        <table class="accounts-table">
          <thead>
            <tr>
              <th>Счет</th>
              <th v-for="monthKey in lastThreeMonths" :key="monthKey">
                {{ formatMonthYear(monthKey) }}
              </th>
              <th>Баланс / Прогноз</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="account in accounts" :key="account.id">
              <tr>
                <td>
                  <span
                    class="account-name clickable"
                    @click="toggleTransactions(account.id)"
                    :title="`${expandedAccountId === account.id ? 'Скрыть' : 'Показать'} транзакции для ${account.name}`"
                    :class="{ expanded: expandedAccountId === account.id }"
                  >
                    {{ account.name }}
                    <span
                      v-if="account.current_interest_rate !== undefined && account.current_interest_rate !== null"
                      class="interest-rate-label"
                      :title="`Текущая ставка: ${account.current_interest_rate}%`"
                    >
                      ({{ account.current_interest_rate }}%)
                    </span>
                    <span
                      v-else
                      class="interest-rate-label"
                      title="Ставка не установлена"
                    >
                      (-%)
                    </span>
                    <span class="expand-icon">{{
                      expandedAccountId === account.id ? "▲" : "▼"
                    }}</span>
                  </span>
                </td>
                <td
                  v-for="monthKey in lastThreeMonths"
                  :key="monthKey"
                  class="historical-cell"
                >
                  <div
                    class="monthly-data"
                    v-if="account.previous_months && account.previous_months[monthKey]"
                  >
                    <div class="balance" title="Остаток на конец месяца">
                      {{ formatBalance(account.previous_months[monthKey].end_balance) }}
                    </div>
                    <div class="interest" title="Начислено процентов за месяц">
                      +{{ formatBalance(account.previous_months[monthKey].interest_accrued) }}
                    </div>
                  </div>
                  <div v-else class="monthly-data-na">-</div>
                </td>
                <td
                  :class="{ negative: account.current_period && account.current_period.current_balance < 0 }"
                >
                  <div class="balance-container">
                    <div class="actual-balance" title="Текущий фактический баланс">
                      {{ formatBalance(account.current_period.current_balance) }}
                    </div>
                    <div
                      class="projected-balance"
                      :title="`Прогноз на конец ${formatMonthYear(currentMonthStr)} с учетом процентов (${formatValueForTitle(account.current_period.projected_interest)} ₽)`"
                    >
                      {{ formatBalance(account.current_period.projected_eom_balance) }}
                    </div>
                  </div>
                </td>
                <td class="actions">
                  <button
                    class="action-button transaction-button"
                    @click="showAddTransaction(account.id, account.name)"
                    title="Добавить транзакцию"
                  >
                    ±
                  </button>
                  <DeleteAccount
                    :account-id="account.id"
                    @deleted="loadAccounts"
                  />
                </td>
              </tr>
              <tr
                v-if="expandedAccountId === account.id"
                class="transaction-details-row"
              >
                <td :colspan="lastThreeMonths.length + 3">
                  <div class="details-wrapper" :style="{ maxHeight: expandedAccountId === account.id ? '1000px' : '0px' }">
                    <TransactionList
                      :account-id="account.id"
                      :account-name="account.name"
                      @transactions-updated="handleTransactionsUpdate"
                      :key="`${account.id}-tx`"
                    />
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
          <tfoot>
            <tr class="totals-row">
              <td><strong>Итого:</strong></td>
              <td
                v-for="monthKey in lastThreeMonths"
                :key="`${monthKey}-total`"
                class="historical-cell totals-cell"
              >
                <div v-if="totalsByMonth[monthKey]" class="monthly-data">
                  <div class="balance" title="Сумма остатков на конец месяца">
                    {{ formatBalance(totalsByMonth[monthKey].totalEndBalance) }}
                  </div>
                  <div
                    class="interest"
                    title="Сумма начисленных процентов за месяц"
                  >
                    +{{ formatBalance(totalsByMonth[monthKey].totalInterestAccrued) }}
                  </div>
                </div>
                <div v-else class="monthly-data-na">-</div>
              </td>
              <td class="totals-cell">
                <div class="balance-container">
                  <div class="actual-balance" title="Сумма текущих балансов">
                    {{ formatBalance(currentPeriodTotals.totalCurrentBalance) }}
                  </div>
                  <div
                    class="projected-balance"
                    title="Сумма прогнозируемых балансов на конец месяца"
                  >
                    {{ formatBalance(currentPeriodTotals.totalProjectedEomBalance) }}
                  </div>
                </div>
              </td>
              <td></td>
            </tr>
          </tfoot>
        </table>
      </div>

      <!-- Модальные окна -->
      <!-- Модальное окно добавления транзакции -->
      <div v-if="showingAddTransaction" class="modal">
        <div class="modal-content">
          <div class="modal-header">
            <h3>Новая транзакция: {{ selectedAccountForModal?.name }}</h3>
            <button @click="closeAddTransaction" class="close-button">&times;</button>
          </div>
          <AddTransaction
            v-if="selectedAccountForModal"
            :account-id="selectedAccountForModal.id"
            @transaction-added="onActionComplete"
            @close="closeAddTransaction"
          />
        </div>
      </div>

      <!-- Модальное окно создания счета -->
      <div v-if="showingCreateAccount" class="modal">
        <div class="modal-content">
          <div class="modal-header">
            <h3>Создать новый счет</h3>
            <button @click="closeCreateAccount" class="close-button">&times;</button>
          </div>
          <CreateAccount
            @account-created="onActionComplete"
            @close="closeCreateAccount"
          />
        </div>
      </div>

      <!-- Модальное окно изменения глобальной ставки -->
      <div v-if="showingGlobalRateModal" class="modal">
        <div class="modal-content small">
          <div class="modal-header">
            <h3>Ставка за {{ formatMonthYear(currentMonthStr) }}</h3>
            <button @click="closeGlobalRateModal" class="close-button">&times;</button>
          </div>
          <div class="change-rate-form">
            <label for="global-rate-input">Новая ставка (%):</label>
            <input
              type="number"
              id="global-rate-input"
              v-model.number="newInterestRate"
              min="0"
              step="0.01"
              placeholder="Например, 15.00"
            />
            <div class="modal-actions">
              <button @click="saveGlobalInterestRate" class="save-button">Сохранить</button>
              <button @click="closeGlobalRateModal" class="cancel-button">Отмена</button>
            </div>
            <p v-if="rateChangeError" class="error">{{ rateChangeError }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* === Общие стили и адаптивность === */
.account-actions {
  border-top: 1px solid #f1f1f1; /* Тонкая линия над кнопками */
  display: flex;
  gap: 10px;
  justify-content: flex-end; /* Кнопки справа */
  margin-top: 6px;
  padding-top: 6px;
}

.account-card {
  background-color: #fff;
  border: 1px solid #e9ecef; /* Светлая граница */
  border-radius: 5px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08); /* Мягкая тень */
  padding: 15px; /* Внутренний отступ */
}

.account-header {
  align-items: center;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  padding-bottom: 6px; /* Отступ под шапкой карточки */
  /* border-bottom: 1px solid #eee; */ /* Убрал границу, чтобы не перегружать */
  /* margin-bottom: 10px; */
}

.account-name {
  font-size: 1.1rem;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis; /* Многоточие для длинных имен */
  white-space: nowrap;
}

.account-name-container {
  align-items: center;
  display: flex;
  gap: 8px; /* Отступ между элементами имени */
  /* flex-grow: 1; */ /* Чтобы занимало доступное место */
  overflow: hidden; /* Обрезать длинное имя */
}

.accounts-container {
  max-width: 100%;
  overflow-x: hidden; /* Предотвращает случайный горизонтальный скролл страницы */
  padding: 1px; /* Предотвращает схлопывание внешних отступов дочерних элементов */
}

.accounts-desktop {
  display: none;
}

.accounts-mobile {
  display: flex;
  flex-direction: column;
  gap: 5px; /* Отступ между карточками */
  padding: 0 3px; /* Небольшие отступы по бокам */
}

.accounts-table {
  border-collapse: collapse;
  margin-top: 10px; /* Отступ сверху */
  width: 100%;
}

.accounts-table .actions { 
  text-align: center; 
  white-space: nowrap; 
  width: 100px; 
}

.accounts-table .actual-balance { 
  font-weight: 600; 
}

.accounts-table .balance-container { 
  display: flex; 
  flex-direction: column; 
  gap: 3px; 
  text-align: right; 
}

.accounts-table .details-wrapper { /* Анимация для десктопа */
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.4s ease-out;
}

.accounts-table .historical-cell { 
  min-width: 100px; 
  text-align: right; 
}

.accounts-table .monthly-data .balance { 
  font-weight: 500; 
}

.accounts-table .monthly-data .interest { 
  color: #198754; 
  font-size: 0.85em; 
}

.accounts-table .monthly-data-na { 
  color: #adb5bd; 
  font-style: italic; 
  text-align: center; 
}

.accounts-table .projected-balance { 
  color: #0d6efd; 
  font-size: 0.9em; 
}

.accounts-table .transaction-details-row td {
  background-color: #fdfdfd;
  border-bottom: 1px solid #dee2e6; /* Граница снизу как у обычных строк */
  border-top: 1px dashed #e0e0e0;
  padding: 0;
}

.accounts-table td.negative .actual-balance { 
  color: #dc3545; 
}

.accounts-table td,
.accounts-table th {
  border-bottom: 1px solid #dee2e6;
  padding: 10px 12px;
  vertical-align: middle;
}

.accounts-table tfoot .totals-cell { 
  text-align: right; 
}

.accounts-table tfoot .totals-cell .balance-container,
.accounts-table tfoot .totals-cell .monthly-data { 
  text-align: right; 
}

.accounts-table tfoot .totals-cell .monthly-data .interest { 
  color: #198754; 
}

.accounts-table tfoot .totals-cell .projected-balance { 
  color: #0d6efd; 
}

.accounts-table tfoot .totals-row td {
  background-color: #f8f9fa;
  border-top: 2px solid #dee2e6;
  font-weight: bold;
}

.accounts-table th {
  background-color: #f8f9fa;
  font-weight: 600;
  text-align: left;
  white-space: nowrap;
}

.accounts-table th:last-child { 
  text-align: center; 
}

.accounts-table th:nth-child(1) { 
  text-align: left; 
}

.accounts-table th:nth-child(n+2) { 
  text-align: right; 
}

.action-button,
:deep(.action-button) /* Для кнопок внутри DeleteAccount */
{
  align-items: center;
  background-color: #fff;
  border: 1px solid;
  border-radius: 5px; /* Чуть больше скругления */
  box-sizing: border-box;
  cursor: pointer;
  display: inline-flex;
  flex-shrink: 0; /* Предотвращает сжатие кнопок в flex контейнере */
  font-size: 1.4em; /* Размер иконки/символа */
  font-weight: normal;
  height: 32px;  /* Стандартный размер */
  justify-content: center;
  line-height: 1;
  margin-right: 10px;
  overflow: hidden;
  padding: 0;
  text-align: center;
  transition: background-color 0.2s, color 0.2s, border-color 0.2s;
  vertical-align: middle;
  width: 32px;   /* Стандартный размер */
}

.action-button.create-button { 
  border-color: #198754; 
  color: #198754; 
}

.action-button.create-button:hover { 
  background-color: #198754; 
  color: white; 
}

.action-button.rate-button { 
  border-color: #ffc107; 
  color: #ffc107; 
}

.action-button.rate-button:hover { 
  background-color: #ffc107; 
  color: white; 
}

.action-button.transaction-button { 
  border-color: #0dcaf0; 
  color: #0dcaf0; 
}

.action-button.transaction-button:hover { 
  background-color: #0dcaf0; 
  color: white; 
}

.action-buttons {
  display: flex;
  gap: 10px; /* Увеличен отступ между кнопками */
}

.actual-balance {
  font-size: 1.1rem; /* Размер как у имени счета */
  font-weight: 600;
  white-space: nowrap;
}

.actual-balance.negative {
  color: #dc3545;
}

.balance-container {
  flex-shrink: 0; /* Не сжимать баланс */
  padding-left: 10px; /* Отступ слева от баланса */
  text-align: right;
}

.change-rate-form {
  display: flex;
  flex-direction: column;
  gap: 15px;
  padding: 20px; /* Увеличены отступы */
}

.change-rate-form .cancel-button { 
  background-color: #6c757d; 
  border: none; 
  border-radius: 5px; 
  color: white; 
  cursor: pointer; 
  font-weight: 500; 
  padding: 9px 18px; 
}

.change-rate-form .error { 
  color: #dc3545; 
  font-size: 0.9em; 
  margin-top: 5px;
  text-align: center; 
}

.change-rate-form input {
  border: 1px solid #ced4da;
  border-radius: 5px;
  font-size: 1em;
  padding: 10px 12px;
}

.change-rate-form input:focus {
  border-color: #86b7fe;
  box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
  outline: none;
}

.change-rate-form label { 
  font-weight: 500; 
  margin-bottom: -8px; 
}

.change-rate-form .modal-actions { 
  display: flex; 
  gap: 10px; 
  justify-content: flex-end; 
  margin-top: 15px; 
}

.change-rate-form .save-button { 
  background-color: #198754; 
  border: none; 
  border-radius: 5px; 
  color: white; 
  cursor: pointer; 
  font-weight: 500; 
  padding: 9px 18px; 
}

.close-button {
  background: none;
  border: none;
  color: #6c757d;
  cursor: pointer;
  font-size: 1.6rem; /* Крупнее крестик */
  font-weight: bold;
  line-height: 1;
  padding: 0 5px; /* Небольшой паддинг для клика */
}

.close-button:hover {
  color: #343a40;
}

.details-wrapper {
  max-height: 0; /* Начальное состояние - скрыто */
  overflow: hidden;
  transition: max-height 0.4s ease-out; /* Анимация */
}

.error {
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
  color: #dc3545;
}

.expand-icon {
  color: #888;
  flex-shrink: 0; /* Не сжимать */
  font-size: 0.8em;
}

.fade-enter, .fade-leave-to {
  opacity: 0;
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s;
}

.header-row {
  align-items: center;
  display: flex;
  flex-wrap: wrap; /* Перенос кнопок на новую строку на мал. экранах */
  gap: 10px; /* Отступ между заголовком и кнопками при переносе */
  justify-content: space-between; /* Заголовок слева, кнопки справа */
  margin-bottom: 20px; /* Больше отступ снизу */
  padding: 0 17px; /* Отступы по бокам для мобильных */
}

.history-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(80px, 1fr)); /* Адаптивные колонки */
}

.history-section,
.transactions-wrapper {
  border-top: 1px dashed #e0e0e0; /* Разделитель для доп. секций */
  margin-top: 15px;
  padding-top: 15px;
}

.interest-rate-label {
  color: #6c757d;
  flex-shrink: 0; /* Не сжимать */
  font-size: 0.8em;
  font-weight: normal;
  white-space: nowrap;
}

.loading, .error {
  font-size: 1em;
  margin: 15px 0;
  padding: 20px 15px; /* Добавлен горизонтальный паддинг */
  text-align: center;
}

.modal {
  align-items: center;
  background-color: rgba(0, 0, 0, 0.6); /* Чуть темнее фон */
  box-sizing: border-box;
  display: flex;
  height: 100%;
  justify-content: center;
  left: 0;
  padding: 15px; /* Отступы, чтобы модалка не прилипала к краям */
  position: fixed;
  top: 0;
  width: 100%;
  z-index: 1000;
}

.modal-content {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3); /* Заметнее тень */
  display: flex; /* Чтобы flex-direction работал */
  flex-direction: column; /* Шапка и контент друг под другом */
  max-height: calc(100vh - 40px); /* Макс высота с отступами */
  max-width: 500px; /* Макс ширина по умолчанию */
  overflow-y: auto; /* Внутренний скролл, если контент не влезает */
  width: 100%; /* Ширина по умолчанию */
}

.modal-content.small {
  max-width: 380px; /* Увеличена ширина для формы ставки */
}

.modal-header {
  align-items: center;
  border-bottom: 1px solid #dee2e6;
  display: flex;
  flex-shrink: 0; /* Шапка не должна сжиматься */
  justify-content: space-between;
  padding: 12px 15px; /* Уменьшен вертикальный паддинг */
}

.modal-header h3 {
  font-size: 1.2rem;
  font-weight: 600;
  margin: 0;
}

.month-card {
  background-color: #f8f9fa;
  border: 1px solid #eee;
  border-radius: 6px;
  padding: 8px;
  text-align: center;
}

.month-data { 
  display: flex; 
  flex-direction: column; 
  gap: 2px; 
}

.month-data .balance { 
  font-size: 0.9em; 
  font-weight: 500; 
}

.month-data .interest { 
  color: #198754; 
  font-size: 0.8em; 
}

.month-data-na { 
  color: #adb5bd; 
  font-size: 0.9em; 
  font-style: italic; 
}

.month-name {
  color: #495057;
  font-size: 0.8em;
  font-weight: 500;
  margin-bottom: 5px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.page-title {
  font-size: 1.6rem; /* Чуть больше */
  font-weight: 600;
  margin: 0;
}

.projected-balance {
  color: #0d6efd;
  font-size: 0.9em;
  white-space: nowrap;
}

.totals-card {
  background-color: #f8f9fa;
  border-color: #dee2e6;
  box-shadow: none;
}

.totals-card .account-name {
  font-weight: bold;
}

:deep(.action-button.delete-button) { 
  border-color: #dc3545; 
  color: #dc3545; 
}

:deep(.action-button.delete-button:hover) { 
  background-color: #dc3545; 
  color: white; 
}

:deep(.accounts-table .transaction-details-row .transaction-list) {
  border: none;
  box-shadow: none;
  padding: 15px; /* Внутренний отступ */
}

:deep(.accounts-table .transaction-details-row .transaction-list .header) {
  display: none;
}

:deep(.accounts-table .transaction-details-row .transactions-table-container) {
  border-top: 1px solid #eee;
  margin-top: 10px;
}

:deep(.transactions-wrapper .transaction-list) {
  /* Убираем лишние отступы/рамки у самого компонента TransactionList */
  border: none;
  box-shadow: none;
  padding: 0;
}

:deep(.transactions-wrapper .transaction-list .header) {
  display: none; /* Скрываем заголовок внутри */
}

:deep(.transactions-wrapper .transaction-list .transactions-table-container) {
  /* Контейнер таблицы внутри */
  border-top: 1px solid #eee;
  margin-top: 0; /* Убираем лишний отступ */
  max-height: 300px; /* Ограничиваем высоту списка транзакций */
  padding: 0; /* Убираем паддинг справа, если он не нужен в мобильной версии */
}

/* === Медиа-запросы для переключения Desktop/Mobile === */
@media (min-width: 992px) { /* Используем breakpoint побольше (lg) для переключения на таблицу */
  .accounts-container {
    padding: 10px 20px; /* Добавляем отступы на больших экранах */
  }

  .accounts-desktop {
    display: block; /* Показываем таблицу на десктопе */
  }

  .accounts-mobile {
    display: none; /* Скрываем карточки на десктопе */
  }

  .header-row {
    padding: 0; /* Убираем боковые отступы шапки на десктопе */
  }

  .modal-content {
    width: auto; /* Позволяем модалке быть шире */
    /* min-width: 500px; */ /* Можно убрать или настроить */
  }
}

/* Дополнительная адаптация для очень маленьких экранов */
@media (max-width: 400px) {
  .account-header {
    flex-wrap: wrap; /* Разрешаем перенос баланса под имя */
    gap: 5px;
  }

  .account-name {
    font-size: 1.0rem; /* Чуть меньше имя */
  }

  .actual-balance {
    font-size: 1.0rem;
  }

  .balance-container {
    /* width: 100%; */ /* Можно растянуть баланс */
    padding-left: 0;
    text-align: right; /* Убедимся, что он справа */
  }

  .history-grid {
    gap: 8px;
    grid-template-columns: repeat(auto-fit, minmax(70px, 1fr)); /* Еще меньше колонки истории */
  }

  .modal-content {
    max-width: calc(100% - 20px); /* Модалка чуть уже */
  }

  .modal-header h3 {
    font-size: 1.1rem;
  }

  .page-title {
    font-size: 1.4rem; /* Уменьшаем заголовок */
  }
}
</style>

<script>
import axios from 'axios';
import TransactionList from './TransactionList.vue';
import AddTransaction from './AddTransaction.vue';
import CreateAccount from './CreateAccount.vue';
import DeleteAccount from './DeleteAccount.vue';

export default {
  name: 'AccountList',
  components: {
    TransactionList,
    AddTransaction,
    CreateAccount,
    DeleteAccount,
  },
  data() {
    return {
      accounts: [],
      loading: true,
      error: null,
      showingAddTransaction: false,
      showingCreateAccount: false,
      showingGlobalRateModal: false,
      expandedAccountId: null, // ID аккаунта, чьи транзакции сейчас показаны
      selectedAccountForModal: null, // Для модальных окон
      newInterestRate: null,
      rateChangeError: null,
      apiBaseUrl: process.env.NODE_ENV === 'production'
        ? '' // В production используем относительные пути (предполагается прокси)
        : process.env.VUE_APP_API_BASE_URL || '', // Используем переменную из .env.local для разработки
    };
  },
  computed: {
    /**
     * Возвращает массив строк с ключами 3-х предыдущих месяцев (относительно текущего).
     */
    lastThreeMonths() {
      const months = [];
      const today = new Date();
      for (let i = 3; i >= 1; i--) {
        const d = new Date(today.getFullYear(), today.getMonth() - i, 1);
        const monthStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
        months.push(monthStr);
      }
      return months;
    },
    
    /**
     * Возвращает строку текущего месяца в формате YYYY-MM.
     */
    currentMonthStr() {
      const today = new Date();
      return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`;
    },
    
    /**
     * Рассчитывает общие суммы для текущего периода.
     */
    currentPeriodTotals() {
      return this.accounts.reduce((totals, account) => {
        // Суммируем текущий баланс
        const currentBalance = parseFloat(account.current_period?.current_balance || 0);
        totals.totalCurrentBalance += isNaN(currentBalance) ? 0 : currentBalance;
        
        // Суммируем прогнозируемый баланс
        const projectedBalance = parseFloat(account.current_period?.projected_eom_balance || 0);
        totals.totalProjectedEomBalance += isNaN(projectedBalance) ? 0 : projectedBalance;
        
        return totals;
      }, { totalCurrentBalance: 0, totalProjectedEomBalance: 0 });
    },
    
    /**
     * Рассчитывает общие суммы для каждого из предыдущих месяцев.
     */
    totalsByMonth() {
      const monthlyTotals = {};
      
      // Инициализируем объект для каждого месяца из заголовков
      this.lastThreeMonths.forEach(monthKey => {
        monthlyTotals[monthKey] = { totalEndBalance: 0, totalInterestAccrued: 0 };
      });
      
      // Проходим по всем счетам
      this.accounts.forEach(account => {
        // Проходим по месяцам, для которых есть ключи в итогах
        this.lastThreeMonths.forEach(monthKey => {
          const monthData = account.previous_months?.[monthKey];
          if (monthData) {
            // Суммируем баланс на конец месяца
            const endBalance = parseFloat(monthData.end_balance || 0);
            monthlyTotals[monthKey].totalEndBalance += isNaN(endBalance) ? 0 : endBalance;
            
            // Суммируем начисленные проценты
            const interestAccrued = parseFloat(monthData.interest_accrued || 0);
            monthlyTotals[monthKey].totalInterestAccrued += isNaN(interestAccrued) ? 0 : interestAccrued;
          }
        });
      });
      
      // Округляем итоговые суммы до 2 знаков после запятой
      Object.keys(monthlyTotals).forEach(monthKey => {
        monthlyTotals[monthKey].totalEndBalance = parseFloat(monthlyTotals[monthKey].totalEndBalance.toFixed(2));
        monthlyTotals[monthKey].totalInterestAccrued = parseFloat(monthlyTotals[monthKey].totalInterestAccrued.toFixed(2));
      });
      
      return monthlyTotals;
    }
  },
  methods: {
      
    /**
     * Форматирует число как валюту без символа валюты.
     */
    formatBalance(amount) {
      const numAmount = (typeof amount === 'string') ? parseFloat(amount) : amount;
      if (numAmount === undefined || numAmount === null || isNaN(numAmount)) return '-';
      
      return new Intl.NumberFormat('ru-RU', {
        style: 'decimal',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
        useGrouping: true
      }).format(numAmount);
    },
    
    /**
     * Обработчик обновления транзакций
     */
    handleTransactionsUpdate() {
      this.loadAccounts();
    },
    
    /**
     * Форматирует ключ месяца "YYYY-MM" в "Месяц".
     */
    formatMonthYear(monthKey) {
      if (!monthKey || !monthKey.includes('-')) return monthKey;
      
      try {
        const [year, month] = monthKey.split('-');
        const date = new Date(parseInt(year), parseInt(month) - 1, 1);
        return date.toLocaleString('ru-RU', { month: 'long' });
      } catch (e) {
        console.error("Error formatting month key:", monthKey, e);
        return monthKey;
      }
    },
    
    /**
     * Форматирует число для title атрибута.
     */
    formatValueForTitle(value) {
      const num = parseFloat(value);
      if (isNaN(num)) {
        return '0.00';
      }
      return num.toFixed(2);
    },
    
    /**
     * Переключает отображение транзакций для счета
     */
    toggleTransactions(accountId) {
      this.expandedAccountId = this.expandedAccountId === accountId ? null : accountId;
    },
    
    /**
     * Показывает модальное окно добавления транзакции
     */
     showAddTransaction(accountId, accountName) {
      this.selectedAccountForModal = this.accounts.find(acc => acc.id === accountId) || 
                                     { id: accountId, name: accountName || 'Счёт' };
      this.showingAddTransaction = true;
      this.showingCreateAccount = false;
      this.showingGlobalRateModal = false;
    },
    
    /**
     * Закрывает модальное окно добавления транзакции
     */
     closeAddTransaction() {
      this.showingAddTransaction = false;
      this.selectedAccountForModal = null;
    },
    
    /**
     * Показывает модальное окно создания счета
     */
     showCreateAccount() {
      this.showingCreateAccount = true;
      this.showingAddTransaction = false;
      this.showingGlobalRateModal = false;
    },
    
    /**
     * Закрывает модальное окно создания счета
     */
     closeCreateAccount() {
      this.showingCreateAccount = false;
    },
    
    /**
     * Показывает модальное окно изменения глобальной ставки
     */
     showGlobalRateModal() {
      this.fetchCurrentMonthRate();
      this.rateChangeError = null;
      this.showingGlobalRateModal = true;
      this.showingAddTransaction = false;
      this.showingCreateAccount = false;
    },
    
    /**
     * Закрывает модальное окно изменения глобальной ставки
     */
     closeGlobalRateModal() {
      this.showingGlobalRateModal = false;
      this.newInterestRate = null;
      this.rateChangeError = null;
    },
    
    /**
     * Получает текущую ставку месяца для предзаполнения поля
     */
     async fetchCurrentMonthRate() {
      try {
        // Используем apiBaseUrl
        const response = await axios.get(`${this.apiBaseUrl}/api/interest-rate/${this.currentMonthStr}`);
        if (response.data && response.data.rate !== undefined) {
          this.newInterestRate = response.data.rate;
        } else {
          this.newInterestRate = null;
        }
      } catch (error) {
        this.newInterestRate = null;
      }
    },
    
    /**
     * Обработчик после добавления транзакции или создания счета
     */
     async onActionComplete() {
      this.closeAddTransaction();
      this.closeCreateAccount();
      await this.loadAccounts();
    },
    
    /**
     * Сохраняет глобальную процентную ставку
     */
     async saveGlobalInterestRate() {
      if (this.newInterestRate === null || this.newInterestRate === undefined || this.newInterestRate < 0) {
        this.rateChangeError = "Пожалуйста, введите корректную неотрицательную ставку.";
        return;
      }

      this.rateChangeError = null;
      const ratePayload = { rate: this.newInterestRate };
      const monthToUpdate = this.currentMonthStr;

      try {
        // Используем apiBaseUrl
        await axios.put(`${this.apiBaseUrl}/api/interest-rate/${monthToUpdate}`, ratePayload);
        this.closeGlobalRateModal();
        await this.loadAccounts();
      } catch (error) {
        this.rateChangeError = 'Ошибка при сохранении ставки: ' +
                             (error.response?.data?.detail || error.message);
      }
    },
    
    /**
     * Загружает список счетов с сервера
     */
     async loadAccounts() {
      this.loading = true;
      this.error = null;

      const timeoutId = setTimeout(() => { // Перенес объявление timeoutId выше
        if (this.loading) {
          // {{ Remove this.log call }}
          // this.log('Request timed out.', 'ERROR');
          console.error('Request timed out.'); // Use console.error instead
          this.loading = false;
          this.error = 'Request timed out. Please check server connectivity.';
        }
      }, 15000); // Таймаут 15 секунд

      try {
        const startTime = performance.now();
        // Используем apiBaseUrl
        const response = await axios.get(`${this.apiBaseUrl}/api/accounts`);
        const endTime = performance.now();
        clearTimeout(timeoutId); // Очищаем таймаут при успехе

        // {{ Remove this.log call }}
        // this.log(`Accounts loaded in ${(endTime - startTime).toFixed(2)}ms`, 'INFO');
        console.info(`Accounts loaded in ${(endTime - startTime).toFixed(2)}ms`); // Use console.info instead

        // ... обработка ответа ...
        this.accounts = response.data;
      } catch (error) {
         clearTimeout(timeoutId); // Очищаем таймаут при ошибке
         // {{ Remove this.log call }}
         // this.log("Ошибка при загрузке счетов.", 'ERROR');
         console.error("Ошибка при загрузке счетов:", error); // Use console.error instead
         // ... логирование ошибки ...
         this.error = (error.response?.data?.detail || error.message || 'Неизвестная ошибка сети');
         this.accounts = [];
      } finally {
        this.loading = false;
        // ... финальное логирование ...
      }
    }
  },

  async created() {
    await this.loadAccounts();
  }
};
</script>