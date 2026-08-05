<template>
  <div class="page-container">
    <div class="page-header">
      <span class="page-title">员工管理</span>
      <el-button type="primary" @click="showDialog()">
        <el-icon><Plus /></el-icon>新增员工
      </el-button>
    </div>

    <div class="filter-bar">
      <el-input v-model="filters.keyword" placeholder="搜索姓名/手机号" clearable style="width: 200px" @clear="fetchData" @keyup.enter="fetchData" />
      <el-select v-model="filters.role" placeholder="角色" clearable style="width: 120px" @change="fetchData">
        <el-option label="管理员" value="admin" />
        <el-option label="主管" value="manager" />
        <el-option label="员工" value="employee" />
      </el-select>
      <el-select v-model="filters.is_active" placeholder="状态" clearable style="width: 120px" @change="fetchData">
        <el-option label="启用" :value="true" />
        <el-option label="禁用" :value="false" />
      </el-select>
      <el-button @click="fetchData">查询</el-button>
    </div>

    <div class="table-container">
      <el-table :data="tableData" v-loading="loading" border stripe>
        <el-table-column prop="real_name" label="姓名" width="100" />
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="role" label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : row.role === 'manager' ? 'warning' : 'info'">
              {{ roleMap[row.role] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="team" label="团队" width="120" />
        <el-table-column prop="commission_rate" label="提成比例" width="100">
          <template #default="{ row }">{{ (row.commission_rate * 100).toFixed(1) }}%</template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showDialog(row)">编辑</el-button>
            <el-button size="small" :type="row.is_active ? 'danger' : 'success'" @click="toggleStatus(row)">
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </div>

    <!-- Add/Edit Dialog -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑员工' : '新增员工'" width="500px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="!!editingId" />
        </el-form-item>
        <el-form-item label="姓名" prop="real_name">
          <el-input v-model="form.real_name" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item label="密码" :prop="editingId ? '' : 'password'">
          <el-input v-model="form.password" type="password" :placeholder="editingId ? '留空不修改' : '请输入密码'" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="form.role" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="主管" value="manager" />
            <el-option label="员工" value="employee" />
          </el-select>
        </el-form-item>
        <el-form-item label="团队">
          <el-input v-model="form.team" />
        </el-form-item>
        <el-form-item label="提成比例">
          <el-input-number v-model="form.commission_rate" :min="0" :max="1" :step="0.01" :precision="2" />
          <span style="margin-left: 8px; color: #909399">例: 0.05 = 5%</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getUsers, createUser, updateUser } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const roleMap = { admin: '管理员', manager: '主管', employee: '员工' }

const loading = ref(false)
const submitting = ref(false)
const tableData = ref([])
const dialogVisible = ref(false)
const editingId = ref(null)
const formRef = ref(null)

const filters = reactive({ keyword: '', role: '', is_active: '' })
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

const form = reactive({
  username: '', real_name: '', phone: '', password: '', role: 'employee', team: '', commission_rate: 0.05,
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, message: '用户名至少3位', trigger: 'blur' },
  ],
  real_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' },
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  phone: [
    {
      validator: (rule, value, callback) => {
        if (!value) return callback()
        if (!/^1[3-9]\d{9}$/.test(value)) return callback(new Error('手机号格式不正确'))
        callback()
      },
      trigger: 'blur',
    },
  ],
}

const fetchData = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
      ...filters,
    }
    // Remove empty values
    Object.keys(params).forEach((k) => { if (params[k] === '' || params[k] === null) delete params[k] })
    const res = await getUsers(params)
    tableData.value = res.items || res
    pagination.total = res.total || 0
  } finally {
    loading.value = false
  }
}

const showDialog = (row) => {
  if (row) {
    editingId.value = row.id
    Object.assign(form, { ...row, password: '' })
  } else {
    editingId.value = null
    Object.assign(form, { username: '', real_name: '', phone: '', password: '', role: 'employee', team: '', commission_rate: 0.05 })
  }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const data = { ...form }
    if (editingId.value && !data.password) delete data.password

    if (editingId.value) {
      await updateUser(editingId.value, data)
      ElMessage.success('更新成功')
    } else {
      await createUser(data)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } finally {
    submitting.value = false
  }
}

const toggleStatus = async (row) => {
  const action = row.is_active ? '禁用' : '启用'
  await ElMessageBox.confirm(`确定要${action}员工"${row.real_name}"吗？`, '提示', { type: 'warning' })
  await updateUser(row.id, { is_active: !row.is_active })
  ElMessage.success(`${action}成功`)
  fetchData()
}

onMounted(fetchData)
</script>
