import axios from 'axios'
import { message } from 'antd'

const TOKEN_KEY = 'cmvp_token'

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

const http = axios.create({ baseURL: '/api', timeout: 30000 })

http.interceptors.request.use((config) => {
  const token = tokenStore.get()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (resp) => resp,
  (error) => {
    const status = error.response?.status
    const detail = error.response?.data?.detail
    if (status === 401) {
      tokenStore.clear()
      if (location.pathname !== '/login') {
        location.href = '/login'
      }
    } else {
      message.error(detail || error.message || '请求失败')
    }
    return Promise.reject(error)
  },
)

export default http

export async function downloadCsv(path: string, filename: string, params?: Record<string, unknown>) {
  const resp = await http.get(path, { params, responseType: 'blob' })
  const url = URL.createObjectURL(resp.data)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
