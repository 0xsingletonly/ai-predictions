import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Questions API
export const fetchQuestions = async (status = null, category = null) => {
  const params = {}
  if (status) params.status = status
  if (category) params.category = category
  
  const response = await api.get('/questions', { params })
  return response.data
}

export const fetchQuestion = async (id) => {
  const response = await api.get(`/questions/${id}`)
  return response.data
}

export const fetchQuestionLogs = async (id, limit = 100) => {
  const response = await api.get(`/questions/${id}/logs`, { params: { limit } })
  return response.data
}

export const fetchQuestionPerformance = async (id) => {
  const response = await api.get(`/questions/${id}/performance`)
  return response.data
}

export const fetchReasoningForDate = async (id, date) => {
  const response = await api.get(`/questions/${id}/reasoning/${date}`)
  return response.data
}

export const fetchStats = async () => {
  const response = await api.get('/stats')
  return response.data
}

export default api
