<template>
  <div>
    <div class="page-header">
      <h2>添加率统计</h2>
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
        <div class="stat-card-title">总分配数</div>
        <div class="stat-card-value">{{ summary.total_assigned || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-title">总添加数</div>
        <div class="stat-card-value">{{ summary.total_added || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-title">整体添加率</div>
        <div class="stat-card-value">{{ summary.overall_rate || '0.00' }}%</div>
      </div>
    </div>

    <!-- 数据表格 -->
    <div class="table-container">
      <el-table :data="tableData" border stripe v-loading="loading" show-summary :summary-method="getSummary">
        <el-table-column prop="salesperson_name" label="业务员" width="120" />
        <el-table-column prop="team" label="团队" width="120" />
        <el-table-column prop="assigned_count" label="分配数" width="100" align="center" />
        <el-table-column prop="added_count" label="添加数" width="100" align="center" />
        <el-table-column prop="addition_rate" label="添加率" width="120" align="center">
          <template #default="{ row }">
            <span :class="rateClass(row.addition_rate)">{{ row.addition_rate }}%</span>
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
import { getAdditionRate, getUsers, exportStatistics } from '@/api'

const loading = ref(false)
const period = ref('day')
const tableData = ref([])
const salespersonList = ref([])
const summary = reactive({
  total_assigned: 0,
  total_added: 0,
  overall_rate: '0.00'
})

const filters = reactive({
  dateRange: null,
  salesperson_id: ''
})

const rateClass = (rate) => {
  const val = parseFloat(rate)
  if (val >= 80) return 'rate-high'
  if (val >= 50) return 'rate-mid'
  return 'rate-low'
}

const getSummary = ({ columns, data }) => {
  const sums = []
  columns.forEach((col, index) => {
    if (index === 0) { sums[index] = '合计'; return }
    if (col.property === 'assigned_count') {
      sums[index] = data.reduce((s, r) => s + (r.assigned_count || 0), 0)
    } else if (col.property === 'added_count') {
      sums[index] = data.reduce((s, r) => s + (r.added_count || 0), 0)
    } else if (col.property === 'addition_rate') {
      const assigned = data.reduce((s, r) => s + (r.assigned_count || 0), 0)
      const added = data.reduce((s, r) => s + (r.added_count || 0), 0)
      sums[index] = assigned > 0 ? (added / assigned * 100).toFixed(2) + '%' : '0.00%'
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
    const res = await getAdditionRate(params)
    const data = res.data
    tableData.value = data.items || data.details || []
    summary.total_assigned = data.total_assigned || 0
    summary.total_added = data.total_added || 0
    summary.overall_rate = data.overall_rate || '0.00'
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
    const params = { type: 'addition', period: period.value }
    if (filters.dateRange) {
      params.start_date = filters.dateRange[0]
      params.end_date = filters.dateRange[1]
    }
    if (filters.salesperson_id) params.salesperson_id = filters.salesperson_id
    const res = await exportStatistics(params)
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = `添加率统计_${period.value}.xlsx`
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
