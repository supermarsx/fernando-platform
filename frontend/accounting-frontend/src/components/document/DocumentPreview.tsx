import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  FileText, 
  Image, 
  Download, 
  ZoomIn, 
  ZoomOut, 
  RotateCw, 
  Eye,
  X,
  ChevronLeft,
  ChevronRight,
  Info,
  CheckCircle,
  AlertTriangle
} from 'lucide-react';
import { format } from 'date-fns';

interface DocumentPreviewData {
  documentId: string;
  format: string;
  filePath: string;
  thumbnails?: {
    small?: string;
    medium?: string;
    large?: string;
  };
  previews?: {
    small?: string;
    medium?: string;
    large?: string;
  };
  pagePreviews?: {
    [pageNumber: string]: {
      small?: string;
      medium?: string;
      large?: string;
    };
  };
  metadata?: {
    pageCount?: number;
    dimensions?: { width: number; height: number };
    fileSize?: number;
    detectedFormat?: string;
    confidence?: number;
    processingStatus?: string;
  };
  validationResults?: {
    isValid: boolean;
    isSafe: boolean;
    isProcessable: boolean;
    warnings: string[];
    errors: string[];
  };
}

interface DocumentPreviewProps {
  document: DocumentPreviewData;
  open: boolean;
  onClose: () => void;
  onDownload?: (documentId: string) => void;
  className?: string;
}

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const getFormatIcon = (format: string) => {
  switch (format.toLowerCase()) {
    case 'pdf':
      return <FileText className="h-5 w-5 text-red-500" />;
    case 'tiff':
    case 'tif':
      return <FileText className="h-5 w-5 text-blue-500" />;
    case 'png':
    case 'jpeg':
    case 'jpg':
      return <Image className="h-5 w-5 text-green-500" />;
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

export function DocumentPreview({
  document,
  open,
  onClose,
  onDownload,
  className
}: DocumentPreviewProps) {
  const [currentView, setCurrentView] = useState<'thumbnail' | 'preview' | 'pages'>('thumbnail');
  const [currentPage, setCurrentPage] = useState(1);
  const [zoomLevel, setZoomLevel] = useState(100);
  const [isImageLoaded, setIsImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);

  const maxPages = document.metadata?.pageCount || 1;
  const hasMultiplePages = maxPages > 1;
  const pageNumbers = Object.keys(document.pagePreviews || {}).map(Number).sort((a, b) => a - b);

  const resetView = () => {
    setZoomLevel(100);
    setIsImageLoaded(false);
    setImageError(false);
  };

  const handleViewChange = (view: 'thumbnail' | 'preview' | 'pages') => {
    setCurrentView(view);
    setCurrentPage(1);
    resetView();
  };

  const handleNextPage = () => {
    if (currentPage < maxPages) {
      setCurrentPage(currentPage + 1);
      resetView();
    }
  };

  const handlePrevPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
      resetView();
    }
  };

  const handleZoomIn = () => {
    setZoomLevel(Math.min(zoomLevel + 25, 200));
  };

  const handleZoomOut = () => {
    setZoomLevel(Math.max(zoomLevel - 25, 50));
  };

  const getCurrentImageUrl = (): string | undefined => {
    let imageUrl: string | undefined;

    switch (currentView) {
      case 'thumbnail':
        imageUrl = document.thumbnails?.large || document.thumbnails?.medium || document.thumbnails?.small;
        break;
      case 'preview':
        imageUrl = document.previews?.large || document.previews?.medium || document.previews?.small;
        break;
      case 'pages':
        if (hasMultiplePages && document.pagePreviews?.[currentPage]) {
          imageUrl = document.pagePreviews[currentPage].large || 
                    document.pagePreviews[currentPage].medium || 
                    document.pagePreviews[currentPage].small;
        } else if (!hasMultiplePages) {
          imageUrl = document.previews?.large || document.previews?.medium || document.previews?.small;
        }
        break;
    }

    return imageUrl;
  };

  const currentImageUrl = getCurrentImageUrl();

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className={`max-w-6xl max-h-[90vh] overflow-hidden ${className}`}>
        <DialogHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <div className="flex items-center space-x-3">
            {getFormatIcon(document.format)}
            <div>
              <DialogTitle className="text-lg">Document Preview</DialogTitle>
              <div className="flex items-center space-x-2 mt-1">
                <Badge variant="secondary" className={getFormatBadgeColor(document.format)}>
                  {document.format.toUpperCase()}
                </Badge>
                {document.metadata?.confidence && (
                  <Badge variant="outline">
                    {Math.round(document.metadata.confidence * 100)}% confidence
                  </Badge>
                )}
              </div>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            {onDownload && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onDownload(document.documentId)}
              >
                <Download className="h-4 w-4 mr-1" />
                Download
              </Button>
            )}
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </DialogHeader>

        <div className="flex-1 overflow-hidden">
          <Tabs value={currentView} onValueChange={(value) => handleViewChange(value as any)} className="h-full">
            <div className="flex items-center justify-between mb-4">
              <TabsList>
                <TabsTrigger value="thumbnail">Thumbnails</TabsTrigger>
                <TabsTrigger value="preview">Preview</TabsTrigger>
                {hasMultiplePages && <TabsTrigger value="pages">Pages ({maxPages})</TabsTrigger>}
              </TabsList>

              {/* Page Navigation for multi-page documents */}
              {hasMultiplePages && currentView === 'pages' && (
                <div className="flex items-center space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handlePrevPage}
                    disabled={currentPage === 1}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <span className="text-sm text-gray-600 min-w-[80px] text-center">
                    Page {currentPage} of {maxPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleNextPage}
                    disabled={currentPage === maxPages}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              )}

              {/* Zoom Controls */}
              {currentImageUrl && currentView !== 'thumbnail' && (
                <div className="flex items-center space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleZoomOut}
                    disabled={zoomLevel <= 50}
                  >
                    <ZoomOut className="h-4 w-4" />
                  </Button>
                  <span className="text-sm text-gray-600 min-w-[50px] text-center">
                    {zoomLevel}%
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleZoomIn}
                    disabled={zoomLevel >= 200}
                  >
                    <ZoomIn className="h-4 w-4" />
                  </Button>
                </div>
              )}
            </div>

            {/* Validation Results */}
            {document.validationResults && (
              <Card className="mb-4">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm flex items-center">
                    <Info className="h-4 w-4 mr-1" />
                    Validation Results
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="flex flex-wrap gap-4 text-xs">
                    <div className="flex items-center space-x-1">
                      {document.validationResults.isValid ? (
                        <CheckCircle className="h-3 w-3 text-green-500" />
                      ) : (
                        <X className="h-3 w-3 text-red-500" />
                      )}
                      <span>Valid Format</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      {document.validationResults.isSafe ? (
                        <CheckCircle className="h-3 w-3 text-green-500" />
                      ) : (
                        <AlertTriangle className="h-3 w-3 text-red-500" />
                      )}
                      <span>Security Check</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      {document.validationResults.isProcessable ? (
                        <CheckCircle className="h-3 w-3 text-green-500" />
                      ) : (
                        <X className="h-3 w-3 text-red-500" />
                      )}
                      <span>Processing Ready</span>
                    </div>
                  </div>
                  
                  {document.validationResults.errors.length > 0 && (
                    <div className="mt-2 space-y-1">
                      <p className="text-xs font-medium text-red-700">Errors:</p>
                      {document.validationResults.errors.map((error, index) => (
                        <p key={index} className="text-xs text-red-600">• {error}</p>
                      ))}
                    </div>
                  )}
                  
                  {document.validationResults.warnings.length > 0 && (
                    <div className="mt-2 space-y-1">
                      <p className="text-xs font-medium text-yellow-700">Warnings:</p>
                      {document.validationResults.warnings.map((warning, index) => (
                        <p key={index} className="text-xs text-yellow-600">• {warning}</p>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            <TabsContent value="thumbnail" className="mt-0">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 max-h-[60vh] overflow-y-auto">
                {Object.entries(document.thumbnails || {}).map(([size, url]) => (
                  <div key={size} className="space-y-2">
                    <h4 className="text-sm font-medium capitalize">{size} Thumbnail</h4>
                    <div className="aspect-[4/3] bg-gray-100 rounded-lg overflow-hidden border">
                      {url ? (
                        <img
                          src={url}
                          alt={`${size} thumbnail`}
                          className="w-full h-full object-cover cursor-pointer hover:opacity-90"
                          onClick={() => setCurrentView('preview')}
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-gray-400">
                          <Image className="h-8 w-8" />
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="preview" className="mt-0">
              <div className="flex justify-center max-h-[60vh] overflow-auto bg-gray-50 rounded-lg">
                {currentImageUrl && !imageError ? (
                  <img
                    src={currentImageUrl}
                    alt="Document preview"
                    className="max-w-full h-auto transition-transform duration-200"
                    style={{ transform: `scale(${zoomLevel / 100})` }}
                    onLoad={() => setIsImageLoaded(true)}
                    onError={() => setImageError(true)}
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center p-8 text-gray-400">
                    <Eye className="h-12 w-12 mb-2" />
                    <p>Preview not available</p>
                    {imageError && (
                      <p className="text-sm text-red-500 mt-1">Failed to load preview image</p>
                    )}
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="pages" className="mt-0">
              <div className="flex justify-center max-h-[60vh] overflow-auto bg-gray-50 rounded-lg">
                {currentImageUrl && !imageError ? (
                  <img
                    src={currentImageUrl}
                    alt={`Page ${currentPage}`}
                    className="max-w-full h-auto transition-transform duration-200"
                    style={{ transform: `scale(${zoomLevel / 100})` }}
                    onLoad={() => setIsImageLoaded(true)}
                    onError={() => setImageError(true)}
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center p-8 text-gray-400">
                    <Eye className="h-12 w-12 mb-2" />
                    <p>Page preview not available</p>
                    {imageError && (
                      <p className="text-sm text-red-500 mt-1">Failed to load page image</p>
                    )}
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </div>

        {/* Document Information Panel */}
        {document.metadata && (
          <Card className="mt-4">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Document Information</CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                {document.metadata.fileSize && (
                  <div>
                    <p className="font-medium text-gray-700">File Size</p>
                    <p className="text-gray-600">{formatBytes(document.metadata.fileSize)}</p>
                  </div>
                )}
                {document.metadata.dimensions && (
                  <div>
                    <p className="font-medium text-gray-700">Dimensions</p>
                    <p className="text-gray-600">
                      {document.metadata.dimensions.width} × {document.metadata.dimensions.height}
                    </p>
                  </div>
                )}
                {document.metadata.pageCount && (
                  <div>
                    <p className="font-medium text-gray-700">Pages</p>
                    <p className="text-gray-600">{document.metadata.pageCount}</p>
                  </div>
                )}
                {document.metadata.processingStatus && (
                  <div>
                    <p className="font-medium text-gray-700">Status</p>
                    <p className="text-gray-600 capitalize">{document.metadata.processingStatus}</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default DocumentPreview;