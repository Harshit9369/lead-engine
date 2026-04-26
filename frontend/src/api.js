import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001';

const api = axios.create({
  baseURL: API_BASE_URL,
});

// Add a request interceptor to include the JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export const authAPI = {
  signup: (data) => api.post('/api/auth/signup', data),
  login: (formData) => api.post('/api/auth/login', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  }),
  getMe: () => api.get('/api/auth/me'),
  updateProfile: (data) => api.patch('/api/auth/profile', data),
};

export const searchAPI = {
  trigger: (data) => api.post('/api/search', data),
  getStatus: () => api.get('/api/search/status'),
  getResults: () => api.get('/api/search/results'),
};

export const leadsAPI = {
  list: (status) => api.get('/api/leads', { params: { status } }),
  save: (lead) => api.post('/api/leads', lead),
  update: (id, data) => api.patch(`/api/leads/${id}`, data),
  delete: (id) => api.delete(`/api/leads/${id}`),
};

export const schedulerAPI = {
  listRoles: () => api.get('/api/scheduler/roles'),
  addRole: (data) => api.post('/api/scheduler/roles', data),
  deleteRole: (id) => api.delete(`/api/scheduler/roles/${id}`),
  toggleRole: (id) => api.patch(`/api/scheduler/roles/${id}/toggle`),
  triggerScan: (id) => api.post(`/api/scheduler/roles/${id}/scan`),
  getGroupedResults: () => api.get('/api/scheduler/results/grouped'),
  trackResult: (id) => api.post(`/api/scheduler/results/${id}/track`),
};

export const statsAPI = {
  get: () => api.get('/api/stats'),
};

export default api;
