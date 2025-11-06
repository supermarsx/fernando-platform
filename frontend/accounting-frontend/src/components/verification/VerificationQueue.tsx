import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { LoadingSpinner } from '../ui/loading-spinner';
import { toast } from '../ui/toast';

interface VerificationQueueProps {
  currentTaskId?: string;
  showCurrentTask?: boolean;
  onTaskSelect?: (taskId: string) => void;
}

interface QueueTask {
  taskId: string;
  documentId: string;
  documentType: string;
  priority: string;
  status: string;
  assignedAt: string;
  dueDate: string;
  aiConfidence: number;
  estimatedProcessingTime: number;
  hasAnomalies: boolean;
  assignedTo?: string;
}

interface QueueStats {
  totalTasks: number;
  pendingTasks: number;
  inProgressTasks: number;
  overdueTasks: number;
  averageProcessingTime: number;
  myTasksCount: number;
}

export function VerificationQueue({ 
  currentTaskId, 
  showCurrentTask = true,
  onTaskSelect 
}: VerificationQueueProps) {
  const [tasks, setTasks] = useState<QueueTask[]>([]);
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'pending' | 'in_progress' | 'urgent'>('all');

  useEffect(() => {
    loadQueueData();
    // Refresh queue data every 30 seconds
    const interval = setInterval(loadQueueData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadQueueData = async () => {
    try {
      setLoading(true);
      
      // Load queue tasks
      const tasksResponse = await fetch(`/api/verification/queue?filter=${filter}`);
      if (!tasksResponse.ok) throw new Error('Failed to load queue tasks');
      const tasksData = await tasksResponse.json();
      
      // Load queue statistics
      const statsResponse = await fetch('/api/verification/queue/stats');
      if (!statsResponse.ok) throw new Error('Failed to load queue stats');
      const statsData = await statsResponse.json();
      
      setTasks(tasksData.tasks || []);
      setStats(statsData);
    } catch (error) {
      console.error('Error loading queue data:', error);
      toast({
        title: "Error",
        description: "Failed to load verification queue",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleTaskSelect = async (taskId: string) => {
    if (onTaskSelect) {
      onTaskSelect(taskId);
    }
  };

  const handleAssignTask = async (taskId: string) => {
    try {
      const response = await fetch(`/api/verification/tasks/${taskId}/assign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (!response.ok) throw new Error('Failed to assign task');

      toast({
        title: "Task Assigned",
        description: "Task has been assigned to you",
        variant: "default"
      });

      loadQueueData(); // Refresh the queue
    } catch (error) {
      console.error('Error assigning task:', error);
      toast({
        title: "Error",
        description: "Failed to assign task",
        variant: "destructive"
      });
    }
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

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'secondary';
      case 'in_progress': return 'default';
      case 'completed': return 'success';
      case 'rejected': return 'destructive';
      case 'escalated': return 'destructive';
      default: return 'secondary';
    }
  };

  const formatTimeRemaining = (dueDate: string) => {
    const now = new Date();
    const due = new Date(dueDate);
    const diffMs = due.getTime() - now.getTime();
    
    if (diffMs <= 0) return 'Overdue';
    
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    
    if (diffHours > 24) {
      const diffDays = Math.floor(diffHours / 24);
      return `${diffDays}d ${diffHours % 24}h`;
    } else if (diffHours > 0) {
      return `${diffHours}h ${diffMinutes}m`;
    } else {
      return `${diffMinutes}m`;
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'text-green-600';
    if (confidence >= 0.7) return 'text-yellow-600';
    return 'text-red-600';
  };

  const filteredTasks = tasks.filter(task => {
    if (filter === 'all') return true;
    if (filter === 'urgent') return task.priority === 'urgent' || task.priority === 'critical';
    return task.status === filter;
  });

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Verification Queue</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-32">
            <LoadingSpinner />
            <span className="ml-2">Loading queue...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Queue Statistics */}
      {stats && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Queue Overview</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div className="font-medium">Total Tasks</div>
                <div className="text-2xl font-bold">{stats.totalTasks}</div>
              </div>
              <div>
                <div className="font-medium">My Tasks</div>
                <div className="text-2xl font-bold text-blue-600">{stats.myTasksCount}</div>
              </div>
              <div>
                <div className="font-medium">Pending</div>
                <div className="text-lg font-semibold">{stats.pendingTasks}</div>
              </div>
              <div>
                <div className="font-medium">Overdue</div>
                <div className="text-lg font-semibold text-red-600">{stats.overdueTasks}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filter Tabs */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Queue Tasks</CardTitle>
            <div className="flex space-x-1">
              {['all', 'pending', 'in_progress', 'urgent'].map((filterOption) => (
                <Button
                  key={filterOption}
                  onClick={() => setFilter(filterOption as any)}
                  size="sm"
                  variant={filter === filterOption ? 'default' : 'outline'}
                  className="text-xs"
                >
                  {filterOption.replace('_', ' ')}
                </Button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {filteredTasks.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                <div className="text-4xl mb-2">📋</div>
                <div>No tasks found</div>
                <div className="text-sm">Try adjusting the filter</div>
              </div>
            ) : (
              filteredTasks.map((task) => (
                <div
                  key={task.taskId}
                  className={`border rounded-lg p-3 space-y-2 ${
                    task.taskId === currentTaskId ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                  } ${
                    !showCurrentTask && task.taskId === currentTaskId ? 'opacity-50' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="font-medium text-sm">
                      {task.documentId}
                      {task.hasAnomalies && (
                        <Badge variant="destructive" className="ml-2 text-xs">
                          ⚠️ Anomaly
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center space-x-2">
                      <Badge variant={getPriorityColor(task.priority)} className="text-xs">
                        {task.priority}
                      </Badge>
                      <Badge variant={getStatusColor(task.status)} className="text-xs">
                        {task.status.replace('_', ' ')}
                      </Badge>
                    </div>
                  </div>
                  
                  <div className="flex items-center justify-between text-xs text-gray-600">
                    <div>
                      <div>Type: {task.documentType}</div>
                      <div className={`font-medium ${getConfidenceColor(task.aiConfidence)}`}>
                        AI Confidence: {Math.round(task.aiConfidence * 100)}%
                      </div>
                    </div>
                    <div className="text-right">
                      <div>Due: {formatTimeRemaining(task.dueDate)}</div>
                      <div>Est. Time: {Math.floor(task.estimatedProcessingTime / 60)}m</div>
                    </div>
                  </div>
                  
                  <div className="flex space-x-2">
                    {onTaskSelect && task.status === 'pending' && (
                      <Button
                        onClick={() => handleTaskSelect(task.taskId)}
                        size="sm"
                        variant="outline"
                        className="text-xs flex-1"
                      >
                        Select
                      </Button>
                    )}
                    {task.status === 'pending' && !onTaskSelect && (
                      <Button
                        onClick={() => handleAssignTask(task.taskId)}
                        size="sm"
                        variant="default"
                        className="text-xs flex-1"
                      >
                        Assign to Me
                      </Button>
                    )}
                    {task.status === 'in_progress' && (
                      <Button
                        onClick={() => handleTaskSelect(task.taskId)}
                        size="sm"
                        variant="default"
                        className="text-xs flex-1"
                      >
                        Continue
                      </Button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}