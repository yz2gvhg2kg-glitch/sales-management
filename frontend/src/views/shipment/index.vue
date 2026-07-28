<template>
  <div class="page-container">
    <div class="page-header">
      <h2>发货管理</h2>
      <div>
        <el-button type="primary" @click="showBatchShipDialog = true">
          <el-icon><Van /></el-icon>批量发货
        </el-button>
        <el-button type="success" @click="showImportDialog = true">
          <el-icon><Upload /></el-icon>导入快递单号
        </el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-input v-model="filters.keyword" placeholder="搜索订单号/客户/快递单号" clearable style="width: 240px" @clear="fetchData" @keyup.enter="fetchData" />
      <el-select v-model="filters.status" placeholder="发货状态" clearable style="width: 140px" @change="fetchData">
        <el-option label="待发货" value="pending" />
        <el-option label="已发货" value="shipped" />
        <el-option label="已签收" value="received" />
      </el-select>
      <el-date-picker v-model="filters.dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" @change="fetchData" />
      <el-button type="primary" @click="fetchData">查询</el-button>
    </div>

    <div class="table-container">
      <el-table :data="tableData" border stripe v-loading="loading" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="50" />
        <el-table-column prop="order_no" label="订单号" width="180" />
        <el-table-column prop="customer_name" label="客户姓名" width="120" />
        <el-table-column prop="product_name" label="产品" width="150" />
        <el-table-column prop="quantity" label="数量" width="80" align="center" />
        <el-table-column prop="tracking_number" label="快递单号" width="180">
          <template #default="{ row }">
            <span v-if="row.tracking_number">{{ row.tracking_number }}</span>
            <el-tag v-else type="warning" size="small">未填写</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="shipping_company" label="快递公司" width="120">
          <template #default="{ row }">
            {{ row.shipping_company || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ship_date" label="发货日期" width="120">
          <template #default="{ row }">
            {{ row.ship_date || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="salesperson_name" label="业务员" width="100" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button v-if="!row.tracking_number" type="primary" link size="small" @click="openEditTracking(row)">填写单号</el-button>
            <el-button v-if="row.status === 'pending'" type="success" link size="small" @click="handleShipSingle(row)">标记发货</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="pagination-container">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="fetchData"
        @current-change="fetchData"
      />
    </div>

    <!-- 批量发货对话框 -->
    <el-dialog v-model="showBatchShipDialog" title="批量发货" width="500px">
      <el-alert v-if="selectedRows.length === 0" title="请先在列表中勾选需要发货的订单" type="warning" show-icon :closable="false" style="margin-bottom: 16px" />
      <div v-else>
        <p>已选择 <strong>{{ selectedRows.length }}</strong> 个订单</p>
        <el-form :model="batchShipForm" label-width="100px" style="margin-top: 16px">
          <el-form-item label="快递公司">
            <el-select v-model="batchShipForm.shipping_company" placeholder="选择快递公司" filterable allow-create style="width: 100%">
              <el-option label="顺丰速运" value="顺丰速运" />
              <el-option label="中通快递" value="中通快递" />
              <el-option label="圆通速递" value="圆通速递" />
              <el-option label="韵达快递" value="韵达快递" />
              <el-option label="申通快递" value="申通快递" />
              <el-option label="极兔速递" value="极兔速递" />
              <el-option label="邮政快递" value="邮政快递" />
              <el-option label="京东物流" value="京东物流" />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="showBatchShipDialog = false">取消</el-button>
        <el-button type="primary" :disabled="selectedRows.length === 0" @click="handleBatchShip">确认发货</el-button>
      </template>
    </el-dialog>

    <!-- 导入快递单号对话框 -->
    <el-dialog v-model="showImportDialog" title="导入快递单号" width="500px">
      <el-alert title="Excel格式要求：订单号、快递单号、快递公司（三列）" type="info" show-icon :closable="false" style="margin-bottom: 16px" />
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :limit="1"
        accept=".xlsx,.xls"
        :on-change="handleFileChange"
      >
        <template #trigger>
          <el-button type="primary">选择文件</el-button>
        </template>
        <template #tip>
          <div class="el-upload__tip">仅支持 .xlsx / .xls 格式</div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="showImportDialog = false">取消</el-button>
        <el-button type="primary" :disabled="!importFile" :loading="importing" @click="handleImportTracking">导入</el-button>
      </template>
    </el-dialog>

    <!-- 编辑快递单号对话框 -->
    <el-dialog v-model="showEditTrackingDialog" title="填写快递单号" width="400px">
      <el-form :model="editTrackingForm" label-width="100px">
        <el-form-item label="快递公司">
          <el-select v-model="editTrackingForm.shipping_company" placeholder="选择快递公司" filterable allow-create style="width: 100%">
            <el-option label="顺丰速运" value="顺丰速运" />
            <el-option label="中通快递" value="中通快递" />
            <el-option label="圆通速递" value="圆通速递" />
            <el-option label="韵达快递" value="韵达快递" />
            <el-option label="申通快递" value="申通快递" />
            <el-option label="极兔速递" value="极兔速递" />
            <el-option label="邮政快递" value="邮政快递" />
            <el-option label="京东物流" value="京东物流" />
          </el-select>
        </el-form-item>
        <el-form-item label="快递单号">
          <el-input v-model="editTrackingForm.tracking_number" placeholder="输入快递单号" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditTrackingDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveTracking">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getShipments, batchShip, importTrackingNumbers } from '@/api'

const loading = ref(false)
const tableData = ref([])
const selectedRows = ref([])
const showBatchShipDialog = ref(false)
const showImportDialog = ref(false)
const showEditTrackingDialog = ref(false)
const importFile = ref(null)
const importing = ref(false)
const uploadRef = ref()

const filters = reactive({
  keyword: '',
  status: '',
  dateRange: null
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const batchShipForm = reactive({
  shipping_company: ''
})

const editTrackingForm = reactive({
  order_id: null,
  shipping_company: '',
  tracking_number: ''
})

const statusTagType = (status) => {
  const map = { pending: 'warning', shipped: 'primary', received: 'success' }
  return map[status] || 'info'
}

const statusLabel = (status) => {
  const map = { pending: '待发货', shipped: '已发货', received: '已签收' }
  return map[status] || status
}

const fetchData = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (filters.keyword) params.keyword = filters.keyword
    if (filters.status) params.status = filters.status
    if (filters.dateRange) {
      params.start_date = filters.dateRange[0]
      params.end_date = filters.dateRange[1]
    }
    const res = await getShipments(params)
    tableData.value = res.data.items || res.data
    pagination.total = res.data.total || 0
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const handleSelectionChange = (rows) => {
  selectedRows.value = rows
}

const handleBatchShip = async () => {
  try {
    const orderIds = selectedRows.value.map(r => r.order_id || r.id)
    await batchShip({
      order_ids: orderIds,
      shipping_company: batchShipForm.shipping_company
    })
    ElMessage.success('批量发货成功')
    showBatchShipDialog.value = false
    batchShipForm.shipping_company = ''
    fetchData()
  } catch (e) {
    ElMessage.error('发货失败')
  }
}

const handleFileChange = (file) => {
  importFile.value = file.raw
}

const handleImportTracking = async () => {
  if (!importFile.value) return
  importing.value = true
  try {
    const formData = new FormData()
    formData.append('file', importFile.value)
    await importTrackingNumbers(formData)
    ElMessage.success('导入成功')
    showImportDialog.value = false
    importFile.value = null
    fetchData()
  } catch (e) {
    ElMessage.error('导入失败')
  } finally {
    importing.value = false
  }
}

const openEditTracking = (row) => {
  editTrackingForm.order_id = row.order_id || row.id
  editTrackingForm.shipping_company = row.shipping_company || ''
  editTrackingForm.tracking_number = row.tracking_number || ''
  showEditTrackingDialog.value = true
}

const handleSaveTracking = async () => {
  try {
    const formData = new FormData()
    const blob = new Blob([
      `订单号,快递单号,快递公司\n${editTrackingForm.order_id},${editTrackingForm.tracking_number},${editTrackingForm.shipping_company}`
    ], { type: 'text/csv' })
    formData.append('file', blob, 'tracking.xlsx')
    await importTrackingNumbers(formData)
    ElMessage.success('保存成功')
    showEditTrackingDialog.value = false
    fetchData()
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

const handleShipSingle = async (row) => {
  try {
    await ElMessageBox.confirm('确认标记该订单为已发货？', '确认')
    await batchShip({
      order_ids: [row.order_id || row.id],
      shipping_company: row.shipping_company || ''
    })
    ElMessage.success('已标记发货')
    fetchData()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('操作失败')
  }
}

onMounted(() => {
  fetchData()
})
</script>
