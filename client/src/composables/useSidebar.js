import { ref, computed, getCurrentInstance, onUnmounted } from 'vue'

const STORAGE_KEY = 'sidebar-collapsed'
// Below this width the sidebar is forced into the icons-only strip
const NARROW_QUERY = '(max-width: 899px)'

const mediaQuery = typeof window !== 'undefined' && window.matchMedia
  ? window.matchMedia(NARROW_QUERY)
  : null

// The user's own choice. Read once at setup (like app-locale in useI18n) and
// only ever written by toggle(), never by the narrow-screen rule below.
const userCollapsed = ref(localStorage.getItem(STORAGE_KEY) === 'true')

// Set by the media query. Kept apart from userCollapsed so that squeezing the
// window never overwrites the saved choice: widen it again and the user's
// preference comes back.
const forcedCollapsed = ref(mediaQuery ? mediaQuery.matches : false)

const isCollapsed = computed(() => forcedCollapsed.value || userCollapsed.value)

const onViewportChange = (event) => {
  forcedCollapsed.value = event.matches
}

// The state is shared at module level, so one listener is enough no matter how
// many components call useSidebar(). Count the callers and detach on the last.
let subscribers = 0

export function useSidebar() {
  // Components are the only callers, but stay safe if used outside one
  if (mediaQuery && getCurrentInstance()) {
    if (subscribers === 0) {
      forcedCollapsed.value = mediaQuery.matches
      mediaQuery.addEventListener('change', onViewportChange)
    }
    subscribers++

    onUnmounted(() => {
      subscribers--
      if (subscribers === 0) {
        mediaQuery.removeEventListener('change', onViewportChange)
      }
    })
  }

  const toggle = () => {
    userCollapsed.value = !userCollapsed.value
    localStorage.setItem(STORAGE_KEY, String(userCollapsed.value))
  }

  return {
    isCollapsed,
    isForced: computed(() => forcedCollapsed.value),
    toggle
  }
}
