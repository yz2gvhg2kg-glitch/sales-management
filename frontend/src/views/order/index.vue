<template>
  <div class="page-container">
    <div class="page-header">
      <span class="page-title">订单管理</span>
      <div>
        <el-button @click="showImportDialog">
          <el-icon><Upload /></el-icon>导入订单
        </el-button>
        <el-button type="primary" @click="showCreateDialog">
          <el-icon><Plus /></el-icon>新建订单
        </el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-input v-model="filters.keyword" placeholder="搜索订单号/客户" clearable style="width: 200px" @clear="fetchData" @keyup.enter="fetchData" />
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 120px" @change="fetchData">
        <el-option label="待发货" value="pending" />
        <el-option label="已发货" value="shipped" />
        <el-option label="已完成" value="completed" />
        <el-option label="已退货" value="returned" />
        <el-option label="已换货" value="exchanged" />
        <el-option label="已拒收" value="rejected" />
      </el-select>
      <el-date-picker v-model="filters.date_range" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 240px" @change="fetchData" />
      <el-button @click="fetchData">查询</el-button>
    </div>

    <div class="table-container">
      <el-table :data="tableData" v-loading="loading" border stripe>
        <el-table-column prop="order_no" label="订单号" width="160" />
        <el-table-column prop="customer_name" label="客户" width="100" />
        <el-table-column prop="product_name" label="产品" width="150" show-overflow-tooltip />
        <el-table-column prop="quantity" label="数量" width="70" />
        <el-table-column prop="amount" label="金额" width="100">
          <template #default="{ row }">¥{{ row.amount?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="salesperson_name" label="业务员" width="100" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="orderStatusType[row.status]">{{ orderStatusMap[row.status] }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button size="small" v-if="canAfterSales(row)" @click="showAfterSalesDialog(row)">售后</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </div>

    <!-- Create Order Dialog -->
    <el-dialog v-model="createDialogVisible" title="新建订单" width="550px">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="80px">
        <el-form-item label="客户姓名" prop="customer_name">
          <el-input v-model="createForm.customer_name" />
        </el-form-item>
        <el-form-item label="客户电话">
          <el-input v-model="createForm.customer_phone" />
        </el-form-item>
        <el-form-item label="产品名称" prop="product_name">
          <el-input v-model="createForm.product_name" />
        </el-form-item>
        <el-form-item label="数量" prop="quantity">
          <el-input-number v-model="createForm.quantity" :min="1" />
        </el-form-item>
        <el-form-item label="金额" prop="amount">
          <el-input-number v-model="createForm.amount" :min="0" :precision="2" style="width: 200px" />
        </el-form-item>
        <el-form-item label="来源">
          <el-input v-model="createForm.source" placeholder="格式：进线日期.渠道.引流产品.所属业务员" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreate">确定</el-button>
      </template>
    </el-dialog>

    <!-- Import Dialog -->
    <el-dialog v-model="importDialogVisible" title="导入订单" width="450px">
      <el-upload ref="uploadRef" :auto-upload="false" :limit="1" accept=".xlsx,.xls" :on-change="handleFileChange">
        <template #trigger>
          <el-button>选择文件</el-button>
        </template>
        <template #tip>
          <div class="el-upload__tip">支持 .xlsx/.xls，表头：订单号、客户姓名、电话、产品、数量、金额、来源</div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="handleImport">导入</el-button>
      </template>
    </el-dialog>

    <!-- After Sales Dialog -->
    <el-dialog v-model="afterSalesDialogVisible" title="售后处理" width="450px">
      <el-form ref="afterSalesFormRef" :model="afterSalesForm" label-width="80px">
        <el-form-item label="订单号">
          <el-input :model-value="afterSalesForm.order_no" disabled />
        </el-form-item>
        <el-form-item label="处理类型" prop="type">
          <el-select v-model="afterSalesForm.type" style="width: 100%">
            <el-option label="退货" value="returned" />
            <el-option label="换货" value="exchanged" />
            <el-option label="拒收" value="rejected" />
          </el-select>
        </el-form-item>
        <el-form-item label="退款金额">
          <el-input-number v-model="afterSalesForm.refund_amount" :min="0" :precision="2" style="width: 200px" />
        </el-form-item>
        <el-form-item label="原因">
          <el-input v-model="afterSalesForm.reason" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="afterSalesDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleAfterSales">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getOrders, createOrder, importOrders, createAfterSales } from '@/api'
import { ElMessage } from 'element-plus'

const orderStatusMap = { pending: '待发货', shipped: '已发货', completed: '已完成', returned: '已退货', exchanged: '已换货', rejected: '已拒收' }
const orderStatusType = { pending: 'warning', shipped: 'primary', completed: 'success', returned: 'danger', exchanged: 'info', rejected: 'danger' }

const loading = ref(false)
const submitting = ref(false)
const importing = ref(false)
const tableData = ref([])
const createDialogVisible = ref(false)
const importDialogVisible = ref(false)
const afterSalesDialogVisible = ref(false)
const createFormRef = ref(null)
const importFile = ref(null)

const filters = reactive({ keyword: '', status: '', date_range: null })
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

const createForm = reactive({
  customer_name: '', customer_phone: '', product_name: '', quantity: 1, amount: 0, source: '',
})
const createRules = {
  customer_name: [{ required: true, message: '请输入客户姓名', trigger: 'blur' }],
  product_name: [{ required: true, message: '请输入产品名称', trigger: 'blur' }],
  amount: [{ required: true, message: '请输入金额', trigger: 'blur' }],
}

const afterSalesForm = reactive({ order_id: null, order_no: '', type: 'returned', refund_amount: 0, reason: '' })

const canAfterSales = (row) => ['shipped', 'completed'].includes(row.status)

const fetchData = async () => {
  loading.value = true
  try {
    const params = { page: pagination.page, page_size: pagination.pageSize, keyword: filters.keyword, status: filters.status }
    if (filters.date_range) {
      params.start_date = filters.date_range[0]
      params.end_date = filters.date_range[1]
    }
    Object.keys(params).forEach((k) => { if (params[k] === '' || params[k] === null) delete params[k] })
    const res = await getOrders(params)
    tableData.value = res.items || res
    pagination.total = res.total || 0
  } finally {
    loading.value = false
  }
}

const showCreateDialog = () => {
  Object.assign(createForm, { customer_name: '', customer_phone: '', product_name: '', quantity: 1, amount: 0, source: '' })
  createDialogVisible.value = true
}

const handleCreate = async () => {
  const valid = await createFormRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await createOrder(createForm)
    ElMessage.success('订单创建成功')
    createDialogVisible.value = false
    fetchData()
  } finally {
    submitting.value = false
  }
}

const showImportDialog = () => { importDialogVisible.value = true }
const handleFileChange = (file) => { importFile.value = file.raw }

const handleImport = async () => {
  if (!importFile.value) { ElMessage.warning('请选择文件'); return }
  importing.value = true
  try {
    await importOrders(importFile.value)
    ElMessage.success('导入成功')
    importDialogVisible.value = false
    fetchData()
  } finally {
    importing.value = false
  }
}

const showAfterSalesDialog = (row) => {
  Object.assign(afterSalesForm, { order_id: row.id, order_no: row.order_no, type: 'returned', refund_amount: row.amount, reason: '' })
  afterSalesDialogVisible.value = true
}

const handleAfterSales = async () => {
  submitting.value = true
  try {
    await createAfterSales(afterSalesForm)
    ElMessage.success('售后处理成功')
    afterSalesDialogVisible.value = false
    fetchData()
  } finally {
    submitting.value = false
  }
}

onMounted(fetchData)
</script>
