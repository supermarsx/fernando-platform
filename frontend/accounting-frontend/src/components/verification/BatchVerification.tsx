import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Checkbox } from '../ui/checkbox';
import { Progress } from '../ui/progress';
import { LoadingSpinner } from '../ui/loading-spinner';
import { toast } from '../ui/toast';

interface BatchVerificationProps {
  onComplete: () => void;
}

interface BatchTask {
  taskId: string;
  documentId: string;
  documentType: string;
  priority: string;
  aiConfidence: number;
  estimatedTime: number;
  hasAnomalies: boolean;
  selected: boolean;
}

interface BatchProgress {
  totalSelected: number;
  completed: number;
  current: string | null;
  errors: number;
  timeRemaining: number;
}

export function BatchVerification({ onComplete }: BatchVerificationProps) {
  const [availableTasks, setAvailableTasks] = useState<BatchTask[]>([]);
  const [selectedTasks, setSelectedTasks] = useState<string[]>([]);
  const [batchProgress, setBatchProgress] = useState<BatchProgress>({
    totalSelected: 0,
    completed: 0,
    current: null,
    errors: 0,
    timeRemaining: 0
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAvailableTasks();
  }, []);

  const loadAvailableTasks = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/verification/batch/available');
      if (!response.ok) throw new Error('Failed to load available tasks');
      
      const data = await response.json();
      setAvailableTasks(data.tasks.map((task: BatchTask) => ({ ...task, selected: false })));
    } catch (error) {
      console.error('Error loading tasks:', error);
      toast({
        title: "Error",
        description: "Failed to load available tasks for batch processing",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleTaskSelect = (taskId: string, selected: boolean) => {
    setAvailableTasks(prev =>
      prev.map(task =>
        task.taskId === taskId ? { ...task, selected } : task
      )
    );

    setSelectedTasks(prev =>
      selected
        ? [...prev, taskId]
        : prev.filter(id => id !== taskId)
    );
  };

  const handleSelectAll = () => {
    const allTaskIds = availableTasks.map(task => task.taskId);
    const allSelected = allTaskIds.every(id => selectedTasks.includes(id));
    
    if (allSelected) {
      // Deselect all
      setSelectedTasks([]);
      setAvailableTasks(prev => prev.map(task => ({ ...task, selected: false })));
    } else {
      // Select all
      setSelectedTasks(allTaskIds);
      setAvailableTasks(prev => prev.map(task => ({ ...task, selected: true })));
    }
  };

  const estimateTotalTime = () => {
    const selectedTasksData = availableTasks.filter(task => selectedTasks.includes(task.taskId));
    const totalTime = selectedTasksData.reduce((sum, task) => sum + task.estimatedTime, 0);
    return totalTime;
  };

  const getAverageConfidence = () => {
    if (selectedTasks.length === 0) return 0;
    const selectedTasksData = availableTasks.filter(task => selectedTasks.includes(task.taskId));
    const totalConfidence = selectedTasksData.reduce((sum, task) => sum + task.aiConfidence, 0);
    return totalConfidence / selectedTasksData.length;
  };

  const startBatchProcessing = async () => {
    if (selectedTasks.length === 0) {
      toast({
        title: "No Tasks Selected",
        description: "Please select at least one task for batch processing",
        variant: "destructive"
      });
      return;
    }

    try {
      setIsProcessing(true);
      
      const estimatedTime = estimateTotalTime();
      setBatchProgress({
        totalSelected: selectedTasks.length,
        completed: 0,
        current: null,
        errors: 0,
        timeRemaining: estimatedTime
      });

      const response = await fetch('/api/verification/batch/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          taskIds: selectedTasks,
          batchOptions: {
            autoApprove: false,
            maxConcurrent: 3,
            pauseOnError: true
          }
        })
      });

      if (!response.ok) throw new Error('Failed to start batch processing');

      const result = await response.json();
      
      // Simulate batch processing progress
      await simulateBatchProcessing(selectedTasks);

    } catch (error) {
      console.error('Error starting batch processing:', error);
      toast({
        title: "Error",
        description: "Failed to start batch processing",
        variant: "destructive"
      });
    } finally {
      setIsProcessing(false);
      setBatchProgress({
        totalSelected: 0,
        completed: 0,
        current: null,
        errors: 0,
        timeRemaining: 0
      });
      setSelectedTasks([]);
    }
  };

  const simulateBatchProcessing = async (taskIds: string[]) => {
    for (let i = 0; i < taskIds.length; i++) {
      setBatchProgress(prev => ({
        ...prev,
        current: taskIds[i],
        timeRemaining: prev.timeRemaining - 60 // Reduce remaining time
      }));

      // Simulate processing time (2-5 minutes per task)
      await new Promise(resolve => setTimeout(resolve, 2000));

      setBatchProgress(prev => ({
        ...prev,
        completed: prev.completed + 1,
        current: null
      }));
    }

    toast({
      title: "Batch Processing Complete",
      description: `Successfully processed ${taskIds.length} verification tasks`,
      variant: "default"
    });

    onComplete();
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical': return 'destructive';
      case 'urgent': return 'destructive';
      case 'high': return 'default';
      case 'normal': return 'secondary';
      case 'low': return 'outline';
      default: return 'secondary';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'text-green-600';
    if (confidence >= 0.7) return 'text-yellow-600';
    return 'text-red-600';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <LoadingSpinner />
        <span className="ml-2">Loading available tasks...</span>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Batch Processing Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-2xl">Batch Verification</CardTitle>
              <p className="text-gray-600 mt-1">
                Process multiple verification tasks efficiently
              </p>
            </div>
            <div className="text-right">
              <div className="text-sm text-gray-600">
                {availableTasks.length} tasks available
              </div>
              <div className="text-2xl font-bold text-blue-600">
                {selectedTasks.length} selected
              </div>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Batch Summary */}
      {selectedTasks.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Batch Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <div className="text-sm text-gray-600">Selected Tasks</div>
                <div className="text-2xl font-bold">{selectedTasks.length}</div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Estimated Time</div>
                <div className="text-2xl font-bold">
                  {Math.floor(estimateTotalTime() / 60)}m {estimateTotalTime() % 60}s
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Average Confidence</div>
                <div className={`text-2xl font-bold ${getConfidenceColor(getAverageConfidence())}`}>
                  {Math.round(getAverageConfidence() * 100)}%
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Priority Tasks</div>
                <div className="text-2xl font-bold">
                  {availableTasks.filter(task => 
                    selectedTasks.includes(task.taskId) && 
                    ['urgent', 'critical', 'high'].includes(task.priority)
                  ).length}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Progress Section */}
      {isProcessing && batchProgress.totalSelected > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Batch Processing Progress</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between text-sm">
              <span>Progress</span>
              <span>{batchProgress.completed} / {batchProgress.totalSelected}</span>
            </div>
            <Progress value={(batchProgress.completed / batchProgress.totalSelected) * 100} />
            
            {batchProgress.current && (
              <div className="text-center">
                <div className="text-sm text-gray-600">Currently processing:</div>
                <div className="font-medium">{batchProgress.current}</div>
              </div>
            )}
            
            {batchProgress.timeRemaining > 0 && (
              <div className="text-center text-sm text-gray-600">
                Estimated time remaining: {Math.floor(batchProgress.timeRemaining / 60)}m {batchProgress.timeRemaining % 60}s
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Task Selection */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Available Tasks</CardTitle>
            <div className="flex space-x-2">
              <Button onClick={handleSelectAll} variant="outline" size="sm">
                {selectedTasks.length === availableTasks.length ? 'Deselect All' : 'Select All'}
              </Button>
              <Button
                onClick={startBatchProcessing}
                disabled={selectedTasks.length === 0 || isProcessing}
                variant="default"
              >
                {isProcessing ? (
                  <>
                    <LoadingSpinner className="mr-2 h-4 w-4" />
                    Processing...
                  </>
                ) : (
                  `Start Batch Processing (${selectedTasks.length})`
                )}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {availableTasks.length === 0 ? (
              <div className="text-center text-gray-500 py-12">
                <div className="text-4xl mb-4">📋</div>
                <div className="text-lg font-medium">No tasks available</div>
                <div className="text-sm">All tasks are currently being processed or assigned</div>
              </div>
            ) : (
              availableTasks.map((task) => (
                <div
                  key={task.taskId}
                  className={`border rounded-lg p-4 ${
                    task.selected ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                  }`}
                >
                  <div className="flex items-center space-x-4">
                    <Checkbox
                      checked={task.selected}
                      onCheckedChange={(checked) => 
                        handleTaskSelect(task.taskId, checked as boolean)
                      }
                      disabled={isProcessing}
                    />
                    
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <div className="font-medium">{task.documentId}</div>
                        <div className="flex items-center space-x-2">
                          <Badge variant={getPriorityColor(task.priority)}>
                            {task.priority}
                          </Badge>
                          {task.hasAnomalies && (
                            <Badge variant="destructive">⚠️ Anomaly</Badge>
                          )}
                        </div>
                      </div>
                      
                      <div className="flex items-center justify-between mt-2 text-sm text-gray-600">
                        <div>
                          <span>Type: {task.documentType}</span>
                          <span className={`ml-4 ${getConfidenceColor(task.aiConfidence)}`}>
                            AI: {Math.round(task.aiConfidence * 100)}%
                          </span>
                        </div>
                        <div>
                          Est. Time: {Math.floor(task.estimatedTime / 60)}m {task.estimatedTime % 60}s
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Batch Processing Guidelines */}
      <Card>
        <CardHeader>
          <CardTitle>Batch Processing Guidelines</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 text-sm">
            <div className="flex items-center space-x-2">
              <span>✅</span>
              <span>Maximum 20 tasks per batch for optimal performance</span>
            </div>
            <div className="flex items-center space-x-2">
              <span>✅</span>
              <span>Tasks with similar document types process more efficiently</span>
            </div>
            <div className="flex items-center space-x-2">
              <span>✅</span>
              <span>High confidence extractions require less manual review</span>
            </div>
            <div className="flex items-center space-x-2">
              <span>⚠️</span>
              <span>Tasks with anomalies or low confidence may need individual attention</span>
            </div>
            <div className="flex items-center space-x-2">
              <span>⚠️</span>
              <span>Batch processing cannot be paused once started</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}