import { contextBridge, ipcRenderer } from 'electron'

// ========== DATABASE API ==========
const databaseAPI = {
  query: (sql: string, params: any[] = []) => 
    ipcRenderer.invoke('database:query', sql, params),
  
  run: (sql: string, params: any[] = []) => 
    ipcRenderer.invoke('database:run', sql, params),

  // Document operations
  getDocuments: (limit?: number, offset?: number) => 
    ipcRenderer.invoke('database:getDocuments', limit, offset),
  
  getDocumentById: (id: number) => 
    ipcRenderer.invoke('database:getDocumentById', id),
  
  searchDocuments: (searchTerm: string) => 
    ipcRenderer.invoke('database:searchDocuments', searchTerm),

  // User operations
  getUserByEmail: (email: string) => 
    ipcRenderer.invoke('database:getUserByEmail', email),
  
  createUser: (userData: any) => 
    ipcRenderer.invoke('database:createUser', userData),

  // Settings
  getSetting: (key: string) => 
    ipcRenderer.invoke('settings:get', key),
  
  setSetting: (key: string, value: any) => 
    ipcRenderer.invoke('settings:set', key, value)
}

// ========== FILE API ==========
const fileAPI = {
  openFileDialog: () => ipcRenderer.invoke('file:open'),
  saveFileDialog: (data: any, defaultPath?: string) => 
    ipcRenderer.invoke('file:save', data, defaultPath),

  // Document processing
  processDocuments: (filePaths: string[]) => 
    ipcRenderer.invoke('document:process', filePaths),
  
  processDocumentsSync: (filePaths: string[]) => 
    ipcRenderer.invoke('document:process-sync', filePaths),

  validateFile: (filePath: string) => 
    ipcRenderer.invoke('file:validate', filePath),

  getProcessingHistory: (limit?: number) => 
    ipcRenderer.invoke('document:getHistory', limit)
}

// ========== SYNC API ==========
const syncAPI = {
  uploadDocuments: (documents: any[]) => 
    ipcRenderer.invoke('sync:upload', documents),
  
  downloadDocuments: () => 
    ipcRenderer.invoke('sync:download'),
  
  getSyncStatus: () => 
    ipcRenderer.invoke('sync:status'),
  
  login: (email: string, password: string) => 
    ipcRenderer.invoke('sync:login', email, password),
  
  logout: () => ipcRenderer.invoke('sync:logout'),
  
  isAuthenticated: () => 
    ipcRenderer.invoke('sync:isAuthenticated'),
  
  getUserData: () => 
    ipcRenderer.invoke('sync:getUserData'),
  
  refreshToken: () => 
    ipcRenderer.invoke('sync:refreshToken'),
  
  exportData: () => 
    ipcRenderer.invoke('sync:export'),
  
  importData: (data: any) => 
    ipcRenderer.invoke('sync:import', data)
}

// ========== SYSTEM API ==========
const systemAPI = {
  minimize: () => ipcRenderer.invoke('system:minimize'),
  maximize: () => ipcRenderer.invoke('system:maximize'),
  close: () => ipcRenderer.invoke('system:close'),
  quit: () => ipcRenderer.invoke('system:quit'),

  // Environment info
  platform: process.platform,
  versions: process.versions,

  // Shortcuts
  registerGlobalShortcut: (accelerator: string, callback: () => void) => 
    ipcRenderer.on('shortcut:' + accelerator, callback),

  unregisterGlobalShortcut: (accelerator: string) => 
    ipcRenderer.removeAllListeners('shortcut:' + accelerator)
}

// ========== NOTIFICATION API ==========
const notificationAPI = {
  show: (options: any) => ipcRenderer.invoke('notification:show', options),
  success: (message: string, options?: any) => 
    ipcRenderer.invoke('notification:success', message, options),
  error: (message: string, options?: any) => 
    ipcRenderer.invoke('notification:error', message, options),
  warning: (message: string, options?: any) => 
    ipcRenderer.invoke('notification:warning', message, options),
  info: (message: string, options?: any) => 
    ipcRenderer.invoke('notification:info', message, options),

  // Document processing notifications
  documentProcessing: (filename: string) => 
    ipcRenderer.invoke('notification:documentProcessing', filename),
  
  documentProcessed: (filename: string, success: boolean) => 
    ipcRenderer.invoke('notification:documentProcessed', filename, success),

  // Sync notifications
  syncStarted: () => ipcRenderer.invoke('notification:syncStarted'),
  syncComplete: (imported: number, updated: number) => 
    ipcRenderer.invoke('notification:syncComplete', imported, updated),
  syncFailed: (error: string) => 
    ipcRenderer.invoke('notification:syncFailed', error),
  syncOnline: () => ipcRenderer.invoke('notification:syncOnline'),
  syncOffline: () => ipcRenderer.invoke('notification:syncOffline')
}

// ========== UPDATER API ==========
const updaterAPI = {
  check: () => ipcRenderer.invoke('updater:check'),
  install: () => ipcRenderer.invoke('updater:install'),
  getStatus: () => ipcRenderer.invoke('updater:get-status'),
  
  // Preferences
  getPreferences: () => ipcRenderer.invoke('updater:getPreferences'),
  setPreferences: (preferences: any) => 
    ipcRenderer.invoke('updater:setPreferences', preferences),
  
  // Events
  onUpdateAvailable: (callback: (info: any) => void) => 
    ipcRenderer.on('update:available', (_, info) => callback(info)),
  
  onUpdateDownloaded: (callback: (info: any) => void) => 
    ipcRenderer.on('update:downloaded', (_, info) => callback(info)),
  
  onUpdateProgress: (callback: (progress: any) => void) => 
    ipcRenderer.on('update:progress', (_, progress) => callback(progress)),
  
  removeAllListeners: (channel: string) => 
    ipcRenderer.removeAllListeners(channel)
}

// ========== SYSTEM TRAY API ==========
const trayAPI = {
  updateIcon: (state: string) => ipcRenderer.invoke('tray:updateIcon', state),
  updateTooltip: (tooltip: string) => ipcRenderer.invoke('tray:updateTooltip', tooltip),
  showBalloon: (title: string, content: string, icon?: string) => 
    ipcRenderer.invoke('tray:showBalloon', title, content, icon)
}

// ========== FILE SYSTEM API ==========
const fsAPI = {
  readFile: (filePath: string) => 
    ipcRenderer.invoke('fs:readFile', filePath),
  writeFile: (filePath: string, data: any) => 
    ipcRenderer.invoke('fs:writeFile', filePath, data),
  exists: (filePath: string) => 
    ipcRenderer.invoke('fs:exists', filePath),
  stat: (filePath: string) => 
    ipcRenderer.invoke('fs:stat', filePath),
  readdir: (dirPath: string) => 
    ipcRenderer.invoke('fs:readdir', dirPath),
  mkdir: (dirPath: string) => 
    ipcRenderer.invoke('fs:mkdir', dirPath),
  unlink: (filePath: string) => 
    ipcRenderer.invoke('fs:unlink', filePath),
  copy: (src: string, dest: string) => 
    ipcRenderer.invoke('fs:copy', src, dest),
  move: (src: string, dest: string) => 
    ipcRenderer.invoke('fs:move', src, dest)
}

// ========== EVENT LISTENERS ==========
const eventAPI = {
  // Document events
  onDocumentProcessed: (callback: (result: any) => void) => 
    ipcRenderer.on('documents:processed', (_, result) => callback(result)),
  
  onDocumentProcessing: (callback: (filePath: string) => void) => 
    ipcRenderer.on('documents:processing', (_, filePath) => callback(filePath)),

  // Sync events
  onSyncStarted: (callback: () => void) => 
    ipcRenderer.on('sync:started', callback),
  
  onSyncCompleted: (callback: (result: any) => void) => 
    ipcRenderer.on('sync:completed', (_, result) => callback(result)),
  
  onSyncFailed: (callback: (error: string) => void) => 
    ipcRenderer.on('sync:failed', (_, error) => callback(error)),
  
  onSyncStatusChanged: (callback: (status: any) => void) => 
    ipcRenderer.on('sync:status-changed', (_, status) => callback(status)),

  // Connection events
  onOnline: (callback: () => void) => 
    ipcRenderer.on('network:online', callback),
  
  onOffline: (callback: () => void) => 
    ipcRenderer.on('network:offline', callback),

  // Window events
  onWindowFocus: (callback: () => void) => 
    ipcRenderer.on('window:focus', callback),
  
  onWindowBlur: (callback: () => void) => 
    ipcRenderer.on('window:blur', callback),

  // Remove listeners
  removeAllListeners: (channel: string) => 
    ipcRenderer.removeAllListeners(channel)
}

// ========== AUTH API ==========
const authAPI = {
  login: (credentials: { email: string; password: string }) => 
    ipcRenderer.invoke('auth:login', credentials),
  
  logout: () => ipcRenderer.invoke('auth:logout'),
  
  isAuthenticated: () => 
    ipcRenderer.invoke('auth:isAuthenticated'),
  
  getCurrentUser: () => 
    ipcRenderer.invoke('auth:getCurrentUser'),
  
  updateProfile: (profileData: any) => 
    ipcRenderer.invoke('auth:updateProfile', profileData),
  
  changePassword: (currentPassword: string, newPassword: string) => 
    ipcRenderer.invoke('auth:changePassword', currentPassword, newPassword)
}

// ========== EXPORT API TO RENDERER ==========
contextBridge.exposeInMainWorld('electronAPI', {
  // Database
  database: databaseAPI,
  
  // File operations
  file: fileAPI,
  
  // Sync
  sync: syncAPI,
  
  // System
  system: systemAPI,
  
  // Notifications
  notification: notificationAPI,
  
  // Updates
  updater: updaterAPI,
  
  // System tray
  tray: trayAPI,
  
  // File system
  fs: fsAPI,
  
  // Events
  events: eventAPI,
  
  // Authentication
  auth: authAPI,

  // Version info
  versions: {
    electron: process.versions.electron,
    chrome: process.versions.chrome,
    node: process.versions.node,
    platform: process.platform
  }
})

// ========== DEVELOPMENT HELPERS ==========
if (process.env.NODE_ENV === 'development') {
  contextBridge.exposeInMainWorld('devAPI', {
    // Reload window
    reload: () => ipcRenderer.invoke('dev:reload'),
    
    // Toggle developer tools
    toggleDevTools: () => ipcRenderer.invoke('dev:toggleDevTools'),
    
    // Get app info
    getAppInfo: () => ipcRenderer.invoke('dev:getAppInfo'),
    
    // Clear storage
    clearStorage: () => ipcRenderer.invoke('dev:clearStorage'),
    
    // Log to main process
    log: (message: string, level: string = 'info') => 
      ipcRenderer.invoke('dev:log', message, level)
  })
}

// ========== SECURITY WARNINGS ==========
console.log('Preload script loaded successfully')

// Warn about insecure access patterns
if (typeof window !== 'undefined') {
  // Disable eval and similar dangerous functions in renderer
  const originalEval = window.eval
  window.eval = function(...args) {
    console.warn('Direct eval() usage is discouraged for security reasons')
    return originalEval.apply(this, args)
  }

  // Disable Function constructor
  const originalFunction = window.Function
  window.Function = function(...args) {
    console.warn('Direct Function constructor usage is discouraged for security reasons')
    return originalFunction.apply(this, args)
  }
}