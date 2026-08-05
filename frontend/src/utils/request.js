import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// Request interceptor - attach JWT
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor - handle errors
request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const { response } = error
    if (response) {
      switch (response.status) {
        case 401:
          localStorage.removeItem('token')
          localStorage.removeItem('user')
          router.push('/login')
          ElMessage.error('登录已过期，请重新登录')
          break
        case 403:
          ElMessage.error('没有权限执行此操作')
          break
        case 422: {
          // FastAPI 422 detail is an array: [{loc, msg, type}]
          const detail = response.data?.detail
          if (Array.isArray(detail) && detail.length > 0) {
            // Extract human-readable messages (strip FastAPI prefix like "Value error, ")
            const msgs = detail.map(e => {
              const raw = e.msg || String(e)
              return raw.replace(/^Value error[,\s]*/i, '')
            })
            ElMessage.error(msgs.join('；'))
          } else {
            ElMessage.error(typeof detail === 'string' ? detail : '请求参数错误')
          }
          break
        }
        default:
          ElMessage.error(response.data?.detail || '服务器错误')
      }
    } else {
      ElMessage.error('网络连接失败')
    }
    return Promise.reject(error)
  }
)

export default request
