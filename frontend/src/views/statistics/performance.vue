<template>
  <div>
    <div class="page-header">
      <h2>业绩核算（实发）</h2>
      <div>
        <el-radio-group v-model="period" @change="fetchData">
          <el-radio-button value="day">日</el-radio-button>
          <el-radio-button value="month">月</el-radio-button>
        </el-radio-group>
        <el-button type="success" :icon="Download" @click="handleExport" style="margin-left: 12px">导出Excel</el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-date-picker v-model="filters.dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" @change="fetchData" />
      <el-select v-model="filters.salesperson_id" placeholder="选择业务员" clearable filterable style="width: 180px" @change="fetchData">
        <el-option v-for="u in salespersonList" :key="u.id" :label="u.real_name" :value="u.id" />
      </el-select>
      <el-button type="primary" @click="fetchData">查询</el-button>
    </div>

    <!-- 汇总卡片 -->
    <div class="stat-cards" style="margin-bottom: 20px">
      <div class="stat-card">
        <div class="stat-card-title">订单总额</div>
        <div class="stat-card-value">¥{{ formatMoney(summary.total_amount) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-title">退款金额</div>
        <div class="stat-card-value" style="color: #f56c6c">¥{{ formatMoney(summary.refund_amount) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-title">拒收金额</div>
        <div class="stat-card-value" style="color: #f56c6c">¥{{ formatMoney(summary.reject_amount) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-title">实发业绩</div>
        <div class="stat-card-value" style="color: #67c23a">¥{{ formatMoney(summary.actual_performance) }}</div>
      </div>
    </div>

    <!-- 数据表格 -->
    <div class="table-container">
      <el-table :data="tableData" border stripe v-loading="loading" show-summary :summary-method="getSummary">
        <el-table-column prop="rank" label="排名" width="70" align="center">
          <template #default="{ row }">
            <el-tag :type="row.rank <= 3 ? 'danger' : 'info'" size="small">{{ row.rank }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="salesperson_name" label="业务员" width="120" />
        <el-table-column prop="team" label="团队" width="120" />
        <el-table-column prop="total_orders" label="订单数" width="90" align="center" />
        <el-table-column prop="total_amount" label="订单总额" width="130" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.total_amount) }}</template>
        </el-table-column>
        <el-table-column prop="refund_amount" label="退款" width="110" align="right">
          <template #default="{ row }">
            <span style="color: #f56c6c">-¥{{ formatMoney(row.refund_amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="reject_amount" label="拒收" width="110" align="right">
          <template #default="{ row }">
            <span style="color: #f56c6c">-¥{{ formatMoney(row.reject_amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="actual_performance" label="实发业绩" width="130" align="right">
          <template #default="{ row }">
            <span style="color: #67c23a; font-weight: bold">¥{{ formatMoney(row.actual_performance) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="period" label="统计周期" />
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import { getPerformance, getUsers, exportStatistics } from '@/api'

const loading = ref(false)
const period = ref('day')
const tableData = ref([])
const salespersonList = ref([])
const summary = reactive({
  total_amount: 0,
  refund_amount: 0,
  reject_amount: 0,
  actual_performance: 0
})

const filters = reactive({
  dateRange: null,
  salesperson_id: ''
})

const formatMoney = (val) => {
  const num = parseFloat(val) || 0
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const getSummary = ({ columns, data }) => {
  const sums = []
  columns.forEach((col, index) => {
    if (index === 0) { sums[index] = '合计'; return }
    if (['total_amount', 'refund_amount', 'reject_amount', 'actual_performance'].includes(col.property)) {
      const total = data.reduce((s, r) => s + (parseFloat(r[col.property]) || 0), 0)
      sums[index] = '¥' + formatMoney(total)
    } else if (col.property === 'total_orders') {
      sums[index] = data.reduce((s, r) => s + (r.total_orders || 0), 0)
    } else {
      sums[index] = ''
    }
  })
  return sums
}

const fetchData = async () => {
  loading.value = true
  try {
    const params = { period: period.value }
    if (filters.dateRange) {
      params.start_date = filters.dateRange[0]
      params.end_date = filters.dateRange[1]
    }
    if (filters.salesperson_id) params.salesperson_id = filters.salesperson_id
    const res = await getPerformance(params)
    const data = res.data
    tableData.value = data.items || data.details || []
    summary.total_amount = data.total_amount || 0
    summary.refund_amount = data.refund_amount || 0
    summary.reject_amount = data.reject_amount || 0
    summary.actual_performance = data.actual_performance || 0
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const fetchSalespersons = async () => {
  try {
    const res = await getUsers({ role: 'employee', page_size: 200 })
    salespersonList.value = res.data.items || res.data || []
  } catch (e) {
    console.error(e)
  }
}

const handleExport = async () => {
  try {
    const params = { type: 'performance', period: period.value }
    if (filters.dateRange) {
      params.start_date = filters.dateRange[0]
      params.end_date = filters.dateRange[1]
    }
    if (filters.salesperson_id) params.salesperson_id = filters.salesperson_id
    const res = await exportStatistics(params)
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = `业绩核算_${period.value}.xlsx`
    link.click()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

onMounted(() => {
  fetchData()
  fetchSalespersons()
})
</script>
