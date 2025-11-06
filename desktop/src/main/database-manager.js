import sqlite3 from 'sqlite3'
import { join } from 'path'
import { app } from 'electron'
import fs from 'fs-extra'
import log from 'electron-log'

class DatabaseManager {
  private db: sqlite3.Database | null = null
  private dbPath: string

  constructor() {
    this.dbPath = join(app.getPath('userData'), 'database', 'fernando.db')
  }

  async initialize(): Promise<void> {
    try {
      // Ensure database directory exists
      await fs.ensureDir(join(app.getPath('userData'), 'database'))
      
      // Initialize database connection
      this.db = new sqlite3.Database(this.dbPath, (err) => {
        if (err) {
          log.error('Error opening database:', err)
          throw err
        }
        log.info('Database connected successfully')
      })

      // Enable WAL mode for better performance
      await this.run('PRAGMA journal_mode = WAL')
      await this.run('PRAGMA synchronous = NORMAL')
      await this.run('PRAGMA cache_size = 1000')
      await this.run('PRAGMA temp_store = memory')
      
      // Create tables
      await this.createTables()
      
      log.info('Database initialized successfully')
    } catch (error) {
      log.error('Failed to initialize database:', error)
      throw error
    }
  }

  private async createTables(): Promise<void> {
    // Users table for offline authentication
    await this.run(`
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        first_name TEXT,
        last_name TEXT,
        role TEXT DEFAULT 'user',
        is_active BOOLEAN DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_sync DATETIME
      )
    `)

    // Documents table for storing processed documents
    await this.run(`
      CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        original_path TEXT NOT NULL,
        file_type TEXT NOT NULL,
        file_size INTEGER,
        processing_status TEXT DEFAULT 'pending',
        processed_data TEXT,
        extracted_text TEXT,
        confidence_score REAL,
        error_message TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_sync DATETIME,
        is_dirty BOOLEAN DEFAULT 0,
        sync_status TEXT DEFAULT 'pending'
      )
    `)

    // Sync log for tracking sync operations
    await this.run(`
      CREATE TABLE IF NOT EXISTS sync_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        operation_type TEXT NOT NULL,
        table_name TEXT NOT NULL,
        record_id INTEGER,
        operation_data TEXT,
        status TEXT DEFAULT 'pending',
        error_message TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        synced_at DATETIME
      )
    `)

    // Settings table for app configuration
    await this.run(`
      CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `)

    // Create indexes for better performance
    await this.run('CREATE INDEX IF NOT EXISTS idx_documents_sync_status ON documents(sync_status)')
    await this.run('CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at)')
    await this.run('CREATE INDEX IF NOT EXISTS idx_sync_log_created_at ON sync_log(created_at)')
    await this.run('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
  }

  async query(sql: string, params: any[] = []): Promise<any[]> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'))
        return
      }

      this.db.all(sql, params, (err, rows) => {
        if (err) {
          log.error('Query error:', err)
          reject(err)
        } else {
          resolve(rows)
        }
      })
    })
  }

  async run(sql: string, params: any[] = []): Promise<{ changes: number; lastID: number }> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'))
        return
      }

      this.db.run(sql, params, function(err) {
        if (err) {
          log.error('Run error:', err)
          reject(err)
        } else {
          resolve({ changes: this.changes, lastID: this.lastID })
        }
      })
    })
  }

  async get(sql: string, params: any[] = []): Promise<any> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'))
        return
      }

      this.db.get(sql, params, (err, row) => {
        if (err) {
          log.error('Get error:', err)
          reject(err)
        } else {
          resolve(row)
        }
      })
    })
  }

  async insertDocument(documentData: any): Promise<number> {
    const sql = `
      INSERT INTO documents (
        filename, original_path, file_type, file_size, 
        processing_status, processed_data, extracted_text, 
        confidence_score, is_dirty
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `
    
    const params = [
      documentData.filename,
      documentData.originalPath,
      documentData.fileType,
      documentData.fileSize,
      documentData.processingStatus || 'pending',
      JSON.stringify(documentData.processedData || {}),
      documentData.extractedText || '',
      documentData.confidenceScore || 0,
      1 // is_dirty
    ]

    const result = await this.run(sql, params)
    return result.lastID
  }

  async updateDocument(documentId: number, updateData: any): Promise<void> {
    const fields = []
    const params = []

    for (const [key, value] of Object.entries(updateData)) {
      if (key !== 'id') {
        fields.push(`${key} = ?`)
        if (key === 'processed_data' || key === 'extracted_text') {
          params.push(typeof value === 'object' ? JSON.stringify(value) : value)
        } else {
          params.push(value)
        }
      }
    }

    fields.push('updated_at = CURRENT_TIMESTAMP')
    fields.push('is_dirty = 1')

    const sql = `UPDATE documents SET ${fields.join(', ')} WHERE id = ?`
    params.push(documentId)

    await this.run(sql, params)
  }

  async getDocuments(limit: number = 50, offset: number = 0): Promise<any[]> {
    const sql = `
      SELECT * FROM documents 
      ORDER BY created_at DESC 
      LIMIT ? OFFSET ?
    `
    return await this.query(sql, [limit, offset])
  }

  async getDirtyDocuments(): Promise<any[]> {
    const sql = 'SELECT * FROM documents WHERE is_dirty = 1 ORDER BY updated_at ASC'
    return await this.query(sql)
  }

  async markDocumentSynced(documentId: number): Promise<void> {
    const sql = `
      UPDATE documents 
      SET is_dirty = 0, sync_status = 'synced', last_sync = CURRENT_TIMESTAMP 
      WHERE id = ?
    `
    await this.run(sql, [documentId])
  }

  async addSyncLog(operationType: string, tableName: string, recordId: number, data: any): Promise<void> {
    const sql = `
      INSERT INTO sync_log (operation_type, table_name, record_id, operation_data, status)
      VALUES (?, ?, ?, ?, 'pending')
    `
    const params = [
      operationType,
      tableName,
      recordId,
      JSON.stringify(data)
    ]
    await this.run(sql, params)
  }

  async getPendingSyncLogs(): Promise<any[]> {
    const sql = 'SELECT * FROM sync_log WHERE status = "pending" ORDER BY created_at ASC'
    return await this.query(sql)
  }

  async markSyncLogCompleted(logId: number): Promise<void> {
    const sql = 'UPDATE sync_log SET status = "completed", synced_at = CURRENT_TIMESTAMP WHERE id = ?'
    await this.run(sql, [logId])
  }

  async markSyncLogFailed(logId: number, errorMessage: string): Promise<void> {
    const sql = 'UPDATE sync_log SET status = "failed", error_message = ? WHERE id = ?'
    await this.run(sql, [errorMessage, logId])
  }

  async getSetting(key: string): Promise<string | null> {
    const sql = 'SELECT value FROM settings WHERE key = ?'
    const result = await this.get(sql, [key])
    return result?.value || null
  }

  async setSetting(key: string, value: string): Promise<void> {
    const sql = `
      INSERT OR REPLACE INTO settings (key, value, updated_at)
      VALUES (?, ?, CURRENT_TIMESTAMP)
    `
    await this.run(sql, [key, value])
  }

  async getUserByEmail(email: string): Promise<any> {
    const sql = 'SELECT * FROM users WHERE email = ? AND is_active = 1'
    return await this.get(sql, [email])
  }

  async createUser(userData: any): Promise<number> {
    const sql = `
      INSERT INTO users (email, password_hash, first_name, last_name, role)
      VALUES (?, ?, ?, ?, ?)
    `
    const params = [
      userData.email,
      userData.passwordHash,
      userData.firstName,
      userData.lastName,
      userData.role || 'user'
    ]
    const result = await this.run(sql, params)
    return result.lastID
  }

  async updateUserSync(email: string): Promise<void> {
    const sql = 'UPDATE users SET last_sync = CURRENT_TIMESTAMP WHERE email = ?'
    await this.run(sql, [email])
  }

  async close(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.db) {
        this.db.close((err) => {
          if (err) {
            log.error('Error closing database:', err)
            reject(err)
          } else {
            log.info('Database closed successfully')
            resolve()
          }
        })
      } else {
        resolve()
      }
    })
  }

  async exportData(): Promise<any> {
    // Export all data for backup
    const tables = ['users', 'documents', 'settings']
    const exportData: any = {}

    for (const table of tables) {
      exportData[table] = await this.query(`SELECT * FROM ${table}`)
    }

    return {
      version: '1.0.0',
      exportedAt: new Date().toISOString(),
      data: exportData
    }
  }

  async importData(importData: any): Promise<void> {
    if (!importData.data) {
      throw new Error('Invalid import data format')
    }

    // Clear existing data
    await this.run('DELETE FROM documents')
    await this.run('DELETE FROM settings')
    await this.run('DELETE FROM users')

    // Import data
    for (const [tableName, records] of Object.entries(importData.data)) {
      for (const record of records as any[]) {
        if (tableName === 'documents') {
          await this.insertDocument({
            filename: record.filename,
            originalPath: record.original_path,
            fileType: record.file_type,
            fileSize: record.file_size,
            processingStatus: record.processing_status,
            processedData: JSON.parse(record.processed_data || '{}'),
            extractedText: record.extracted_text,
            confidenceScore: record.confidence_score
          })
        } else if (tableName === 'settings') {
          await this.setSetting(record.key, record.value)
        } else if (tableName === 'users') {
          await this.createUser({
            email: record.email,
            passwordHash: record.password_hash,
            firstName: record.first_name,
            lastName: record.last_name,
            role: record.role
          })
        }
      }
    }
  }
}

export default DatabaseManager