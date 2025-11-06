import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { LoadingSpinner } from '../ui/loading-spinner';
import { DocumentVerification } from './DocumentVerification';
import { VerificationQueue } from './VerificationQueue';
import { BatchVerification } from './BatchVerification';
import { VerificationTeamPanel } from './VerificationTeamPanel';
import { toast } from '../ui/toast';

interface DashboardData {
  userStats: UserStats;
  teamStats: TeamStats;
  recentTasks: RecentTask[];
  qualityMetrics: QualityMetrics;
  alerts: Alert[];
}

interface UserStats {
  tasksCompleted: number;
  averageAccuracy: number;
  averageProcessingTime: number;
  qualityScore: string;
  streakDays: number;
  todayTasks: number;
}

interface TeamStats {
  totalTeamMembers: number;
  activeMembers: number;
  teamAccuracy: number;
  queueSize: number;
  overdueTasks: number;
}

interface RecentTask {
  taskId: string;
  documentId: string;
  completedAt: string;
  qualityScore: number;
  processingTime: number;
}

interface QualityMetrics {
  overallAccuracy: number;
  qualityTrend: 'improving' | 'stable' | 'declining';
  peerReviewScore: number;
  errorRate: number;
}

interface Alert {
  id: string;
  type: 'warning' | 'info' | 'error';
  title: string;
  message: string;
  timestamp: string;
}

export function VerificationDashboard() {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState<'dashboard' | 'verification' | 'batch' | 'team'>('dashboard');
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData();
    // Refresh dashboard data every 2 minutes
    const interval = setInterval(loadDashboardData, 120000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/verification/dashboard');
      if (!response.ok) throw new Error('Failed to load dashboard data');
      
      const data = await response.json();
      setDashboardData(data);
    } catch (error) {
      console.error('Error loading dashboard data:', error);
      toast({
        title: "Error",
        description: "Failed to load dashboard data",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleTaskSelect = (taskId: string) => {
    setSelectedTaskId(taskId);
    setActiveView('verification');
  };

  const handleVerificationComplete = (result: any) => {
    toast({
      title: "Verification Completed",
      description: "Task has been successfully completed",
      variant: "default"
    });
    setActiveView('dashboard');
    setSelectedTaskId(null);
    loadDashboardData(); // Refresh dashboard
  };

  const handleVerificationReject = (reason: string) => {
    toast({
      title: "Verification Rejected",
      description: "Task has been rejected",
      variant: "default"
    });
    setActiveView('dashboard');
    setSelectedTaskId(null);
    loadDashboardData(); // Refresh dashboard
  };

  if (loading && !dashboardData) {
    return (
      <div className="flex items-center justify-center h-96">
        <LoadingSpinner />
        <span className="ml-2">Loading verification dashboard...</span>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="text-center p-8">
        <h2 className="text-xl font-semibold text-gray-900">Dashboard unavailable</h2>
        <p className="text-gray-600 mt-2">Unable to load dashboard data.</p>
        <Button onClick={loadDashboardData} className="mt-4">
          Retry
        </Button>
      </div>
    );
  }

  const renderMainDashboard = () => (
    <div className="space-y-6">
      {/* Welcome Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Verification Dashboard</h1>
          <p className="text-gray-600 mt-1">
            Manage your verification tasks and monitor quality metrics
          </p>
        </div>
        <div className="flex space-x-2">
          <Button onClick={() => setActiveView('verification')} variant="default">
            New Verification
          </Button>
          <Button onClick={() => setActiveView('batch')} variant="outline">
            Batch Processing
          </Button>
        </div>
      </div>

      {/* Alerts */}
      {dashboardData.alerts.length > 0 && (
        <div className="space-y-2">
          {dashboardData.alerts.map((alert) => (
            <Alert key={alert.id} className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium">{alert.title}</h4>
                  <p className="text-sm text-gray-600">{alert.message}</p>
                </div>
                <Badge variant={alert.type === 'error' ? 'destructive' : 'default'}>
                  {alert.type}
                </Badge>
              </div>
            </Alert>
          ))}
        </div>
      )}

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Today's Tasks</CardTitle>
            <Badge variant="outline">{dashboardData.userStats.todayTasks}</Badge>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboardData.userStats.tasksCompleted}</div>
            <p className="text-xs text-gray-600">
              Completed this month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Accuracy Rate</CardTitle>
            <Badge variant={dashboardData.userStats.averageAccuracy >= 85 ? 'default' : 'destructive'}>
              {Math.round(dashboardData.userStats.averageAccuracy)}%
            </Badge>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboardData.qualityMetrics.overallAccuracy}%</div>
            <p className="text-xs text-gray-600">
              Team average: {Math.round(dashboardData.teamStats.teamAccuracy)}%
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Processing Time</CardTitle>
            <Badge variant="outline">
              {Math.floor(dashboardData.userStats.averageProcessingTime / 60)}m
            </Badge>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {Math.floor(dashboardData.userStats.averageProcessingTime / 60)}:
              {String(dashboardData.userStats.averageProcessingTime % 60).padStart(2, '0')}
            </div>
            <p className="text-xs text-gray-600">
              Average per task
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Quality Score</CardTitle>
            <Badge variant="default">
              {dashboardData.userStats.qualityScore.toUpperCase()}
            </Badge>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboardData.userStats.streakDays}</div>
            <p className="text-xs text-gray-600">
              Day streak
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Queue and Recent Tasks */}
        <div className="lg:col-span-2 space-y-6">
          <VerificationQueue
            showCurrentTask={false}
            onTaskSelect={handleTaskSelect}
          />
          
          <Card>
            <CardHeader>
              <CardTitle>Recent Completions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {dashboardData.recentTasks.length === 0 ? (
                  <div className="text-center text-gray-500 py-8">
                    <div className="text-4xl mb-2">📋</div>
                    <div>No recent completions</div>
                    <div className="text-sm">Completed tasks will appear here</div>
                  </div>
                ) : (
                  dashboardData.recentTasks.map((task) => (
                    <div key={task.taskId} className="flex items-center justify-between p-3 border rounded-lg">
                      <div>
                        <div className="font-medium">{task.documentId}</div>
                        <div className="text-sm text-gray-600">
                          {new Date(task.completedAt).toLocaleString()}
                        </div>
                      </div>
                      <div className="flex items-center space-x-3">
                        <Badge variant={task.qualityScore >= 85 ? 'default' : 'destructive'}>
                          {Math.round(task.qualityScore)}%
                        </Badge>
                        <div className="text-sm text-gray-600">
                          {Math.floor(task.processingTime / 60)}m {task.processingTime % 60}s
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column - Team and Quality */}
        <div className="space-y-6">
          <VerificationTeamPanel />
          
          <Card>
            <CardHeader>
              <CardTitle>Quality Trends</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm">Overall Trend</span>
                <Badge variant={
                  dashboardData.qualityMetrics.qualityTrend === 'improving' ? 'default' :
                  dashboardData.qualityMetrics.qualityTrend === 'declining' ? 'destructive' : 'secondary'
                }>
                  {dashboardData.qualityMetrics.qualityTrend}
                </Badge>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm">Peer Review Score</span>
                <span className="font-medium">
                  {Math.round(dashboardData.qualityMetrics.peerReviewScore)}%
                </span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm">Error Rate</span>
                <span className="font-medium text-red-600">
                  {Math.round(dashboardData.qualityMetrics.errorRate)}%
                </span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );

  const renderVerificationView = () => (
    <div>
      <div className="flex items-center mb-6">
        <Button
          onClick={() => setActiveView('dashboard')}
          variant="ghost"
          className="mr-4"
        >
          ← Back to Dashboard
        </Button>
        <h1 className="text-2xl font-bold">Document Verification</h1>
      </div>
      
      {selectedTaskId ? (
        <DocumentVerification
          taskId={selectedTaskId}
          onComplete={handleVerificationComplete}
          onReject={handleVerificationReject}
        />
      ) : (
        <VerificationQueue
          showCurrentTask={true}
          onTaskSelect={handleTaskSelect}
        />
      )}
    </div>
  );

  const renderBatchView = () => (
    <div>
      <div className="flex items-center mb-6">
        <Button
          onClick={() => setActiveView('dashboard')}
          variant="ghost"
          className="mr-4"
        >
          ← Back to Dashboard
        </Button>
        <h1 className="text-2xl font-bold">Batch Verification</h1>
      </div>
      
      <BatchVerification onComplete={() => {
        toast({
          title: "Batch Processing Complete",
          description: "All tasks have been processed",
          variant: "default"
        });
        setActiveView('dashboard');
        loadDashboardData();
      }} />
    </div>
  );

  const renderTeamView = () => (
    <div>
      <div className="flex items-center mb-6">
        <Button
          onClick={() => setActiveView('dashboard')}
          variant="ghost"
          className="mr-4"
        >
          ← Back to Dashboard
        </Button>
        <h1 className="text-2xl font-bold">Team Management</h1>
      </div>
      
      <VerificationTeamPanel />
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto p-6">
        <Tabs value={activeView} onValueChange={(value) => setActiveView(value as any)}>
          <TabsContent value="dashboard" className="mt-0">
            {renderMainDashboard()}
          </TabsContent>
          
          <TabsContent value="verification" className="mt-0">
            {renderVerificationView()}
          </TabsContent>
          
          <TabsContent value="batch" className="mt-0">
            {renderBatchView()}
          </TabsContent>
          
          <TabsContent value="team" className="mt-0">
            {renderTeamView()}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}