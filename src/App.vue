<script setup lang="ts">
import { ref, computed } from "vue";
import { invoke } from "@tauri-apps/api/core";
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import Card from 'primevue/card';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Tag from 'primevue/tag';
import ProgressSpinner from 'primevue/progressspinner';
import Paginator from 'primevue/paginator';
import Toast from 'primevue/toast';
import { useToast } from "primevue/usetoast";

const stockSymbol = ref("");
const loading = ref(false); // 用于个股分析的加载
const downloadLoading = ref(false); // 用于下载财报的加载
const reportsLoading = ref(false); // 用于财报列表刷新的加载
const analysisResult = ref<any>(null);
const reports = ref<any[]>([]);
const reportsFirst = ref(0);
const reportsRows = ref(10);

// 计算当前显示的财报
const paginatedReports = computed(() => {
  return reports.value.slice(reportsFirst.value, reportsFirst.value + reportsRows.value);
});

const currentView = ref(localStorage.getItem('current_view') || 'home');
const toast = useToast();

// 切换视图
async function setView(view: string) {
  currentView.value = view;
  localStorage.setItem('current_view', view);
  if (view === 'reports') {
    await fetchReports();
  }
}

// 获取财报列表
async function fetchReports() {
  reportsLoading.value = true;
  try {
    const result = await invoke("list_reports") as any[];
    // 按日期降序排列，确保最新的在前面
    reports.value = result.sort((a, b) => b.date.localeCompare(a.date));
    // 刷新时重置到第一页
    reportsFirst.value = 0;
  } catch (error) {
    toast.add({ severity: 'error', summary: '错误', detail: '无法获取财报列表', life: 3000 });
  } finally {
    reportsLoading.value = false;
  }
}

function onPage(event: any) {
  reportsFirst.value = event.first;
  reportsRows.value = event.rows;
}

// 打开财报
async function openReport(path: string) {
  try {
    await invoke("open_file", { path });
  } catch (error) {
    toast.add({ severity: 'error', summary: '错误', detail: '无法打开文件', life: 3000 });
  }
}

async function startAnalysis(download = false) {
  if (!stockSymbol.value) {
    toast.add({ severity: 'warn', summary: '提示', detail: '请输入股票代码', life: 3000 });
    return;
  }
  
  if (download) {
    downloadLoading.value = true;
  } else {
    loading.value = true;
    setView('home'); // 如果是开始分析，自动跳转到概览页查看进度和结果
  }

  try {
    const result = await invoke("analyze_stock", { symbol: stockSymbol.value, download }) as any;
    analysisResult.value = result;
    
    if (download) {
      await fetchReports(); // 下载完成后刷新列表
    }
    
    toast.add({ 
      severity: 'success', 
      summary: '成功', 
      detail: download ? '分析完成并已下载财报' : '分析完成', 
      life: 3000 
    });
  } catch (error) {
    console.error(error);
    toast.add({ severity: 'error', summary: '错误', detail: `分析失败: ${error}`, life: 5000 });
  } finally {
    loading.value = false;
    downloadLoading.value = false;
  }
}

if (currentView.value === 'reports') {
  fetchReports();
}
</script>

<template>
  <div class="layout-wrapper">
    <Toast />
    <aside class="sidebar">
      <div class="logo">
        <i class="pi pi-chart-line" style="font-size: 2rem; color: var(--p-primary-color)"></i>
        <span>Oliviar</span>
      </div>
      <nav class="nav-menu">
        <div class="nav-item" :class="{ active: currentView === 'home' }" @click="setView('home')">
          <i class="pi pi-home"></i>
          <span>概览</span>
        </div>
        <div class="nav-item" :class="{ active: currentView === 'reports' }" @click="setView('reports')">
          <i class="pi pi-file-pdf"></i>
          <span>财报管理</span>
        </div>
        <div class="nav-item" :class="{ active: currentView === 'settings' }" @click="setView('settings')">
          <i class="pi pi-cog"></i>
          <span>设置</span>
        </div>
      </nav>
    </aside>
    
    <main class="main-content">
      <header class="top-bar">
        <div class="search-box">
          <div class="search-input-field">
            <i class="pi pi-search" />
            <InputText v-model="stockSymbol" placeholder="输入股票代码 (如 600036)" @keyup.enter="startAnalysis(false)" />
          </div>
          <div class="button-group">
            <Button label="开始分析" icon="pi pi-play" :loading="loading" @click="startAnalysis(false)" />
            <Button label="下载财报" icon="pi pi-download" severity="secondary" :loading="downloadLoading" @click="startAnalysis(true)" />
          </div>
        </div>
      </header>
      
      <section class="content-area">
        <div v-if="currentView === 'home'" class="view-container">
          <div v-if="loading" class="loader-container">
            <ProgressSpinner />
            <p>正在执行量化风控分析，请稍候...</p>
          </div>
          
          <div v-else-if="analysisResult" class="results-grid">
            <Card class="result-card stat-card">
              <template #title>
                <div class="card-header">
                  <span class="title">基本信息</span>
                  <Tag :value="analysisResult['证券代码']" severity="info" />
                </div>
              </template>
              <template #content>
                <div class="info-grid">
                  <div class="info-item">
                    <span class="label">股票名称</span>
                    <span class="value">{{ analysisResult["分析标的"] }}</span>
                  </div>
                  <div class="info-item">
                    <span class="label">所属行业</span>
                    <span class="value">{{ analysisResult["所属行业"] || 'N/A' }}</span>
                  </div>
                  <div class="info-item">
                    <span class="label">分析时间</span>
                    <span class="value">{{ analysisResult["分析时间"] }}</span>
                  </div>
                </div>
              </template>
            </Card>

            <Card class="result-card stat-card">
              <template #title>风险评估</template>
              <template #content>
                <div class="summary-stats">
                  <div class="stat-item">
                    <span class="label">HV20 (波动率)</span>
                    <span class="value" :class="{ 'text-red-500': parseFloat(analysisResult['HV20']) > 0.4 }">
                      {{ analysisResult["HV20"] || 'N/A' }}
                    </span>
                  </div>
                  <div class="stat-item">
                    <span class="label">流动性评估</span>
                    <Tag :value="analysisResult['流动性评估']" :severity="analysisResult['流动性评估'] === '良好' ? 'success' : 'warn'" />
                  </div>
                </div>
              </template>
            </Card>

            <Card class="result-card stat-card">
              <template #title>资金流向 (万元)</template>
              <template #content>
                <div class="summary-stats">
                  <div class="stat-item">
                    <span class="label">今日主力</span>
                    <span class="value" :class="parseFloat(analysisResult['今日主力净流入(万元)']) > 0 ? 'text-green-500' : 'text-red-500'">
                      {{ analysisResult["今日主力净流入(万元)"] || '0.00' }}
                    </span>
                  </div>
                  <div class="stat-item">
                    <span class="label">近一周</span>
                    <span class="value" :class="parseFloat(analysisResult['近一周主力净流入(万元)']) > 0 ? 'text-green-500' : 'text-red-500'">
                      {{ analysisResult["近一周主力净流入(万元)"] || '0.00' }}
                    </span>
                  </div>
                </div>
              </template>
            </Card>
            
            <Card class="result-card full-width">
              <template #title>详细财务 & 市场指标</template>
              <template #content>
                <DataTable :value="Object.entries(analysisResult).map(([k, v]) => ({ key: k, value: v }))" stripedRows responsiveLayout="scroll">
                  <Column field="key" header="指标项"></Column>
                  <Column field="value" header="数值"></Column>
                </DataTable>
              </template>
            </Card>
          </div>
          
          <div v-else class="empty-state">
            <i class="pi pi-search" style="font-size: 5rem; color: #eee"></i>
            <h3>输入股票代码并点击开始分析</h3>
          </div>
        </div>

        <div v-else-if="currentView === 'reports'" class="view-container reports-view">
          <div class="reports-header">
            <h2>已下载财报列表</h2>
            <Button icon="pi pi-refresh" label="刷新" @click="fetchReports" :loading="reportsLoading" />
          </div>
          
          <div class="table-content-wrapper">
            <DataTable :value="paginatedReports" stripedRows class="flex-table">
              <Column field="symbol" header="代码" sortable style="width: 15%"></Column>
              <Column field="name" header="名称" sortable style="width: 20%"></Column>
              <Column field="title" header="公告标题" sortable style="width: 40%"></Column>
              <Column field="date" header="发布日期" sortable style="width: 15%"></Column>
              <Column header="操作" style="width: 10%">
                <template #body="slotProps">
                  <Button icon="pi pi-external-link" label="打开" class="p-button-text" @click="openReport(slotProps.data.path)" />
                </template>
              </Column>
            </DataTable>
            
            <div class="sticky-paginator">
              <Paginator 
                :rows="reportsRows" 
                :totalRecords="reports.length" 
                :first="reportsFirst"
                @page="onPage"
                template="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink"
              />
            </div>
          </div>
        </div>

        <div v-else-if="currentView === 'settings'" class="view-container">
          <Card>
            <template #title>应用设置</template>
            <template #content>
              <p>更多配置选项即将上线...</p>
            </template>
          </Card>
        </div>
      </section>
    </main>
  </div>
</template>

<style>
:root {
  --sidebar-width: 260px;
  --top-bar-height: 70px;
}

body {
  margin: 0;
  font-family: var(--p-font-family);
  background-color: #f8f9fa;
  color: #333;
}

.layout-wrapper {
  display: flex;
  height: 100vh;
}

.sidebar {
  width: var(--sidebar-width);
  background: white;
  border-right: 1px solid #eee;
  display: flex;
  flex-direction: column;
}

.logo {
  height: var(--top-bar-height);
  display: flex;
  align-items: center;
  padding: 0 2rem;
  gap: 1rem;
  font-weight: bold;
  font-size: 1.5rem;
}

.nav-menu {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-grid {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.info-item {
  display: flex;
  justify-content: space-between;
}

.info-item .label {
  color: #999;
}

.reports-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.text-red-500 { color: #ef4444; }
.text-green-500 { color: #22c55e; }

.nav-item {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  cursor: pointer;
  gap: 1rem;
  color: #666;
  transition: all 0.2s;
}

.nav-item:hover {
  background: #f0f0f0;
}

.nav-item.active {
  background: var(--p-primary-50);
  color: var(--p-primary-color);
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.top-bar {
  height: var(--top-bar-height);
  background: white;
  border-bottom: 1px solid #eee;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 2rem;
}

.search-box {
  display: flex;
  gap: 1rem;
  width: 100%;
  max-width: 900px; /* 稍微增加宽度以容纳两个按钮 */
}

.button-group {
  display: flex;
  gap: 0.5rem;
}

.search-input-field {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
}

.search-input-field i {
  position: absolute;
  left: 1rem;
  color: #999;
  z-index: 1;
}

.search-input-field input {
  width: 100%;
  padding-left: 2.5rem !important;
}

.content-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto; /* 允许纵向滚动 */
}

.view-container {
  display: flex;
  flex-direction: column;
  padding: 2rem;
  position: relative;
}

.reports-view {
  padding-bottom: 0; /* 分页栏将使用自己的内边距 */
}

.table-content-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  position: relative;
}

.flex-table {
  flex: 1;
  overflow-y: auto;
  margin-bottom: 4rem; /* 为底部的分页栏留出固定空间 */
}

.sticky-paginator {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 4rem;
  background: transparent; /* 取消白色背景 */
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.flex-table :deep(.p-datatable-wrapper) {
  height: 100%;
}

/* 彻底移除表格所有可能的边框，只保留表头下方那一根 */
.flex-table :deep(.p-datatable),
.flex-table :deep(.p-datatable-table-container),
.flex-table :deep(.p-datatable-wrapper),
.flex-table :deep(.p-datatable-table),
.flex-table :deep(.p-datatable-thead),
.flex-table :deep(.p-datatable-tbody),
.flex-table :deep(.p-datatable-tfoot),
.flex-table :deep(.p-datatable-thead > tr > th),
.flex-table :deep(.p-datatable-tbody > tr > td),
.flex-table :deep(.p-datatable-tbody > tr) {
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
}

/* 唯独手动给表头单元格添加底边框 */
.flex-table :deep(.p-datatable-thead > tr > th) {
  border-bottom: 1px solid #eee !important;
  background: #f8f9fa !important;
}

/* 确保表格背景透明，防止遮挡 */
.flex-table :deep(.p-datatable-table) {
  background: transparent !important;
  border-collapse: collapse !important;
}

.flex-table :deep(.p-paginator) {
  display: none; /* 隐藏 DataTable 内部可能残留的分页器 */
}

.sticky-paginator :deep(.p-paginator) {
  border: none !important;
  background: transparent !important;
}

/* 确保分页栏在 reports-view 中处于最底部 */
.reports-view .flex-table {
  margin-top: 0;
}

.loader-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 60%;
  gap: 1rem;
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
}

.result-card.full-width {
  grid-column: 1 / -1;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 60%;
  color: #999;
}

.summary-stats {
  display: flex;
  gap: 2rem;
}

.stat-item {
  display: flex;
  flex-direction: column;
}

.stat-item .label {
  font-size: 0.875rem;
  color: #666;
}

.stat-item .value {
  font-size: 1.5rem;
  font-weight: bold;
  color: var(--p-primary-color);
}
.p-paginator .p-paginator-pages .p-paginator-page.p-highlight {
  background: var(--p-primary-color) !important;
  color: white !important;
}
</style>
