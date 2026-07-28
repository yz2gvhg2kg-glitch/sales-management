<template>
  <div class="page-container">
    <div class="page-header">
      <span class="page-title">产品管理</span>
      <el-button type="primary" @click="showDialog()">
        <el-icon><Plus /></el-icon>新增产品
      </el-button>
    </div>

    <div class="filter-bar">
      <el-input v-model="filters.keyword" placeholder="搜索产品名称/SKU" clearable style="width: 200px" @clear="fetchData" @keyup.enter="fetchData" />
      <el-select v-model="filters.category" placeholder="分类" clearable style="width: 150px" @change="fetchData">
        <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
      </el-select>
      <el-button @click="fetchData">查询</el-button>
    </div>

    <div class="table-container">
      <el-table :data="tableData" v-loading="loading" border stripe>
        <el-table-column prop="name" label="产品名称" min-width="150" />
        <el-table-column prop="category" label="分类" width="120" />
        <el-table-column prop="sku" label="SKU" width="120" />
        <el-table-column prop="price" label="售价(元)" width="100">
          <template #default="{ row }">¥{{ row.price?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="cost" label="成本(元)" width="100">
          <template #default="{ row }">¥{{ row.cost?.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="specs" label="规格" min-width="150" show-overflow-tooltip />
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'">{{ row.is_active ? '上架' : '下架' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showDialog(row)">编辑</el-button>
            <el-button size="small" :type="row.is_active ? 'danger' : 'success'" @click="toggleStatus(row)">
              {{ row.is_active ? '下架' : '上架' }}
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
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑产品' : '新增产品'" width="550px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="产品名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="分类" prop="category">
          <el-select v-model="form.category" filterable allow-create style="width: 100%">
            <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
          </el-select>
        </el-form-item>
        <el-form-item label="SKU">
          <el-input v-model="form.sku" />
        </el-form-item>
        <el-form-item label="售价" prop="price">
          <el-input-number v-model="form.price" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="成本" prop="cost">
          <el-input-number v-model="form.cost" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="规格">
          <el-input v-model="form.specs" type="textarea" :rows="3" placeholder="如：500ml/瓶, 30粒/盒" />
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
import { getProducts, createProduct, updateProduct } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const loading = ref(false)
const submitting = ref(false)
const tableData = ref([])
const dialogVisible = ref(false)
const editingId = ref(null)
const formRef = ref(null)
const categories = ref(['保健品', '护肤品', '食品', '日用品'])

const filters = reactive({ keyword: '', category: '' })
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

const form = reactive({
  name: '', category: '', sku: '', price: 0, cost: 0, specs: '',
})

const rules = {
  name: [{ required: true, message: '请输入产品名称', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  price: [{ required: true, message: '请输入售价', trigger: 'blur' }],
  cost: [{ required: true, message: '请输入成本', trigger: 'blur' }],
}

const fetchData = async () => {
  loading.value = true
  try {
    const params = { page: pagination.page, page_size: pagination.pageSize, ...filters }
    Object.keys(params).forEach((k) => { if (params[k] === '' || params[k] === null) delete params[k] })
    const res = await getProducts(params)
    tableData.value = res.items || res
    pagination.total = res.total || 0
  } finally {
    loading.value = false
  }
}

const showDialog = (row) => {
  if (row) {
    editingId.value = row.id
    Object.assign(form, row)
  } else {
    editingId.value = null
    Object.assign(form, { name: '', category: '', sku: '', price: 0, cost: 0, specs: '' })
  }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (editingId.value) {
      await updateProduct(editingId.value, form)
      ElMessage.success('更新成功')
    } else {
      await createProduct(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } finally {
    submitting.value = false
  }
}

const toggleStatus = async (row) => {
  const action = row.is_active ? '下架' : '上架'
  await ElMessageBox.confirm(`确定要${action}产品"${row.name}"吗？`, '提示', { type: 'warning' })
  await updateProduct(row.id, { is_active: !row.is_active })
  ElMessage.success(`${action}成功`)
  fetchData()
}

onMounted(fetchData)
</script>
