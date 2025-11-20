import axios from 'axios'

// Direct connection to backend (hardcoded for preview compatibility)
const API_BASE_URL = 'http://localhost:5001/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  const authStorage = localStorage.getItem('auth-storage')
  if (authStorage) {
    const { state } = JSON.parse(authStorage)
    if (state.token) {
      config.headers.Authorization = `Bearer ${state.token}`
    }
  }
  return config
})

// Auth APIs
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  getProfile: () => api.get('/user/profile')
}

// Photos APIs
export const photosAPI = {
  getAll: () => api.get('/photos'),
  upload: (formData) => api.post('/photos', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  delete: (id) => api.delete(`/photos/${id}`),
  select: (id) => api.put(`/photos/${id}/select`)
}

// Clothing APIs
export const clothingAPI = {
  getAll: (category) => api.get('/clothing', { params: { category } }),
  upload: (formData) => api.post('/clothing', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  delete: (id) => api.delete(`/clothing/${id}`)
}

// Try-On APIs
export const tryonAPI = {
  generate: (data) => api.post('/tryon', data),
  getSaved: () => api.get('/saved-looks'),
  deleteSaved: (id) => api.delete(`/saved-looks/${id}`)
}

export default api

