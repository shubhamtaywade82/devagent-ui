import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_BACKEND_URL || import.meta.env.REACT_APP_BACKEND_URL || 'http://localhost:8001'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export default {
  // Projects
  async createProject(data) {
    const response = await api.post('/api/projects', data)
    return response.data
  },

  async getProject(projectId) {
    const response = await api.get(`/api/projects/${projectId}`)
    return response.data
  },

  async getAllProjects() {
    const response = await api.get('/api/projects')
    return response.data
  },

  async deleteProject(projectId) {
    const response = await api.delete(`/api/projects/${projectId}`)
    return response.data
  },

  // Files
  async saveFile(data) {
    const response = await api.post('/api/files', data)
    return response.data
  },

  async getFiles(projectId) {
    const response = await api.get(`/api/files/${projectId}`)
    return response.data
  },

  async deleteFile(projectId, path) {
    const response = await api.delete('/api/files', {
      data: { project_id: projectId, path }
    })
    return response.data
  },

  // AI Chat
  async chat(message, projectId, context = []) {
    const response = await api.post('/api/chat', {
      message,
      project_id: projectId,
      context
    })
    return response.data
  },

  // Component Generation
  async generateComponent(description, framework = 'react') {
    const response = await api.post('/api/generate/component', {
      description,
      framework
    })
    return response.data
  },

  // Design System Generation
  async generateDesignSystem(description, style = 'modern') {
    const response = await api.post('/api/generate/design-system', {
      description,
      style
    })
    return response.data
  },
}

