import { app, shell, BrowserWindow, Tray, Menu, Notification, dialog, ipcMain, globalShortcut } from 'electron'
import { join } from 'path'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import DatabaseManager from './database-manager'
import FileProcessor from './file-processor'
import SyncManager from './sync-manager'
import AutoUpdater from './auto-updater'
import NotificationManager from './notification-manager'
import SystemTrayManager from './system-tray-manager'
import log from 'electron-log'
import { autoUpdater } from 'electron-updater'
import Store from 'electron-store'
import windowState from 'electron-window-state'

// Configure logging
log.transports.file.level = 'info'
log.transports.console.level = 'debug'

class AppManager {
  private mainWindow: BrowserWindow | null = null
  private tray: Tray | null = null
  private database: DatabaseManager
  private fileProcessor: FileProcessor
  private syncManager: SyncManager
  private autoUpdater: AutoUpdater
  private notificationManager: NotificationManager
  private systemTrayManager: SystemTrayManager
  private store: Store

  constructor() {
    this.store = new Store()
    this.database = new DatabaseManager()
    this.fileProcessor = new FileProcessor(this.database)
    this.syncManager = new SyncManager()
    this.notificationManager = new NotificationManager()
    this.systemTrayManager = new SystemTrayManager()
  }

  async initialize() {
    try {
      // Initialize database
      await this.database.initialize()
      
      // Initialize managers
      await this.syncManager.initialize(this.database)
      this.autoUpdater = new AutoUpdater()
      
      // Setup event handlers
      this.setupAppEventHandlers()
      this.setupIpcHandlers()
      this.setupGlobalShortcuts()
      
      log.info('Application initialized successfully')
    } catch (error) {
      log.error('Failed to initialize application:', error)
      throw error
    }
  }

  private setupAppEventHandlers() {
    // Single instance lock
    const gotTheLock = app.requestSingleInstanceLock()
    
    if (!gotTheLock) {
      app.quit()
    } else {
      app.on('second-instance', () => {
        // Focus on the main window when another instance is launched
        if (this.mainWindow) {
          if (this.mainWindow.isMinimized()) this.mainWindow.restore()
          this.mainWindow.focus()
        }
      })
    }

    // App ready
    app.whenReady().then(async () => {
      await this.initialize()
      await this.createMainWindow()
      await this.setupSystemTray()
      
      // Hide dock icon on macOS
      if (process.platform === 'darwin') {
        app.dock.hide()
      }

      autoUpdater.checkForUpdatesAndNotify()
    })

    // Window closed
    app.on('window-all-closed', () => {
      if (process.platform !== 'darwin') {
        app.quit()
      }
    })

    app.on('activate', async () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        await this.createMainWindow()
      }
    })

    // Security: Prevent new window creation
    app.on('web-contents-created', (event, contents) => {
      contents.on('new-window', (navigationEvent, navigationUrl) => {
        event.preventDefault()
        shell.openExternal(navigationUrl)
      })
    })
  }

  private async createMainWindow() {
    // Load window state from store
    let windowStateManager = windowState({
      defaultWidth: 1200,
      defaultHeight: 800
    })

    this.mainWindow = new BrowserWindow({
      x: windowStateManager.x,
      y: windowStateManager.y,
      width: windowStateManager.width,
      height: windowStateManager.height,
      minWidth: 800,
      minHeight: 600,
      show: false,
      autoHideMenuBar: !is.dev,
      icon: join(__dirname, '../../resources/icon.png'),
      webPreferences: {
        preload: join(__dirname, '../preload/preload.js'),
        nodeIntegration: false,
        contextIsolation: true,
        sandbox: true,
        webSecurity: true,
        experimentalFeatures: false
      }
    })

    // Manage window state
    windowStateManager.manage(this.mainWindow)

    // Show window when ready
    this.mainWindow.once('ready-to-show', () => {
      this.mainWindow?.show()
      
      if (is.dev) {
        this.mainWindow?.webContents.openDevTools()
      }
    })

    // Handle window closed
    this.mainWindow.on('closed', () => {
      this.mainWindow = null
    })

    // Handle external links
    this.mainWindow.webContents.setWindowOpenHandler(({ url }) => {
      shell.openExternal(url)
      return { action: 'deny' }
    })

    // Load app
    if (is.dev) {
      await this.mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL']!)
    } else {
      await this.mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
    }

    // Handle renderer crashes
    this.mainWindow.webContents.on('render-process-gone', (event, details) => {
      log.error('Renderer process crashed:', details)
      
      const choice = dialog.showMessageBoxSync(this.mainWindow!, {
        type: 'error',
        title: 'Application Error',
        message: 'The application has encountered an unexpected error.',
        detail: details.reason,
        buttons: ['Restart', 'Close']
      })
      
      if (choice === 0) {
        app.relaunch()
        app.exit(0)
      }
    })
  }

  private async setupSystemTray() {
    this.tray = await this.systemTrayManager.createTray(this.mainWindow!, {
      onShow: () => this.mainWindow?.show(),
      onHide: () => this.mainWindow?.hide(),
      onProcessFiles: async (files: string[]) => {
        await this.handleDroppedFiles(files)
      }
    })
  }

  private setupIpcHandlers() {
    // Database operations
    ipcMain.handle('database:query', async (event, sql: string, params: any[] = []) => {
      return await this.database.query(sql, params)
    })

    ipcMain.handle('database:run', async (event, sql: string, params: any[] = []) => {
      return await this.database.run(sql, params)
    })

    // File operations
    ipcMain.handle('file:open', async () => {
      const result = await dialog.showOpenDialog(this.mainWindow!, {
        properties: ['openFile', 'multiSelections'],
        filters: [
          { name: 'Documents', extensions: ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'doc', 'docx'] }
        ]
      })
      return result.filePaths
    })

    ipcMain.handle('file:save', async (event, data: any, defaultPath?: string) => {
      const result = await dialog.showSaveDialog(this.mainWindow!, {
        defaultPath: defaultPath || 'processed-document.json',
        filters: [
          { name: 'JSON Files', extensions: ['json'] },
          { name: 'Text Files', extensions: ['txt'] }
        ]
      })
      return result.filePath
    })

    // Document processing
    ipcMain.handle('document:process', async (event, filePaths: string[]) => {
      return await this.fileProcessor.processDocuments(filePaths)
    })

    ipcMain.handle('document:process-sync', async (event, filePaths: string[]) => {
      return await this.fileProcessor.processDocumentsSync(filePaths)
    })

    // Sync operations
    ipcMain.handle('sync:upload', async (event, documents: any[]) => {
      return await this.syncManager.uploadDocuments(documents)
    })

    ipcMain.handle('sync:download', async () => {
      return await this.syncManager.downloadDocuments()
    })

    ipcMain.handle('sync:status', async () => {
      return await this.syncManager.getSyncStatus()
    })

    // Settings
    ipcMain.handle('settings:get', async (event, key: string) => {
      return this.store.get(key)
    })

    ipcMain.handle('settings:set', async (event, key: string, value: any) => {
      this.store.set(key, value)
      return true
    })

    // Notifications
    ipcMain.handle('notification:show', async (event, options: any) => {
      return this.notificationManager.show(options)
    })

    // System operations
    ipcMain.handle('system:minimize', () => {
      this.mainWindow?.minimize()
    })

    ipcMain.handle('system:maximize', () => {
      if (this.mainWindow?.isMaximized()) {
        this.mainWindow.unmaximize()
      } else {
        this.mainWindow?.maximize()
      }
    })

    ipcMain.handle('system:close', () => {
      this.mainWindow?.hide()
    })

    ipcMain.handle('system:quit', () => {
      app.quit()
    })

    // Auto-updater
    ipcMain.handle('updater:check', async () => {
      return await this.autoUpdater.checkForUpdates()
    })

    ipcMain.handle('updater:install', async () => {
      return await this.autoUpdater.installUpdate()
    })

    ipcMain.handle('updater:get-status', async () => {
      return this.autoUpdater.getUpdateStatus()
    })
  }

  private setupGlobalShortcuts() {
    // Global shortcut for showing/hiding app
    globalShortcut.register('CommandOrControl+Shift+A', () => {
      if (this.mainWindow?.isVisible()) {
        this.mainWindow.hide()
      } else {
        this.mainWindow?.show()
        this.mainWindow?.focus()
      }
    })

    // Global shortcut for quick processing
    globalShortcut.register('CommandOrControl+Shift+P', async () => {
      // Open file dialog for quick processing
      const result = await dialog.showOpenDialog(this.mainWindow!, {
        properties: ['openFile', 'multiSelections'],
        filters: [
          { name: 'Documents', extensions: ['pdf', 'jpg', 'jpeg', 'png'] }
        ]
      })
      
      if (!result.canceled && result.filePaths.length > 0) {
        await this.handleDroppedFiles(result.filePaths)
      }
    })
  }

  private async handleDroppedFiles(filePaths: string[]) {
    try {
      this.notificationManager.show({
        title: 'Processing Documents',
        body: `Processing ${filePaths.length} document(s)...`,
        silent: true
      })

      const results = await this.fileProcessor.processDocuments(filePaths)
      
      this.notificationManager.show({
        title: 'Documents Processed',
        body: `Successfully processed ${results.length} document(s)`,
      })

      // Send results to renderer
      this.mainWindow?.webContents.send('documents:processed', results)

    } catch (error) {
      log.error('Error processing dropped files:', error)
      this.notificationManager.show({
        title: 'Processing Error',
        body: 'Failed to process some documents',
        type: 'error'
      })
    }
  }

  public getMainWindow(): BrowserWindow | null {
    return this.mainWindow
  }
}

// Initialize the app
const appManager = new AppManager()

// Initialize when app is ready
app.whenReady().then(() => {
  // Set app user model ID for Windows
  if (process.platform === 'win32') {
    app.setAppUserModelId('com.fernando.desktop')
  }
  
  // Security: Disable web security in development only
  if (is.dev) {
    process.env['ELECTRON_DISABLE_SECURITY_WARNINGS'] = 'true'
  }
})

// Error handling
process.on('uncaughtException', (error) => {
  log.error('Uncaught Exception:', error)
  app.quit()
})

process.on('unhandledRejection', (reason, promise) => {
  log.error('Unhandled Rejection at:', promise, 'reason:', reason)
})

export default appManager