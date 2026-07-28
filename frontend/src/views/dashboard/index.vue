<template>
  <div class="page-container">
    <div class="stat-cards">
      <div class="stat-card" v-for="item in statCards" :key="item.label">
        <div class="stat-card__title">{{ item.label }}</div>
        <div class="stat-card__value">{{ item.value }}</div>
        <div class="stat-card__footer">{{ item.footer }}</div>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col :span="16">
        <div class="chart-container">
          <h3 class="chart-title">本月业绩趋势</h3>
          <v-chart :option="trendOption" style="height: 320px" autoresize />
        </div>
      </el-col>
      <el-col :span="8">
        <div class="chart-container">
          <h3 class="chart-title">团队排名 TOP 10</h3>
          <div class="ranking-list">
            <div class="ranking-item" v-for="(item, index) in rankings" :key="item.name">
              <span class="ranking-index" :class="{ top3: index < 3 }">{{ index + 1 }}</span>
              <span class="ranking-name">{{ item.name }}</span>
              <span class="ranking-value">¥{{ formatNumber(item.revenue) }}</span>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { getDashboard } from '@/api'

use([CanvasRenderer, LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent])

const dashboardData = ref({})
const rankings = ref([])

const statCards = computed(() => {
  const d = dashboardData.value
  return [
    { label: '今日新客户', value: d.today_new_customers || 0, footer: `本月累计: ${d.month_new_customers || 0}` },
    { label: '今日添加率', value: `${(d.today_addition_rate || 0).toFixed(1)}%`, footer: `本月: ${(d.month_addition_rate || 0).toFixed(1)}%` },
    { label: '今日订单数', value: d.today_orders || 0, footer: `本月累计: ${d.month_orders || 0}` },
    { label: '今日营收', value: `¥${formatNumber(d.today_revenue || 0)}`, footer: `本月累计: ¥${formatNumber(d.month_revenue || 0)}` },
    { label: '今日发货', value: d.today_shipped || 0, footer: `本月累计: ${d.month_shipped || 0}` },
    { label: '今日转化', value: d.today_converted || 0, footer: `转化率: ${(d.today_conversion_rate || 0).toFixed(1)}%` },
    { label: '本月业绩(实发)', value: `¥${formatNumber(d.month_performance || 0)}`, footer: '已扣退换货' },
    { label: '本月利润', value: `¥${formatNumber(d.month_profit || 0)}`, footer: `毛利率: ${(d.month_gross_margin || 0).toFixed(1)}%` },
  ]
})

const trendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['营收', '订单数'] },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: {
    type: 'category',
    data: dashboardData.value.trend_dates || [],
  },
  yAxis: [
    { type: 'value', name: '营收(元)' },
    { type: 'value', name: '订单数' },
  ],
  series: [
    {
      name: '营收',
      type: 'line',
      smooth: true,
      data: dashboardData.value.trend_revenue || [],
      itemStyle: { color: '#409EFF' },
    },
    {
      name: '订单数',
      type: 'bar',
      yAxisIndex: 1,
      data: dashboardData.value.trend_orders || [],
      itemStyle: { color: '#67C23A' },
    },
  ],
}))

const formatNumber = (num) => {
  if (num >= 10000) return (num / 10000).toFixed(1) + 'w'
  return Number(num).toLocaleString()
}

onMounted(async () => {
  try {
    const res = await getDashboard()
    dashboardData.value = res
    rankings.value = res.team_rankings || []
  } catch (e) {
    // handled by interceptor
  }
})
</script>

<style lang="scss" scoped>
.chart-container {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  margin-bottom: 16px;
}

.chart-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
}

.ranking-list {
  .ranking-item {
    display: flex;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid #f0f0f0;

    &:last-child {
      border-bottom: none;
    }
  }

  .ranking-index {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: #f0f0f0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 600;
    margin-right: 12px;

    &.top3 {
      background: #409EFF;
      color: #fff;
    }
  }

  .ranking-name {
    flex: 1;
    font-size: 14px;
    color: #303133;
  }

  .ranking-value {
    font-size: 14px;
    font-weight: 600;
    color: #409EFF;
  }
}
</style>
