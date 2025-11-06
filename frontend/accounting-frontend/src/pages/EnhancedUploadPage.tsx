import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { jobsAPI } from '@/lib/api';
import { EnhancedDocumentUpload, DocumentFile } from '@/components/document/EnhancedDocumentUpload';
import { DocumentPreview } from '@/components/document/DocumentPreview';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  ArrowLeft, 
  CheckCircle, 
  Upload, 
  FileText, 
  Image, 
  BarChart3,
  Settings,
  HelpCircle
} from 'lucide-react';

interface ProcessingStats {
  totalProcessed: number;
  formatDistribution: Record<string, { total: number; success: number; failed: number }>;
  averageProcessingTime: number;
  successRate: number;
}

export default function EnhancedUploadPage() {
  const [files, setFiles] = useState<DocumentFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [previewDocument, setPreviewDocument] = useState(null);
  const [processingStats, setProcessingStats] = useState<ProcessingStats | null>(null);
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);
  
  const navigate = useNavigate();

  // Advanced processing options
  const [processingOptions, setProcessingOptions] = useState({
    validateDocuments: true,
    generatePreviews: true,
    enableFormatConversion: true,
    highQualityProcessing: true,
    continueOnValidationFailure: false,
    integrateWithExisting: true,
    preferredOutputFormat: 'auto', // auto, pdf, png, jpeg
    ocrLanguage: 'eng',
    processingPriority: 'normal' // fast, normal, high
  });

  const handleFilesSelected = useCallback((selectedFiles: DocumentFile[]) => {
    setFiles(selectedFiles);
    setError('');
  }, []);

  const handleUpload = async (filesToUpload: DocumentFile[]) => {
    if (filesToUpload.length === 0) {
      setError('Please select at least one file');
      return;
    }

    setError('');
    setUploading(true);

    try {
      // Create job
      const jobResponse = await jobsAPI.create({});
      const jobId = jobResponse.data.job_id;

      // Prepare enhanced upload data
      const uploadData = {
        job_id: jobId,
        files: filesToUpload.map(file => ({
          file: file.file,
          validation: file.validation,
          format: file.format
        })),
        processing_options: processingOptions
      };

      // Upload documents with enhanced processing
      await jobsAPI.uploadDocumentsEnhanced(jobId, filesToUpload, processingOptions);

      setSuccess(true);
      
      // Fetch processing statistics
      try {
        const statsResponse = await jobsAPI.getProcessingStatistics();
        setProcessingStats(statsResponse.data);
      } catch (statsError) {
        console.warn('Failed to fetch processing statistics:', statsError);
      }

      setTimeout(() => {
        navigate(`/jobs/${jobId}`);
      }, 2000);

    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const formatStats = {
    total: files.length,
    valid: files.filter(f => f.validation?.isValid).length,
    invalid: files.filter(f => f.validation && !f.validation.isValid).length,
    totalSize: files.reduce((sum, f) => sum + f.file.size, 0),
    formats: files.reduce((acc, f) => {
      if (f.format) {
        acc[f.format] = (acc[f.format] || 0) + 1;
      }
      return acc;
    }, {} as Record<string, number>)
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto">
        <Button
          variant="ghost"
          className="mb-4"
          onClick={() => navigate('/dashboard')}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Dashboard
        </Button>

        <Tabs defaultValue="upload" className="space-y-6">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="upload" className="flex items-center space-x-2">
              <Upload className="h-4 w-4" />
              <span>Upload Documents</span>
            </TabsTrigger>
            <TabsTrigger value="stats" className="flex items-center space-x-2">
              <BarChart3 className="h-4 w-4" />
              <span>Processing Stats</span>
            </TabsTrigger>
            <TabsTrigger value="help" className="flex items-center space-x-2">
              <HelpCircle className="h-4 w-4" />
              <span>Help</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="upload" className="space-y-6">
            {success ? (
              <Alert className="mb-6 bg-green-50 text-green-900 border-green-200">
                <CheckCircle className="h-4 w-4" />
                <AlertDescription>
                  Documents uploaded successfully with enhanced processing! Redirecting to job details...
                </AlertDescription>
              </Alert>
            ) : (
              <>
                {error && (
                  <Alert variant="destructive" className="mb-6">
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}

                <EnhancedDocumentUpload
                  onFilesSelected={handleFilesSelected}
                  onUpload={handleUpload}
                  maxFiles={20}
                  maxFileSize={100 * 1024 * 1024} // 100MB for enhanced processing
                  acceptedFormats={['.pdf', '.tiff', '.png', '.jpeg', '.jpg']}
                />

                {/* Processing Options */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      <span className="flex items-center">
                        <Settings className="h-5 w-5 mr-2" />
                        Advanced Processing Options
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
                      >
                        {showAdvancedOptions ? 'Hide' : 'Show'} Options
                      </Button>
                    </CardTitle>
                    <CardDescription>
                      Configure enhanced processing settings for optimal results
                    </CardDescription>
                  </CardHeader>
                  
                  {showAdvancedOptions && (
                    <CardContent className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-3">
                          <h4 className="font-medium">Processing Features</h4>
                          
                          <label className="flex items-center space-x-2">
                            <input
                              type="checkbox"
                              checked={processingOptions.validateDocuments}
                              onChange={(e) => setProcessingOptions(prev => ({
                                ...prev,
                                validateDocuments: e.target.checked
                              }))}
                              className="rounded"
                            />
                            <span className="text-sm">Enhanced Document Validation</span>
                          </label>
                          
                          <label className="flex items-center space-x-2">
                            <input
                              type="checkbox"
                              checked={processingOptions.generatePreviews}
                              onChange={(e) => setProcessingOptions(prev => ({
                                ...prev,
                                generatePreviews: e.target.checked
                              }))}
                              className="rounded"
                            />
                            <span className="text-sm">Generate Previews & Thumbnails</span>
                          </label>
                          
                          <label className="flex items-center space-x-2">
                            <input
                              type="checkbox"
                              checked={processingOptions.enableFormatConversion}
                              onChange={(e) => setProcessingOptions(prev => ({
                                ...prev,
                                enableFormatConversion: e.target.checked
                              }))}
                              className="rounded"
                            />
                            <span className="text-sm">Enable Format Conversion</span>
                          </label>
                          
                          <label className="flex items-center space-x-2">
                            <input
                              type="checkbox"
                              checked={processingOptions.highQualityProcessing}
                              onChange={(e) => setProcessingOptions(prev => ({
                                ...prev,
                                highQualityProcessing: e.target.checked
                              }))}
                              className="rounded"
                            />
                            <span className="text-sm">High Quality Processing</span>
                          </label>
                        </div>
                        
                        <div className="space-y-3">
                          <h4 className="font-medium">Processing Settings</h4>
                          
                          <div>
                            <label className="block text-sm font-medium mb-1">Preferred Output Format</label>
                            <select
                              value={processingOptions.preferredOutputFormat}
                              onChange={(e) => setProcessingOptions(prev => ({
                                ...prev,
                                preferredOutputFormat: e.target.value
                              }))}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                            >
                              <option value="auto">Auto (Recommended)</option>
                              <option value="pdf">PDF</option>
                              <option value="png">PNG</option>
                              <option value="jpeg">JPEG</option>
                            </select>
                          </div>
                          
                          <div>
                            <label className="block text-sm font-medium mb-1">Processing Priority</label>
                            <select
                              value={processingOptions.processingPriority}
                              onChange={(e) => setProcessingOptions(prev => ({
                                ...prev,
                                processingPriority: e.target.value
                              }))}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                            >
                              <option value="fast">Fast (Lower Quality)</option>
                              <option value="normal">Normal (Balanced)</option>
                              <option value="high">High Quality (Slower)</option>
                            </select>
                          </div>
                          
                          <label className="flex items-center space-x-2">
                            <input
                              type="checkbox"
                              checked={processingOptions.continueOnValidationFailure}
                              onChange={(e) => setProcessingOptions(prev => ({
                                ...prev,
                                continueOnValidationFailure: e.target.checked
                              }))}
                              className="rounded"
                            />
                            <span className="text-sm">Continue on Validation Failure</span>
                          </label>
                        </div>
                      </div>
                    </CardContent>
                  )}
                </Card>

                {/* File Summary */}
                {files.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Upload Summary</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                        <div className="text-center p-3 bg-gray-50 rounded-lg">
                          <FileText className="h-6 w-6 mx-auto mb-1 text-gray-600" />
                          <p className="text-sm font-medium">{formatStats.total}</p>
                          <p className="text-xs text-gray-500">Total Files</p>
                        </div>
                        <div className="text-center p-3 bg-green-50 rounded-lg">
                          <CheckCircle className="h-6 w-6 mx-auto mb-1 text-green-600" />
                          <p className="text-sm font-medium">{formatStats.valid}</p>
                          <p className="text-xs text-gray-500">Valid</p>
                        </div>
                        <div className="text-center p-3 bg-red-50 rounded-lg">
                          <FileText className="h-6 w-6 mx-auto mb-1 text-red-600" />
                          <p className="text-sm font-medium">{formatStats.invalid}</p>
                          <p className="text-xs text-gray-500">Invalid</p>
                        </div>
                        <div className="text-center p-3 bg-blue-50 rounded-lg">
                          <BarChart3 className="h-6 w-6 mx-auto mb-1 text-blue-600" />
                          <p className="text-sm font-medium">
                            {formatStats.totalSize < 1024 ? '1KB' : 
                             formatStats.totalSize < 1024 * 1024 ? `${Math.round(formatStats.totalSize / 1024)}KB` : 
                             `${Math.round(formatStats.totalSize / (1024 * 1024))}MB`}
                          </p>
                          <p className="text-xs text-gray-500">Total Size</p>
                        </div>
                      </div>
                      
                      {/* Format Distribution */}
                      {Object.keys(formatStats.formats).length > 0 && (
                        <div>
                          <h4 className="font-medium mb-2">Format Distribution</h4>
                          <div className="flex flex-wrap gap-2">
                            {Object.entries(formatStats.formats).map(([format, count]) => (
                              <div key={format} className="flex items-center space-x-2 px-3 py-1 bg-gray-100 rounded-full text-sm">
                                {format.toLowerCase() === 'pdf' && <FileText className="h-4 w-4 text-red-500" />}
                                {format.toLowerCase() === 'tiff' && <Image className="h-4 w-4 text-blue-500" />}
                                {(format.toLowerCase() === 'png' || format.toLowerCase() === 'jpeg') && <Image className="h-4 w-4 text-green-500" />}
                                <span>{format.toUpperCase()}</span>
                                <span className="text-gray-500">({count})</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}
              </>
            )}
          </TabsContent>

          <TabsContent value="stats" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <BarChart3 className="h-5 w-5 mr-2" />
                  Processing Statistics
                </CardTitle>
                <CardDescription>
                  Real-time statistics about document processing performance
                </CardDescription>
              </CardHeader>
              <CardContent>
                {processingStats ? (
                  <div className="space-y-6">
                    {/* Overall Stats */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="text-center p-4 bg-blue-50 rounded-lg">
                        <p className="text-2xl font-bold text-blue-600">{processingStats.totalProcessed}</p>
                        <p className="text-sm text-gray-600">Total Processed</p>
                      </div>
                      <div className="text-center p-4 bg-green-50 rounded-lg">
                        <p className="text-2xl font-bold text-green-600">{Math.round(processingStats.successRate * 100)}%</p>
                        <p className="text-sm text-gray-600">Success Rate</p>
                      </div>
                      <div className="text-center p-4 bg-purple-50 rounded-lg">
                        <p className="text-2xl font-bold text-purple-600">{processingStats.averageProcessingTime.toFixed(1)}s</p>
                        <p className="text-sm text-gray-600">Avg Processing Time</p>
                      </div>
                    </div>
                    
                    {/* Format Distribution */}
                    <div>
                      <h4 className="font-medium mb-3">Processing by Format</h4>
                      <div className="space-y-3">
                        {Object.entries(processingStats.formatDistribution).map(([format, stats]) => (
                          <div key={format} className="p-3 border rounded-lg">
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-medium">{format.toUpperCase()}</span>
                              <span className="text-sm text-gray-500">{stats.total} files</span>
                            </div>
                            <div className="flex space-x-4 text-sm">
                              <span className="text-green-600">Success: {stats.success}</span>
                              <span className="text-red-600">Failed: {stats.failed}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <BarChart3 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No processing statistics available yet</p>
                    <p className="text-sm">Upload some documents to see statistics</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="help" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <HelpCircle className="h-5 w-5 mr-2" />
                  Enhanced Document Processing Help
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h3 className="font-medium mb-2">Supported Formats</h3>
                  <ul className="text-sm text-gray-600 space-y-1">
                    <li>• <strong>PDF:</strong> Text and image-based PDFs with intelligent processing</li>
                    <li>• <strong>TIFF:</strong> Multi-page TIFF documents with compression support</li>
                    <li>• <strong>PNG:</strong> High-quality PNG images with transparency support</li>
                    <li>• <strong>JPEG/JPG:</strong> Compressed JPEG images optimized for processing</li>
                  </ul>
                </div>
                
                <div>
                  <h3 className="font-medium mb-2">Processing Features</h3>
                  <ul className="text-sm text-gray-600 space-y-1">
                    <li>• <strong>Format Detection:</strong> Automatic format identification with confidence scoring</li>
                    <li>• <strong>Document Validation:</strong> Security scanning and integrity checks</li>
                    <li>• <strong>Preview Generation:</strong> Thumbnails and preview images for all formats</li>
                    <li>• <strong>Format Conversion:</strong> Convert between formats when needed for optimal processing</li>
                    <li>• <strong>Enhanced OCR:</strong> Format-optimized OCR processing</li>
                  </ul>
                </div>
                
                <div>
                  <h3 className="font-medium mb-2">Tips for Best Results</h3>
                  <ul className="text-sm text-gray-600 space-y-1">
                    <li>• Use high-resolution images (300 DPI or higher) for better OCR accuracy</li>
                    <li>• Ensure documents are clear and well-lit for optimal text extraction</li>
                    <li>• PDF files with text layers will process faster than image-only PDFs</li>
                    <li>• Enable format conversion for documents that need optimization</li>
                    <li>• Use high-quality processing for important or complex documents</li>
                  </ul>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Document Preview Modal */}
      {previewDocument && (
        <DocumentPreview
          document={previewDocument}
          open={!!previewDocument}
          onClose={() => setPreviewDocument(null)}
        />
      )}
    </div>
  );
}