// Check if Electron API is available
if (typeof window.electronAPI === 'undefined') {
  console.error('Electron API not available. This application must be run in Electron.')
  showErrorScreen('Electron API not available')
  throw new Error('Electron API not available')
}

// Application state
interface AppState {
  isOnline: boolean
  isAuthenticated: boolean
  syncStatus: any
  documentCount: number
  currentUser: any
}

let appState: AppState = {
  isOnline: false,
  isAuthenticated: false,
  syncStatus: null,
  documentCount: 0,
  currentUser: null
}

// Initialize application
async function initializeApp() {
  try {
    console.log('Initializing desktop application...')
    
    // Check authentication status
    await checkAuthentication()
    
    // Initialize event listeners
    setupEventListeners()
    
    // Start monitoring
    await startMonitoring()
    
    // Load initial data
    await loadInitialData()
    
    // Hide loading screen and show app
    showApp()
    
    console.log('Application initialized successfully')
    
  } catch (error) {
    console.error('Failed to initialize application:', error)
    showErrorScreen(error.message || 'Failed to initialize application')
  }
}

// Authentication
async function checkAuthentication() {
  try {
    const isAuth = await window.electronAPI.auth.isAuthenticated()
    appState.isAuthenticated = isAuth
    
    if (isAuth) {
      appState.currentUser = await window.electronAPI.auth.getCurrentUser()
    }
    
    console.log('Authentication check:', isAuth)
  } catch (error) {
    console.error('Authentication check failed:', error)
    appState.isAuthenticated = false
  }
}

// Event listeners
function setupEventListeners() {
  // Navigation
  document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault()
      const page = (e.target as HTMLElement).getAttribute('data-page')
      if (page) {
        navigateToPage(page)
      }
    })
  })
  
  // Window events
  window.electronAPI.events.onWindowFocus(() => {
    console.log('Window focused')
    refreshData()
  })
  
  window.electronAPI.events.onWindowBlur(() => {
    console.log('Window blurred')
  })
  
  // Network events
  window.electronAPI.events.onOnline(() => {
    console.log('Network online')
    updateConnectionStatus(true)
  })
  
  window.electronAPI.events.onOffline(() => {
    console.log('Network offline')
    updateConnectionStatus(false)
  })
  
  // Document events
  window.electronAPI.events.onDocumentProcessed((result) => {
    console.log('Document processed:', result)
    refreshDocuments()
    updateDocumentCount()
  })
  
  // Sync events
  window.electronAPI.events.onSyncStarted(() => {
    console.log('Sync started')
    updateSyncStatus('Syncing...')
  })
  
  window.electronAPI.events.onSyncCompleted((result) => {
    console.log('Sync completed:', result)
    updateSyncStatus('Synced')
    refreshData()
  })
  
  window.electronAPI.events.onSyncFailed((error) => {
    console.error('Sync failed:', error)
    updateSyncStatus('Sync failed')
    showNotification('Sync failed: ' + error, 'error')
  })
  
  window.electronAPI.events.onSyncStatusChanged((status) => {
    console.log('Sync status changed:', status)
    updateSyncStatusUI(status)
  })
  
  // Update events
  window.electronAPI.updater.onUpdateAvailable((info) => {
    console.log('Update available:', info)
    showUpdateNotification(info)
  })
  
  window.electronAPI.updater.onUpdateDownloaded((info) => {
    console.log('Update downloaded:', info)
    showUpdateDownloaded(info)
  })
  
  window.electronAPI.updater.onUpdateProgress((progress) => {
    console.log('Update progress:', progress)
    updateDownloadProgress(progress)
  })
}

// Start monitoring services
async function startMonitoring() {
  // Check network status
  await updateConnectionStatus()
  
  // Check sync status
  await updateSyncStatus()
  
  // Start periodic refresh
  setInterval(refreshData, 30000) // Every 30 seconds
}

// Load initial data
async function loadInitialData() {
  try {
    // Load documents
    await refreshDocuments()
    await updateDocumentCount()
    
    // Load sync status
    await updateSyncStatus()
    
    // Update UI
    updateUI()
    
  } catch (error) {
    console.error('Failed to load initial data:', error)
  }
}

// Navigation
function navigateToPage(pageId: string) {
  // Hide all pages
  document.querySelectorAll('.content-page').forEach(page => {
    page.classList.remove('active')
  })
  
  // Show selected page
  const targetPage = document.getElementById(`${pageId}-page`)
  if (targetPage) {
    targetPage.classList.add('active')
  }
  
  // Update navigation
  document.querySelectorAll('.nav-link').forEach(link => {
    link.classList.remove('active')
  })
  
  const activeLink = document.querySelector(`[data-page="${pageId}"]`)
  if (activeLink) {
    activeLink.classList.add('active')
  }
  
  // Load page-specific data
  loadPageData(pageId)
}

// Load page-specific data
async function loadPageData(pageId: string) {
  switch (pageId) {
    case 'dashboard':
      await loadDashboardData()
      break
    case 'documents':
      await refreshDocuments()
      break
    case 'sync':
      await updateSyncStatus()
      break
    case 'settings':
      await loadSettings()
      break
  }
}

// Dashboard
async function loadDashboardData() {
  try {
    const stats = await window.electronAPI.database.query(`
      SELECT 
        COUNT(*) as total_documents,
        SUM(CASE WHEN processing_status = 'completed' THEN 1 ELSE 0 END) as processed,
        SUM(CASE WHEN processing_status = 'failed' THEN 1 ELSE 0 END) as failed,
        SUM(CASE WHEN sync_status = 'pending' THEN 1 ELSE 0 END) as pending_sync
      FROM documents
    `)
    
    const statsData = stats[0] || {
      total_documents: 0,
      processed: 0,
      failed: 0,
      pending_sync: 0
    }
    
    updateDashboardStats(statsData)
    
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  }
}

// Documents
async function refreshDocuments() {
  try {
    const documents = await window.electronAPI.database.getDocuments(50)
    renderDocumentsList(documents)
    
  } catch (error) {
    console.error('Failed to refresh documents:', error)
    renderDocumentsList([])
  }
}

// Sync status
async function updateSyncStatus() {
  try {
    const syncStatus = await window.electronAPI.sync.getSyncStatus()
    appState.syncStatus = syncStatus
    updateSyncStatusUI(syncStatus)
    
  } catch (error) {
    console.error('Failed to update sync status:', error)
  }
}

// Settings
async function loadSettings() {
  try {
    const preferences = await window.electronAPI.updater.getPreferences()
    renderSettings(preferences)
    
  } catch (error) {
    console.error('Failed to load settings:', error)
  }
}

// UI Updates
function updateDashboardStats(stats: any) {
  const container = document.getElementById('dashboard-stats')
  if (!container) return
  
  container.innerHTML = `
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-top: 24px;">
      <div style="background: white; padding: 16px; border-radius: 8px; border: 1px solid #e2e8f0;">
        <h3 style="margin: 0 0 8px 0; font-size: 14px; color: #64748b;">Total Documents</h3>
        <p style="margin: 0; font-size: 24px; font-weight: 600; color: #1e293b;">${stats.total_documents || 0}</p>
      </div>
      <div style="background: white; padding: 16px; border-radius: 8px; border: 1px solid #e2e8f0;">
        <h3 style="margin: 0 0 8px 0; font-size: 14px; color: #64748b;">Processed</h3>
        <p style="margin: 0; font-size: 24px; font-weight: 600; color: #10b981;">${stats.processed || 0}</p>
      </div>
      <div style="background: white; padding: 16px; border-radius: 8px; border: 1px solid #e2e8f0;">
        <h3 style="margin: 0 0 8px 0; font-size: 14px; color: #64748b;">Failed</h3>
        <p style="margin: 0; font-size: 24px; font-weight: 600; color: #ef4444;">${stats.failed || 0}</p>
      </div>
      <div style="background: white; padding: 16px; border-radius: 8px; border: 1px solid #e2e8f0;">
        <h3 style="margin: 0 0 8px 0; font-size: 14px; color: #64748b;">Pending Sync</h3>
        <p style="margin: 0; font-size: 24px; font-weight: 600; color: #f59e0b;">${stats.pending_sync || 0}</p>
      </div>
    </div>
  `
}

function renderDocumentsList(documents: any[]) {
  const container = document.getElementById('documents-list')
  if (!container) return
  
  if (documents.length === 0) {
    container.innerHTML = '<p>No documents found.</p>'
    return
  }
  
  const documentHTML = documents.map(doc => `
    <div style="background: white; padding: 16px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 12px;">
      <div style="display: flex; justify-content: between; align-items: center;">
        <div>
          <h4 style="margin: 0 0 8px 0; color: #1e293b;">${doc.filename}</h4>
          <p style="margin: 0; font-size: 12px; color: #64748b;">
            ${doc.file_type.toUpperCase()} • ${formatFileSize(doc.file_size)} • 
            ${new Date(doc.created_at).toLocaleDateString()}
          </p>
        </div>
        <div style="text-align: right;">
          <span style="padding: 4px 8px; border-radius: 4px; font-size: 12px; 
                 background: ${getStatusColor(doc.processing_status)}; color: white;">
            ${doc.processing_status}
          </span>
          ${doc.sync_status !== 'synced' ? `<br><small style="color: #f59e0b;">Sync pending</small>` : ''}
        </div>
      </div>
      ${doc.extracted_text ? `<p style="margin: 8px 0 0 0; font-size: 14px; color: #64748b;">${doc.extracted_text.substring(0, 100)}...</p>` : ''}
    </div>
  `).join('')
  
  container.innerHTML = documentHTML
}

function renderSettings(preferences: any) {
  const container = document.getElementById('settings-content')
  if (!container) return
  
  container.innerHTML = `
    <div style="background: white; padding: 24px; border-radius: 8px; border: 1px solid #e2e8f0;">
      <h3 style="margin: 0 0 16px 0;">Update Settings</h3>
      <div style="display: flex; flex-direction: column; gap: 12px;">
        <label style="display: flex; align-items: center;">
          <input type="checkbox" ${preferences.enabled ? 'checked' : ''} 
                 onchange="updateSetting('enabled', this.checked)">
          <span style="margin-left: 8px;">Enable automatic updates</span>
        </label>
        <label style="display: flex; align-items: center;">
          <input type="checkbox" ${preferences.autoDownload ? 'checked' : ''} 
                 onchange="updateSetting('autoDownload', this.checked)">
          <span style="margin-left: 8px;">Automatically download updates</span>
        </label>
        <label style="display: flex; align-items: center;">
          <input type="checkbox" ${preferences.autoInstall ? 'checked' : ''} 
                 onchange="updateSetting('autoInstall', this.checked)">
          <span style="margin-left: 8px;">Automatically install updates</span>
        </label>
      </div>
      
      <div style="margin-top: 24px;">
        <button onclick="checkForUpdates()" style="background: #3b82f6; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer;">
          Check for Updates
        </button>
      </div>
    </div>
  `
}

function updateSyncStatusUI(status: any) {
  const statusElement = document.getElementById('sync-status-text')
  const statusElement2 = document.getElementById('sync-status')
  
  if (statusElement) {
    if (status.syncInProgress) {
      statusElement.textContent = 'Syncing...'
    } else if (status.hasPendingUploads) {
      statusElement.textContent = 'Pending upload'
    } else {
      statusElement.textContent = 'Synced'
    }
  }
  
  if (statusElement2) {
    statusElement2.innerHTML = `
      <div style="background: white; padding: 16px; border-radius: 8px; border: 1px solid #e2e8f0;">
        <h4>Sync Status</h4>
        <p>Connection: ${status.isOnline ? 'Online' : 'Offline'}</p>
        <p>Pending uploads: ${status.pendingUploads || 0}</p>
        <p>Last sync: ${status.lastSync ? new Date(status.lastSync).toLocaleString() : 'Never'}</p>
        <button onclick="syncNow()" style="background: #3b82f6; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer;">
          Sync Now
        </button>
      </div>
    `
  }
}

function updateConnectionStatus(isOnline?: boolean) {
  const status = document.getElementById('connection-status')
  const text = document.getElementById('connection-text')
  
  if (status && text) {
    if (isOnline !== undefined) {
      appState.isOnline = isOnline
    }
    
    status.className = `status-dot ${appState.isOnline ? 'online' : 'offline'}`
    text.textContent = appState.isOnline ? 'Online' : 'Offline'
  }
}

async function updateDocumentCount() {
  try {
    const result = await window.electronAPI.database.query('SELECT COUNT(*) as count FROM documents')
    appState.documentCount = result[0]?.count || 0
    
    const countElement = document.getElementById('document-count')
    if (countElement) {
      countElement.textContent = `${appState.documentCount} document${appState.documentCount !== 1 ? 's' : ''}`
    }
    
  } catch (error) {
    console.error('Failed to update document count:', error)
  }
}

function updateUI() {
  updateConnectionStatus()
  updateSyncStatusUI(appState.syncStatus || {})
}

// Utility functions
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'completed': return '#10b981'
    case 'processing': return '#f59e0b'
    case 'failed': return '#ef4444'
    default: return '#6b7280'
  }
}

function showNotification(message: string, type: string = 'info') {
  window.electronAPI.notification.show({
    title: type === 'error' ? 'Error' : type === 'success' ? 'Success' : 'Information',
    body: message,
    urgency: type === 'error' ? 'critical' : 'normal'
  })
}

function showErrorScreen(message: string) {
  const loading = document.getElementById('loading-screen')
  const error = document.getElementById('error-screen')
  const errorMessage = document.getElementById('error-message')
  
  if (loading) loading.style.display = 'none'
  if (error) error.style.display = 'flex'
  if (errorMessage) errorMessage.textContent = message
}

function showApp() {
  const loading = document.getElementById('loading-screen')
  const app = document.getElementById('app')
  
  if (loading) loading.style.display = 'none'
  if (app) app.style.display = 'block'
}

// Global functions for HTML onclick handlers
(window as any).updateSetting = async (key: string, value: any) => {
  try {
    const preferences = await window.electronAPI.updater.getPreferences()
    preferences[key] = value
    await window.electronAPI.updater.setPreferences(preferences)
    showNotification('Settings updated', 'success')
  } catch (error) {
    showNotification('Failed to update settings', 'error')
  }
}

(window as any).checkForUpdates = async () => {
  try {
    await window.electronAPI.updater.check()
    showNotification('Checking for updates...', 'info')
  } catch (error) {
    showNotification('Failed to check for updates', 'error')
  }
}

(window as any).syncNow = async () => {
  try {
    if (appState.syncStatus?.hasPendingUploads) {
      await window.electronAPI.sync.uploadDocuments([])
    }
    await window.electronAPI.sync.downloadDocuments()
    showNotification('Sync completed', 'success')
  } catch (error) {
    showNotification('Sync failed', 'error')
  }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeApp)

// Development helpers
if (typeof window.devAPI !== 'undefined') {
  (window as any).reloadApp = () => window.devAPI.reload()
  (window as any).toggleDevTools = () => window.devAPI.toggleDevTools()
}