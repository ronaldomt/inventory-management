<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="eligibleItems.length === 0" class="card empty-state">
      {{ t('restocking.noEligible') }}
    </div>
    <div v-else>
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.budget') }}</h3>
          <strong class="budget-value">{{ money(budget) }}</strong>
        </div>
        <input
          v-model.number="budget"
          type="range"
          class="budget-slider"
          min="0"
          :max="maxBudget"
          :step="budgetStep"
          :aria-label="t('restocking.budgetLabel')"
        />
        <div class="slider-scale">
          <span>{{ money(0) }}</span>
          <span>{{ money(maxBudget) }}</span>
        </div>
        <p class="rule-note">{{ t('restocking.rule') }}</p>
      </div>

      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.budget') }}</div>
          <div class="stat-value">{{ money(budget) }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.recommendedTotal') }}</div>
          <div class="stat-value">{{ money(recommendedTotal) }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.remainingBudget') }}</div>
          <div class="stat-value">{{ money(remainingBudget) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('restocking.itemsToOrder') }}</div>
          <div class="stat-value">{{ recommendedItems.length }}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendedItems') }} ({{ recommendedItems.length }})</h3>
          <button
            type="button"
            class="place-order-btn"
            :disabled="recommendedItems.length === 0 || submitting || alreadySubmitted"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.placing') : alreadySubmitted ? t('restocking.orderPlaced') : t('restocking.placeOrder') }}
          </button>
        </div>

        <div v-if="successMessage" class="success-message" role="status">
          <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true">
            <path d="M4 10.5l4 4 8-9" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          <span>{{ successMessage }}</span>
          <router-link to="/orders" class="success-link">{{ t('restocking.viewOrders') }}</router-link>
        </div>
        <div v-if="submitError" class="error" role="alert">{{ submitError }}</div>

        <div v-if="recommendedItems.length === 0" class="empty-state">
          {{ t('restocking.empty') }}
        </div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.itemName') }}</th>
                <th>{{ t('restocking.table.quantity') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.lineTotal') }}</th>
                <th>{{ t('restocking.table.leadTime') }}</th>
                <th>{{ t('restocking.table.growth') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in recommendedItems" :key="item.sku">
                <td><strong>{{ item.sku }}</strong></td>
                <td>{{ translateProductName(item.name) }}</td>
                <td>{{ item.quantity.toLocaleString() }}</td>
                <td>{{ money(item.unitCost, 2) }}</td>
                <td><strong>{{ money(item.cost) }}</strong></td>
                <td>{{ t('restocking.days', { count: item.leadTimeDays }) }}</td>
                <td>{{ formatGrowth(item.growth) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrency, formatCurrencyWithDecimals } from '../utils/currency'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, translateProductName } = useI18n()

    const loading = ref(true)
    const error = ref(null)
    const demandItems = ref([])
    const budget = ref(0)
    const submitting = ref(false)
    const successMessage = ref('')
    const submitError = ref('')

    // Money is always held in USD; formatCurrency converts for display when the locale is ja
    const money = (amount, decimals = 0) => {
      return decimals > 0
        ? formatCurrencyWithDecimals(amount, currentCurrency.value, decimals)
        : formatCurrency(amount, currentCurrency.value)
    }

    const formatGrowth = (growth) => {
      const percent = (growth * 100).toFixed(1)
      return growth > 0 ? `+${percent}%` : `${percent}%`
    }

    // Only items whose demand is flat or rising are worth restocking; we order the forecasted quantity.
    // Cost is kept in integer cents so the budget comparison never suffers from float drift.
    const eligibleItems = computed(() => {
      return demandItems.value
        .filter(d => d.trend === 'increasing' || d.trend === 'stable')
        .map(d => {
          const costCents = Math.round(d.forecasted_demand * d.unit_cost * 100)
          return {
            sku: d.item_sku,
            name: d.item_name,
            quantity: d.forecasted_demand,
            unitCost: d.unit_cost,
            leadTimeDays: d.lead_time_days,
            costCents,
            cost: costCents / 100,
            // Guard against a zero baseline so growth is never NaN/Infinity
            growth: d.current_demand > 0
              ? (d.forecasted_demand - d.current_demand) / d.current_demand
              : 0
          }
        })
    })

    // Slider max is the cost of buying every eligible item, rounded up to a whole step
    // so the right end of the slider always affords the full list.
    const totalEligibleCents = computed(() => {
      return eligibleItems.value.reduce((sum, item) => sum + item.costCents, 0)
    })

    // Step is one hundredth of the max's order of magnitude (e.g. max 72,100 -> step 100)
    const budgetStep = computed(() => {
      const total = totalEligibleCents.value / 100
      if (total < 1) return 1
      return Math.max(1, Math.pow(10, Math.floor(Math.log10(total)) - 2))
    })

    const maxBudget = computed(() => {
      return Math.ceil(totalEligibleCents.value / 100 / budgetStep.value) * budgetStep.value
    })

    // Greedy budget fill: rank by growth (highest first), then walk the list and take an item
    // only if its FULL cost fits in what is left. An item that does not fit is skipped, not
    // truncated, and the walk continues because a cheaper item further down may still fit.
    const recommendedItems = computed(() => {
      const ranked = [...eligibleItems.value].sort((a, b) => b.growth - a.growth)
      let remainingCents = Math.round(budget.value * 100)
      const picked = []
      for (const item of ranked) {
        if (item.costCents <= remainingCents) {
          picked.push(item)
          remainingCents -= item.costCents
        }
      }
      return picked
    })

    const recommendedTotal = computed(() => {
      return recommendedItems.value.reduce((sum, item) => sum + item.costCents, 0) / 100
    })

    const remainingBudget = computed(() => budget.value - recommendedTotal.value)

    // Identifies the exact order the user is about to place (same SKUs, same quantities).
    // After a successful submit we remember it, so the same order cannot be placed twice
    // by a second click. Moving the slider to a different recommendation unlocks the button.
    const orderKey = computed(() => {
      return recommendedItems.value.map(item => `${item.sku}:${item.quantity}`).join(',')
    })
    const submittedKey = ref('')
    const alreadySubmitted = computed(() => submittedKey.value !== '' && submittedKey.value === orderKey.value)

    // The "order submitted" message only describes the order that was placed, so drop it
    // as soon as the recommendation changes to something else.
    watch(orderKey, (key) => {
      if (key !== submittedKey.value) successMessage.value = ''
    })

    const loadDemand = async () => {
      try {
        loading.value = true
        error.value = null
        demandItems.value = await api.getDemandForecasts()
        // Default to half the max budget, snapped to the step
        budget.value = Math.round(maxBudget.value / 2 / budgetStep.value) * budgetStep.value
      } catch (err) {
        error.value = t('restocking.loadFailed') + ': ' + err.message
      } finally {
        loading.value = false
      }
    }

    const placeOrder = async () => {
      if (recommendedItems.value.length === 0 || submitting.value || alreadySubmitted.value) return
      // Capture the key now: the slider can move while the request is in flight
      const keyAtSubmit = orderKey.value
      submitting.value = true
      successMessage.value = ''
      submitError.value = ''
      try {
        // Only sku and quantity are sent; the server looks up prices and totals
        const lines = recommendedItems.value.map(item => ({ sku: item.sku, quantity: item.quantity }))
        const order = await api.createRestockingOrder(lines)
        submittedKey.value = keyAtSubmit
        // Show the message only if the recommendation still matches the order that was placed
        if (orderKey.value === keyAtSubmit) {
          successMessage.value = t('restocking.orderSuccess', {
            orderNumber: order.order_number,
            days: order.lead_time_days
          })
        }
      } catch (err) {
        const detail = err.response?.data?.detail
        submitError.value = typeof detail === 'string' ? detail : t('restocking.orderFailed')
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadDemand)

    return {
      t,
      translateProductName,
      loading,
      error,
      budget,
      budgetStep,
      maxBudget,
      eligibleItems,
      recommendedItems,
      recommendedTotal,
      remainingBudget,
      submitting,
      alreadySubmitted,
      successMessage,
      submitError,
      money,
      formatGrowth,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-value {
  font-size: 1.25rem;
  color: #0f172a;
}

/* Slider */
.budget-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: #e2e8f0;
  outline: none;
  cursor: pointer;
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #3b82f6;
  border: 2px solid white;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.3);
}

.budget-slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #3b82f6;
  border: 2px solid white;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.3);
}

.budget-slider:focus-visible {
  outline: 2px solid #93c5fd;
  outline-offset: 4px;
}

.slider-scale {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  font-size: 0.813rem;
  color: #64748b;
}

.rule-note {
  margin-top: 0.875rem;
  font-size: 0.813rem;
  color: #64748b;
}

.empty-state {
  text-align: center;
  padding: 2rem 1rem;
  color: #64748b;
  font-size: 0.938rem;
}

/* Place Order button */
.place-order-btn {
  padding: 0.5rem 1.25rem;
  border: none;
  border-radius: 8px;
  background: #3b82f6;
  color: white;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease;
}

.place-order-btn:hover:not(:disabled) {
  background: #2563eb;
}

.place-order-btn:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

/* Success message */
.success-message {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #065f46;
  padding: 1rem;
  border-radius: 8px;
  margin: 0 0 1rem;
  font-size: 0.938rem;
}

.success-message svg {
  flex-shrink: 0;
}

/* Pushes the "view in Orders" link to the right edge of the message */
.success-link {
  margin-left: auto;
  color: #065f46;
  font-weight: 600;
  white-space: nowrap;
  text-decoration: underline;
}
</style>
