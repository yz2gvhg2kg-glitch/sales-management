<template>
  <div>
    <div class="page-header">
      <h2>财务结算</h2>
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

    <!-- 财务汇总卡片 -->
    <div class="stat-cards" style="margin-bottom: 20px">
      <div class="stat-card">
        <div class="stat-card-title">总营收</div>
        <div class="stat-card-value">¥{{ formatMoney(summary.total_revenue) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-title">实际营收</div>
        <div class="stat-card-value">¥{{ formatMoney(summary.actual_revenue) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-title">总成本</div>
        <div class="stat-card-value" style="color: #f56c6c">¥{{ formatMoney(summary.total_cost) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-title">毛利润</div>
        <div class="stat-card-value" style="color: #e6a23c">¥{{ formatMoney(summary.gross_profit) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-title">提成总额</div>
        <div class="stat-card-value" style="color: #909399">¥{{ formatMoney(summary.total_commission) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-title">净利润</div>
        <div class="stat-card-value" style="color: #67c23a">¥{{ formatMoney(summary.net_profit) }}</div>
      </div>
    </div>

    <!-- 明细表格 -->
    <div class="table-container">
      <el-table :data="tableData" border stripe v-loading="loading" show-summary :summary-method="getSummary">
        <el-table-column prop="salesperson_name" label="业务员" width="120" />
        <el-table-column prop="team" label="团队" width="100" />
        <el-table-column prop="total_revenue" label="营收" width="120" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.total_revenue) }}</template>
        </el-table-column>
        <el-table-column prop="actual_revenue" label="实际营收" width="120" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.actual_revenue) }}</template>
        </el-table-column>
        <el-table-column prop="total_cost" label="成本" width="120" align="right">
          <template #default="{ row }">
            <span style="color: #f56c6c">¥{{ formatMoney(row.total_cost) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="gross_profit" label="毛利润" width="120" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.gross_profit) }}</template>
        </el-table-column>
        <el-table-column prop="commission_rate" label="提成比例" width="100" align="center">
          <template #default="{ row }">{{ row.commission_rate }}%</template>
        </el-table-column>
        <el-table-column prop="commission" label="提成金额" width="120" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.commission) }}</template>
        </el-table-column>
        <el-table-column prop="net_profit" label="净利润" width="120" align="right">
          <template #default="{ row }">
            <span :style="{ color: parseFloat(row.net_profit) >= 0 ? '#67c23a' : '#f56c6c', fontWeight: 'bold' }">
              ¥{{ formatMoney(row.net_profit) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="period" label="统计周期" />
      </el-table>
    </div>

    <!-- 利润趋势图 -->
    <div style="margin-top: 24px; padding: 20px; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
      <h3 style="margin-bottom: 16px">利润趋势</h3>
      <v-chart :option="chartOption" style="height: 300px; width: 100%" autoresize />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import { getFinance, getUsers, exportStatistics } from '@/api'

const loading = ref(false)
const period = ref('month')
const tableData = ref([])
const salespersonList = ref([])
const trendData = ref([])
const summary = reactive({
  total_revenue: 0,
  actual_revenue: 0,
  total_cost: 0,
  gross_profit: 0,
  total_commission: 0,
  net_profit: 0
})

const filters = reactive({
  dateRange: null,
  salesperson_id: ''
})

const formatMoney = (val) => {
  const num = parseFloat(val) || 0
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const chartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['营收', '成本', '净利润'] },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: {
    type: 'category',
    data: trendData.value.map(d => d.period)
  },
  yAxis: { type: 'value' },
  series: [
    {
      name: '营收',
      type: 'bar',
      data: trendData.value.map(d => d.revenue),
      itemStyle: { color: '#409eff' }
    },
    {
      name: '成本',
      type: 'bar',
      data: trendData.value.map(d => d.cost),
      itemStyle: { color: '#f56c6c' }
    },
    {
      name: '净利润',
      type: 'line',
      data: trendData.value.map(d => d.net_profit),
      itemStyle: { color: '#67c23a' },
      smooth: true
    }
  ]
}))

const getSummary = ({ columns, data }) => {
  const sums = []
  const moneyFields = ['total_revenue', 'actual_revenue', 'total_cost', 'gross_profit', 'commission', 'net_profit']
  columns.forEach((col, index) => {
    if (index === 0) { sums[index] = '合计'; return }
    if (moneyFields.includes(col.property)) {
      const total = data.reduce((s, r) => s + (parseFloat(r[col.property]) || 0), 0)
      sums[index] = '¥' + formatMoney(total)
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
    const res = await getFinance(params)
    const data = res.data
    tableData.value = data.items || data.details || []
    summary.total_revenue = data.total_revenue || 0
    summary.actual_revenue = data.actual_revenue || 0
    summary.total_cost = data.total_cost || 0
    summary.gross_profit = data.gross_profit || 0
    summary.total_commission = data.total_commission || 0
    summary.net_profit = data.net_profit || 0
    trendData.value = data.trend || []
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
    const params = { type: 'finance', period: period.value }
    if (filters.dateRange) {
      params.start_date = filters.dateRange[0]
      params.end_date = filters.dateRange[1]
    }
    if (filters.salesperson_id) params.salesperson_id = filters.salesperson_id
    const res = await exportStatistics(params)
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = `财务结算_${period.value}.xlsx`
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
