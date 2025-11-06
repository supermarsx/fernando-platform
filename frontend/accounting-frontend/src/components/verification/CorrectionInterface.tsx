import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { Badge } from '../ui/badge';
import { Alert, AlertDescription } from '../ui/alert';

interface Correction {
  fieldName: string;
  originalValue: any;
  correctedValue: any;
  correctionType: string;
  reason: string;
}

interface CorrectionInterfaceProps {
  corrections: Correction[];
  comments: string;
  onCommentsChange: (comments: string) => void;
  onRemoveCorrection: (index: number) => void;
}

export function CorrectionInterface({
  corrections,
  comments,
  onCommentsChange,
  onRemoveCorrection
}: CorrectionInterfaceProps) {
  const formatValue = (value: any): string => {
    if (value === null || value === undefined) return '';
    if (typeof value === 'object') return JSON.stringify(value, null, 2);
    return String(value);
  };

  const getCorrectionTypeColor = (type: string) => {
    switch (type) {
      case 'correction': return 'default';
      case 'validation': return 'secondary';
      case 'formatting': return 'outline';
      default: return 'secondary';
    }
  };

  const getCorrectionTypeIcon = (type: string) => {
    switch (type) {
      case 'correction': return '✏️';
      case 'validation': return '✅';
      case 'formatting': return '🔧';
      default: return '📝';
    }
  };

  const calculateQualityImpact = () => {
    if (corrections.length === 0) return { score: 100, impact: 'none' };
    
    // Each correction reduces quality score
    const deduction = corrections.length * 5; // 5% per correction
    const score = Math.max(0, 100 - deduction);
    
    let impact = 'minimal';
    if (score >= 90) impact = 'excellent';
    else if (score >= 80) impact = 'good';
    else if (score >= 70) impact = 'acceptable';
    else if (score >= 60) impact = 'poor';
    else impact = 'critical';
    
    return { score, impact };
  };

  const qualityImpact = calculateQualityImpact();

  return (
    <div className="space-y-6">
      {/* Quality Impact Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center space-x-2">
            <span>Quality Impact</span>
            <Badge variant={qualityImpact.impact === 'excellent' ? 'default' : 'destructive'}>
              {qualityImpact.impact.toUpperCase()} ({qualityImpact.score}%)
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span>Corrections Made:</span>
              <Badge variant="outline">{corrections.length}</Badge>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full ${
                  qualityImpact.score >= 90 ? 'bg-green-500' :
                  qualityImpact.score >= 80 ? 'bg-yellow-500' :
                  qualityImpact.score >= 70 ? 'bg-orange-500' :
                  'bg-red-500'
                }`}
                style={{ width: `${qualityImpact.score}%` }}
              ></div>
            </div>
            <div className="text-xs text-gray-600">
              {qualityImpact.impact === 'excellent' && 'Minimal corrections - high quality extraction'}
              {qualityImpact.impact === 'good' && 'Few corrections - good extraction quality'}
              {qualityImpact.impact === 'acceptable' && 'Some corrections - acceptable quality'}
              {qualityImpact.impact === 'poor' && 'Many corrections - needs improvement'}
              {qualityImpact.impact === 'critical' && 'Too many corrections - major issues detected'}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Corrections List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Corrections Made</CardTitle>
        </CardHeader>
        <CardContent>
          {corrections.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              <div className="text-4xl mb-2">✅</div>
              <div>No corrections made</div>
              <div className="text-sm">All extracted data appears to be correct</div>
            </div>
          ) : (
            <div className="space-y-4">
              {corrections.map((correction, index) => (
                <div key={index} className="border border-gray-200 rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="font-medium capitalize">
                        {correction.fieldName.replace(/_/g, ' ')}
                      </span>
                      <Badge variant={getCorrectionTypeColor(correction.correctionType)}>
                        {getCorrectionTypeIcon(correction.correctionType)} {correction.correctionType}
                      </Badge>
                    </div>
                    <Button
                      onClick={() => onRemoveCorrection(index)}
                      size="sm"
                      variant="ghost"
                      className="h-6 w-6 p-0 text-gray-400 hover:text-red-500"
                    >
                      ✕
                    </Button>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <div className="text-gray-600 mb-1">Original Value:</div>
                      <code className="text-xs bg-gray-100 p-2 rounded block">
                        {formatValue(correction.originalValue)}
                      </code>
                    </div>
                    <div>
                      <div className="text-gray-600 mb-1">Corrected Value:</div>
                      <code className="text-xs bg-blue-50 p-2 rounded block">
                        {formatValue(correction.correctedValue)}
                      </code>
                    </div>
                  </div>
                  
                  <div>
                    <div className="text-gray-600 mb-1 text-sm">Reason for Correction:</div>
                    <div className="text-sm text-gray-800 bg-gray-50 p-2 rounded">
                      {correction.reason}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Comments Section */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Additional Comments</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Textarea
              value={comments}
              onChange={(e) => onCommentsChange(e.target.value)}
              placeholder="Add any additional comments about the verification process, document quality, or suggestions for improvement..."
              rows={4}
              className="text-sm"
            />
            <div className="text-xs text-gray-500 mt-1">
              {comments.length}/500 characters
            </div>
          </div>
          
          {corrections.length > 0 && (
            <Alert>
              <AlertDescription className="text-sm">
                <strong>Tip:</strong> Providing detailed comments helps improve the AI models and 
                overall system performance. Consider explaining why corrections were made and any 
                patterns you noticed.
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      {corrections.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Quick Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  // Copy corrections summary to clipboard
                  const summary = corrections.map(c => 
                    `${c.fieldName}: ${c.originalValue} → ${c.correctedValue} (${c.reason})`
                  ).join('\n');
                  navigator.clipboard.writeText(summary);
                }}
              >
                📋 Copy Summary
              </Button>
              
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  // Clear all corrections
                  corrections.forEach((_, index) => onRemoveCorrection(0)); // Remove from start to avoid index shift
                }}
              >
                🗑️ Clear All
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}