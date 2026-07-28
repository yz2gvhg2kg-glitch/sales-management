import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录', noAuth: true },
  },
  {
    path: '/',
    component: () => import('@/components/Layout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '数据总览', icon: 'DataAnalysis' },
      },
      {
        path: 'employees',
        name: 'Employees',
        component: () => import('@/views/employee/index.vue'),
        meta: { title: '员工管理', icon: 'User', adminOnly: true },
      },
      {
        path: 'products',
        name: 'Products',
        component: () => import('@/views/product/index.vue'),
        meta: { title: '产品管理', icon: 'Goods', adminOnly: true },
      },
      {
        path: 'customers',
        name: 'Customers',
        component: () => import('@/views/customer/index.vue'),
        meta: { title: '客户管理', icon: 'UserFilled' },
      },
      {
        path: 'orders',
        name: 'Orders',
        component: () => import('@/views/order/index.vue'),
        meta: { title: '订单管理', icon: 'Document' },
      },
      {
        path: 'shipments',
        name: 'Shipments',
        component: () => import('@/views/shipment/index.vue'),
        meta: { title: '发货管理', icon: 'Van' },
      },
      {
        path: 'statistics',
        name: 'Statistics',
        component: () => import('@/views/statistics/index.vue'),
        meta: { title: '数据统计', icon: 'TrendCharts' },
        children: [
          {
            path: 'addition',
            name: 'AdditionRate',
            component: () => import('@/views/statistics/addition.vue'),
            meta: { title: '添加率统计' },
          },
          {
            path: 'conversion',
            name: 'ConversionRate',
            component: () => import('@/views/statistics/conversion.vue'),
            meta: { title: '转化统计' },
          },
          {
            path: 'performance',
            name: 'Performance',
            component: () => import('@/views/statistics/performance.vue'),
            meta: { title: '业绩核算' },
          },
          {
            path: 'finance',
            name: 'Finance',
            component: () => import('@/views/statistics/finance.vue'),
            meta: { title: '财务结算' },
          },
        ],
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Navigation guard
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const user = JSON.parse(localStorage.getItem('user') || '{}')

  if (to.meta.noAuth) {
    if (token) {
      next('/')
    } else {
      next()
    }
    return
  }

  if (!token) {
    next('/login')
    return
  }

  if (to.meta.adminOnly && user.role === 'employee') {
    next('/dashboard')
    return
  }

  next()
})

export default router
