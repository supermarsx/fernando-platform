import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Alert, AlertDescription } from '../ui/alert';

interface SideBySideComparisonProps {
  documentId: string;
  documentType: string;
  extractedData: Record<string, any>;
  verifiedData: Record<string, any>;
  onFieldCorrection: (fieldName: string, originalValue: any, correctedValue: any, reason: string) => void;
  aiSuggestions: Record<string, any>;
  anomalies: AnomalyAlert[];
}

interface AnomalyAlert {
  field: string;
  type: string;
  severity: 'low' | 'medium' | 'high';
  value: any;
  description: string;
}

interface FieldSuggestion {
  type: string;
  suggestion: string;
  confidence: number;
  reasoning: string;
}

export function SideBySideComparison({
  documentId,
  documentType,
  extractedData,
  verifiedData,
  onFieldCorrection,
  aiSuggestions,
  anomalies
}: SideBySideComparisonProps) {
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<any>('');
  const [editReason, setEditReason] = useState('');

  const handleEditField = (fieldName: string, currentValue: any) => {
    setEditingField(fieldName);
    setEditValue(currentValue);
    setEditReason('');
  };

  const handleSaveEdit = () => {
    if (editingField && editReason.trim()) {
      const originalValue = extractedData[editingField];
      onFieldCorrection(editingField, originalValue, editValue, editReason.trim());
    }
    setEditingField(null);
    setEditValue('');
    setEditReason('');
  };

  const handleCancelEdit = () => {
    setEditingField(null);
    setEditValue('');
    setEditReason('');
  };

  const formatValue = (value: any): string => {
    if (value === null || value === undefined) return '';
    if (typeof value === 'object') return JSON.stringify(value, null, 2);
    return String(value);
  };

  const getFieldSuggestions = (fieldName: string): FieldSuggestion[] => {
    return aiSuggestions[fieldName] || [];
  };

  const getAnomalyForField = (fieldName: string): AnomalyAlert | null => {
    return anomalies.find(anomaly => anomaly.field === fieldName) || null;
  };

  const getFieldType = (fieldName: string): string => {
    const fieldTypes: Record<string, string> = {
      'amount': 'number',
      'total': 'number',
      'subtotal': 'number',
      'tax_amount': 'number',
      'date': 'date',
      'invoice_date': 'date',
      'due_date': 'date',
      'percentage': 'number',
      'tax_rate': 'number'
    };
    return fieldTypes[fieldName] || 'text';
  };

  const renderFieldValue = (fieldName: string, value: any, isEditable: boolean = true) => {
    const originalValue = extractedData[fieldName];
    const verifiedValue = verifiedData[fieldName];
    const currentValue = verifiedValue !== undefined ? verifiedValue : originalValue;
    
    const hasCorrection = verifiedValue !== undefined && verifiedValue !== originalValue;
    const anomaly = getAnomalyForField(fieldName);
    const suggestions = getFieldSuggestions(fieldName);

    if (editingField === fieldName) {
      return (
        <div className="space-y-2">
          <Input
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            type={getFieldType(fieldName)}
            className="text-sm"
          />
          <div className="space-y-2">
            <Label htmlFor="edit-reason" className="text-xs">Correction Reason:</Label>
            <Input
              id="edit-reason"
              value={editReason}
              onChange={(e) => setEditReason(e.target.value)}
              placeholder="Explain the correction..."
              className="text-xs"
            />
          </div>
          <div className="flex space-x-2">
            <Button onClick={handleSaveEdit} size="sm" variant="default">
              Save
            </Button>
            <Button onClick={handleCancelEdit} size="sm" variant="outline">
              Cancel
            </Button>
          </div>
        </div>
      );
    }

    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <code className={`text-sm ${hasCorrection ? 'text-blue-600 font-semibold' : ''}`}>
            {formatValue(currentValue)}
          </code>
          {isEditable && (
            <Button
              onClick={() => handleEditField(fieldName, currentValue)}
              size="sm"
              variant="ghost"
              className="h-6 w-6 p-0"
            >
              ✏️
            </Button>
          )}
        </div>
        
        {hasCorrection && (
          <div className="text-xs text-gray-600">
            <span className="font-medium">Original:</span> {formatValue(originalValue)}
          </div>
        )}
        
        {anomaly && (
          <Alert className="mt-2">
            <AlertDescription className="text-xs">
              <div className="flex items-center space-x-2">
                <Badge variant={anomaly.severity === 'high' ? 'destructive' : 'default'} className="text-xs">
                  {anomaly.severity.toUpperCase()}
                </Badge>
                <span>{anomaly.description}</span>
              </div>
            </AlertDescription>
          </Alert>
        )}
        
        {suggestions.length > 0 && (
          <div className="mt-2 space-y-1">
            <div className="text-xs font-medium text-gray-700">AI Suggestions:</div>
            {suggestions.map((suggestion, index) => (
              <div key={index} className="text-xs text-gray-600 p-2 bg-gray-50 rounded">
                <div className="flex items-center justify-between">
                  <span>{suggestion.suggestion}</span>
                  <Badge variant="outline" className="text-xs">
                    {Math.round(suggestion.confidence * 100)}%
                  </Badge>
                </div>
                <div className="text-gray-500 mt-1">{suggestion.reasoning}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  const renderDocumentPreview = () => (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Document Preview</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="border-2 border-dashed border-gray-300 rounded-lg h-64 flex items-center justify-center bg-gray-50">
            <div className="text-center">
              <div className="text-gray-500 mb-2">📄</div>
              <div className="text-sm text-gray-600">Document Preview</div>
              <div className="text-xs text-gray-500">Document ID: {documentId}</div>
              <div className="text-xs text-gray-500">Type: {documentType}</div>
            </div>
          </div>
          <div className="text-xs text-gray-500">
            <p>Original document would be displayed here</p>
            <p>This would include image preview, PDF viewer, or document content</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );

  const renderExtractedData = () => {
    const sortedFields = Object.keys(extractedData).sort();

    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Extracted Data</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="fields" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="fields">Field View</TabsTrigger>
              <TabsTrigger value="form">Form View</TabsTrigger>
            </TabsList>
            
            <TabsContent value="fields" className="space-y-3">
              {sortedFields.map((fieldName) => (
                <div key={fieldName} className="border-b border-gray-200 pb-3">
                  <div className="flex items-center justify-between mb-2">
                    <Label className="font-medium text-sm capitalize">
                      {fieldName.replace(/_/g, ' ')}
                    </Label>
                  </div>
                  {renderFieldValue(fieldName, extractedData[fieldName])}
                </div>
              ))}
            </TabsContent>
            
            <TabsContent value="form">
              <div className="space-y-4">
                {sortedFields.map((fieldName) => (
                  <div key={fieldName} className="space-y-2">
                    <Label className="font-medium text-sm capitalize">
                      {fieldName.replace(/_/g, ' ')}:
                    </Label>
                    {renderFieldValue(fieldName, extractedData[fieldName])}
                  </div>
                ))}
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="space-y-6">
      <Tabs defaultValue="comparison" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="comparison">Side-by-Side</TabsTrigger>
          <TabsTrigger value="document">Document</TabsTrigger>
          <TabsTrigger value="extracted">Extracted Data</TabsTrigger>
        </TabsList>
        
        <TabsContent value="comparison" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {renderDocumentPreview()}
            {renderExtractedData()}
          </div>
        </TabsContent>
        
        <TabsContent value="document">
          {renderDocumentPreview()}
        </TabsContent>
        
        <TabsContent value="extracted">
          {renderExtractedData()}
        </TabsContent>
      </Tabs>
    </div>
  );
}