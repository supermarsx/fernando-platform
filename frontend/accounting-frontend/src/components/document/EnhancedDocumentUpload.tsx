import React, { useState, useCallback, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { 
  Upload, 
  FileText, 
  Image, 
  FileImage, 
  CheckCircle, 
  X, 
  AlertTriangle,
  Info,
  Eye,
  XCircle
} from 'lucide-react';
import { format } from 'date-fns';

interface DocumentFile {
  id: string;
  file: File;
  preview?: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  progress: number;
  error?: string;
  format?: string;
  validation?: ValidationResult;
}

interface ValidationResult {
  isValid: boolean;
  isSafe: boolean;
  isProcessable: boolean;
  detectedFormat?: string;
  warnings: string[];
  errors: string[];
}

interface EnhancedUploadProps {
  onFilesSelected: (files: DocumentFile[]) => void;
  onUpload?: (files: DocumentFile[]) => Promise<void>;
  maxFiles?: number;
  maxFileSize?: number; // in bytes
  acceptedFormats?: string[];
  className?: string;
}

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const getFileIcon = (format: string) => {
  switch (format.toLowerCase()) {
    case 'pdf':
      return <FileText className="h-5 w-5 text-red-500" />;
    case 'tiff':
    case 'tif':
      return <FileImage className="h-5 w-5 text-blue-500" />;
    case 'png':
      return <Image className="h-5 w-5 text-green-500" />;
    case 'jpeg':
    case 'jpg':
      return <Image className="h-5 w-5 text-purple-500" />;
    default:
      return <FileText className="h-5 w-5 text-gray-500" />;
  }
};

const getFormatBadgeColor = (format: string): string => {
  switch (format.toLowerCase()) {
    case 'pdf':
      return 'bg-red-100 text-red-800';
    case 'tiff':
      return 'bg-blue-100 text-blue-800';
    case 'png':
      return 'bg-green-100 text-green-800';
    case 'jpeg':
    case 'jpg':
      return 'bg-purple-100 text-purple-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
};

export function EnhancedDocumentUpload({
  onFilesSelected,
  onUpload,
  maxFiles = 10,
  maxFileSize = 50 * 1024 * 1024, // 50MB default
  acceptedFormats = ['.pdf', '.tiff', '.png', '.jpeg', '.jpg'],
  className
}: EnhancedUploadProps) {
  const [files, setFiles] = useState<DocumentFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [validationInProgress, setValidationInProgress] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = async (file: File): Promise<ValidationResult> => {
    // Basic file validation
    const isValidSize = file.size <= maxFileSize;
    const extension = '.' + file.name.split('.').pop()?.toLowerCase();
    const isValidFormat = acceptedFormats.includes(extension);

    const validation: ValidationResult = {
      isValid: isValidSize && isValidFormat,
      isSafe: true, // Will be updated by server-side validation
      isProcessable: isValidSize && isValidFormat,
      detectedFormat: extension.replace('.', ''),
      warnings: [],
      errors: []
    };

    if (!isValidSize) {
      validation.errors.push(`File size exceeds ${formatBytes(maxFileSize)} limit`);
    }

    if (!isValidFormat) {
      validation.errors.push(`File format ${extension} not supported`);
    }

    if (file.size < 100) {
      validation.warnings.push('File is very small and may not contain readable content');
    }

    return validation;
  };

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    setValidationInProgress(true);
    
    const newFiles: DocumentFile[] = [];
    
    for (const file of acceptedFiles) {
      const id = Math.random().toString(36).substr(2, 9);
      const validation = await validateFile(file);
      
      let preview = undefined;
      if (validation.detectedFormat && ['png', 'jpeg', 'jpg'].includes(validation.detectedFormat)) {
        // Create preview for images
        preview = URL.createObjectURL(file);
      }
      
      newFiles.push({
        id,
        file,
        preview,
        status: 'pending',
        progress: 0,
        validation,
        format: validation.detectedFormat
      });
    }
    
    const updatedFiles = [...files, ...newFiles];
    setFiles(updatedFiles);
    setValidationInProgress(false);
    
    // Notify parent component
    onFilesSelected(updatedFiles);
  }, [files, maxFileSize, acceptedFormats, onFilesSelected]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/tiff': ['.tiff', '.tif'],
      'image/png': ['.png'],
      'image/jpeg': ['.jpeg', '.jpg']
    },
    maxFiles,
    maxSize: maxFileSize
  });

  const removeFile = (fileId: string) => {
    const updatedFiles = files.filter(f => f.id !== fileId);
    setFiles(updatedFiles);
    onFilesSelected(updatedFiles);
    
    // Clean up preview URLs
    const fileToRemove = files.find(f => f.id === fileId);
    if (fileToRemove?.preview) {
      URL.revokeObjectURL(fileToRemove.preview);
    }
  };

  const handleUpload = async () => {
    if (!onUpload || files.length === 0) return;

    setUploading(true);
    setUploadProgress(0);

    try {
      await onUpload(files);
      
      // Update file statuses
      const updatedFiles = files.map(file => ({
        ...file,
        status: 'completed' as const,
        progress: 100
      }));
      setFiles(updatedFiles);
      
    } catch (error) {
      console.error('Upload failed:', error);
      
      // Update file statuses to error
      const updatedFiles = files.map(file => ({
        ...file,
        status: 'error' as const,
        error: 'Upload failed'
      }));
      setFiles(updatedFiles);
    } finally {
      setUploading(false);
    }
  };

  const getStatusIcon = (status: DocumentFile['status']) => {
    switch (status) {
      case 'pending':
        return <FileText className="h-4 w-4 text-gray-400" />;
      case 'processing':
        return <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full" />;
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'error':
        return <XCircle className="h-4 w-4 text-red-500" />;
    }
  };

  const formatStats = {
    total: files.length,
    valid: files.filter(f => f.validation?.isValid).length,
    invalid: files.filter(f => f.validation && !f.validation.isValid).length,
    totalSize: files.reduce((sum, f) => sum + f.file.size, 0)
  };

  return (
    <div className={className}>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Upload className="h-6 w-6 mr-2" />
            Enhanced Document Upload
          </CardTitle>
          <CardDescription>
            Upload documents in PDF, TIFF, PNG, JPEG formats with intelligent validation and preview
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Upload Statistics */}
          {files.length > 0 && (
            <div className="flex flex-wrap gap-4 text-sm text-gray-600">
              <span className="flex items-center">
                <FileText className="h-4 w-4 mr-1" />
                {formatStats.total} files
              </span>
              <span className="flex items-center">
                <CheckCircle className="h-4 w-4 mr-1 text-green-500" />
                {formatStats.valid} valid
              </span>
              <span className="flex items-center">
                <XCircle className="h-4 w-4 mr-1 text-red-500" />
                {formatStats.invalid} invalid
              </span>
              <span className="flex items-center">
                <Info className="h-4 w-4 mr-1" />
                {formatBytes(formatStats.totalSize)}
              </span>
            </div>
          )}

          {/* Drop Zone */}
          <div
            {...getRootProps()}
            className={`
              border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
              ${isDragActive 
                ? 'border-blue-500 bg-blue-50' 
                : 'border-gray-300 hover:border-gray-400'
              }
            `}
          >
            <input {...getInputProps()} />
            <Upload className={`mx-auto h-12 w-12 mb-4 ${isDragActive ? 'text-blue-500' : 'text-gray-400'}`} />
            <p className="text-lg font-medium mb-2">
              {isDragActive ? 'Drop files here' : 'Drag & drop files or click to browse'}
            </p>
            <p className="text-sm text-gray-500 mb-4">
              Supported formats: PDF, TIFF, PNG, JPEG, JPG
            </p>
            <p className="text-xs text-gray-400">
              Maximum {maxFiles} files, {formatBytes(maxFileSize)} per file
            </p>
          </div>

          {/* Validation Progress */}
          {validationInProgress && (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                Validating files...
              </AlertDescription>
            </Alert>
          )}

          {/* File List */}
          {files.length > 0 && (
            <div className="space-y-3">
              <h3 className="font-medium text-gray-900">
                Selected Files ({files.length})
              </h3>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {files.map((fileData) => (
                  <div
                    key={fileData.id}
                    className={`
                      flex items-center justify-between p-4 rounded-lg border
                      ${fileData.validation?.isValid 
                        ? 'bg-white border-gray-200' 
                        : 'bg-red-50 border-red-200'
                      }
                    `}
                  >
                    <div className="flex items-center space-x-3">
                      {/* Preview Thumbnail */}
                      {fileData.preview && (
                        <div className="w-12 h-12 rounded-lg overflow-hidden bg-gray-100">
                          <img 
                            src={fileData.preview} 
                            alt={fileData.file.name}
                            className="w-full h-full object-cover"
                          />
                        </div>
                      )}
                      
                      {/* File Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-1">
                          {getFileIcon(fileData.format || 'unknown')}
                          <p className="font-medium text-gray-900 truncate">
                            {fileData.file.name}
                          </p>
                          {fileData.format && (
                            <Badge 
                              variant="secondary" 
                              className={getFormatBadgeColor(fileData.format)}
                            >
                              {fileData.format.toUpperCase()}
                            </Badge>
                          )}
                        </div>
                        
                        <div className="flex items-center space-x-4 text-sm text-gray-500">
                          <span>{formatBytes(fileData.file.size)}</span>
                          <div className="flex items-center space-x-1">
                            {getStatusIcon(fileData.status)}
                            <span className="capitalize">{fileData.status}</span>
                          </div>
                        </div>
                        
                        {/* Validation Results */}
                        {fileData.validation && (
                          <div className="mt-2 space-y-1">
                            {fileData.validation.errors.length > 0 && (
                              <div className="flex items-center space-x-1 text-red-600">
                                <XCircle className="h-3 w-3" />
                                <span className="text-xs">
                                  {fileData.validation.errors[0]}
                                </span>
                              </div>
                            )}
                            
                            {fileData.validation.warnings.length > 0 && (
                              <div className="flex items-center space-x-1 text-yellow-600">
                                <AlertTriangle className="h-3 w-3" />
                                <span className="text-xs">
                                  {fileData.validation.warnings[0]}
                                </span>
                              </div>
                            )}
                          </div>
                        )}
                        
                        {/* Progress Bar */}
                        {fileData.status === 'processing' && (
                          <Progress value={fileData.progress} className="mt-2" />
                        )}
                      </div>
                    </div>
                    
                    {/* Actions */}
                    <div className="flex items-center space-x-2">
                      {fileData.preview && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => window.open(fileData.preview, '_blank')}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                      )}
                      
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeFile(fileData.id)}
                        disabled={uploading}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Upload Progress */}
          {uploading && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span>Uploading files...</span>
                <span>{uploadProgress}%</span>
              </div>
              <Progress value={uploadProgress} />
            </div>
          )}

          {/* Actions */}
          {files.length > 0 && (
            <div className="flex justify-end space-x-4">
              <Button
                variant="outline"
                onClick={() => {
                  setFiles([]);
                  onFilesSelected([]);
                }}
                disabled={uploading}
              >
                Clear All
              </Button>
              
              {onUpload && (
                <Button
                  onClick={handleUpload}
                  disabled={
                    uploading || 
                    files.length === 0 || 
                    files.every(f => f.status === 'completed')
                  }
                >
                  {uploading ? 'Uploading...' : `Upload ${files.length} file(s)`}
                </Button>
              )}
            </div>
          )}

          {/* Format Support Information */}
          <Card className="bg-gray-50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Supported Formats</CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                <div className="flex items-center space-x-2">
                  <FileText className="h-4 w-4 text-red-500" />
                  <span>PDF Documents</span>
                </div>
                <div className="flex items-center space-x-2">
                  <FileImage className="h-4 w-4 text-blue-500" />
                  <span>TIFF Images</span>
                </div>
                <div className="flex items-center space-x-2">
                  <Image className="h-4 w-4 text-green-500" />
                  <span>PNG Images</span>
                </div>
                <div className="flex items-center space-x-2">
                  <Image className="h-4 w-4 text-purple-500" />
                  <span>JPEG Images</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </CardContent>
      </Card>
    </div>
  );
}

export default EnhancedDocumentUpload;