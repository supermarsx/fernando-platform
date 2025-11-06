import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { LoadingSpinner } from '../ui/loading-spinner';
import { SideBySideComparison } from './SideBySideComparison';
import { CorrectionInterface } from './CorrectionInterface';
import { QualityMetrics } from './QualityMetrics';
import { VerificationQueue } from './VerificationQueue';
import { toast } from '../ui/toast';

interface DocumentVerificationProps {
  taskId: string;
  onComplete: (result: VerificationResult) => void;
  onReject: (reason: string) => void;
}

interface VerificationResult {
  verifiedData: Record<string, any>;
  corrections: Correction[];
  comments: string;
  qualityScore: QualityScore;
  timeSpent: number;
}

interface Correction {
  fieldName: string;
  originalValue: any;
  correctedValue: any;
  correctionType: string;
  reason: string;
}

interface TaskData {
  taskId: string;
  documentId: string;
  documentType: string;
  extractedData: Record<string, any>;
  aiConfidence: number;
  aiSuggestions: Record<string, any>;
  anomalies: AnomalyAlert[];
  priority: string;
  status: string;
  assignedAt: string;
  dueDate: string;
}

interface AnomalyAlert {
  field: string;
  type: string;
  severity: 'low' | 'medium' | 'high';
  value: any;
  description: string;
}

type QualityScore = 'excellent' | 'good' | 'acceptable' | 'poor';

export function DocumentVerification({ taskId, onComplete, onReject }: DocumentVerificationProps) {
  const [taskData, setTaskData] = useState<TaskData | null>(null);
  const [loading, setLoading] = useState(true);
  const [verifiedData, setVerifiedData] = useState<Record<string, any>>({});
  const [corrections, setCorrections] = useState<Correction[]>([]);
  const [comments, setComments] = useState('');
  const [qualityScore, setQualityScore] = useState<QualityScore>('acceptable');
  const [startTime] = useState(Date.now());
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    loadTaskData();
  }, [taskId]);

  const loadTaskData = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/verification/tasks/${taskId}`);
      if (!response.ok) throw new Error('Failed to load task data');
      
      const data = await response.json();
      setTaskData(data);
      setVerifiedData(data.extractedData || {});
    } catch (error) {
      console.error('Error loading task data:', error);
      toast({
        title: "Error",
        description: "Failed to load verification task data",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleFieldCorrection = (fieldName: string, originalValue: any, correctedValue: any, reason: string) => {
    const correctionType = originalValue !== correctedValue ? 'correction' : 'validation';
    
    const correction: Correction = {
      fieldName,
      originalValue,
      correctedValue,
      correctionType,
      reason
    };

    setCorrections(prev => {
      const filtered = prev.filter(c => c.fieldName !== fieldName);
      return [...filtered, correction];
    });

    // Update verified data
    setVerifiedData(prev => ({
      ...prev,
      [fieldName]: correctedValue
    }));
  };

  const handleCompleteVerification = async () => {
    if (!taskData) return;

    try {
      setIsSubmitting(true);

      // Calculate quality score based on corrections and confidence
      const aiConfidence = taskData.aiConfidence || 0.8;
      const correctionPenalty = corrections.length * 0.05;
      const accuracy = Math.max(0, aiConfidence - correctionPenalty);
      
      let quality: QualityScore = 'poor';
      if (accuracy >= 0.95) quality = 'excellent';
      else if (accuracy >= 0.85) quality = 'good';
      else if (accuracy >= 0.70) quality = 'acceptable';

      setQualityScore(quality);

      const result: VerificationResult = {
        verifiedData,
        corrections,
        comments,
        qualityScore: quality,
        timeSpent: Math.floor((Date.now() - startTime) / 1000)
      };

      const response = await fetch(`/api/verification/tasks/${taskId}/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(result)
      });

      if (!response.ok) throw new Error('Failed to complete verification');

      toast({
        title: "Verification Completed",
        description: `Task completed with ${quality} quality score`,
        variant: "default"
      });

      onComplete(result);
    } catch (error) {
      console.error('Error completing verification:', error);
      toast({
        title: "Error",
        description: "Failed to complete verification",
        variant: "destructive"
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRejectVerification = async () => {
    const reason = prompt('Please provide a reason for rejection:');
    if (!reason) return;

    try {
      const response = await fetch(`/api/verification/tasks/${taskId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason })
      });

      if (!response.ok) throw new Error('Failed to reject verification');

      toast({
        title: "Verification Rejected",
        description: "Task has been rejected",
        variant: "default"
      });

      onReject(reason);
    } catch (error) {
      console.error('Error rejecting verification:', error);
      toast({
        title: "Error",
        description: "Failed to reject verification",
        variant: "destructive"
      });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <LoadingSpinner />
        <span className="ml-2">Loading verification task...</span>
      </div>
    );
  }

  if (!taskData) {
    return (
      <div className="text-center p-8">
        <h2 className="text-xl font-semibold text-gray-900">Task not found</h2>
        <p className="text-gray-600 mt-2">The verification task could not be loaded.</p>
      </div>
    );
  }

  const timeElapsed = Math.floor((Date.now() - startTime) / 1000);
  const timeRemaining = Math.max(0, new Date(taskData.dueDate).getTime() - Date.now());
  const hoursRemaining = Math.floor(timeRemaining / (1000 * 60 * 60));
  const minutesRemaining = Math.floor((timeRemaining % (1000 * 60 * 60)) / (1000 * 60));

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical': return 'destructive';
      case 'urgent': return 'destructive';
      case 'high': return 'default';
      default: return 'secondary';
    }
  };

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Task Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-2xl">Document Verification</CardTitle>
              <p className="text-gray-600 mt-1">Task ID: {taskData.taskId}</p>
            </div>
            <div className="flex items-center space-x-4">
              <Badge variant={getPriorityColor(taskData.priority)}>
                {taskData.priority.toUpperCase()}
              </Badge>
              <div className="text-sm text-gray-600">
                <div>Time Elapsed: {Math.floor(timeElapsed / 60)}m {timeElapsed % 60}s</div>
                {hoursRemaining > 0 && (
                  <div>Time Remaining: {hoursRemaining}h {minutesRemaining}m</div>
                )}
              </div>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Main Verification Interface */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Panel - Document and Comparison */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Document Review</CardTitle>
            </CardHeader>
            <CardContent>
              <SideBySideComparison
                documentId={taskData.documentId}
                documentType={taskData.documentType}
                extractedData={taskData.extractedData}
                verifiedData={verifiedData}
                onFieldCorrection={handleFieldCorrection}
                aiSuggestions={taskData.aiSuggestions}
                anomalies={taskData.anomalies}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Corrections & Comments</CardTitle>
            </CardHeader>
            <CardContent>
              <CorrectionInterface
                corrections={corrections}
                comments={comments}
                onCommentsChange={setComments}
                onRemoveCorrection={(index) => {
                  setCorrections(prev => prev.filter((_, i) => i !== index));
                }}
              />
            </CardContent>
          </Card>
        </div>

        {/* Right Panel - Quality Metrics and Actions */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Quality Metrics</CardTitle>
            </CardHeader>
            <CardContent>
              <QualityMetrics
                aiConfidence={taskData.aiConfidence}
                corrections={corrections}
                processingTime={timeElapsed}
                anomalies={taskData.anomalies}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Verification Queue</CardTitle>
            </CardHeader>
            <CardContent>
              <VerificationQueue
                currentTaskId={taskData.taskId}
                showCurrentTask={false}
              />
            </CardContent>
          </Card>

          {/* Action Buttons */}
          <Card>
            <CardHeader>
              <CardTitle>Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button
                onClick={handleCompleteVerification}
                disabled={isSubmitting}
                className="w-full"
                variant="default"
              >
                {isSubmitting ? (
                  <>
                    <LoadingSpinner className="mr-2 h-4 w-4" />
                    Submitting...
                  </>
                ) : (
                  'Complete Verification'
                )}
              </Button>
              
              <Button
                onClick={handleRejectVerification}
                disabled={isSubmitting}
                className="w-full"
                variant="destructive"
              >
                Reject Verification
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}