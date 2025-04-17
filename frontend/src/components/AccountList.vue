<template>
  <div class="accounts-container">
    <div class="header-row">
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

    <div v-if="loading" class="loading">Загрузка счетов...</div>

    <div v-else-if="error" class="error">
      Ошибка при загрузке данных: {{ error }}
    </div>

    <div v-else>
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
                  @click="toggleTransactions(account.id)" :title="`${ expandedAccountId === account.id ? 'Скрыть' : 'Показать'} транзакции для ${account.name}`"
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
                  v-if="account.previous_months[monthKey]"
                >
                  <div class="balance" title="Остаток на конец месяца">
                    {{
                      formatBalance(
                        account.previous_months[monthKey].end_balance
                      )
                    }}
                  </div>
                  <div class="interest" title="Начислено процентов за месяц">
                    +{{
                      formatBalance(
                        account.previous_months[monthKey].interest_accrued
                      )
                    }}
                  </div>
                </div>
                <div v-else class="monthly-data-na">-</div>
              </td>

              <td
                :class="{ negative: account.current_period.current_balance < 0 }"
              >
                <div class="balance-container">
                  <div class="actual-balance" title="Текущий фактический баланс">
                    {{
                      formatBalance(account.current_period.current_balance)
                    }}
                  </div>
                  <div
                    class="projected-balance"
                    :title="`Прогноз на конец ${formatMonthYear(
                      currentMonthStr
                    )} с учетом процентов (${formatValueForTitle(
                      account.current_period.projected_interest
                    )} ₽)`"
                  >
                    {{
                      formatBalance(
                        account.current_period.projected_eom_balance
                      )
                    }}
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
              <td :colspan="1 + lastThreeMonths.length + 1 + 1">
                <div class="details-wrapper" :style="{ maxHeight: expandedAccountId === account.id ? '1000px' : '0px' }">
                    <TransactionList
                        :account-id="account.id"
                        :account-name="account.name"
                        @transactions-updated="handleTransactionsUpdate"
                        :key="account.id + '-tx'" />
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
              :key="monthKey + '-total'"
              class="historical-cell totals-cell"
            >
              <div v-if="totalsByMonth[monthKey]" class="monthly-data">
                <div class="balance" title="Сумма остатков на конец месяца">
                  {{
                    formatBalance(totalsByMonth[monthKey].totalEndBalance)
                  }}
                </div>
                <div
                  class="interest"
                  title="Сумма начисленных процентов за месяц"
                >
                  +{{
                    formatBalance(
                      totalsByMonth[monthKey].totalInterestAccrued
                    )
                  }}
                </div>
              </div>
              <div v-else class="monthly-data-na">-</div>
            </td>

            <td class="totals-cell">
              <div class="balance-container">
                <div class="actual-balance" title="Сумма текущих балансов">
                  {{
                    formatBalance(currentPeriodTotals.totalCurrentBalance)
                  }}
                </div>
                <div
                  class="projected-balance"
                  title="Сумма прогнозируемых балансов на конец месяца"
                >
                  {{
                    formatBalance(
                      currentPeriodTotals.totalProjectedEomBalance
                    )
                  }}
                </div>
              </div>
            </td>

            <td></td> </tr>
        </tfoot>
      </table>

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

      <div v-if="showingGlobalRateModal" class="modal">
        <div class="modal-content small"> <div class="modal-header">
           <h3>Ставка за {{ formatMonthYear(currentMonthStr) }}</h3>
           <button @click="closeGlobalRateModal" class="close-button">&times;</button>
         </div>
         <div class="change-rate-form">
            <label for="global-rate-input">Новая ставка (%):</label>
            <input
               type="number"
               id="global-rate-input"
               v-model.number="newInterestRate" min="0"
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
/* === Общие стили контейнера и загрузки === */
.accounts-container {
  /* Можно добавить стили для общего контейнера, если нужно */
  /* Например: padding: 20px; */
}

.loading, .error {
  text-align: center;
  padding: 20px;
  font-size: 1.0em;
}
.error {
  color: #dc3545;
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
}

.header-row {
  margin-bottom: 15px; /* Отступ снизу от кнопок до таблицы */
  display: flex;
  gap: 10px; /* Пространство между кнопками */
  /* align-items: center; */ /* Если нужно выровнять по вертикали */
}

/* === Стили таблицы счетов === */
.accounts-table {
  width: 100%;
  border-collapse: collapse;
  /* table-layout: fixed; */ /* Раскомментируйте, если хотите фиксированную ширину столбцов */
}

.accounts-table th,
.accounts-table td {
  padding: 10px 12px;
  vertical-align: middle;
  border-bottom: 1px solid #dee2e6; /* Стандартная граница строки */
}

.accounts-table th {
  background-color: #f8f9fa;
  font-weight: 600;
  text-align: left; /* Выравнивание заголовков по левому краю */
  white-space: nowrap;
}
.accounts-table th:nth-child(1) { text-align: left; } /* Первый столбец - счет */
.accounts-table th:nth-child(n+2) { text-align: right; } /* Остальные (месяцы, баланс) - вправо */
.accounts-table th:last-child { text-align: center; } /* Последний (действия) - центр */


/* === Стили ячеек таблицы === */

/* Имя счета (кликабельное) */
.account-name.clickable {
  cursor: pointer;
  display: inline-flex; /* Чтобы иконка была на той же строке */
  align-items: center;
  font-weight: 500; /* Слегка выделить имя счета */
  transition: color 0.15s ease-in-out;
}
.account-name.clickable:hover {
  color: #0056b3;
  text-decoration: none; /* Убираем подчеркивание, если оно есть по умолчанию */
}
.interest-rate-label {
  font-size: 0.8em;
  color: #6c757d;
  margin-left: 6px;
  font-weight: normal;
  white-space: nowrap; /* Не переносить ставку */
}
.expand-icon {
  display: inline-block;
  margin-left: 8px;
  font-size: 0.8em;
  color: #888;
  transition: transform 0.2s ease-in-out; /* Анимация поворота иконки */
}
.account-name.clickable:hover .expand-icon {
  color: #555;
}
/* Если нужно поворачивать иконку: */
/* .account-name.expanded .expand-icon {
     transform: rotate(180deg);
} */

/* Исторические данные (прошлые месяцы) */
.historical-cell {
  min-width: 100px;
  text-align: right;
}
.monthly-data .balance {
    font-weight: 500;
    /* font-size: 0.95em; */
}
.monthly-data .interest {
    font-size: 0.85em;
    color: #198754; /* Используем тот же зеленый, что и в TransactionList */
}
.monthly-data-na {
    color: #adb5bd; /* Сделать 'н/д' менее заметным */
    text-align: center;
    font-style: italic;
}

/* Текущий баланс и прогноз */
.balance-container {
  display: flex;
  flex-direction: column;
  gap: 3px; /* Чуть больше разрыв для читаемости */
  text-align: right;
}
.actual-balance {
  font-weight: 600; /* Текущий баланс жирнее */
}
.projected-balance {
  font-size: 0.9em;
  color: #0d6efd; /* Используем тот же синий, что и в TransactionList */
}
/* Стиль для отрицательного баланса */
td.negative .actual-balance {
    color: #dc3545;
}

/* Ячейка с кнопками действий */
.actions {
  text-align: center;
  white-space: nowrap;
  width: 100px; /* Немного больше места для кнопок */
}

/* === Стили подвала таблицы (Итоги) === */
tfoot .totals-row td {
  font-weight: bold;
  border-top: 2px solid #dee2e6;
  background-color: #f8f9fa;
}

tfoot .totals-cell {
  text-align: right;
}
/* Убедимся, что контейнеры внутри итогов выровнены */
tfoot .totals-cell .balance-container,
tfoot .totals-cell .monthly-data {
  text-align: right;
}
/* Сохраняем цвета для процентов и прогноза в итогах */
tfoot .totals-cell .monthly-data .interest {
  color: #198754;
}
tfoot .totals-cell .projected-balance {
  color: #0d6efd;
}

/* === Стили кнопок действий (верхние и в строках) === */

/* Общие стили для всех маленьких квадратных кнопок */
:deep(.action-button), /* Для кнопок в DeleteAccount */
.action-button /* Для кнопок в этом компоненте */
{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;            /* Чуть меньше */
  height: 30px;           /* Чуть меньше */
  padding: 0;
  box-sizing: border-box;
  margin: 0 2px;
  border: 1px solid;
  border-radius: 4px; /* Слегка скруглим */
  background-color: #fff;
  font-size: 1.6em; /* Уменьшим иконку/текст */
  font-weight: normal; /* Уберем жирность, если не нужна */
  line-height: 1;
  text-align: center;
  vertical-align: middle;
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s, border-color 0.2s;
  overflow: hidden;
}

/* Кнопка Ставки (%) */
.action-button.rate-button {
  border-color: #ffc107;
  color: #ffc107;
}
.action-button.rate-button:hover {
  background-color: #ffc107;
  color: white;
}

/* Кнопка Создать (+) */
.action-button.create-button {
  /* border-color: #07ff77; */ /* Яркий цвет */
  /* color: #07ff77; */
   border-color: #198754; /* Стандартный зеленый */
   color: #198754;
}
.action-button.create-button:hover {
  /* background-color: #07ff77; */
  background-color: #198754;
  color: white;
}

/* Кнопка Добавить транзакцию (±) */
.action-button.transaction-button {
  /* border-color: #17a2b8; */ /* Бирюзовый */
  /* color: #17a2b8; */
   border-color: #0dcaf0; /* Голубой */
   color: #0dcaf0;
}
.action-button.transaction-button:hover {
  /* background-color: #17a2b8; */
  background-color: #0dcaf0;
  color: white;
}

/* Кнопка Удалить аккаунт (X) - стилизуется через :deep() */
:deep(.action-button.delete-button) {
  border-color: #dc3545;
  color: #dc3545;
}
:deep(.action-button.delete-button:hover) {
  background-color: #dc3545;
  color: white;
}


/* === Стили для раскрывающегося блока транзакций === */

/* Строка, содержащая TransactionList */
.transaction-details-row td {
  padding: 0; /* Убираем паддинг ячейки */
  background-color: #fdfdfd; /* Очень легкий фон */
  border-top: 1px dashed #e0e0e0; /* Менее заметный разделитель */
  /* Убираем нижнюю границу, чтобы не было двойной линии с TransactionList */
  border-bottom: none;
}

/* Обертка для анимации max-height */
.details-wrapper {
  overflow: hidden;
  max-height: 0; /* Начальное состояние - скрыто */
  transition: max-height 0.4s ease-out; /* Плавное раскрытие/скрытие */
}

/* Переопределение стилей TransactionList для лучшего встраивания */
:deep(.transaction-details-row .transaction-list) {
  padding: 15px; /* Внутренний отступ для содержимого */
  box-shadow: none;
  border-radius: 0;
  max-width: 100%;
  margin: 0;
  border: none; /* Убираем свои рамки */
  /* Добавим тонкую рамку сверху для отделения, если нужно */
  /* border-top: 1px solid #eee; */
}
/* Скрытие заголовка внутри TransactionList */
:deep(.transaction-details-row .transaction-list .header) {
  display: none;
}
/* Стилизация контейнера таблицы внутри TransactionList */
:deep(.transaction-details-row .transactions-table-container) {
  border-top: 1px solid #eee; /* Линия над таблицей транзакций */
  margin-top: 10px; /* Отступ от возможного (скрытого) заголовка */
}


/* === Стили для оставшихся модальных окон === */
.modal-content.wide {
    max-width: 70%; /* Шире для списка транзакций (Если это окно все еще используется) */
}
.modal-content.small {
    max-width: 350px; /* Чуть шире для формы ставки */
}

/* Форма изменения ставки */
.change-rate-form {
    display: flex;
    flex-direction: column;
    gap: 15px;
    padding: 10px 5px; /* Небольшой внутренний отступ */
}
.change-rate-form label {
    margin-bottom: -10px; /* Меньше отступ */
    font-weight: 500;
    font-size: 0.95em;
}
.change-rate-form input {
    padding: 8px 10px;
    border: 1px solid #ced4da;
    border-radius: 4px;
    font-size: 1em;
}
.change-rate-form input:focus {
    outline: none;
    border-color: #86b7fe;
    box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
}
.change-rate-form .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 10px;
}
.change-rate-form .save-button,
.change-rate-form .cancel-button {
    padding: 8px 15px;
    border-radius: 4px;
    cursor: pointer;
    border: none;
    font-weight: 500;
    transition: background-color 0.2s, opacity 0.2s;
}
.change-rate-form .save-button {
    background-color: #198754; /* Зеленый */
    color: white;
}
.change-rate-form .save-button:hover {
    background-color: #157347;
}
.change-rate-form .cancel-button {
    background-color: #6c757d; /* Серый */
    color: white;
}
.change-rate-form .cancel-button:hover {
    background-color: #5c636a;
}
.change-rate-form .error {
    color: #dc3545;
    font-size: 0.9em;
    margin-top: -5px;
    text-align: center;
}

</style>

<script>
import axios from 'axios';
import TransactionList from './TransactionList.vue'; // Предполагаем, что этот компонент существует
import AddTransaction from './AddTransaction.vue';   // Предполагаем, что этот компонент существует
import CreateAccount from './CreateAccount.vue';     // Предполагаем, что этот компонент существует
import DeleteAccount from './DeleteAccount.vue';     // Предполагаем, что этот компонент существует
// import ChangeInterestRate from './ChangeInterestRate.vue'; // Опционально, если выносить в отдельный компонент

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
    // showingTransactionList: false,
    showingAddTransaction: false,
    showingCreateAccount: false,
    showingGlobalRateModal: false,
    // selectedAccountForModal: null,
    expandedAccountId: null, // ID аккаунта, чьи транзакции сейчас показаны, null если все свернуты
    newInterestRate: null,
    rateChangeError: null,
    };
  },

  computed: {
    /**
     * Возвращает массив строк с ключами 3-х предыдущих месяцев (относительно текущего).
     * Пример: если сейчас апрель 2025, вернет ["2025-01", "2025-02", "2025-03"]
     */
    lastThreeMonths() {
      const months = [];
      const today = new Date();
      for (let i = 3; i >= 1; i--) { // Идем назад на 3, 2, 1 месяц
        // new Date(year, monthIndex (0-11), day)
        const d = new Date(today.getFullYear(), today.getMonth() - i, 1);
        const monthStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
        months.push(monthStr);
      }
  //    console.log("Previous months keys:", months); // Для отладки
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
     * @returns {{ totalCurrentBalance: number, totalProjectedEomBalance: number }}
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
      }, { totalCurrentBalance: 0, totalProjectedEomBalance: 0 }); // Начальные значения сумм
    },

    /**
     * Рассчитывает общие суммы для каждого из предыдущих месяцев.
     * @returns {Object.<string, { totalEndBalance: number, totalInterestAccrued: number }>}
     * Пример: { "2025-03": { totalEndBalance: 15000, totalInterestAccrued: 150.50 }, ... }
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
          const monthData = account.previous_months?.[monthKey]; // Безопасный доступ
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

        // Округляем итоговые суммы до 2 знаков после запятой (опционально, но желательно)
        Object.keys(monthlyTotals).forEach(monthKey => {
            monthlyTotals[monthKey].totalEndBalance = parseFloat(monthlyTotals[monthKey].totalEndBalance.toFixed(2));
            monthlyTotals[monthKey].totalInterestAccrued = parseFloat(monthlyTotals[monthKey].totalInterestAccrued.toFixed(2));
        });

      return monthlyTotals;
    }

  },

  methods: {
    /**
     * Форматирует число как валюту RUB.
     */
formatBalance(amount) {
    // Преобразуем в число, если это строка (API может вернуть Decimal как строку)
    const numAmount = (typeof amount === 'string') ? parseFloat(amount) : amount;
    if (numAmount === undefined || numAmount === null || isNaN(numAmount)) return '-';
    return new Intl.NumberFormat('ru-RU', {
        style: 'decimal',                   // Используем обычный числовой стиль
        minimumFractionDigits: 2,           // Всегда отображаем минимум 2 цифры после запятой
        maximumFractionDigits: 2,           // Максимальная длина дробной части — 2 цифры
        useGrouping: true                   // Включаем группировку разрядов (разделители тысяч)
    }).format(numAmount);
},

    handleTransactionsUpdate() {
        console.log("Transaction list updated, reloading accounts...");
        this.loadAccounts(); // Перезагружаем список счетов для обновления баланса
    },

    /**
     * Форматирует ключ месяца "YYYY-MM" в "Месяц Год".
     */
     formatMonthYear(monthKey) {
    if (!monthKey || !monthKey.includes('-')) return monthKey; // Возвращаем как есть, если формат неверный
    try {
        const [year, month] = monthKey.split('-');
        // В JS месяцы 0-11, поэтому month - 1
        const date = new Date(parseInt(year), parseInt(month) - 1, 1);
        return date.toLocaleString('ru-RU', { month: 'long' }); // Оставляем только месяц
    } catch (e) {
        console.error("Error formatting month key:", monthKey, e);
        return monthKey; // Возвращаем исходный ключ при ошибке
    }
},

    /**
     * Безопасно форматирует число (полученное как строка или число) для title атрибута.
     * @param {*} value Значение для форматирования (может быть строкой, числом, null)
     * @returns {string} Отформатированная строка (e.g., "22.50") или дефолтное значение.
     */
     formatValueForTitle(value) {
        const num = parseFloat(value); // Преобразуем в число
        if (isNaN(num)) {
             // Возвращаем дефолтное значение, если не число
            return '0.00'; // или '-', или 'н/д'
        }
        return num.toFixed(2); // Форматируем число
    },

    /**
     * Получает отформатированный баланс на конец месяца для счета и ключа месяца.
     */
    getHistoricalBalance(account, monthKey) {
      const monthData = account.previous_months?.[monthKey];
      // Проверяем наличие данных и самого значения end_balance
      return (monthData && monthData.end_balance !== null && monthData.end_balance !== undefined)
             ? this.formatBalance(monthData.end_balance)
             : "-";
    },

    /**
     * Получает отформатированные проценты, начисленные за месяц, для счета и ключа месяца.
     */
    getHistoricalInterest(account, monthKey) {
      const monthData = account.previous_months?.[monthKey];
       // Проверяем наличие данных и самого значения interest_accrued
      return (monthData && monthData.interest_accrued !== null && monthData.interest_accrued !== undefined)
             ? this.formatBalance(monthData.interest_accrued)
             : "-";
    },

// --- Управление Модальными Окнами ---

    //showTransactions(accountId, accountName) {
    //  this.selectedAccountForModal = { id: accountId, name: accountName };
    //  this.showingTransactionList = true;
    //  this.showingAddTransaction = false;
    //  this.showingCreateAccount = false;
    //  this.showingGlobalRateModal = false; 
    //},

    toggleTransactions(accountId) {
    if (this.expandedAccountId === accountId) {
      // Если кликнули по уже раскрытому счету, сворачиваем
      this.expandedAccountId = null;
    } else {
      // Раскрываем новый счет (старый автоматически свернется)
      this.expandedAccountId = accountId;
      // Важно: Не нужно вызывать fetchTransactions здесь,
      // так как TransactionList сам загрузит свои данные при отрисовке
    }
    },    

    // closeTransactionList() {
    //   this.showingTransactionList = false;
    //   this.selectedAccountForModal = null;
    //},

    showAddTransaction(accountId, accountName) { // Добавим имя для заголовка
      // Ищем полный объект аккаунта, чтобы показать имя в заголовке
      this.selectedAccountForModal = this.accounts.find(acc => acc.id === accountId) || { id: accountId, name: accountName || 'Счет' };
      this.showingAddTransaction = true;
      this.showingTransactionList = false;
      this.showingCreateAccount = false;
      this.showingGlobalRateModal = false; 
    },
    closeAddTransaction() {
      this.showingAddTransaction = false;
       this.selectedAccountForModal = null;
    },

    showCreateAccount() {
      this.showingCreateAccount = true;
      this.showingTransactionList = false;
      this.showingAddTransaction = false;
      this.showingGlobalRateModal = false; 
      this.selectedAccountForModal = null;
    },
    closeCreateAccount() {
      this.showingCreateAccount = false;
    },

    showGlobalRateModal() {
      // Пытаемся получить текущую ставку месяца для предзаполнения поля
      this.fetchCurrentMonthRate(); // Вызываем вспомогательный метод
      this.rateChangeError = null; // Сбрасываем ошибку
      this.showingGlobalRateModal = true; // Показываем окно

      // Убедимся, что другие окна закрыты
      this.showingTransactionList = false;
      this.showingAddTransaction = false;
      this.showingCreateAccount = false;
    },

    closeGlobalRateModal() {
      this.showingGlobalRateModal = false;
      this.newInterestRate = null; // Сбрасываем поле ввода
      this.rateChangeError = null; // Сбрасываем ошибку
    },

    // --- Обработчики после действий ---
    async onActionComplete() {
      // Вызывается после добавления транзакции или создания счета
      this.closeAddTransaction(); // Закрываем окно добавления транзакции, если было открыто
      this.closeCreateAccount(); // Закрываем окно создания счета, если было открыто
      // Не нужно вызывать closeGlobalRateModal здесь
      await this.loadAccounts(); // Перезагружаем список
    },

     async saveGlobalInterestRate() {
        // Валидация ввода
        if (this.newInterestRate === null || this.newInterestRate === undefined || this.newInterestRate < 0) {
            this.rateChangeError = "Пожалуйста, введите корректную неотрицательную ставку.";
            return;
        }
        this.rateChangeError = null; // Сброс ошибки перед запросом

        const ratePayload = { rate: this.newInterestRate };
        // Используем currentMonthStr из computed properties
        const monthToUpdate = this.currentMonthStr;

        try {
            console.log(`Sending PUT to /api/interest-rate/${monthToUpdate} with payload:`, ratePayload);
            // Вызываем API для установки/обновления ставки на месяц
            await axios.put(`/api/interest-rate/${monthToUpdate}`, ratePayload);
            this.closeGlobalRateModal(); // Закрываем окно при успехе
            await this.loadAccounts(); // Обновляем список счетов
        } catch (error) {
            console.error("Error updating global interest rate:", error);
            // Показываем ошибку пользователю
            this.rateChangeError = 'Ошибка при сохранении ставки: ' + (error.response?.data?.detail || error.message);
        }
    },

    // --- ДОБАВЛЕН вспомогательный метод для получения текущей ставки ---
    async fetchCurrentMonthRate() {
        // Используем currentMonthStr из computed properties
        const monthToFetch = this.currentMonthStr;
        try {
            // Используем эндпоинт GET /api/interest-rate для получения ставки
            const response = await axios.get(`/api/interest-rate?month=${monthToFetch}`);
            // Если API вернуло ставку, устанавливаем ее в поле ввода
            if (response.data && response.data.rate !== null && response.data.rate !== undefined) {
                // Преобразуем в число, т.к. API может вернуть Decimal как строку
                this.newInterestRate = parseFloat(response.data.rate);
            } else {
                // Если ставка не установлена, очищаем поле
                this.newInterestRate = null;
            }
        } catch (error) {
             console.error(`Error fetching interest rate for ${monthToFetch}:`, error);
             // При ошибке просто очищаем поле
             this.newInterestRate = null;
        }
    },

    // --- Метод loadAccounts() здесь не нужен, он находится ниже ---
    // async loadAccounts() { ... }

    // --- Загрузка Данных ---
    async loadAccounts() {
      this.loading = true; // Устанавливаем флаг загрузки
      this.error = null;   // Сбрасываем предыдущие ошибки
      console.log("Loading accounts from /api/accounts");
      try {
        const response = await axios.get('/api/accounts');
        console.log("API Response:", response.data); // Отладка ответа API

        // Используем данные напрямую, так как бэкенд теперь возвращает нужную структуру
        this.accounts = response.data;

        // Проверка структуры полученных данных (для отладки)
        if (this.accounts.length > 0) {
            console.log("First account structure:", this.accounts[0]);
            console.log("Previous months data for first account:", this.accounts[0].previous_months);
            console.log("Current period data for first account:", this.accounts[0].current_period);
        }


      } catch (error) {
         console.error("Error loading accounts:", error);
         // Устанавливаем сообщение об ошибке для отображения пользователю
        this.error = (error.response?.data?.detail || error.message || 'Неизвестная ошибка сети');
        this.accounts = []; // Очищаем список при ошибке
      } finally {
        this.loading = false; // Снимаем флаг загрузки в любом случае
      }
    }
  },
  // --- Хук Жизненного Цикла ---
  async created() {
    // Загружаем данные при создании компонента
    await this.loadAccounts();
  }
};
</script>