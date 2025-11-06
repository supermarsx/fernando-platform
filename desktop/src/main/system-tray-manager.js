import { Tray, Menu, shell, dialog } from 'electron'
import path from 'path'
import fs from 'fs-extra'
import log from 'electron-log'

class SystemTrayManager {
  private tray: Tray | null = null
  private iconPath: string
  private iconStates: Map<string, string> = new Map()

  constructor() {
    this.iconPath = this.getIconPath()
    this.setupIconStates()
  }

  private setupIconStates(): void {
    this.iconStates.set('normal', this.getIconPath('tray'))
    this.iconStates.set('processing', this.getIconPath('tray-processing'))
    this.iconStates.set('sync', this.getIconPath('tray-sync'))
    this.iconStates.set('error', this.getIconPath('tray-error'))
  }

  private getIconPath(iconName: string = 'tray'): string {
    try {
      const iconFile = `${iconName}.png`
      const possiblePaths = [
        path.join(process.resourcesPath, 'icons', iconFile),
        path.join(__dirname, '../../resources/icons', iconFile),
        path.join(process.cwd(), 'resources/icons', iconFile),
        // Fallback to default icon
        path.join(process.resourcesPath, 'icon.png')
      ]

      for (const iconPath of possiblePaths) {
        if (fs.existsSync(iconPath)) {
          return iconPath
        }
      }

      // If no icon found, return empty string (Electron will use default)
      return ''
    } catch (error) {
      log.warn('Could not find icon:', error)
      return ''
    }
  }

  async createTray(mainWindow: any, options: any): Promise<Tray> {
    try {
      // Create tray with icon
      this.tray = new Tray(this.iconPath)

      // Set tooltip
      this.tray.setToolTip('Fernando')

      // Set up context menu
      await this.setupContextMenu(mainWindow, options)

      // Set up event handlers
      this.setupTrayEventHandlers(mainWindow, options)

      log.info('System tray initialized successfully')
      return this.tray

    } catch (error) {
      log.error('Failed to create system tray:', error)
      throw error
    }
  }

  private async setupContextMenu(mainWindow: any, options: any): Promise<void> {
    const menu = Menu.buildFromTemplate([
      {
        label: 'Show Application',
        click: () => {
          if (options.onShow) {
            options.onShow()
          } else {
            this.showMainWindow(mainWindow)
          }
        }
      },
      {
        label: 'Process Files',
        click: async () => {
          await this.handleProcessFiles(mainWindow, options)
        }
      },
      { type: 'separator' },
      {
        label: 'Sync Status',
        submenu: [
          {
            label: 'Upload Pending Changes',
            click: async () => {
              await this.handleSync(mainWindow, 'upload')
            }
          },
          {
            label: 'Download Updates',
            click: async () => {
              await this.handleSync(mainWindow, 'download')
            }
          },
          {
            label: 'View Sync Status',
            click: () => {
              this.showSyncStatus(mainWindow)
            }
          }
        ]
      },
      {
        label: 'Recent Documents',
        submenu: await this.buildRecentDocumentsMenu()
      },
      { type: 'separator' },
      {
        label: 'Preferences',
        submenu: [
          {
            label: 'Settings',
            click: () => {
              this.showSettings(mainWindow)
            }
          },
          {
            label: 'Data Export',
            click: async () => {
              await this.handleDataExport(mainWindow)
            }
          },
          {
            label: 'Data Import',
            click: async () => {
              await this.handleDataImport(mainWindow)
            }
          }
        ]
      },
      { type: 'separator' },
      {
        label: 'Help',
        submenu: [
          {
            label: 'Documentation',
            click: () => {
              shell.openExternal('https://docs.fernando.com')
            }
          },
          {
            label: 'Support',
            click: () => {
              shell.openExternal('https://support.fernando.com')
            }
          },
          { type: 'separator' },
          {
            label: 'About',
            click: () => {
              this.showAbout(mainWindow)
            }
          }
        ]
      },
      { type: 'separator' },
      {
        label: 'Hide',
        click: () => {
          if (options.onHide) {
            options.onHide()
          } else {
            mainWindow.hide()
          }
        }
      },
      {
        label: 'Quit',
        click: () => {
          const { app } = require('electron')
          app.quit()
        }
      }
    ])

    this.tray.setContextMenu(menu)
  }

  private setupTrayEventHandlers(mainWindow: any, options: any): void {
    // Single click to show/hide
    this.tray.on('click', () => {
      if (mainWindow.isVisible()) {
        mainWindow.hide()
      } else {
        this.showMainWindow(mainWindow)
      }
    })

    // Double click to show
    this.tray.on('double-click', () => {
      this.showMainWindow(mainWindow)
    })

    // Right click shows context menu (default behavior)
    this.tray.on('right-click', () => {
      this.tray.popUpContextMenu()
    })

    // Drag and drop events
    this.tray.on('drop-files', async (event: any, files: string[]) => {
      if (options.onProcessFiles) {
        await options.onProcessFiles(files)
      }
    })

    // Balloon events (Windows)
    this.tray.on('balloon-show', () => {
      log.debug('Tray balloon shown')
    })

    this.tray.on('balloon-click', () => {
      this.showMainWindow(mainWindow)
    })

    this.tray.on('balloon-closed', () => {
      log.debug('Tray balloon closed')
    })
  }

  private showMainWindow(mainWindow: any): void {
    if (mainWindow.isMinimized()) {
      mainWindow.restore()
    }
    mainWindow.show()
    mainWindow.focus()
  }

  private async handleProcessFiles(mainWindow: any, options: any): Promise<void> {
    try {
      const { dialog } = require('electron')
      const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openFile', 'multiSelections'],
        filters: [
          { name: 'Documents', extensions: ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'doc', 'docx'] },
          { name: 'PDF Files', extensions: ['pdf'] },
          { name: 'Images', extensions: ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff'] }
        ]
      })

      if (!result.canceled && result.filePaths.length > 0) {
        if (options.onProcessFiles) {
          await options.onProcessFiles(result.filePaths)
        }
      }
    } catch (error) {
      log.error('Failed to process files:', error)
    }
  }

  private async handleSync(mainWindow: any, action: string): Promise<void> {
    try {
      const { ipcMain } = require('electron')
      
      if (action === 'upload') {
        await ipcMain.emit('sync:upload')
      } else if (action === 'download') {
        await ipcMain.emit('sync:download')
      }
    } catch (error) {
      log.error('Sync operation failed:', error)
    }
  }

  private showSyncStatus(mainWindow: any): void {
    // This would typically open a sync status dialog
    log.info('Showing sync status')
  }

  private async buildRecentDocumentsMenu(): Promise<any[]> {
    try {
      const { ipcMain } = require('electron')
      const documents = await ipcMain.emit('database:query', 'SELECT * FROM documents ORDER BY created_at DESC LIMIT 10')
      
      if (documents.length === 0) {
        return [{
          label: 'No recent documents',
          enabled: false
        }]
      }

      return documents.map((doc: any) => ({
        label: doc.filename,
        click: () => {
          this.openDocument(doc)
        }
      }))
    } catch (error) {
      log.error('Failed to build recent documents menu:', error)
      return [{
        label: 'Error loading documents',
        enabled: false
      }]
    }
  }

  private openDocument(document: any): void {
    try {
      if (document.original_path && fs.existsSync(document.original_path)) {
        const { shell } = require('electron')
        shell.openItem(document.original_path)
      }
    } catch (error) {
      log.error('Failed to open document:', error)
    }
  }

  private showSettings(mainWindow: any): void {
    // This would typically open a settings dialog or navigate to settings page
    log.info('Showing settings')
  }

  private async handleDataExport(mainWindow: any): Promise<void> {
    try {
      const { dialog } = require('electron')
      const result = await dialog.showSaveDialog(mainWindow, {
        defaultPath: `accounting-data-${new Date().toISOString().split('T')[0]}.json`,
        filters: [
          { name: 'JSON Files', extensions: ['json'] }
        ]
      })

      if (!result.canceled) {
        const { ipcMain } = require('electron')
        const data = await ipcMain.emit('sync:export')
        await fs.writeJson(result.filePath, data, { spaces: 2 })
        
        const { Notification } = require('electron')
        new Notification({
          title: 'Data Export',
          body: 'Data exported successfully'
        }).show()
      }
    } catch (error) {
      log.error('Data export failed:', error)
    }
  }

  private async handleDataImport(mainWindow: any): Promise<void> {
    try {
      const { dialog } = require('electron')
      const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openFile'],
        filters: [
          { name: 'JSON Files', extensions: ['json'] }
        ]
      })

      if (!result.canceled) {
        const data = await fs.readJson(result.filePaths[0])
        const { ipcMain } = require('electron')
        await ipcMain.emit('sync:import', data)
        
        const { Notification } = require('electron')
        new Notification({
          title: 'Data Import',
          body: 'Data imported successfully'
        }).show()
      }
    } catch (error) {
      log.error('Data import failed:', error)
    }
  }

  private showAbout(mainWindow: any): void {
    // This would typically show an about dialog
    dialog.showMessageBox(mainWindow, {
      type: 'info',
      title: 'About',
      message: 'Fernando',
      detail: 'Version 1.0.0\n\nA desktop client for Fernando document processing and automation.',
      buttons: ['OK']
    })
  }

  // Update tray icon state
  updateIcon(state: string): void {
    if (!this.tray) {
      return
    }

    const iconPath = this.iconStates.get(state)
    if (iconPath) {
      this.tray.setImage(iconPath)
      log.debug(`Tray icon updated to: ${state}`)
    }
  }

  // Update tray tooltip
  updateTooltip(tooltip: string): void {
    if (this.tray) {
      this.tray.setToolTip(tooltip)
    }
  }

  // Show balloon notification (Windows)
  showBalloon(title: string, content: string, icon: string = 'info'): void {
    if (!this.tray) {
      return
    }

    this.tray.displayBalloon({
      icon: this.getIconPath(icon),
      title,
      content
    })
  }

  // Destroy tray
  destroy(): void {
    if (this.tray) {
      this.tray.destroy()
      this.tray = null
      log.info('System tray destroyed')
    }
  }
}

export default SystemTrayManager