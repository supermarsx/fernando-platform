import fs from 'fs-extra'
import path from 'path'
import pdf from 'pdf-parse'
import sharp from 'sharp'
import { spawn } from 'child_process'
import log from 'electron-log'

class FileProcessor {
  private database: any

  constructor(database: any) {
    this.database = database
  }

  async processDocuments(filePaths: string[]): Promise<any[]> {
    const results = []
    
    for (const filePath of filePaths) {
      try {
        const result = await this.processDocument(filePath)
        results.push(result)
      } catch (error) {
        log.error(`Failed to process ${filePath}:`, error)
        results.push({
          filePath,
          success: false,
          error: error.message
        })
      }
    }

    return results
  }

  async processDocument(filePath: string): Promise<any> {
    const fileInfo = await fs.stat(filePath)
    const extension = path.extname(filePath).toLowerCase()
    const basename = path.basename(filePath)
    
    log.info(`Processing document: ${basename}`)

    // Create document record in database
    const documentId = await this.database.insertDocument({
      filename: basename,
      originalPath: filePath,
      fileType: extension.slice(1), // Remove dot
      fileSize: fileInfo.size,
      processingStatus: 'processing'
    })

    try {
      let processedData = {}
      let extractedText = ''
      let confidenceScore = 0

      if (extension === '.pdf') {
        ({ processedData, extractedText, confidenceScore } = await this.processPDF(filePath))
      } else if (['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'].includes(extension)) {
        ({ processedData, extractedText, confidenceScore } = await this.processImage(filePath))
      } else if (['.doc', '.docx'].includes(extension)) {
        ({ processedData, extractedText, confidenceScore } = await this.processWordDocument(filePath))
      } else {
        throw new Error(`Unsupported file type: ${extension}`)
      }

      // Extract accounting information
      const accountingData = this.extractAccountingInfo(extractedText)
      processedData = { ...processedData, ...accountingData }

      // Update database with results
      await this.database.updateDocument(documentId, {
        processing_status: 'completed',
        processed_data: processedData,
        extracted_text: extractedText,
        confidence_score: confidenceScore
      })

      log.info(`Successfully processed document: ${basename}`)

      return {
        id: documentId,
        filePath,
        filename: basename,
        success: true,
        data: processedData,
        extractedText,
        confidenceScore,
        processedAt: new Date().toISOString()
      }

    } catch (error) {
      // Update database with error
      await this.database.updateDocument(documentId, {
        processing_status: 'failed',
        error_message: error.message
      })

      throw error
    }
  }

  private async processPDF(filePath: string): Promise<any> {
    try {
      // Read PDF file
      const dataBuffer = await fs.readFile(filePath)
      
      // Extract text using pdf-parse
      const pdfData = await pdf(dataBuffer)
      
      let extractedText = pdfData.text || ''
      let confidenceScore = 0.8 // PDF text extraction is generally reliable

      // If PDF has images, extract text from images using OCR
      if (extractedText.trim().length < 50) {
        try {
          const ocrText = await this.performOCR(filePath)
          if (ocrText.trim().length > extractedText.trim().length) {
            extractedText = ocrText
            confidenceScore = 0.6 // OCR is less reliable
          }
        } catch (ocrError) {
          log.warn('OCR failed, using PDF text only:', ocrError)
        }
      }

      // Parse PDF metadata
      const processedData = {
        type: 'pdf',
        pages: pdfData.numpages,
        info: pdfData.info,
        metadata: pdfData.metadata,
        textLength: extractedText.length
      }

      return {
        processedData,
        extractedText,
        confidenceScore
      }

    } catch (error) {
      log.error('PDF processing error:', error)
      throw new Error(`Failed to process PDF: ${error.message}`)
    }
  }

  private async processImage(filePath: string): Promise<any> {
    try {
      // Perform OCR on image
      const extractedText = await this.performOCR(filePath)
      
      // Get image metadata
      const image = sharp(filePath)
      const metadata = await image.metadata()
      
      const processedData = {
        type: 'image',
        format: metadata.format,
        width: metadata.width,
        height: metadata.height,
        channels: metadata.channels,
        hasAlpha: metadata.hasAlpha,
        textLength: extractedText.length
      }

      return {
        processedData,
        extractedText,
        confidenceScore: 0.7 // OCR confidence
      }

    } catch (error) {
      log.error('Image processing error:', error)
      throw new Error(`Failed to process image: ${error.message}`)
    }
  }

  private async processWordDocument(filePath: string): Promise<any> {
    // Note: Word document processing would require additional libraries
    // For now, we'll treat it as a text file or try to extract if possible
    
    try {
      // Try to read as text (basic implementation)
      const content = await fs.readFile(filePath, 'utf8')
      
      const processedData = {
        type: 'word',
        textLength: content.length
      }

      return {
        processedData,
        extractedText: content,
        confidenceScore: 0.9 // High confidence for text extraction
      }

    } catch (error) {
      log.error('Word document processing error:', error)
      throw new Error(`Failed to process Word document: ${error.message}`)
    }
  }

  private async performOCR(filePath: string): Promise<string> {
    return new Promise((resolve, reject) => {
      // Use tesseract for OCR
      const tesseract = spawn('tesseract', [filePath, 'stdout', '--psm', '6'])
      
      let text = ''
      let error = ''

      tesseract.stdout.on('data', (data) => {
        text += data.toString()
      })

      tesseract.stderr.on('data', (data) => {
        error += data.toString()
      })

      tesseract.on('close', (code) => {
        if (code === 0) {
          resolve(text.trim())
        } else {
          reject(new Error(`Tesseract OCR failed: ${error}`))
        }
      })

      tesseract.on('error', (err) => {
        reject(new Error(`Failed to start tesseract: ${err.message}`))
      })
    })
  }

  private extractAccountingInfo(text: string): any {
    const accountingData: any = {}
    
    // Common patterns for accounting documents
    const patterns = {
      // Invoice patterns
      invoiceNumber: /invoice\s*#?\s*:?\s*([A-Z0-9\-]+)/gi,
      invoiceDate: /date\s*:?\s*([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})/gi,
      totalAmount: /total\s*:?\s*\$?\s*([0-9,]+\.?\d*)/gi,
      subtotal: /subtotal\s*:?\s*\$?\s*([0-9,]+\.?\d*)/gi,
      tax: /tax\s*:?\s*\$?\s*([0-9,]+\.?\d*)/gi,
      
      // Vendor/Company patterns
      vendor: /(?:from|vendor|supplier|company)\s*:?\s*([^\n\r]+)/gi,
      
      // Receipt patterns
      receiptNumber: /receipt\s*#?\s*:?\s*([A-Z0-9\-]+)/gi,
      time: /time\s*:?\s*([0-9]{1,2}:[0-9]{2}(?:\s?[AP]M)?)/gi,
      
      // Bank statement patterns
      accountNumber: /account\s*#?\s*:?\s*([0-9\-]+)/gi,
      balance: /balance\s*:?\s*\$?\s*([0-9,]+\.?\d*)/gi,
      
      // Check patterns
      checkNumber: /check\s*#?\s*:?\s*([0-9]+)/gi,
      payee: /pay\s*to\s*the\s*order\s*of\s*:?\s*([^\n\r]+)/gi
    }

    // Extract information using patterns
    for (const [key, pattern] of Object.entries(patterns)) {
      const matches = Array.from(text.matchAll(pattern))
      if (matches.length > 0) {
        const value = matches[0][1]?.trim()
        if (value) {
          accountingData[key] = value
        }
      }
    }

    // Extract monetary amounts
    const amountPattern = /\$?\s*([0-9,]+\.?\d{2})/g
    const amounts = Array.from(text.matchAll(amountPattern))
    if (amounts.length > 0) {
      accountingData.amounts = amounts.map(match => ({
        amount: parseFloat(match[1].replace(/,/g, '')),
        context: text.substring(Math.max(0, match.index! - 20), match.index! + 20)
      }))
    }

    // Extract dates
    const datePattern = /\b([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})\b/g
    const dates = Array.from(text.matchAll(datePattern))
    if (dates.length > 0) {
      accountingData.dates = dates.map(match => match[1])
    }

    // Detect document type
    const documentType = this.detectDocumentType(text)
    accountingData.documentType = documentType

    // Extract key vendor/company names
    const vendorPattern = /^(?:from|vendor|supplier|company)\s*:?\s*(.+)$/gmi
    const vendorMatches = Array.from(text.matchAll(vendorPattern))
    if (vendorMatches.length > 0) {
      accountingData.vendor = vendorMatches[0][1].trim().substring(0, 100) // Limit length
    }

    return accountingData
  }

  private detectDocumentType(text: string): string {
    const lowerText = text.toLowerCase()
    
    // Check for specific document type indicators
    if (lowerText.includes('invoice') || lowerText.includes('bill')) {
      return 'invoice'
    } else if (lowerText.includes('receipt') || lowerText.includes('purchase')) {
      return 'receipt'
    } else if (lowerText.includes('bank statement') || lowerText.includes('statement')) {
      return 'bank_statement'
    } else if (lowerText.includes('check') || lowerText.includes('cheque')) {
      return 'check'
    } else if (lowerText.includes('tax') || lowerText.includes('irs') || lowerText.includes('form')) {
      return 'tax_document'
    } else {
      return 'unknown'
    }
  }

  async processDocumentsSync(filePaths: string[]): Promise<any[]> {
    // Process documents sequentially instead of parallel
    const results = []
    
    for (const filePath of filePaths) {
      try {
        const result = await this.processDocument(filePath)
        results.push(result)
      } catch (error) {
        log.error(`Failed to process ${filePath}:`, error)
        results.push({
          filePath,
          success: false,
          error: error.message
        })
      }
    }

    return results
  }

  async validateFile(filePath: string): Promise<boolean> {
    try {
      const stats = await fs.stat(filePath)
      const extension = path.extname(filePath).toLowerCase()
      
      // Check if file exists and is readable
      if (!stats.isFile() || stats.size === 0) {
        return false
      }

      // Check supported file types
      const supportedExtensions = [
        '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.doc', '.docx'
      ]
      
      return supportedExtensions.includes(extension)
    } catch (error) {
      return false
    }
  }

  async getProcessingHistory(limit: number = 50): Promise<any[]> {
    return await this.database.getDocuments(limit)
  }

  async getDocumentById(id: number): Promise<any> {
    const documents = await this.database.query('SELECT * FROM documents WHERE id = ?', [id])
    return documents[0] || null
  }

  async searchDocuments(searchTerm: string): Promise<any[]> {
    const sql = `
      SELECT * FROM documents 
      WHERE filename LIKE ? 
         OR extracted_text LIKE ? 
         OR processed_data LIKE ?
      ORDER BY created_at DESC
    `
    const searchPattern = `%${searchTerm}%`
    return await this.database.query(sql, [searchPattern, searchPattern, searchPattern])
  }
}

export default FileProcessor