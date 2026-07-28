import request from '@/utils/request'

// Auth
export const login = (data) => {
  const formData = new URLSearchParams()
  formData.append('username', data.username)
  formData.append('password', data.password)
  return request.post('/auth/login', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
}
export const getMe = () => request.get('/auth/me')

// Users / Employees
export const getUsers = (params) => request.get('/users/', { params })
export const createUser = (data) => request.post('/users/', data)
export const updateUser = (id, data) => request.put(`/users/${id}`, data)
export const deleteUser = (id) => request.delete(`/users/${id}`)

// Products
export const getProducts = (params) => request.get('/products/', { params })
export const createProduct = (data) => request.post('/products/', data)
export const updateProduct = (id, data) => request.put(`/products/${id}`, data)
export const deleteProduct = (id) => request.delete(`/products/${id}`)

// Customers
export const getCustomers = (params) => request.get('/customers/', { params })
export const createCustomer = (data) => request.post('/customers/', data)
export const updateCustomerStatus = (id, data) => request.put(`/customers/${id}/status`, data)
export const batchAssignCustomers = (data) => request.post('/customers/batch-assign', data)
export const importCustomers = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/customers/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// Orders
export const getOrders = (params) => request.get('/orders/', { params })
export const createOrder = (data) => request.post('/orders/', data)
export const importOrders = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/orders/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
export const createAfterSales = (data) => request.post('/orders/after-sales', data)

// Shipments
export const getShipments = (params) => request.get('/shipments/', { params })
export const batchShip = (data) => request.post('/shipments/batch-ship', data)
export const importTrackingNumbers = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/shipments/import-tracking', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// Statistics
export const getAdditionRate = (params) => request.get('/statistics/addition-rate', { params })
export const getConversionRate = (params) => request.get('/statistics/conversion-rate', { params })
export const getPerformance = (params) => request.get('/statistics/performance', { params })
export const getFinance = (params) => request.get('/statistics/finance', { params })
export const exportStatistics = (type, params) => request.get(`/statistics/export/${type}`, {
  params,
  responseType: 'blob',
})

// Dashboard
export const getDashboard = () => request.get('/dashboard/')
