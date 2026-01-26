<script setup lang="ts">
// @ts-nocheck
import { ref, computed, onMounted, watch } from "vue";
import { invoke, convertFileSrc } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import Card from 'primevue/card';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Tag from 'primevue/tag';
import ProgressSpinner from 'primevue/progressspinner';
import Paginator from 'primevue/paginator';
import Toast from 'primevue/toast';
import Tabs from 'primevue/tabs';
import TabList from 'primevue/tablist';
import Tab from 'primevue/tab';
import TabPanels from 'primevue/tabpanels';
import TabPanel from 'primevue/tabpanel';
import Divider from 'primevue/divider';
import { useToast } from "primevue/usetoast";

const stockSymbol = ref("");
const loading = ref(false); // 用于个股分析的加载
const downloadLoading = ref(false); // 用于下载财报的加载
const reportsLoading = ref(false); // 用于财报列表刷新的加载
const downloadPath = ref(localStorage.getItem('downloadPath') || '');
const analysisResult = ref<any>(null);

// 监听下载路径变化并保存
watch(downloadPath, (newPath) => {
  localStorage.setItem('downloadPath', newPath);
});

async function selectDownloadPath() {
  try {
    const selected = await open({
      directory: true,
      multiple: false,
      title: '选择下载保存路径'
    });
    if (selected) {
      downloadPath.value = selected as string;
    }
  } catch (error) {
    toast.add({ severity: 'error', summary: '错误', detail: '选择路径失败', life: 3000 });
  }
}

const emptyResult = {
  "分析标的": "等待分析",
  "证券代码": "000000",
  "所属行业": "N/A",
  "分析时间": "尚未执行",
  "涨幅": "N/A",
  "现价": "N/A",
  "涨跌": "N/A",
  "主力净额": "N/A",
  "主力净量": "N/A",
  "涨速": "N/A",
  "总市值": "N/A",
  "流通市值": "N/A",
  "净利润": "N/A",
  "成交额": "N/A",
  "换手率%": "N/A",
  "振幅": "N/A",
  "市盈(静)": "N/A",
  "市盈(动)": "N/A",
  "市盈率(TTM)": "N/A",
  "市净率(MRQ)": "N/A",
  "最高": "N/A",
  "最低": "N/A",
  "开盘": "N/A",
  "昨收": "N/A",
  "外盘": "N/A",
  "内盘": "N/A",
  "5日涨幅": "N/A",
  "10日涨幅": "N/A",
  "20日涨幅": "N/A",
  "总股本": "N/A",
  "流通股本": "N/A",
  "净利润同比": "N/A",
  "净资产收益率(ROE)": "N/A",
  "资产负债率": "N/A",
  "基本每股收益": "N/A",
  "每股净资产": "N/A",
  "股息率": "N/A",
  "商誉": "N/A",
  "营业总收入": "N/A",
  "营业利润": "N/A",
  "归母净利润": "N/A",
  "扣非净利润": "N/A",
  "营业总收入同比": "N/A",
  "营业利润同比": "N/A",
  "归母净利润同比": "N/A",
  "扣非净利润同比": "N/A",
  "销售毛利率": "N/A",
  "销售净利率": "N/A",
  "每股经营现金流": "N/A",
  "每股未分配利润": "N/A",
  "每股公积金": "N/A",
  "HV20": "N/A",
  "HV60": "N/A",
  "行业相关性": "N/A",
  "流动性评估": "N/A",
  "买卖盘深度": "N/A",
  "今日主力净流入(万元)": "0.00",
  "近一周主力净流入(万元)": "0.00",
  "资金流向饼图": null,
  "historical_data": Array.from({ length: 5 }, () => ({}))
};

const displayResult = computed(() => analysisResult.value || emptyResult);

// 定义每个选项卡显示的 Excel 表头
const tabColumns = {
  "0": ["日期", "现价", "涨幅", "涨跌", "涨速", "换手率%", "成交额", "振幅", "最高", "最低", "开盘", "昨收"],
  "1": ["日期", "营业总收入", "营业利润", "归母净利润", "扣非净利润", "净资产收益率(ROE)", "销售毛利率", "销售净利率", "每股经营现金流", "每股未分配利润", "每股公积金", "股息率", "资产负债率", "商誉"],
  "2": ["日期", "市盈率(TTM)", "市盈(静)", "市盈(动)", "市净率(MRQ)", "营业总收入同比", "营业利润同比", "归母净利润同比", "扣非净利润同比", "总市值", "流通市值", "总股本", "流通股本", "基本每股收益", "每股净资产"],
  "3": ["日期", "HV20", "HV60", "行业相关性", "流动性评估", "买卖盘深度", "5日涨幅", "10日涨幅", "20日涨幅", "60日涨跌幅"],
  "4": ["日期", "流入小单", "流入中单", "流入大单", "流入特大单", "流出小单", "流出中单", "流出大单", "流出特大单"]
};

function onCellEditComplete(event: any) {
    let { data, newValue, field } = event;
    data[field] = newValue;
}

const reports = ref<any[]>([]);
const reportsFirst = ref(0);
const reportsRows = ref(10);
const searchQuery = ref("");

// 移除局部排序用的 paginatedReports，直接使用 DataTable 内置分页实现全局排序
const filteredReports = computed(() => {
  if (!searchQuery.value) return reports.value;
  const query = searchQuery.value.toLowerCase();
  return reports.value.filter(report => 
    report.symbol.toLowerCase().includes(query) ||
    report.name.toLowerCase().includes(query) ||
    report.title.toLowerCase().includes(query)
  );
});

const currentView = ref(localStorage.getItem('current_view') || 'home');
const toast = useToast();
const exportLoading = ref(false);

async function downloadAllExcel() {
  if (!analysisResult.value || !downloadPath.value) {
    toast.add({ severity: 'warn', summary: '提示', detail: '请先完成分析并设置下载路径', life: 3000 });
    return;
  }

  exportLoading.value = true;
  try {
    const symbol = analysisResult.value["证券代码"];
    const name = analysisResult.value["分析标的"];
    const tabNames = {
      "0": "行情数据",
      "1": "深度财务",
      "2": "成长与估值",
      "3": "风险与量化",
      "4": "资金流向分析"
    };

    const promises = Object.entries(tabColumns).map(async ([key, columns]) => {
      const tabName = tabNames[key as keyof typeof tabNames];
      const filename = `${symbol}_${name}_${tabName}.xlsx`;
      // 将文件保存到标的对应的子文件夹中
      const subFolder = `${symbol}_${name}`;
      const fullPath = `${downloadPath.value}\\${subFolder}`;
      
      return invoke("export_excel", {
        path: fullPath,
        filename: filename,
        columns: columns,
        data: analysisResult.value.historical_data
      });
    });

    await Promise.all(promises);
    toast.add({ severity: 'success', summary: '成功', detail: '五份 Excel 文件已导出至指定路径', life: 3000 });
  } catch (error) {
    console.error("Export failed:", error);
    toast.add({ severity: 'error', summary: '错误', detail: '导出 Excel 失败: ' + error, life: 5000 });
  } finally {
    exportLoading.value = false;
  }
}

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
    const result = await invoke("list_reports", { 
      outputDir: downloadPath.value || null 
    }) as any[];
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

// 打开文件夹
async function openFolder(path: string) {
  try {
    await invoke("show_in_folder", { path });
  } catch (error) {
    toast.add({ severity: 'error', summary: '错误', detail: '无法打开文件夹', life: 3000 });
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
    setView('analysis'); // 开始分析后跳转到“标的数据”视图
  }

  try {
    const result = await invoke("analyze_stock", { 
      symbol: stockSymbol.value, 
      download,
      outputDir: downloadPath.value || null
    }) as any;

    if (result.error) {
      throw new Error(result.error);
    }

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
        <div class="nav-menu-top">
          <div class="nav-item" :class="{ active: currentView === 'home' }" @click="setView('home')">
            <i class="pi pi-home"></i>
            <span>主页</span>
          </div>
          <div class="nav-item" :class="{ active: currentView === 'analysis' }" @click="setView('analysis')">
            <i class="pi pi-database"></i>
            <span>标的数据</span>
          </div>
          <div class="nav-item" :class="{ active: currentView === 'reports' }" @click="setView('reports')">
            <i class="pi pi-file-pdf"></i>
            <span>财报管理</span>
          </div>
          
        </div>
        <div class="nav-menu-bottom">
          <div class="nav-item" :class="{ active: currentView === 'settings' }" @click="setView('settings')">
            <i class="pi pi-cog"></i>
            <span>设置</span>
          </div>
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
        <div v-if="currentView === 'home'" class="view-container welcome-view">
          <div class="welcome-content">
            <div class="welcome-header">
              <h1>Oliviar</h1>
              <p>智能、专业、高效的量化风控与深度财务分析平台</p>
            </div>
            <div class="quick-actions">
              <Card class="action-card" @click="setView('analysis')">
                <template #title><i class="pi pi-search"></i> 标的分析</template>
                <template #content>输入股票代码，快速获取行情、财务、估值及资金流向的深度量化报告。</template>
              </Card>
              <Card class="action-card" @click="setView('reports')">
                <template #title><i class="pi pi-file-pdf"></i> 财报管理</template>
                <template #content>查看已下载的财报公告，支持本地预览与目录管理。</template>
              </Card>
            </div>
          </div>
        </div>

        <div v-else-if="currentView === 'analysis'" class="view-container">
          <div class="analysis-container">
            <!-- 顶部基本信息 -->
            <div class="basic-info-section">
              <div class="info-header-vertical">
                <div class="stock-name">{{ displayResult["分析标的"] }}</div>
                <div class="stock-meta-list">
                  <div class="meta-row">
                    <span class="meta-label">标的代码：</span>
                    <span class="meta-value">{{ displayResult['证券代码'] }}</span>
                  </div>
                  <div class="meta-row">
                    <span class="meta-label">所属行业：</span>
                    <span class="meta-value">{{ displayResult["所属行业"] || 'N/A' }}</span>
                  </div>
                  <div class="meta-row">
                    <span class="meta-label">分析时间：</span>
                    <span class="meta-value">{{ displayResult["分析时间"] }}</span>
                  </div>
                </div>
              </div>
            </div>

            <Divider />

            <!-- 下方选项卡机制 -->
            <Tabs value="0" class="analysis-tabs">
              <div class="tabs-header-wrapper">
                <TabList>
                  <Tab value="0">行情数据</Tab>
                  <Tab value="4">资金流向分析</Tab>
                  <Tab value="1">深度财务</Tab>
                  <Tab value="2">成长与估值</Tab>
                  <Tab value="3">风险与量化</Tab>
                </TabList>
                <Button 
                  icon="pi pi-download" 
                  label="一键下载 (5份Excel)" 
                  class="p-button-outlined p-button-sm download-all-btn" 
                  @click="downloadAllExcel" 
                  :loading="exportLoading" 
                  v-if="analysisResult" 
                />
              </div>
                <TabPanels>
                <!-- 1. 行情数据 -->
                <TabPanel value="0">
                  <div class="excel-section">
                    <h3 class="section-title"><i class="pi pi-table mr-2"></i> 历史行情明细 (近一月)</h3>
                    <div v-if="loading" class="loader-container">
                      <ProgressSpinner />
                      <p>正在执行量化风控分析，请稍候...</p>
                    </div>
                    <div v-else-if="analysisResult">
                      <DataTable :value="displayResult.historical_data" editMode="cell" @cell-edit-complete="onCellEditComplete" class="p-datatable-sm excel-table" scrollable stripedRows showGridlines>
                        <Column v-for="col in tabColumns['0']" :key="col" :field="col" :header="col" sortable>
                          <template #editor="{ data, field }">
                            <InputText v-model="data[field]" autofocus class="w-full" />
                          </template>
                        </Column>
                      </DataTable>
                    </div>
                    <div v-else class="no-data-message">
                      <p><i>尚未查询</i></p>
                    </div>
                  </div>
                </TabPanel>

                <!-- 2. 资金流向分析 -->
                <TabPanel value="4">
                  <div class="fund-flow-container">
                    <div class="fund-flow-table-section">
                      <div class="excel-section">
                        <h3 class="section-title"><i class="pi pi-table mr-2"></i> 历史资金流向明细 (近一月)</h3>
                        <div v-if="loading" class="loader-container">
                          <ProgressSpinner />
                          <p>正在执行量化风控分析，请稍候...</p>
                        </div>
                        <div v-else-if="analysisResult">
                          <DataTable :value="displayResult.historical_data" editMode="cell" @cell-edit-complete="onCellEditComplete" class="p-datatable-sm excel-table" scrollable stripedRows showGridlines>
                            <Column v-for="col in tabColumns['4']" :key="col" :field="col" :header="col" sortable>
                              <template #editor="{ data, field }">
                                <InputText v-model="data[field]" autofocus class="w-full" />
                              </template>
                            </Column>
                          </DataTable>
                        </div>
                        <div v-else class="no-data-message">
                          <p><i>尚未查询</i></p>
                        </div>
                      </div>
                    </div>
                  </div>
                </TabPanel>

                <!-- 3. 深度财务 -->
                <TabPanel value="1">
                  <!-- 历史数据表格 (Excel 风格) -->
                  <div class="excel-section">
                    <h3 class="section-title"><i class="pi pi-table mr-2"></i> 历史深度财务明细 (近一月)</h3>
                    <div v-if="loading" class="loader-container">
                      <ProgressSpinner />
                      <p>正在执行量化风控分析，请稍候...</p>
                    </div>
                    <div v-else-if="analysisResult">
                      <DataTable :value="displayResult.historical_data" editMode="cell" @cell-edit-complete="onCellEditComplete" class="p-datatable-sm excel-table" scrollable stripedRows showGridlines>
                        <Column v-for="col in tabColumns['1']" :key="col" :field="col" :header="col" sortable>
                          <template #editor="{ data, field }">
                            <InputText v-model="data[field]" autofocus class="w-full" />
                          </template>
                        </Column>
                      </DataTable>
                    </div>
                    <div v-else class="no-data-message">
                      <p><i>尚未查询</i></p>
                    </div>
                  </div>
                </TabPanel>

                <!-- 3. 成长与估值 -->
                <TabPanel value="2">
                  <!-- 历史数据表格 (Excel 风格) -->
                  <div class="excel-section">
                    <h3 class="section-title"><i class="pi pi-table mr-2"></i> 历史成长与估值明细 (近一月)</h3>
                    <div v-if="loading" class="loader-container">
                      <ProgressSpinner />
                      <p>正在执行量化风控分析，请稍候...</p>
                    </div>
                    <div v-else-if="analysisResult">
                      <DataTable :value="displayResult.historical_data" editMode="cell" @cell-edit-complete="onCellEditComplete" class="p-datatable-sm excel-table" scrollable stripedRows showGridlines>
                        <Column v-for="col in tabColumns['2']" :key="col" :field="col" :header="col" sortable>
                          <template #editor="{ data, field }">
                            <InputText v-model="data[field]" autofocus class="w-full" />
                          </template>
                        </Column>
                      </DataTable>
                    </div>
                    <div v-else class="no-data-message">
                      <p><i>尚未查询</i></p>
                    </div>
                  </div>
                </TabPanel>

                <!-- 4. 风险与量化 -->
                <TabPanel value="3">
                  <!-- 历史数据表格 (Excel 风格) -->
                  <div class="excel-section">
                    <h3 class="section-title"><i class="pi pi-table mr-2"></i> 历史风险与量化明细 (近一月)</h3>
                    <div v-if="loading" class="loader-container">
                      <ProgressSpinner />
                      <p>正在执行量化风控分析，请稍候...</p>
                    </div>
                    <div v-else-if="analysisResult">
                      <DataTable :value="displayResult.historical_data" editMode="cell" @cell-edit-complete="onCellEditComplete" class="p-datatable-sm excel-table" scrollable stripedRows showGridlines>
                        <Column v-for="col in tabColumns['3']" :key="col" :field="col" :header="col" sortable>
                          <template #editor="{ data, field }">
                            <InputText v-model="data[field]" autofocus class="w-full" />
                          </template>
                        </Column>
                      </DataTable>
                    </div>
                    <div v-else class="no-data-message">
                      <p><i>尚未查询</i></p>
                    </div>
                  </div>
                </TabPanel>
              </TabPanels>
            </Tabs>
          </div>
        </div>

        <div v-else-if="currentView === 'reports'" class="view-container reports-view">
          <div class="reports-header">
            <h2>已下载财报列表</h2>
            <div class="header-actions">
              <div class="report-search">
                <i class="pi pi-search" />
                <InputText v-model="searchQuery" placeholder="搜索代码、名称或标题..." class="p-inputtext-sm" @input="reportsFirst = 0" />
              </div>
              <Button icon="pi pi-refresh" label="刷新" @click="fetchReports" :loading="reportsLoading" />
            </div>
          </div>
          
          <div class="table-content-wrapper">
            <DataTable 
              :value="filteredReports" 
              paginator 
              :rows="reportsRows" 
              v-model:first="reportsFirst" 
              stripedRows 
              class="flex-table"
              paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
              currentPageReportTemplate="显示第 {first} 到 {last} 条，共 {totalRecords} 条"
            >
              <Column field="symbol" header="代码" sortable style="width: 15%"></Column>
              <Column field="name" header="名称" sortable style="width: 20%"></Column>
              <Column field="title" header="公告标题" sortable style="width: 40%"></Column>
              <Column field="date" header="发布日期" sortable style="width: 15%"></Column>
              <Column header="操作" style="width: 20%">
                <template #body="slotProps">
                  <div class="operation-buttons">
                    <Button icon="pi pi-external-link" label="打开" class="p-button-text p-button-sm" @click="openReport(slotProps.data.path)" />
                    <Button icon="pi pi-folder-open" label="文件夹" class="p-button-text p-button-sm" @click="openFolder(slotProps.data.path)" />
                  </div>
                </template>
              </Column>
            </DataTable>
          </div>
        </div>

        <div v-else-if="currentView === 'settings'" class="view-container">
          <Card>
            <template #title>通用设置</template>
            <template #content>
              <div class="settings-group">
                <h3>文件保存路径</h3>
                <p class="settings-desc">设置分析报告、资金流向图及下载财报的全局保存路径。</p>
                <div class="path-selector">
                  <InputText v-model="downloadPath" placeholder="默认保存至应用数据目录" class="path-input" readonly />
                  <Button icon="pi pi-folder-open" label="更改路径" @click="selectDownloadPath" />
                  <Button icon="pi pi-refresh" class="p-button-secondary" @click="downloadPath = ''" v-if="downloadPath" title="恢复默认" />
                </div>
              </div>
            </template>
          </Card>
        </div>
      </section>
    </main>
  </div>
</template>

<style>
:root {
  --sidebar-width: 200px;
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
  padding: 0 1.5rem;
  gap: 0.75rem;
  font-weight: bold;
  font-size: 1.25rem;
}

.nav-menu {
  flex: 1;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.nav-menu-top, .nav-menu-bottom {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.settings-group {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem 0;
}

.settings-group h3 {
  margin: 0;
  font-size: 1.1rem;
  color: #1a1a1a;
}

.settings-desc {
  color: #666;
  font-size: 0.9rem;
  margin: 0;
}

.path-selector {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.path-input {
  flex: 1;
  background: #f8f9fa !important;
}

.excel-section {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  border: 1px solid #eee;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.section-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 1rem;
  color: #2c3e50;
  display: flex;
  align-items: center;
}

.fund-flow-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  width: 100%;
  flex: 1;
  min-height: 0;
}

.fund-flow-table-section, .fund-flow-chart-section {
  width: 100%;
  flex: 1;
  min-height: 0;
}

.pie-chart-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 1rem;
}

.fund-flow-pie {
  max-width: 600px;
  width: 100%;
  height: auto;
  border-radius: 8px;
}

.no-chart {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #999;
}

.excel-table {
  border: 1px solid #f0f0f0;
}

.excel-table .p-datatable-thead > tr > th {
  background-color: #f8f9fa;
  color: #495057;
  font-weight: 600;
  font-size: 0.85rem;
  padding: 1rem 1.25rem; /* 增加表头行高 */
  border-right: 1px solid #e9ecef !important; /* 表头列分割线 */
}

.excel-table .p-datatable-tbody > tr > td {
  font-size: 0.9rem;
  padding: 0.8rem 1.25rem; /* 增加数据行高 */
  border-right: 1px solid #f0f0f0 !important; /* 数据列分割线 */
}

.excel-table.p-datatable-striped .p-datatable-tbody > tr:nth-child(even) {
  background-color: #fafafa; /* 斑马纹背景色 */
}

.excel-table .p-inputtext {
  font-size: 0.85rem;
  padding: 0.25rem 0.5rem;
}

.excel-table .p-editable-column.p-cell-editing {
  padding: 0 !important;
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
  margin-bottom: 1.5rem;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.report-search {
  position: relative;
  display: flex;
  align-items: center;
}

.report-search i {
  position: absolute;
  left: 0.75rem;
  color: #999;
}

.report-search input {
  padding-left: 2.5rem;
  width: 300px;
}

.operation-buttons {
  display: flex;
  gap: 0.5rem;
}

.text-red-500 { color: #ef4444; }
.text-green-500 { color: #22c55e; }

.nav-item {
  display: flex;
  align-items: center;
  padding: 0.75rem 0.75rem;
  border-radius: 8px;
  cursor: pointer;
  gap: 0.75rem;
  color: #666;
  transition: all 0.2s;
  font-size: 0.9rem;
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
  flex: 1;
  min-height: 0;
}

.reports-view {
  padding-bottom: 0; /* 分页栏将使用自己的内边距 */
}

.flex-table {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.flex-table :deep(.p-datatable-wrapper) {
  flex: 1;
  overflow-y: auto;
}

.flex-table :deep(.p-paginator) {
  border-top: 1px solid #eee !important;
  background: white !important;
  padding: 0.5rem !important;
  justify-content: center !important;
  flex-shrink: 0;
}

.table-content-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  position: relative;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.05);
  overflow: hidden;
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

/* 确保分页栏在 reports-view 中处于最底部 */
.reports-view .flex-table {
  margin-top: 0;
}

.loader-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  gap: 1rem;
  color: #666;
}

.analysis-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  flex: 1;
  min-height: 0;
}

.no-data-message {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  color: #999;
  height: 300px;
  border: 1px dashed #ddd;
  border-radius: 8px;
  margin-top: 1rem;
  background: #fafafa;
}

.welcome-view {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 80vh;
  background: radial-gradient(circle at top right, var(--p-primary-50), transparent);
}

.welcome-content {
  text-align: center;
  max-width: 800px;
  width: 100%;
}

.welcome-header h1 {
  font-size: 3rem;
  font-weight: 800;
  margin-bottom: 1rem;
  color: #1a1a1a;
}

.welcome-header p {
  font-size: 1.25rem;
  color: #666;
  margin-bottom: 3rem;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 2rem;
}

.action-card {
  cursor: pointer;
  transition: all 0.3s;
  border: 1px solid #eee;
  text-align: left;
}

.action-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0,0,0,0.1);
  border-color: var(--p-primary-color);
}

.action-card :deep(.p-card-title) {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1.25rem;
  color: #333;
}

.action-card :deep(.p-card-title) i {
  color: var(--p-primary-color);
}

.action-card :deep(.p-card-content) {
  color: #666;
  line-height: 1.6;
}

.basic-info-section {
  padding: 1.5rem 0;
}

.info-header-vertical {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.stock-name {
  font-size: 2.5rem;
  font-weight: 800;
  color: #1a1a1a;
  line-height: 1;
}

.stock-meta-list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.meta-row {
  display: flex;
  align-items: center;
  font-size: 0.95rem;
  color: #666;
}

.meta-label {
  font-weight: 500;
  color: #888;
  width: 80px;
}

.meta-value {
  color: #333;
  font-weight: 600;
}

.analysis-tabs {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.analysis-tabs :deep(.p-tablist) {
  flex-shrink: 0;
}

.analysis-tabs :deep(.p-tabpanels) {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.analysis-tabs :deep(.p-tablist-content) {
  display: flex;
  justify-content: center;
  background: #f8f9fa;
  padding: 0.5rem;
  border-radius: 12px;
  margin: 0 1rem;
}

.analysis-tabs :deep(.p-tablist-tab-list) {
  border-bottom: none !important;
  background: transparent !important;
  gap: 0.5rem;
}

.analysis-tabs :deep(.p-tab) {
  border-radius: 8px !important;
  transition: all 0.3s;
  padding: 0.5rem 1.5rem !important;
  border: none !important;
  color: #666 !important;
}

.analysis-tabs :deep(.p-tab-active) {
  background: white !important;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05) !important;
  color: var(--p-primary-color) !important;
}

.analysis-tabs :deep(.p-tab-active-bar) {
  display: none;
}

.analysis-tabs :deep(.p-tabpanel) {
  padding: 1.5rem 0;
}

.excel-section {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  border: 1px solid #eee;
}

.section-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 1rem;
  color: #2c3e50;
  display: flex;
  align-items: center;
}

.excel-table {
  border: 1px solid #f0f0f0;
}

.excel-table .p-datatable-thead > tr > th {
  background-color: #f8f9fa;
  color: #495057;
  font-weight: 600;
  font-size: 0.85rem;
  padding: 0.75rem 1rem;
}

.excel-table .p-datatable-tbody > tr > td {
  font-size: 0.85rem;
  padding: 0.5rem 1rem;
}

.excel-table .p-inputtext {
  font-size: 0.85rem;
  padding: 0.25rem 0.5rem;
}

.excel-table .p-editable-column.p-cell-editing {
  padding: 0 !important;
}

.p-paginator .p-paginator-pages .p-paginator-page.p-highlight {
  background: var(--p-primary-color) !important;
  color: white !important;
}
.tabs-header-wrapper {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-right: 1rem;
  border-bottom: 1px solid #e9ecef;
}

.download-all-btn {
  height: 32px;
  align-self: center;
}
</style>
