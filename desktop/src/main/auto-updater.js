import { autoUpdater } from 'electron-updater'
import { dialog, shell } from 'electron'
import log from 'electron-log'

class AutoUpdater {
  private updateAvailable = false
  private updateDownloaded = false
  private downloadPromise: Promise<any> | null = null

  constructor() {
    this.setupAutoUpdater()
  }

  private setupAutoUpdater(): void {
    // Configure logging
    autoUpdater.logger = log
    autoUpdater.log = log.info

    // Set update server URL
    if (process.env.NODE_ENV === 'production') {
      autoUpdater.setFeedURL({
        provider: 'github',
        owner: 'your-org',
        repo: 'fernando-desktop'
      })
    } else {
      // Development update server
      autoUpdater.setFeedURL({
        provider: 'github',
        owner: 'your-org',
        repo: 'fernando-desktop',
        private: true
      })
    }

    // Setup event handlers
    this.setupEventHandlers()
  }

  private setupEventHandlers(): void {
    // Check for updates
    autoUpdater.on('checking-for-update', () => {
      log.info('Checking for update...')
    })

    // Update available
    autoUpdater.on('update-available', (info) => {
      log.info('Update available:', info)
      this.updateAvailable = true
      this.showUpdateAvailableDialog(info)
    })

    // Update not available
    autoUpdater.on('update-not-available', (info) => {
      log.info('Update not available:', info)
    })

    // Error occurred
    autoUpdater.on('error', (error) => {
      log.error('Auto updater error:', error)
      this.handleUpdateError(error)
    })

    // Download started
    autoUpdater.on('download-progress', (progressObj) => {
      log.info(`Download progress: ${progressObj.percent.toFixed(2)}%`)
      this.showDownloadProgress(progressObj)
    })

    // Download completed
    autoUpdater.on('update-downloaded', (info) => {
      log.info('Update downloaded:', info)
      this.updateDownloaded = true
      this.showUpdateDownloadedDialog(info)
    })

    // Before quitting for update
    autoUpdater.on('before-quit-for-update', () => {
      log.info('Quitting for update...')
    })
  }

  async checkForUpdates(): Promise<any> {
    try {
      log.info('Manual update check initiated')
      await autoUpdater.checkForUpdatesAndNotify()
      return { success: true }
    } catch (error) {
      log.error('Manual update check failed:', error)
      return { 
        success: false, 
        error: error.message 
      }
    }
  }

  async downloadUpdate(): Promise<any> {
    if (this.downloadPromise) {
      return this.downloadPromise
    }

    this.downloadPromise = this.performDownload()
    return this.downloadPromise
  }

  private async performDownload(): Promise<any> {
    try {
      log.info('Starting update download...')
      await autoUpdater.downloadUpdate()
      
      return { 
        success: true,
        downloaded: true 
      }
    } catch (error) {
      log.error('Update download failed:', error)
      this.downloadPromise = null
      return { 
        success: false, 
        error: error.message 
      }
    }
  }

  async installUpdate(): Promise<any> {
    try {
      if (!this.updateDownloaded) {
        // Download update first if not already downloaded
        const downloadResult = await this.downloadUpdate()
        if (!downloadResult.success) {
          return downloadResult
        }
      }

      log.info('Installing update...')
      
      // Show installation dialog
      const choice = await this.showInstallConfirmation()
      
      if (choice === 0) { // Install Now
        autoUpdater.quitAndInstall()
        return { 
          success: true,
          installing: true 
        }
      } else { // Install on Exit
        return { 
          success: true,
          installing: false,
          message: 'Update will be installed on next application restart' 
        }
      }
    } catch (error) {
      log.error('Update installation failed:', error)
      return { 
        success: false, 
        error: error.message 
      }
    }
  }

  private async showUpdateAvailableDialog(updateInfo: any): Promise<void> {
    const { BrowserWindow } = require('electron')
    const mainWindow = BrowserWindow.getFocusedWindow()

    if (!mainWindow) return

    const choice = await dialog.showMessageBox(mainWindow, {
      type: 'info',
      title: 'Update Available',
      message: `A new version (${updateInfo.version}) is available`,
      detail: `Would you like to download and install the update now?\n\nRelease notes: ${updateInfo.releaseNotes || 'No release notes available'}`,
      buttons: ['Download & Install', 'Remind Me Later', 'Skip This Version'],
      defaultId: 0,
      cancelId: 1
    })

    switch (choice) {
      case 0: // Download & Install
        await this.downloadUpdate()
        break
      case 2: // Skip This Version
        // Store skipped version
        this.skipVersion(updateInfo.version)
        break
      default:
        // Remind Me Later - do nothing
        break
    }
  }

  private async showUpdateDownloadedDialog(updateInfo: any): Promise<void> {
    const { BrowserWindow } = require('electron')
    const mainWindow = BrowserWindow.getFocusedWindow()

    if (!mainWindow) return

    const choice = await dialog.showMessageBox(mainWindow, {
      type: 'info',
      title: 'Update Ready',
      message: `Version ${updateInfo.version} has been downloaded`,
      detail: 'Would you like to install the update now? The application will restart.',
      buttons: ['Install Now', 'Install on Exit', 'View Release Notes'],
      defaultId: 0,
      cancelId: 1
    })

    switch (choice) {
      case 0: // Install Now
        autoUpdater.quitAndInstall()
        break
      case 2: // View Release Notes
        if (updateInfo.releaseNotes) {
          this.showReleaseNotes(updateInfo.releaseNotes)
        } else {
          shell.openExternal('https://github.com/your-org/fernando-desktop/releases')
        }
        break
      default:
        // Install on Exit - do nothing, will install automatically
        break
    }
  }

  private async showDownloadProgress(progressObj: any): Promise<void> {
    const { BrowserWindow, Notification } = require('electron')
    const mainWindow = BrowserWindow.getFocusedWindow()

    if (mainWindow) {
      // Send progress to renderer
      mainWindow.webContents.send('update:progress', {
        percent: progressObj.percent,
        bytesPerSecond: progressObj.bytesPerSecond,
        transferred: progressObj.transferred,
        total: progressObj.total
      })
    } else {
      // Show notification if no window
      new Notification({
        title: 'Downloading Update',
        body: `${progressObj.percent.toFixed(1)}% complete`,
        silent: true
      }).show()
    }
  }

  private async showInstallConfirmation(): Promise<number> {
    const { BrowserWindow } = require('electron')
    const mainWindow = BrowserWindow.getFocusedWindow()

    if (!mainWindow) return 1

    return await dialog.showMessageBox(mainWindow, {
      type: 'question',
      title: 'Install Update',
      message: 'Install update now?',
      detail: 'The application will restart to complete the installation.',
      buttons: ['Install Now', 'Install on Exit'],
      defaultId: 0,
      cancelId: 1
    })
  }

  private showReleaseNotes(releaseNotes: any): void {
    const { BrowserWindow } = require('electron')
    const mainWindow = BrowserWindow.getFocusedWindow()

    if (mainWindow) {
      dialog.showMessageBox(mainWindow, {
        type: 'info',
        title: 'Release Notes',
        message: 'What\'s New',
        detail: typeof releaseNotes === 'string' ? releaseNotes : JSON.stringify(releaseNotes, null, 2),
        buttons: ['OK', 'View on GitHub'],
        defaultId: 0,
        cancelId: 1
      }).then((choice) => {
        if (choice.response === 1) {
          shell.openExternal('https://github.com/your-org/fernando-desktop/releases')
        }
      })
    }
  }

  private handleUpdateError(error: any): void {
    const { BrowserWindow, Notification } = require('electron')
    const mainWindow = BrowserWindow.getFocusedWindow()

    // Show user-friendly error message
    const errorMessage = this.getErrorMessage(error)

    if (mainWindow) {
      dialog.showMessageBox(mainWindow, {
        type: 'error',
        title: 'Update Error',
        message: 'Failed to check for updates',
        detail: errorMessage,
        buttons: ['OK', 'Retry'],
        defaultId: 0,
        cancelId: 1
      }).then((choice) => {
        if (choice.response === 1) {
          this.checkForUpdates()
        }
      })
    } else {
      new Notification({
        title: 'Update Error',
        body: errorMessage
      }).show()
    }
  }

  private getErrorMessage(error: any): string {
    // Common error messages
    if (error.message?.includes('net::ERR_INTERNET_DISCONNECTED')) {
      return 'No internet connection available. Please check your connection and try again.'
    }
    
    if (error.message?.includes('net::ERR_CONNECTION_REFUSED')) {
      return 'Could not connect to update server. Please try again later.'
    }
    
    if (error.message?.includes('signature')) {
      return 'Update package signature is invalid. This may indicate a security issue.'
    }
    
    if (error.message?.includes('sha512')) {
      return 'Update package checksum verification failed. Please try again.'
    }

    return error.message || 'An unknown error occurred while checking for updates.'
  }

  private skipVersion(version: string): void {
    const Store = require('electron-store')
    const store = new Store()
    const skippedVersions = store.get('skippedVersions', [])
    
    if (!skippedVersions.includes(version)) {
      skippedVersions.push(version)
      store.set('skippedVersions', skippedVersions)
    }
  }

  shouldSkipVersion(version: string): boolean {
    const Store = require('electron-store')
    const store = new Store()
    const skippedVersions = store.get('skippedVersions', [])
    
    return skippedVersions.includes(version)
  }

  getUpdateStatus(): any {
    return {
      available: this.updateAvailable,
      downloaded: this.updateDownloaded,
      downloading: this.downloadPromise !== null,
      currentVersion: autoUpdater.currentVersion?.version || '1.0.0',
      latestVersion: autoUpdater.updateInfo?.version || null
    }
  }

  // Manual update configuration
  configureUpdateServer(serverUrl: string, authToken?: string): void {
    autoUpdater.setFeedURL({
      provider: 'generic',
      url: serverUrl,
      channel: 'latest'
    })

    if (authToken) {
      autoUpdater.setAuthToken(authToken)
    }
  }

  // Check if updates are enabled
  areUpdatesEnabled(): boolean {
    const Store = require('electron-store')
    const store = new Store()
    return store.get('updatesEnabled', true)
  }

  // Enable/disable automatic updates
  setUpdatesEnabled(enabled: boolean): void {
    const Store = require('electron-store')
    const store = new Store()
    store.set('updatesEnabled', enabled)

    if (!enabled) {
      log.info('Automatic updates disabled')
    } else {
      log.info('Automatic updates enabled')
    }
  }

  // Get update preferences
  getUpdatePreferences(): any {
    const Store = require('electron-store')
    const store = new Store()
    
    return {
      enabled: this.areUpdatesEnabled(),
      autoDownload: store.get('autoDownload', true),
      autoInstall: store.get('autoInstall', false),
      checkOnStartup: store.get('checkOnStartup', true),
      checkFrequency: store.get('checkFrequency', 'daily')
    }
  }

  // Set update preferences
  setUpdatePreferences(preferences: any): void {
    const Store = require('electron-store')
    const store = new Store()
    
    if (preferences.enabled !== undefined) {
      this.setUpdatesEnabled(preferences.enabled)
    }
    
    if (preferences.autoDownload !== undefined) {
      store.set('autoDownload', preferences.autoDownload)
    }
    
    if (preferences.autoInstall !== undefined) {
      store.set('autoInstall', preferences.autoInstall)
    }
    
    if (preferences.checkOnStartup !== undefined) {
      store.set('checkOnStartup', preferences.checkOnStartup)
    }
    
    if (preferences.checkFrequency !== undefined) {
      store.set('checkFrequency', preferences.checkFrequency)
    }
  }
}

export default AutoUpdater