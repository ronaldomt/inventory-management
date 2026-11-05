<template>
  <div class="app">
    <aside class="sidebar" :class="{ collapsed: isCollapsed }">
      <div class="sidebar-brand">
        <span class="brand-mark" aria-hidden="true">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M10 2.5L17 6.5L10 10.5L3 6.5L10 2.5Z" />
            <path d="M3 10L10 14L17 10" />
            <path d="M3 13.5L10 17.5L17 13.5" />
          </svg>
        </span>
        <div class="brand-text">
          <h1 class="brand-name">{{ t('nav.companyName') }}</h1>
          <span class="brand-subtitle">{{ t('nav.subtitle') }}</span>
        </div>
      </div>

      <nav class="sidebar-nav">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-link"
          :class="{ active: $route.path === item.to }"
          :aria-label="item.label()"
          :title="isCollapsed ? item.label() : null"
        >
          <svg class="nav-icon" width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path v-for="d in item.icon" :key="d" :d="d" />
          </svg>
          <span class="nav-label">{{ item.label() }}</span>
        </router-link>
      </nav>

      <!-- Dropdowns in the footer open upward, see LanguageSwitcher and ProfileMenu -->
      <div class="sidebar-footer">
        <LanguageSwitcher />
        <ProfileMenu
          @show-profile-details="showProfileDetails = true"
          @show-tasks="showTasks = true"
        />
        <!-- Hidden while the narrow-screen rule forces the strip: toggling would do nothing visible -->
        <button
          v-if="!isForced"
          type="button"
          class="collapse-toggle"
          :aria-label="collapseLabel"
          :aria-expanded="!isCollapsed"
          :title="isCollapsed ? collapseLabel : null"
          @click="toggleSidebar"
        >
          <svg class="nav-icon" width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <rect x="3" y="3.5" width="14" height="13" rx="2" />
            <path d="M8 3.5V16.5" />
          </svg>
          <span class="nav-label">{{ collapseLabel }}</span>
        </button>
      </div>
    </aside>

    <div class="content">
      <FilterBar />
      <main class="main-content">
        <router-view />
      </main>
    </div>

    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import { useSidebar } from './composables/useSidebar'
import FilterBar from './components/FilterBar.vue'
import ProfileMenu from './components/ProfileMenu.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'

export default {
  name: 'App',
  components: {
    FilterBar,
    ProfileMenu,
    ProfileDetailsModal,
    TasksModal,
    LanguageSwitcher
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const { isCollapsed, isForced, toggle: toggleSidebar } = useSidebar()
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    onMounted(loadTasks)

    // Labels are functions so they re-evaluate when the locale changes.
    // Each icon is a list of SVG path strings drawn in a 20x20 box.
    const navItems = [
      {
        to: '/',
        label: () => t('nav.overview'),
        icon: ['M3.5 3.5H8.5V8.5H3.5Z', 'M11.5 3.5H16.5V8.5H11.5Z', 'M3.5 11.5H8.5V16.5H3.5Z', 'M11.5 11.5H16.5V16.5H11.5Z']
      },
      {
        to: '/inventory',
        label: () => t('nav.inventory'),
        icon: ['M10 2.5L17 6.25V13.75L10 17.5L3 13.75V6.25L10 2.5Z', 'M3 6.25L10 10L17 6.25', 'M10 10V17.5']
      },
      {
        to: '/orders',
        label: () => t('nav.orders'),
        icon: ['M6 3.5H14A1.5 1.5 0 0 1 15.5 5V16A1.5 1.5 0 0 1 14 17.5H6A1.5 1.5 0 0 1 4.5 16V5A1.5 1.5 0 0 1 6 3.5Z', 'M7.5 8H12.5', 'M7.5 11H12.5', 'M7.5 14H10']
      },
      {
        to: '/spending',
        label: () => t('nav.finance'),
        icon: ['M3 6.5A1.5 1.5 0 0 1 4.5 5H15.5A1.5 1.5 0 0 1 17 6.5V14.5A1.5 1.5 0 0 1 15.5 16H4.5A1.5 1.5 0 0 1 3 14.5V6.5Z', 'M3 8.5H17', 'M13 12.25H14.5']
      },
      {
        to: '/demand',
        label: () => t('nav.demandForecast'),
        icon: ['M3 14.5L7.5 10L10.5 13L16.5 6.5', 'M12.5 6.5H16.5V10.5']
      },
      {
        to: '/restocking',
        label: () => t('nav.restocking'),
        icon: ['M4 10A6 6 0 0 1 14.2 5.8L16 7.5', 'M16 4V7.5H12.5', 'M16 10A6 6 0 0 1 5.8 14.2L4 12.5', 'M4 16V12.5H7.5']
      },
      {
        to: '/reports',
        // Hardcoded English on purpose: a known i18n bug, out of scope for the redesign
        label: () => 'Reports',
        icon: ['M5.5 2.5H11.5L16 7V16.5A1 1 0 0 1 15 17.5H5.5A1 1 0 0 1 4.5 16.5V3.5A1 1 0 0 1 5.5 2.5Z', 'M11.5 2.5V7H16', 'M7.5 14V12', 'M10 14V10.5', 'M12.5 14V11.5']
      }
    ]

    const collapseLabel = computed(() =>
      isCollapsed.value ? t('nav.expandSidebar') : t('nav.collapseSidebar')
    )

    return {
      t,
      navItems,
      isCollapsed,
      isForced,
      collapseLabel,
      toggleSidebar,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>

<style>
/* Design tokens: every shared color, space, radius and shadow comes from here */
:root {
  --color-bg: #f8fafc;
  --color-surface: #ffffff;
  --color-border: #e2e8f0;
  --color-text: #0f172a;
  --color-text-muted: #64748b;
  --color-accent: #3b82f6;
  --color-accent-strong: #2563eb;
  --color-accent-soft: #eff6ff;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;

  --radius-card: 12px;
  --radius-control: 8px;
  --shadow-card: 0 1px 2px rgba(15, 23, 42, 0.04), 0 1px 3px rgba(15, 23, 42, 0.06);

  --sidebar-width: 248px;
  --sidebar-width-collapsed: 72px;
  --transition: 200ms ease;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background: var(--color-bg);
  color: #1e293b;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Keyboard focus is always visible, for every control in the app */
:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

/* Two columns: sidebar on the left, content column on the right */
.app {
  display: flex;
  min-height: 100vh;
}

/* flex-shrink: 0 keeps wide content from crushing the sidebar.
   overflow stays visible so the footer dropdowns are not clipped. */
.sidebar {
  position: sticky;
  top: 0;
  align-self: flex-start;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  width: var(--sidebar-width);
  height: 100vh;
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  z-index: 100;
  transition: width var(--transition);
}

.sidebar.collapsed {
  width: var(--sidebar-width-collapsed);
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-6) var(--space-4);
  min-height: 80px;
}

.brand-mark {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: var(--radius-control);
  background: var(--color-accent-strong);
  color: var(--color-surface);
}

.brand-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.brand-name {
  font-size: 0.938rem;
  font-weight: 700;
  line-height: 1.25;
  color: var(--color-text);
  letter-spacing: -0.01em;
}

.brand-subtitle {
  font-size: 0.75rem;
  line-height: 1.3;
  color: var(--color-text-muted);
}

/* min-height: 0 lets the list scroll on short screens while the footer stays put */
.sidebar-nav {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-4);
  overflow-y: auto;
}

.nav-link,
.collapse-toggle {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
  height: 40px;
  padding: 0 var(--space-3);
  border: none;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--color-text-muted);
  font-family: inherit;
  font-size: 0.938rem;
  font-weight: 500;
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
  cursor: pointer;
  flex-shrink: 0;
  transition: background-color var(--transition), color var(--transition);
}

.nav-link:hover,
.collapse-toggle:hover {
  background: var(--color-bg);
  color: var(--color-text);
}

.nav-link.active {
  background: var(--color-accent-soft);
  color: var(--color-accent-strong);
}

/* 3px accent bar on the left edge of the active link */
.nav-link.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--color-accent);
}

.nav-icon {
  flex-shrink: 0;
}

.nav-label {
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-footer {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-4);
  border-top: 1px solid var(--color-border);
}

/* Collapsed: labels leave the layout but stay readable for screen readers */
.sidebar.collapsed .nav-label,
.sidebar.collapsed .brand-text {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

.sidebar.collapsed .nav-link,
.sidebar.collapsed .collapse-toggle {
  justify-content: center;
  padding: 0;
}

.sidebar.collapsed .sidebar-brand {
  justify-content: center;
  padding-left: 0;
  padding-right: 0;
}

/* min-width: 0 stops wide tables and charts from pushing the page sideways */
.content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1;
  min-width: 0;
  max-width: 1600px;
  width: 100%;
  margin: 0 auto;
  padding: var(--space-8);
}

@media (prefers-reduced-motion: reduce) {
  .sidebar,
  .nav-link,
  .collapse-toggle {
    transition: none;
  }
}

.page-header {
  margin-bottom: var(--space-6);
}

.page-header h2 {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 0.375rem;
  letter-spacing: -0.025em;
}

.page-header p {
  color: var(--color-text-muted);
  font-size: 0.938rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-6);
  margin-bottom: var(--space-6);
}

.stat-card {
  background: var(--color-surface);
  padding: var(--space-6);
  border-radius: var(--radius-card);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-card);
  transition: all 0.2s ease;
}

.stat-card:hover {
  border-color: #cbd5e1;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.stat-label {
  color: var(--color-text-muted);
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.625rem;
}

.stat-value {
  font-size: 2.25rem;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.025em;
}

.stat-card.warning .stat-value {
  color: #ea580c;
}

.stat-card.success .stat-value {
  color: #059669;
}

.stat-card.danger .stat-value {
  color: #dc2626;
}

.stat-card.info .stat-value {
  color: #2563eb;
}

.card {
  background: var(--color-surface);
  border-radius: var(--radius-card);
  padding: var(--space-6);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-card);
  margin-bottom: var(--space-6);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
  padding-bottom: 0.875rem;
  border-bottom: 1px solid var(--color-border);
}

.card-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-text);
  letter-spacing: -0.025em;
}

.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: var(--color-bg);
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
}

th {
  text-align: left;
  padding: var(--space-3) var(--space-4);
  font-weight: 600;
  color: var(--color-text-muted);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

td {
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid #f1f5f9;
  color: #334155;
  font-size: 0.875rem;
}

tbody tr {
  transition: background-color 0.15s ease;
}

tbody tr:hover {
  background: var(--color-bg);
}

.badge {
  display: inline-block;
  padding: 0.313rem 0.75rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.badge.success {
  background: #d1fae5;
  color: #065f46;
}

.badge.warning {
  background: #fed7aa;
  color: #92400e;
}

.badge.danger {
  background: #fecaca;
  color: #991b1b;
}

.badge.info {
  background: #dbeafe;
  color: #1e40af;
}

.badge.increasing {
  background: #d1fae5;
  color: #065f46;
}

.badge.decreasing {
  background: #fecaca;
  color: #991b1b;
}

.badge.stable {
  background: #e0e7ff;
  color: #3730a3;
}

.badge.high {
  background: #fecaca;
  color: #991b1b;
}

.badge.medium {
  background: #fed7aa;
  color: #92400e;
}

.badge.low {
  background: #dbeafe;
  color: #1e40af;
}

.loading {
  text-align: center;
  padding: 3rem;
  color: var(--color-text-muted);
  font-size: 0.938rem;
}

.error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  padding: 1rem;
  border-radius: var(--radius-control);
  margin: 1rem 0;
  font-size: 0.938rem;
}
</style>
