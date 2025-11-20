import { create } from 'zustand'

export const useAuthStore = create((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  
  login: (user, token) => {
    localStorage.setItem('auth-storage', JSON.stringify({ state: { user, token, isAuthenticated: true } }))
    set({ user, token, isAuthenticated: true })
  },
  
  logout: () => {
    localStorage.removeItem('auth-storage')
    set({ user: null, token: null, isAuthenticated: false })
  },
  
  updateUser: (user) => {
    const storage = JSON.parse(localStorage.getItem('auth-storage') || '{}')
    storage.state.user = user
    localStorage.setItem('auth-storage', JSON.stringify(storage))
    set({ user })
  },
  
  // Initialize from localStorage
  init: () => {
    const storage = localStorage.getItem('auth-storage')
    if (storage) {
      try {
        const { state } = JSON.parse(storage)
        if (state?.token) {
          set({ user: state.user, token: state.token, isAuthenticated: true })
        }
      } catch (e) {
        console.error('Error loading auth state:', e)
      }
    }
  }
}))

// Initialize auth state on load
useAuthStore.getState().init()

