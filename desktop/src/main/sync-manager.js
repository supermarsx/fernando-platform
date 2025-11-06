import axios from 'axios'
import fs from 'fs-extra'
import path from 'path'
import log from 'electron-log'

class SyncManager {
  private database: any
  private apiUrl: string
  private syncInterval: NodeJS.Timeout | null = null
  private isOnline: boolean = false
  private syncQueue: any[] = []
  private maxRetries: number = 3
  private retryDelay: number = 5000 // 5 seconds

  constructor() {
    this.apiUrl = process.env.NODE_ENV === 'production' 
      ? 'https://your-api-domain.com/api'
      : 'http://localhost:8000/api'
  }

  async initialize(database: any): Promise<void> {
    this.database = database
    
    // Set up network monitoring
    this.setupNetworkMonitoring()
    
    // Start periodic sync
    this.startPeriodicSync()
    
    log.info('Sync manager initialized')
  }

  private setupNetworkMonitoring(): void {
    // Check network connectivity
    this.checkConnectivity()
    
    // Set up periodic connectivity check
    setInterval(() => {
      this.checkConnectivity()
    }, 30000) // Check every 30 seconds
  }

  private async checkConnectivity(): Promise<void> {
    try {
      const response = await axios.get(`${this.apiUrl}/health`, { 
        timeout: 5000 
      })
      this.isOnline = response.status === 200
      log.debug('Network connectivity:', this.isOnline)
    } catch (error) {
      this.isOnline = false
      log.debug('Network connectivity: offline')
    }
  }

  private startPeriodicSync(): void {
    // Sync every 5 minutes
    this.syncInterval = setInterval(async () => {
      await this.performSync()
    }, 5 * 60 * 1000)
  }

  async uploadDocuments(documents: any[]): Promise<any> {
    if (!this.isOnline) {
      throw new Error('No internet connection available')
    }

    const results = []
    
    for (const document of documents) {
      try {
        const result = await this.uploadDocument(document)
        results.push(result)
        
        // Mark as synced in database
        await this.database.markDocumentSynced(document.id)
        
        // Remove from sync queue
        await this.removeFromSyncQueue(document.id)
        
      } catch (error) {
        log.error(`Failed to upload document ${document.id}:`, error)
        results.push({
          documentId: document.id,
          success: false,
          error: error.message
        })
      }
    }

    return {
      uploaded: results.filter(r => r.success).length,
      failed: results.filter(r => !r.success).length,
      results
    }
  }

  private async uploadDocument(document: any): Promise<any> {
    const formData = new FormData()
    
    // Add document file if exists
    if (document.original_path && await fs.pathExists(document.original_path)) {
      const fileBuffer = await fs.readFile(document.original_path)
      formData.append('file', new Blob([fileBuffer]), document.filename)
    }
    
    // Add document data
    formData.append('data', JSON.stringify({
      id: document.id,
      filename: document.filename,
      fileType: document.file_type,
      fileSize: document.file_size,
      processedData: JSON.parse(document.processed_data || '{}'),
      extractedText: document.extracted_text,
      confidenceScore: document.confidence_score,
      processingStatus: document.processing_status
    }))

    const response = await axios.post(`${this.apiUrl}/documents/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
        'Authorization': await this.getAuthToken()
      },
      timeout: 30000 // 30 second timeout
    })

    return {
      documentId: document.id,
      success: true,
      serverId: response.data.id,
      uploadedAt: new Date().toISOString()
    }
  }

  async downloadDocuments(): Promise<any> {
    if (!this.isOnline) {
      throw new Error('No internet connection available')
    }

    try {
      const response = await axios.get(`${this.apiUrl}/documents/sync`, {
        headers: {
          'Authorization': await this.getAuthToken()
        },
        timeout: 30000
      })

      const { documents, lastSync } = response.data
      let imported = 0
      let updated = 0

      for (const serverDocument of documents) {
        try {
          // Check if document already exists
          const existingDocs = await this.database.query(
            'SELECT id FROM documents WHERE filename = ?', 
            [serverDocument.filename]
          )

          if (existingDocs.length > 0) {
            // Update existing document
            await this.database.updateDocument(existingDocs[0].id, {
              processed_data: JSON.stringify(serverDocument.processed_data),
              extracted_text: serverDocument.extracted_text,
              confidence_score: serverDocument.confidence_score,
              processing_status: serverDocument.processing_status,
              last_sync: new Date().toISOString()
            })
            updated++
          } else {
            // Insert new document
            await this.database.insertDocument({
              filename: serverDocument.filename,
              originalPath: serverDocument.original_path || '',
              fileType: serverDocument.file_type,
              fileSize: serverDocument.file_size,
              processingStatus: serverDocument.processing_status || 'completed',
              processedData: serverDocument.processed_data || {},
              extractedText: serverDocument.extracted_text || '',
              confidenceScore: serverDocument.confidence_score || 0
            })
            imported++
          }
        } catch (error) {
          log.error(`Failed to sync document ${serverDocument.filename}:`, error)
        }
      }

      // Update last sync time
      await this.database.setSetting('lastSync', lastSync || new Date().toISOString())

      return {
        imported,
        updated,
        totalProcessed: documents.length,
        syncedAt: new Date().toISOString()
      }

    } catch (error) {
      log.error('Failed to download documents:', error)
      throw error
    }
  }

  async getSyncStatus(): Promise<any> {
    const dirtyDocuments = await this.database.getDirtyDocuments()
    const pendingLogs = await this.database.getPendingSyncLogs()
    const lastSync = await this.database.getSetting('lastSync')
    
    // Get server sync status if online
    let serverStatus = null
    if (this.isOnline) {
      try {
        const response = await axios.get(`${this.apiUrl}/sync/status`, {
          headers: {
            'Authorization': await this.getAuthToken()
          },
          timeout: 5000
        })
        serverStatus = response.data
      } catch (error) {
        log.warn('Failed to get server sync status:', error)
      }
    }

    return {
      isOnline: this.isOnline,
      hasPendingUploads: dirtyDocuments.length > 0,
      hasPendingSync: pendingLogs.length > 0,
      pendingUploads: dirtyDocuments.length,
      pendingSync: pendingLogs.length,
      lastSync: lastSync || null,
      serverStatus: serverStatus,
      syncInProgress: this.syncQueue.length > 0
    }
  }

  private async addToSyncQueue(document: any): Promise<void> {
    this.syncQueue.push({
      ...document,
      retryCount: 0,
      addedAt: new Date().toISOString()
    })
  }

  private async removeFromSyncQueue(documentId: number): Promise<void> {
    this.syncQueue = this.syncQueue.filter(item => item.id !== documentId)
  }

  private async performSync(): Promise<void> {
    if (!this.isOnline || this.syncQueue.length === 0) {
      return
    }

    log.info(`Starting sync for ${this.syncQueue.length} documents`)

    const itemsToSync = [...this.syncQueue]
    
    for (const item of itemsToSync) {
      try {
        await this.uploadDocument(item)
        await this.database.markDocumentSynced(item.id)
        await this.removeFromSyncQueue(item.id)
        
      } catch (error) {
        log.error(`Sync failed for document ${item.id}:`, error)
        
        item.retryCount++
        
        if (item.retryCount >= this.maxRetries) {
          // Mark as failed
          await this.database.addSyncLog('upload', 'documents', item.id, item)
          await this.removeFromSyncQueue(item.id)
        } else {
          // Retry later
          setTimeout(() => {
            this.syncQueue.push(item)
          }, this.retryDelay * item.retryCount)
        }
      }
    }

    log.info('Sync operation completed')
  }

  private async getAuthToken(): Promise<string> {
    // Get stored auth token
    const token = await this.database.getSetting('authToken')
    if (!token) {
      throw new Error('No authentication token available')
    }
    return `Bearer ${token}`
  }

  async login(email: string, password: string): Promise<any> {
    try {
      const response = await axios.post(`${this.apiUrl}/auth/login`, {
        email,
        password
      })

      const { token, user } = response.data
      
      // Store token and user data
      await this.database.setSetting('authToken', token)
      await this.database.setSetting('userData', JSON.stringify(user))
      
      // Update user in local database
      await this.database.createUser({
        email: user.email,
        passwordHash: password, // Store hash of password (in production, hash it)
        firstName: user.first_name,
        lastName: user.last_name,
        role: user.role
      })

      return {
        success: true,
        user,
        token
      }

    } catch (error) {
      log.error('Login failed:', error)
      throw error
    }
  }

  async logout(): Promise<void> {
    try {
      // Notify server about logout
      if (this.isOnline) {
        await axios.post(`${this.apiUrl}/auth/logout`, {}, {
          headers: {
            'Authorization': await this.getAuthToken()
          }
        })
      }
    } catch (error) {
      log.warn('Logout request failed:', error)
    }

    // Clear local data
    await this.database.setSetting('authToken', '')
    await this.database.setSetting('userData', '')
  }

  async getUserData(): Promise<any> {
    const userData = await this.database.getSetting('userData')
    return userData ? JSON.parse(userData) : null
  }

  async isAuthenticated(): Promise<boolean> {
    const token = await this.database.getSetting('authToken')
    return !!token
  }

  async refreshToken(): Promise<boolean> {
    try {
      const response = await axios.post(`${this.apiUrl}/auth/refresh`, {}, {
        headers: {
          'Authorization': await this.getAuthToken()
        }
      })

      const { token } = response.data
      await this.database.setSetting('authToken', token)
      return true

    } catch (error) {
      log.error('Token refresh failed:', error)
      return false
    }
  }

  async exportData(): Promise<any> {
    try {
      const localData = await this.database.exportData()
      
      if (!this.isOnline) {
        return {
          local: localData,
          server: null,
          exportedAt: new Date().toISOString()
        }
      }

      // Try to get server data
      const response = await axios.get(`${this.apiUrl}/data/export`, {
        headers: {
          'Authorization': await this.getAuthToken()
        }
      })

      return {
        local: localData,
        server: response.data,
        exportedAt: new Date().toISOString()
      }

    } catch (error) {
      log.error('Data export failed:', error)
      // Return local data only
      return {
        local: await this.database.exportData(),
        server: null,
        exportedAt: new Date().toISOString()
      }
    }
  }

  async importData(importData: any): Promise<void> {
    try {
      // Import local data first
      if (importData.local) {
        await this.database.importData(importData.local)
      }

      // Try to sync to server
      if (this.isOnline && importData.local) {
        const documents = await this.database.getDocuments(1000) // Get all documents
        
        for (const document of documents) {
          try {
            await this.uploadDocument(document)
          } catch (error) {
            log.warn(`Failed to sync document ${document.filename} during import:`, error)
          }
        }
      }

    } catch (error) {
      log.error('Data import failed:', error)
      throw error
    }
  }

  stop(): void {
    if (this.syncInterval) {
      clearInterval(this.syncInterval)
      this.syncInterval = null
    }
  }
}

export default SyncManager