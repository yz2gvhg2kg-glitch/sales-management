<template>
  <div>
    <div class="page-header">
      <h2>转化统计</h2>
      <div>
        <el-radio-group v-model="period" @change="fetchData">
          <el-radio-button value="day">日</el-radio-button>
          <el-radio-button value="week">周</el-radio-button>
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
        <div class="stat-card-title">新增好友数</div>
        <div class="stat-card-value">{{ summary.total_new_friends || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-title">成交客户数</div>
        <div class="stat-card-value">{{ summary.total_converted || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-title">转化率</div>
        <div class="stat-card-value">{{ summary.conversion_rate || '0.00' }}%</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-title">复购客户数</div>
        <div class="stat-card-value">{{ summary.repurchase_count || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-title">复购率</div>
        <div class="stat-card-value">{{ summary.repurchase_rate || '0.00' }}%</div>
      </div>
    </div>

    <!-- 数据表格 -->
    <div class="table-container">
      <el-table :data="tableData" border stripe v-loading="loading" show-summary :summary-method="getSummary">
        <el-table-column prop="salesperson_name" label="业务员" width="120" />
        <el-table-column prop="team" label="团队" width="120" />
        <el-table-column prop="new_friends" label="新增好友" width="100" align="center" />
        <el-table-column prop="converted_count" label="成交客户" width="100" align="center" />
        <el-table-column prop="conversion_rate" label="转化率" width="100" align="center">
          <template #default="{ row }">
            <span :class="rateClass(row.conversion_rate)">{{ row.conversion_rate }}%</span>
          </template>
        </el-table-column>
        <el-table-column prop="repurchase_count" label="复购客户" width="100" align="center" />
        <el-table-column prop="repurchase_rate" label="复购率" width="100" align="center">
          <template #default="{ row }">
            {{ row.repurchase_rate }}%
          </template>
        </el-table-column>
        <el-table-column prop="rank" label="排名" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.rank <= 3 ? 'danger' : 'info'" size="small">{{ row.rank }}</el-tag>
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
import { getConversionRate, getUsers, exportStatistics } from '@/api'

const loading = ref(false)
const period = ref('day')
const tableData = ref([])
const salespersonList = ref([])
const summary = reactive({
  total_new_friends: 0,
  total_converted: 0,
  conversion_rate: '0.00',
  repurchase_count: 0,
  repurchase_rate: '0.00'
})

const filters = reactive({
  dateRange: null,
  salesperson_id: ''
})

const rateClass = (rate) => {
  const val = parseFloat(rate)
  if (val >= 30) return 'rate-high'
  if (val >= 15) return 'rate-mid'
  return 'rate-low'
}

const getSummary = ({ columns, data }) => {
  const sums = []
  columns.forEach((col, index) => {
    if (index === 0) { sums[index] = '合计'; return }
    if (col.property === 'new_friends') {
      sums[index] = data.reduce((s, r) => s + (r.new_friends || 0), 0)
    } else if (col.property === 'converted_count') {
      sums[index] = data.reduce((s, r) => s + (r.converted_count || 0), 0)
    } else if (col.property === 'conversion_rate') {
      const friends = data.reduce((s, r) => s + (r.new_friends || 0), 0)
      const converted = data.reduce((s, r) => s + (r.converted_count || 0), 0)
      sums[index] = friends > 0 ? (converted / friends * 100).toFixed(2) + '%' : '0.00%'
    } else if (col.property === 'repurchase_count') {
      sums[index] = data.reduce((s, r) => s + (r.repurchase_count || 0), 0)
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
    const res = await getConversionRate(params)
    const data = res.data
    tableData.value = data.items || data.details || []
    summary.total_new_friends = data.total_new_friends || 0
    summary.total_converted = data.total_converted || 0
    summary.conversion_rate = data.conversion_rate || '0.00'
    summary.repurchase_count = data.repurchase_count || 0
    summary.repurchase_rate = data.repurchase_rate || '0.00'
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
    const params = { type: 'conversion', period: period.value }
    if (filters.dateRange) {
      params.start_date = filters.dateRange[0]
      params.end_date = filters.dateRange[1]
    }
    if (filters.salesperson_id) params.salesperson_id = filters.salesperson_id
    const res = await exportStatistics(params)
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = `转化统计_${period.value}.xlsx`
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

<style scoped>
.rate-high { color: #67c23a; font-weight: bold; }
.rate-mid { color: #e6a23c; font-weight: bold; }
.rate-low { color: #f56c6c; font-weight: bold; }
</style>
