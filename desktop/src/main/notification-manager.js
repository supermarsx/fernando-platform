import { Notification, app } from 'electron'
import log from 'electron-log'

class NotificationManager {
  private notificationQueue: any[] = []
  private isProcessingQueue = false
  private maxNotifications = 10

  constructor() {
    this.setupNotificationHandlers()
  }

  private setupNotificationHandlers(): void {
    // Handle notification clicks
    app.on('notification-click', (event, notification) => {
      // Focus app window when notification is clicked
      const windows = require('electron').BrowserWindow.getAllWindows()
      if (windows.length > 0) {
        windows[0].show()
        windows[0].focus()
      }
      
      // Log notification interaction
      log.info('Notification clicked:', notification.title)
    })

    // Handle notification close
    app.on('notification-close', (event, notification) => {
      log.info('Notification closed:', notification.title)
    })
  }

  show(options: any): boolean {
    try {
      // Validate notification options
      if (!this.validateNotificationOptions(options)) {
        log.warn('Invalid notification options:', options)
        return false
      }

      // Check if we should queue the notification
      if (this.shouldQueueNotification(options)) {
        this.queueNotification(options)
        return true
      }

      // Show notification immediately
      return this.displayNotification(options)

    } catch (error) {
      log.error('Failed to show notification:', error)
      return false
    }
  }

  private validateNotificationOptions(options: any): boolean {
    const required = ['title', 'body']
    const hasRequired = required.every(field => options[field] && typeof options[field] === 'string')
    
    if (!hasRequired) {
      log.warn('Notification missing required fields:', required)
      return false
    }

    // Validate icon if provided
    if (options.icon && !this.validateIconPath(options.icon)) {
      log.warn('Invalid notification icon path:', options.icon)
      options.icon = undefined
    }

    // Validate urgency level
    const validUrgencies = ['normal', 'critical', 'low']
    if (options.urgency && !validUrgencies.includes(options.urgency)) {
      log.warn('Invalid urgency level:', options.urgency)
      options.urgency = 'normal'
    }

    return true
  }

  private validateIconPath(iconPath: string): boolean {
    const fs = require('fs-extra')
    return fs.existsSync(iconPath)
  }

  private shouldQueueNotification(options: any): boolean {
    // Critical notifications should always be shown immediately
    if (options.urgency === 'critical' || options.silent === true) {
      return false
    }

    // Queue if we have too many notifications
    if (this.notificationQueue.length >= this.maxNotifications) {
      return true
    }

    return false
  }

  private queueNotification(options: any): void {
    this.notificationQueue.push({
      ...options,
      queuedAt: new Date().toISOString()
    })

    // Start processing queue if not already processing
    if (!this.isProcessingQueue) {
      this.processNotificationQueue()
    }
  }

  private displayNotification(options: any): boolean {
    try {
      const notification = new Notification({
        title: options.title,
        body: options.body,
        icon: options.icon || this.getDefaultIcon(),
        silent: options.silent || false,
        urgency: options.urgency || 'normal',
        timeoutType: options.timeoutType || 'default',
        actions: options.actions || [],
        closeButtonText: options.closeButtonText
      })

      // Set up event listeners
      notification.on('click', () => {
        this.handleNotificationClick(options)
      })

      notification.on('close', () => {
        this.handleNotificationClose(options)
      })

      notification.on('failed', (error: any) => {
        log.error('Notification failed to display:', error)
      })

      // Show the notification
      notification.show()

      log.info('Notification displayed:', options.title)
      return true

    } catch (error) {
      log.error('Failed to display notification:', error)
      return false
    }
  }

  private handleNotificationClick(options: any): void {
    if (options.onClick) {
      try {
        options.onClick()
      } catch (error) {
        log.error('Notification click handler failed:', error)
      }
    }
  }

  private handleNotificationClose(options: any): void {
    if (options.onClose) {
      try {
        options.onClose()
      } catch (error) {
        log.error('Notification close handler failed:', error)
      }
    }
  }

  private async processNotificationQueue(): Promise<void> {
    if (this.isProcessingQueue || this.notificationQueue.length === 0) {
      return
    }

    this.isProcessingQueue = true

    try {
      while (this.notificationQueue.length > 0) {
        const notification = this.notificationQueue.shift()
        
        // Wait before showing next notification
        await this.sleep(1000) // 1 second delay
        
        this.displayNotification(notification)
      }
    } finally {
      this.isProcessingQueue = false
    }
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }

  private getDefaultIcon(): string | undefined {
    try {
      const path = require('path')
      const appPath = require('electron').app.getAppPath()
      const iconPath = path.join(appPath, 'resources', 'icon.png')
      
      const fs = require('fs-extra')
      if (fs.existsSync(iconPath)) {
        return iconPath
      }
    } catch (error) {
      log.warn('Could not find default icon:', error)
    }
    
    return undefined
  }

  // Predefined notification types
  showSuccess(message: string, options: any = {}): boolean {
    return this.show({
      title: 'Success',
      body: message,
      urgency: 'low',
      icon: this.getSuccessIcon(),
      ...options
    })
  }

  showError(message: string, options: any = {}): boolean {
    return this.show({
      title: 'Error',
      body: message,
      urgency: 'critical',
      icon: this.getErrorIcon(),
      ...options
    })
  }

  showWarning(message: string, options: any = {}): boolean {
    return this.show({
      title: 'Warning',
      body: message,
      urgency: 'normal',
      icon: this.getWarningIcon(),
      ...options
    })
  }

  showInfo(message: string, options: any = {}): boolean {
    return this.show({
      title: 'Information',
      body: message,
      urgency: 'normal',
      icon: this.getInfoIcon(),
      ...options
    })
  }

  // Document processing notifications
  showDocumentProcessing(filename: string): boolean {
    return this.show({
      title: 'Processing Document',
      body: `Processing ${filename}...`,
      urgency: 'normal',
      silent: true
    })
  }

  showDocumentProcessed(filename: string, success: boolean = true): boolean {
    if (success) {
      return this.showSuccess(`Successfully processed ${filename}`)
    } else {
      return this.showError(`Failed to process ${filename}`)
    }
  }

  showBatchProcessed(count: number, success: number, failed: number): boolean {
    return this.show({
      title: 'Batch Processing Complete',
      body: `Processed ${count} documents: ${success} successful, ${failed} failed`,
      urgency: success > failed ? 'normal' : 'critical'
    })
  }

  // Sync notifications
  showSyncStarted(): boolean {
    return this.show({
      title: 'Synchronization',
      body: 'Starting data synchronization...',
      urgency: 'low',
      silent: true
    })
  }

  showSyncComplete(imported: number, updated: number): boolean {
    return this.showSuccess(
      `Synchronization complete: ${imported} imported, ${updated} updated`
    )
  }

  showSyncFailed(error: string): boolean {
    return this.showError(`Synchronization failed: ${error}`)
  }

  showSyncOnline(): boolean {
    return this.showInfo('Connected to server', {
      urgency: 'low',
      timeoutType: 'never'
    })
  }

  showSyncOffline(): boolean {
    return this.showWarning('No internet connection - working offline', {
      urgency: 'normal',
      timeoutType: 'never'
    })
  }

  // Update notifications
  showUpdateAvailable(version: string): boolean {
    return this.show({
      title: 'Update Available',
      body: `Version ${version} is now available`,
      urgency: 'normal',
      actions: [
        {
          type: 'button',
          text: 'Update Now'
        },
        {
          type: 'button',
          text: 'Later'
        }
      ],
      onClick: () => {
        // Trigger update check
        const { ipcMain } = require('electron')
        ipcMain.emit('updater:install')
      }
    })
  }

  showUpdateDownloaded(): boolean {
    return this.show({
      title: 'Update Downloaded',
      body: 'Restart the application to install the update',
      urgency: 'normal',
      actions: [
        {
          type: 'button',
          text: 'Restart Now'
        },
        {
          type: 'button',
          text: 'Later'
        }
      ],
      onClick: () => {
        // Restart application
        const { app } = require('electron')
        app.relaunch()
        app.exit(0)
      }
    })
  }

  // Helper methods for icons
  private getSuccessIcon(): string | undefined {
    return this.getIconPath('success')
  }

  private getErrorIcon(): string | undefined {
    return this.getIconPath('error')
  }

  private getWarningIcon(): string | undefined {
    return this.getIconPath('warning')
  }

  private getInfoIcon(): string | undefined {
    return this.getIconPath('info')
  }

  private getIconPath(type: string): string | undefined {
    try {
      const path = require('path')
      const appPath = require('electron').app.getAppPath()
      const iconPath = path.join(appPath, 'resources', 'icons', `${type}.png`)
      
      const fs = require('fs-extra')
      if (fs.existsSync(iconPath)) {
        return iconPath
      }
    } catch (error) {
      log.warn(`Could not find ${type} icon:`, error)
    }
    
    return undefined
  }

  // Clear all queued notifications
  clearQueue(): void {
    this.notificationQueue = []
    log.info('Notification queue cleared')
  }

  // Get queue status
  getQueueStatus(): any {
    return {
      queued: this.notificationQueue.length,
      processing: this.isProcessingQueue,
      maxQueueSize: this.maxNotifications
    }
  }
}

export default NotificationManager