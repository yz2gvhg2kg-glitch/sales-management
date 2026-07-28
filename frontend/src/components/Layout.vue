<template>
  <el-container class="layout-container">
    <el-aside :width="isCollapse ? '64px' : '220px'" class="layout-aside">
      <div class="logo-container">
        <el-icon :size="28" color="#409EFF" v-if="isCollapse"><DataAnalysis /></el-icon>
        <span v-else class="logo-text">销售管理系统</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        :router="true"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>数据总览</template>
        </el-menu-item>
        <el-menu-item index="/employees" v-if="isAdmin">
          <el-icon><User /></el-icon>
          <template #title>员工管理</template>
        </el-menu-item>
        <el-menu-item index="/products" v-if="isAdmin">
          <el-icon><Goods /></el-icon>
          <template #title>产品管理</template>
        </el-menu-item>
        <el-menu-item index="/customers">
          <el-icon><UserFilled /></el-icon>
          <template #title>客户管理</template>
        </el-menu-item>
        <el-menu-item index="/orders">
          <el-icon><Document /></el-icon>
          <template #title>订单管理</template>
        </el-menu-item>
        <el-menu-item index="/shipments">
          <el-icon><Van /></el-icon>
          <template #title>发货管理</template>
        </el-menu-item>
        <el-sub-menu index="/statistics">
          <template #title>
            <el-icon><TrendCharts /></el-icon>
            <span>数据统计</span>
          </template>
          <el-menu-item index="/statistics/addition">添加率统计</el-menu-item>
          <el-menu-item index="/statistics/conversion">转化统计</el-menu-item>
          <el-menu-item index="/statistics/performance">业绩核算</el-menu-item>
          <el-menu-item index="/statistics/finance" v-if="isAdmin">财务结算</el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="layout-header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapse = !isCollapse">
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
        </div>
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-icon><Avatar /></el-icon>
              {{ userStore.username }}
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="layout-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const isCollapse = ref(false)

const isAdmin = computed(() => userStore.isAdmin)
const activeMenu = computed(() => route.path)

const handleCommand = (command) => {
  if (command === 'logout') {
    userStore.logout()
    router.push('/login')
  }
}
</script>

<style lang="scss" scoped>
.layout-container {
  height: 100vh;
}

.layout-aside {
  background-color: #304156;
  transition: width 0.3s;
  overflow: hidden;

  .el-menu {
    border-right: none;
  }
}

.logo-container {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #263445;

  .logo-text {
    color: #fff;
    font-size: 16px;
    font-weight: 700;
    white-space: nowrap;
  }

  .logo-icon {
    width: 32px;
    height: 32px;
  }
}

.layout-header {
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: #606266;
  &:hover {
    color: #409EFF;
  }
}

.header-right {
  .user-info {
    display: flex;
    align-items: center;
    gap: 4px;
    cursor: pointer;
    color: #606266;
    font-size: 14px;
  }
}

.layout-main {
  background: #f0f2f5;
  overflow-y: auto;
}
</style>
