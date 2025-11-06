import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { Alert, AlertDescription } from '../ui/alert';

interface QualityMetricsProps {
  aiConfidence: number;
  corrections: Correction[];
  processingTime: number;
  anomalies: AnomalyAlert[];
}

interface Correction {
  fieldName: string;
  originalValue: any;
  correctedValue: any;
  correctionType: string;
  reason: string;
}

interface AnomalyAlert {
  field: string;
  type: string;
  severity: 'low' | 'medium' | 'high';
  value: any;
  description: string;
}

export function QualityMetrics({
  aiConfidence,
  corrections,
  processingTime,
  anomalies
}: QualityMetricsProps) {
  const calculateOverallQuality = () => {
    // Base confidence from AI
    let qualityScore = aiConfidence * 100;
    
    // Deduct for corrections
    const correctionPenalty = corrections.length * 8; // 8% penalty per correction
    qualityScore -= correctionPenalty;
    
    // Deduct for anomalies
    const anomalyPenalty = anomalies.reduce((penalty, anomaly) => {
      switch (anomaly.severity) {
        case 'high': return penalty + 15;
        case 'medium': return penalty + 8;
        case 'low': return penalty + 3;
        default: return penalty;
      }
    }, 0);
    qualityScore -= anomalyPenalty;
    
    // Time factor (faster processing = higher quality, up to a point)
    const optimalTime = 300; // 5 minutes
    const timePenalty = Math.max(0, (processingTime - optimalTime) / optimalTime * 5);
    qualityScore -= timePenalty;
    
    return Math.max(0, Math.min(100, qualityScore));
  };

  const getQualityGrade = (score: number) => {
    if (score >= 95) return { grade: 'A+', color: 'text-green-600', bg: 'bg-green-100' };
    if (score >= 90) return { grade: 'A', color: 'text-green-600', bg: 'bg-green-100' };
    if (score >= 85) return { grade: 'B+', color: 'text-blue-600', bg: 'bg-blue-100' };
    if (score >= 80) return { grade: 'B', color: 'text-blue-600', bg: 'bg-blue-100' };
    if (score >= 75) return { grade: 'C+', color: 'text-yellow-600', bg: 'bg-yellow-100' };
    if (score >= 70) return { grade: 'C', color: 'text-yellow-600', bg: 'bg-yellow-100' };
    if (score >= 60) return { grade: 'D', color: 'text-orange-600', bg: 'bg-orange-100' };
    return { grade: 'F', color: 'text-red-600', bg: 'bg-red-100' };
  };

  const getConfidenceLevel = (confidence: number) => {
    if (confidence >= 0.9) return { level: 'Very High', color: 'text-green-600' };
    if (confidence >= 0.8) return { level: 'High', color: 'text-green-600' };
    if (confidence >= 0.7) return { level: 'Medium', color: 'text-yellow-600' };
    if (confidence >= 0.6) return { level: 'Low', color: 'text-orange-600' };
    return { level: 'Very Low', color: 'text-red-600' };
  };

  const formatProcessingTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  const getAnomalySummary = () => {
    const high = anomalies.filter(a => a.severity === 'high').length;
    const medium = anomalies.filter(a => a.severity === 'medium').length;
    const low = anomalies.filter(a => a.severity === 'low').length;
    return { high, medium, low, total: anomalies.length };
  };

  const getCorrectionSummary = () => {
    const types = corrections.reduce((acc, correction) => {
      acc[correction.correctionType] = (acc[correction.correctionType] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    return types;
  };

  const overallQuality = calculateOverallQuality();
  const qualityGrade = getQualityGrade(overallQuality);
  const confidenceLevel = getConfidenceLevel(aiConfidence);
  const anomalySummary = getAnomalySummary();
  const correctionSummary = getCorrectionSummary();

  return (
    <div className="space-y-4">
      {/* Overall Quality Score */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Overall Quality</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="text-center">
            <div className={`text-4xl font-bold ${qualityGrade.color} mb-2`}>
              {qualityGrade.grade}
            </div>
            <div className="text-2xl font-semibold mb-2">
              {Math.round(overallQuality)}%
            </div>
            <Progress value={overallQuality} className="w-full" />
          </div>
          
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-gray-600">AI Confidence</div>
              <div className={`font-medium ${confidenceLevel.color}`}>
                {Math.round(aiConfidence * 100)}% ({confidenceLevel.level})
              </div>
            </div>
            <div>
              <div className="text-gray-600">Processing Time</div>
              <div className="font-medium">
                {formatProcessingTime(processingTime)}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* AI Confidence Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">AI Confidence Analysis</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Overall Confidence</span>
              <span className={confidenceLevel.color}>
                {Math.round(aiConfidence * 100)}%
              </span>
            </div>
            <Progress value={aiConfidence * 100} />
          </div>
          
          {aiConfidence < 0.7 && (
            <Alert>
              <AlertDescription className="text-xs">
                <strong>Low Confidence:</strong> This extraction has relatively low AI confidence. 
                Human verification is especially important.
              </AlertDescription>
            </Alert>
          )}
          
          {aiConfidence >= 0.9 && corrections.length === 0 && (
            <Alert>
              <AlertDescription className="text-xs">
                <strong>High Confidence:</strong> Excellent AI extraction with no corrections needed.
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Anomaly Detection */}
      {anomalies.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">
              Anomalies Detected ({anomalySummary.total})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="p-2 bg-red-100 rounded">
                <div className="text-lg font-bold text-red-600">{anomalySummary.high}</div>
                <div className="text-xs text-red-600">High</div>
              </div>
              <div className="p-2 bg-yellow-100 rounded">
                <div className="text-lg font-bold text-yellow-600">{anomalySummary.medium}</div>
                <div className="text-xs text-yellow-600">Medium</div>
              </div>
              <div className="p-2 bg-blue-100 rounded">
                <div className="text-lg font-bold text-blue-600">{anomalySummary.low}</div>
                <div className="text-xs text-blue-600">Low</div>
              </div>
            </div>
            
            <div className="space-y-2">
              {anomalies.slice(0, 3).map((anomaly, index) => (
                <div key={index} className="text-xs p-2 bg-gray-50 rounded">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium">{anomaly.field}</span>
                    <Badge variant={anomaly.severity === 'high' ? 'destructive' : 'default'}>
                      {anomaly.severity}
                    </Badge>
                  </div>
                  <div className="text-gray-600">{anomaly.description}</div>
                </div>
              ))}
              
              {anomalies.length > 3 && (
                <div className="text-xs text-gray-500 text-center">
                  +{anomalies.length - 3} more anomalies
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Corrections Analysis */}
      {corrections.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">
              Corrections Made ({corrections.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-2">
              {Object.entries(correctionSummary).map(([type, count]) => (
                <div key={type} className="flex justify-between text-sm">
                  <span className="capitalize">{type}</span>
                  <div className="flex items-center space-x-2">
                    <Badge variant="outline">{count}</Badge>
                    <Progress 
                      value={(count / corrections.length) * 100} 
                      className="w-16 h-2" 
                    />
                  </div>
                </div>
              ))}
            </div>
            
            <div className="text-xs text-gray-600">
              Most corrections in: {corrections.length > 0 ? 
                corrections.reduce((acc, curr) => {
                  acc[curr.fieldName] = (acc[curr.fieldName] || 0) + 1;
                  return acc;
                }, {} as Record<string, number>) && 
                Object.entries(corrections.reduce((acc, curr) => {
                  acc[curr.fieldName] = (acc[curr.fieldName] || 0) + 1;
                  return acc;
                }, {} as Record<string, number>))
                  .sort(([,a], [,b]) => b - a)[0][0].replace(/_/g, ' ')
                : 'None'
              }
            </div>
          </CardContent>
        </Card>
      )}

      {/* Performance Indicators */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Performance Indicators</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-gray-600">Accuracy Rate</div>
              <div className="font-medium">
                {Math.round((1 - corrections.length / Math.max(Object.keys(corrections).length || 1, 1)) * 100)}%
              </div>
            </div>
            <div>
              <div className="text-gray-600">Efficiency</div>
              <div className="font-medium">
                {processingTime < 300 ? 'Excellent' : 
                 processingTime < 600 ? 'Good' : 
                 processingTime < 900 ? 'Average' : 'Slow'}
              </div>
            </div>
          </div>
          
          {overallQuality >= 85 && (
            <div className="text-xs text-green-600 bg-green-50 p-2 rounded">
              ✅ Excellent quality work! This verification meets high standards.
            </div>
          )}
          
          {overallQuality < 70 && (
            <div className="text-xs text-red-600 bg-red-50 p-2 rounded">
              ⚠️ Quality below standard. Consider additional review.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}