<template>
  <div class="page-container">
    <div class="page-header">
      <span class="page-title">客户管理</span>
      <div>
        <el-button @click="showImportDialog">
          <el-icon><Upload /></el-icon>导入客户
        </el-button>
        <el-button type="primary" @click="showAssignDialog" v-if="isAdmin">
          <el-icon><Share /></el-icon>批量分配
        </el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-input v-model="filters.keyword" placeholder="搜索姓名/手机/微信" clearable style="width: 200px" @clear="fetchData" @keyup.enter="fetchData" />
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 120px" @change="fetchData">
        <el-option label="未分配" value="unassigned" />
        <el-option label="已分配" value="assigned" />
        <el-option label="已添加" value="added" />
        <el-option label="已转化" value="converted" />
        <el-option label="已流失" value="lost" />
      </el-select>
      <el-date-picker v-model="filters.date_range" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 240px" @change="fetchData" />
      <el-button @click="fetchData">查询</el-button>
    </div>

    <div class="table-container">
      <el-table :data="tableData" v-loading="loading" border stripe @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" v-if="isAdmin" />
        <el-table-column prop="name" label="客户姓名" width="100" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="wechat" label="微信号" width="130" />
        <el-table-column prop="source" label="来源" width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.source || formatSource(row) }}</template>
        </el-table-column>
        <el-table-column prop="assigned_to_name" label="所属业务员" width="100" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusType[row.status]">{{ statusMap[row.status] }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="assign_date" label="分配日期" width="110" />
        <el-table-column prop="add_date" label="添加日期" width="110" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" v-if="row.status === 'assigned'" @click="markAdded(row)">标记已添加</el-button>
            <el-button size="small" v-if="row.status === 'added'" type="success" @click="markConverted(row)">标记转化</el-button>
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

    <!-- Import Dialog -->
    <el-dialog v-model="importDialogVisible" title="导入客户" width="450px">
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :limit="1"
        accept=".xlsx,.xls"
        :on-change="handleFileChange"
      >
        <template #trigger>
          <el-button>选择文件</el-button>
        </template>
        <template #tip>
          <div class="el-upload__tip">支持 .xlsx/.xls 格式，表头：姓名、手机号、微信号、进线日期、渠道、引流产品</div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="handleImport">导入</el-button>
      </template>
    </el-dialog>

    <!-- Batch Assign Dialog -->
    <el-dialog v-model="assignDialogVisible" title="批量分配客户" width="450px">
      <el-form label-width="80px">
        <el-form-item label="分配给">
          <el-select v-model="assignTarget" filterable placeholder="选择业务员" style="width: 100%">
            <el-option v-for="u in salesList" :key="u.id" :label="u.real_name" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <span>已选择 {{ selectedRows.length }} 个客户</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="assigning" @click="handleAssign">分配</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { getCustomers, importCustomers, batchAssignCustomers, updateCustomerStatus, getUsers } from '@/api'
import { useUserStore } from '@/store/user'
import { ElMessage } from 'element-plus'

const userStore = useUserStore()
const isAdmin = computed(() => userStore.isAdmin)

const statusMap = { unassigned: '未分配', assigned: '已分配', added: '已添加', converted: '已转化', lost: '已流失' }
const statusType = { unassigned: 'info', assigned: 'warning', added: 'primary', converted: 'success', lost: 'danger' }

const loading = ref(false)
const importing = ref(false)
const assigning = ref(false)
const tableData = ref([])
const selectedRows = ref([])
const importDialogVisible = ref(false)
const assignDialogVisible = ref(false)
const assignTarget = ref(null)
const salesList = ref([])
const importFile = ref(null)

const filters = reactive({ keyword: '', status: '', date_range: null })
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

const formatSource = (row) => {
  const parts = [row.channel, row.source_product].filter(Boolean)
  return parts.join(' · ') || '-'
}

const fetchData = async () => {
  loading.value = true
  try {
    const params = { page: pagination.page, page_size: pagination.pageSize, keyword: filters.keyword, status: filters.status }
    if (filters.date_range) {
      params.start_date = filters.date_range[0]
      params.end_date = filters.date_range[1]
    }
    Object.keys(params).forEach((k) => { if (params[k] === '' || params[k] === null) delete params[k] })
    const res = await getCustomers(params)
    tableData.value = res.items || res
    pagination.total = res.total || 0
  } finally {
    loading.value = false
  }
}

const handleSelectionChange = (rows) => { selectedRows.value = rows }

const showImportDialog = () => { importDialogVisible.value = true }

const handleFileChange = (file) => { importFile.value = file.raw }

const handleImport = async () => {
  if (!importFile.value) { ElMessage.warning('请选择文件'); return }
  importing.value = true
  try {
    await importCustomers(importFile.value)
    ElMessage.success('导入成功')
    importDialogVisible.value = false
    fetchData()
  } finally {
    importing.value = false
  }
}

const showAssignDialog = async () => {
  if (selectedRows.value.length === 0) { ElMessage.warning('请先选择客户'); return }
  // Load sales list
  const res = await getUsers({ role: 'employee', is_active: true, page_size: 100 })
  salesList.value = res.items || res
  assignDialogVisible.value = true
}

const handleAssign = async () => {
  if (!assignTarget.value) { ElMessage.warning('请选择业务员'); return }
  assigning.value = true
  try {
    await batchAssignCustomers({
      customer_ids: selectedRows.value.map((r) => r.id),
      salesperson_id: assignTarget.value,
    })
    ElMessage.success('分配成功')
    assignDialogVisible.value = false
    fetchData()
  } finally {
    assigning.value = false
  }
}

const markAdded = async (row) => {
  await updateCustomerStatus(row.id, { status: 'added' })
  ElMessage.success('已标记为已添加')
  fetchData()
}

const markConverted = async (row) => {
  await updateCustomerStatus(row.id, { status: 'converted' })
  ElMessage.success('已标记为已转化')
  fetchData()
}

onMounted(fetchData)
</script>
