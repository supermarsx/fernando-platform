import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { LoadingSpinner } from '../ui/loading-spinner';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { toast } from '../ui/toast';

interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: string;
  status: 'active' | 'inactive' | 'busy';
  currentTasks: number;
  completedToday: number;
  accuracyRate: number;
  averageProcessingTime: number;
  joinDate: string;
}

interface TeamStats {
  totalMembers: number;
  activeMembers: number;
  busyMembers: number;
  averageAccuracy: number;
  totalCompleted: number;
  queueSize: number;
}

interface Workload {
  teamId: string;
  teamName: string;
  currentLoad: number;
  maxCapacity: number;
  utilizationRate: number;
  averageAccuracy: number;
  pendingTasks: number;
  overdueTasks: number;
}

export function VerificationTeamPanel() {
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [teamStats, setTeamStats] = useState<TeamStats | null>(null);
  const [workloads, setWorkloads] = useState<Workload[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('members');

  useEffect(() => {
    loadTeamData();
    // Refresh team data every 1 minute
    const interval = setInterval(loadTeamData, 60000);
    return () => clearInterval(interval);
  }, []);

  const loadTeamData = async () => {
    try {
      setLoading(true);
      
      // Load team members
      const membersResponse = await fetch('/api/verification/team/members');
      if (!membersResponse.ok) throw new Error('Failed to load team members');
      const membersData = await membersResponse.json();
      setTeamMembers(membersData.members || []);
      
      // Load team statistics
      const statsResponse = await fetch('/api/verification/team/stats');
      if (!statsResponse.ok) throw new Error('Failed to load team stats');
      const statsData = await statsResponse.json();
      setTeamStats(statsData);
      
      // Load team workloads
      const workloadResponse = await fetch('/api/verification/team/workload');
      if (!workloadResponse.ok) throw new Error('Failed to load workload data');
      const workloadData = await workloadResponse.data || [];
      setWorkloads(workloadData);
      
    } catch (error) {
      console.error('Error loading team data:', error);
      toast({
        title: "Error",
        description: "Failed to load team management data",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'default';
      case 'busy': return 'destructive';
      case 'inactive': return 'secondary';
      default: return 'secondary';
    }
  };

  const getAccuracyColor = (accuracy: number) => {
    if (accuracy >= 90) return 'text-green-600';
    if (accuracy >= 80) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getUtilizationColor = (rate: number) => {
    if (rate >= 90) return 'text-red-600';
    if (rate >= 70) return 'text-yellow-600';
    return 'text-green-600';
  };

  const formatProcessingTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  const inviteTeamMember = async () => {
    const email = prompt('Enter email address to invite:');
    const role = prompt('Enter role (reviewer/senior_reviewer/supervisor):');
    
    if (!email || !role) return;

    try {
      const response = await fetch('/api/verification/team/invite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, role })
      });

      if (!response.ok) throw new Error('Failed to invite team member');

      toast({
        title: "Invitation Sent",
        description: `Invitation sent to ${email}`,
        variant: "default"
      });

      loadTeamData();
    } catch (error) {
      console.error('Error inviting team member:', error);
      toast({
        title: "Error",
        description: "Failed to send invitation",
        variant: "destructive"
      });
    }
  };

  const reassignTasks = async (fromUserId: string, toUserId: string) => {
    try {
      const response = await fetch('/api/verification/team/reassign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fromUserId, toUserId })
      });

      if (!response.ok) throw new Error('Failed to reassign tasks');

      toast({
        title: "Tasks Reassigned",
        description: "Tasks have been reassigned successfully",
        variant: "default"
      });

      loadTeamData();
    } catch (error) {
      console.error('Error reassigning tasks:', error);
      toast({
        title: "Error",
        description: "Failed to reassign tasks",
        variant: "destructive"
      });
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Team Management</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-32">
            <LoadingSpinner />
            <span className="ml-2">Loading team data...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Team Management</CardTitle>
          <div className="flex space-x-2">
            <Button onClick={inviteTeamMember} size="sm" variant="default">
              Invite Member
            </Button>
            <Button onClick={loadTeamData} size="sm" variant="outline">
              Refresh
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="members">Team Members</TabsTrigger>
            <TabsTrigger value="workload">Workload</TabsTrigger>
            <TabsTrigger value="performance">Performance</TabsTrigger>
          </TabsList>
          
          {/* Team Overview */}
          {teamStats && (
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{teamStats.totalMembers}</div>
                <div className="text-sm text-gray-600">Total Members</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{teamStats.activeMembers}</div>
                <div className="text-sm text-gray-600">Active</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">{teamStats.totalCompleted}</div>
                <div className="text-sm text-gray-600">Completed Today</div>
              </div>
            </div>
          )}
          
          <TabsContent value="members" className="space-y-4">
            <div className="space-y-3 max-h-80 overflow-y-auto">
              {teamMembers.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  <div className="text-4xl mb-2">👥</div>
                  <div>No team members found</div>
                  <div className="text-sm">Invite team members to get started</div>
                </div>
              ) : (
                teamMembers.map((member) => (
                  <div key={member.id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                          <span className="text-blue-600 font-medium">
                            {member.name.split(' ').map(n => n[0]).join('').slice(0, 2)}
                          </span>
                        </div>
                        <div>
                          <div className="font-medium">{member.name}</div>
                          <div className="text-sm text-gray-600">{member.email}</div>
                          <div className="text-xs text-gray-500">
                            Joined {new Date(member.joinDate).toLocaleDateString()}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <Badge variant={getStatusColor(member.status)} className="mb-2">
                          {member.status}
                        </Badge>
                        <div className="text-sm text-gray-600">{member.role}</div>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-4 gap-4 mt-3 text-sm">
                      <div>
                        <div className="text-gray-600">Current Tasks</div>
                        <div className="font-medium">{member.currentTasks}</div>
                      </div>
                      <div>
                        <div className="text-gray-600">Completed Today</div>
                        <div className="font-medium">{member.completedToday}</div>
                      </div>
                      <div>
                        <div className="text-gray-600">Accuracy</div>
                        <div className={`font-medium ${getAccuracyColor(member.accuracyRate)}`}>
                          {Math.round(member.accuracyRate)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-600">Avg Time</div>
                        <div className="font-medium">
                          {formatProcessingTime(member.averageProcessingTime)}
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </TabsContent>
          
          <TabsContent value="workload" className="space-y-4">
            <div className="space-y-3 max-h-80 overflow-y-auto">
              {workloads.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  <div className="text-4xl mb-2">⚖️</div>
                  <div>No workload data available</div>
                  <div className="text-sm">Workload information will appear here</div>
                </div>
              ) : (
                workloads.map((workload) => (
                  <div key={workload.teamId} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="font-medium">{workload.teamName}</div>
                      <div className="text-sm text-gray-600">
                        {workload.currentLoad} / {workload.maxCapacity} tasks
                      </div>
                    </div>
                    
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>Utilization</span>
                        <span className={`font-medium ${getUtilizationColor(workload.utilizationRate)}`}>
                          {Math.round(workload.utilizationRate)}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${
                            workload.utilizationRate >= 90 ? 'bg-red-500' :
                            workload.utilizationRate >= 70 ? 'bg-yellow-500' :
                            'bg-green-500'
                          }`}
                          style={{ width: `${workload.utilizationRate}%` }}
                        ></div>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-3 gap-4 mt-3 text-sm">
                      <div>
                        <div className="text-gray-600">Pending</div>
                        <div className="font-medium">{workload.pendingTasks}</div>
                      </div>
                      <div>
                        <div className="text-gray-600">Overdue</div>
                        <div className="font-medium text-red-600">{workload.overdueTasks}</div>
                      </div>
                      <div>
                        <div className="text-gray-600">Accuracy</div>
                        <div className={`font-medium ${getAccuracyColor(workload.averageAccuracy)}`}>
                          {Math.round(workload.averageAccuracy)}%
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </TabsContent>
          
          <TabsContent value="performance" className="space-y-4">
            <div className="space-y-4">
              {teamStats && (
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center p-4 border rounded-lg">
                    <div className="text-2xl font-bold text-blue-600">
                      {Math.round(teamStats.averageAccuracy)}%
                    </div>
                    <div className="text-sm text-gray-600">Team Average Accuracy</div>
                  </div>
                  <div className="text-center p-4 border rounded-lg">
                    <div className="text-2xl font-bold text-purple-600">
                      {teamStats.queueSize}
                    </div>
                    <div className="text-sm text-gray-600">Tasks in Queue</div>
                  </div>
                </div>
              )}
              
              <div className="space-y-3">
                <h4 className="font-medium">Top Performers (Last 7 Days)</h4>
                {teamMembers
                  .filter(member => member.status === 'active')
                  .sort((a, b) => b.accuracyRate - a.accuracyRate)
                  .slice(0, 5)
                  .map((member, index) => (
                    <div key={member.id} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-medium text-sm">
                          #{index + 1}
                        </div>
                        <div>
                          <div className="font-medium">{member.name}</div>
                          <div className="text-sm text-gray-600">{member.completedToday} tasks completed</div>
                        </div>
                      </div>
                      <div className={`font-medium ${getAccuracyColor(member.accuracyRate)}`}>
                        {Math.round(member.accuracyRate)}%
                      </div>
                    </div>
                  ))
                }
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}