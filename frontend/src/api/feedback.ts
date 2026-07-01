import http from './client'
import { ApiResponse, Feedback } from './types'

export async function createFeedback(data: { title: string; description?: string; page_url?: string }) {
  const resp = await http.post<ApiResponse<Feedback>>('/feedback', data)
  return resp.data
}

export async function listFeedback(params?: { page?: number; page_size?: number }) {
  const resp = await http.get<ApiResponse<{ items: Feedback[]; page: number; page_size: number; total: number }>>('/feedback', { params })
  return resp.data
}
