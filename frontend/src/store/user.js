import { defineStore } from 'pinia'
import { login as loginApi, getMe } from '@/api'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || '{}'),
  }),
  getters: {
    isAdmin: (state) => state.user.role === 'admin' || state.user.role === 'manager',
    isEmployee: (state) => state.user.role === 'employee',
    username: (state) => state.user.real_name || state.user.username || '',
  },
  actions: {
    async login(credentials) {
      const res = await loginApi(credentials)
      this.token = res.access_token
      localStorage.setItem('token', res.access_token)
      // Fetch user info
      const userInfo = await getMe()
      this.user = userInfo
      localStorage.setItem('user', JSON.stringify(userInfo))
      return res
    },
    logout() {
      this.token = ''
      this.user = {}
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    },
  },
})
