import React, { useEffect, useState, useRef } from 'react';
import { 
  Play, Pause, Square, RotateCcw, Upload, FileText, CheckCircle, 
  Clock, AlertCircle, MoreVertical, Trash2, Eye, Download,
  BarChart3, Cpu, Database, Server, Zap, Activity, Settings,
  RefreshCw, Plus, Filter, Search
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { 
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow 
} from '@/components/ui/table';
import { 
  Dialog, DialogContent, DialogDescription, DialogFooter, 
  DialogHeader, DialogTitle 
} from '@/components/ui/dialog';
import { 
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue 
} from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/contexts/AuthContext';
import { ThemeToggle } from '@/components/ThemeToggle';
import api from '@/lib/api';
import { useNavigate } from 'react-router-dom';

interface ProcessingJob {
  id: string;
  name: string;
  type: 'upload' | 'batch' | 'scheduled' | 'manual';
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'paused';
  progress: number;
  total_files: number;
  processed_files: number;
  failed_files: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  estimated_completion?: string;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  user_id: string;
  username: string;
  settings: {
    max_concurrent: number;
    batch_size: number;
    output_format: string;
    options: Record<string, any>;
  };
  results?: {
    summary: string;
    files: Array<{
      name: string;
      status: string;
      result?: any;
      error?: string;
    }>;
  };
}

export default function BatchProcessingPage() {
  const [jobs, setJobs] = useState<ProcessingJob[]>([]);
  const [selectedJobs, setSelectedJobs] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterType, setFilterType] = useState<string>('all');
  const [showJobModal, setShowJobModal] = useState(false);
  const [selectedJob, setSelectedJob] = useState<ProcessingJob | null>(null);
  const [queueStats, setQueueStats] = useState({
    total_jobs: 0,
    active_jobs: 0,
    completed_today: 0,
    avg_processing_time: 0,
    queue_position: 0,
    estimated_wait_time: 0
  });
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const { toast } = useToast();
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (user?.role !== 'admin' && user?.role !== 'user') {
      navigate('/dashboard');
      return;
    }
    fetchJobs();
    fetchQueueStats();
    // Set up real-time updates every 5 seconds
    intervalRef.current = setInterval(() => {
      fetchJobs(false);
      fetchQueueStats(false);
    }, 5000);
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [user, navigate]);

  const fetchJobs = async (showLoading = true) => {
    try {
      if (showLoading) setLoading(true);
      setRefreshing(true);
      const response = await api.get('/api/v1/processing/jobs');
      setJobs(response.data);
    } catch (error) {
      console.error('Failed to fetch processing jobs:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load processing jobs"
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const fetchQueueStats = async (showLoading = true) => {
    try {
      if (showLoading) setLoading(true);
      const response = await api.get('/api/v1/processing/queue/stats');
      setQueueStats(response.data);
    } catch (error) {
      console.error('Failed to fetch queue stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleJobAction = async (jobId: string, action: string) => {
    try {
      await api.post(`/api/v1/processing/jobs/${jobId}/${action}`);
      fetchJobs(false);
      toast({
        variant: "success",
        title: "Success",
        description: `Job ${action} action completed`
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: `Failed to ${action} job`
      });
    }
  };

  const handleBulkAction = async (action: string) => {
    if (selectedJobs.size === 0) return;
    try {
      await api.post('/api/v1/processing/jobs/bulk', {
        action,
        job_ids: Array.from(selectedJobs)
      });
      fetchJobs(false);
      setSelectedJobs(new Set());
      toast({
        variant: "success",
        title: "Success",
        description: `${action} completed for ${selectedJobs.size} jobs`
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: `Failed to ${action} jobs`
      });
    }
  };

  const createNewJob = async (jobData: any) => {
    try {
      const response = await api.post('/api/v1/processing/jobs', jobData);
      setJobs(prev => [response.data, ...prev]);
      setShowJobModal(false);
      toast({
        variant: "success",
        title: "Success",
        description: "New processing job created"
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to create processing job"
      });
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending': return <Clock className="h-4 w-4 text-warning-600" />;
      case 'processing': return <Activity className="h-4 w-4 text-primary-600 animate-pulse" />;
      case 'completed': return <CheckCircle className="h-4 w-4 text-success-600" />;
      case 'failed': return <AlertCircle className="h-4 w-4 text-error-600" />;
      case 'paused': return <Pause className="h-4 w-4 text-muted-foreground" />;
      default: return <Clock className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants = {
      pending: 'warning' as const,
      processing: 'primary' as const,
      completed: 'success' as const,
      failed: 'error' as const,
      paused: 'secondary' as const
    };
    
    return (
      <Badge variant={variants[status as keyof typeof variants] || 'outline'}>
        {status}
      </Badge>
    );
  };

  const getPriorityBadge = (priority: string) => {
    const variants = {
      low: 'outline' as const,
      normal: 'secondary' as const,
      high: 'warning' as const,
      urgent: 'error' as const
    };
    
    return (
      <Badge variant={variants[priority as keyof typeof variants] || 'outline'}>
        {priority}
      </Badge>
    );
  };

  const getTypeBadge = (type: string) => (
    <Badge variant="outline">{type}</Badge>
  );

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const formatDuration = (startTime: string, endTime?: string) => {
    const start = new Date(startTime);
    const end = endTime ? new Date(endTime) : new Date();
    const duration = end.getTime() - start.getTime();
    const minutes = Math.floor(duration / 60000);
    const seconds = Math.floor((duration % 60000) / 1000);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const filteredJobs = jobs.filter(job => {
    const matchesSearch = 
      job.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      job.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
      job.type.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = filterStatus === 'all' || job.status === filterStatus;
    const matchesType = filterType === 'all' || job.type === filterType;
    
    return matchesSearch && matchesStatus && matchesType;
  });

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-soft">
        <div className="text-center">
          <LoadingSpinner size="lg" />
          <p className="mt-4 text-muted-foreground">Loading processing queue...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-soft">
      {/* Header */}
      <header className="glass-effect border-b sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold bg-gradient-primary bg-clip-text text-transparent">
                Batch Processing
              </h1>
              <p className="text-sm text-muted-foreground">
                Queue management and document processing controls
              </p>
            </div>
            <div className="flex items-center gap-4">
              <ThemeToggle />
              <Button 
                variant="pastel-primary" 
                onClick={() => setShowJobModal(true)}
              >
                <Plus className="h-4 w-4 mr-2" />
                New Job
              </Button>
              <Button 
                variant="pastel-secondary" 
                onClick={() => navigate('/dashboard')}
              >
                Dashboard
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Queue Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-6 mb-8">
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Active Jobs</CardTitle>
              <Activity className="h-4 w-4 text-primary-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{queueStats.active_jobs}</div>
              <p className="text-xs text-muted-foreground">Currently processing</p>
            </CardContent>
          </Card>
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Queue Position</CardTitle>
              <BarChart3 className="h-4 w-4 text-warning-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{queueStats.queue_position}</div>
              <p className="text-xs text-muted-foreground">Your position in queue</p>
            </CardContent>
          </Card>
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Est. Wait Time</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{queueStats.estimated_wait_time}min</div>
              <p className="text-xs text-muted-foreground">Estimated processing time</p>
            </CardContent>
          </Card>
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Completed Today</CardTitle>
              <CheckCircle className="h-4 w-4 text-success-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{queueStats.completed_today}</div>
              <p className="text-xs text-muted-foreground">Jobs completed</p>
            </CardContent>
          </Card>
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Avg Time</CardTitle>
              <Zap className="h-4 w-4 text-secondary-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{queueStats.avg_processing_time}min</div>
              <p className="text-xs text-muted-foreground">Processing duration</p>
            </CardContent>
          </Card>
          <Card className="card-hover">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Total Jobs</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{queueStats.total_jobs}</div>
              <p className="text-xs text-muted-foreground">All time total</p>
            </CardContent>
          </Card>
        </div>

        {/* Filters and Actions */}
        <Card className="mb-6">
          <CardContent className="p-6">
            <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
              <div className="flex flex-col sm:flex-row gap-4 flex-1">
                <div className="relative flex-1 max-w-sm">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                  <Input
                    placeholder="Search jobs..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10"
                  />
                </div>
                <Select value={filterStatus} onValueChange={setFilterStatus}>
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Filter by status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Statuses</SelectItem>
                    <SelectItem value="pending">Pending</SelectItem>
                    <SelectItem value="processing">Processing</SelectItem>
                    <SelectItem value="completed">Completed</SelectItem>
                    <SelectItem value="failed">Failed</SelectItem>
                    <SelectItem value="paused">Paused</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={filterType} onValueChange={setFilterType}>
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Filter by type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Types</SelectItem>
                    <SelectItem value="upload">Upload</SelectItem>
                    <SelectItem value="batch">Batch</SelectItem>
                    <SelectItem value="scheduled">Scheduled</SelectItem>
                    <SelectItem value="manual">Manual</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {selectedJobs.size > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">
                    {selectedJobs.size} selected
                  </span>
                  <Button 
                    variant="pastel-success" 
                    size="sm"
                    onClick={() => handleBulkAction('resume')}
                  >
                    <Play className="h-4 w-4 mr-1" />
                    Resume
                  </Button>
                  <Button 
                    variant="pastel-warning" 
                    size="sm"
                    onClick={() => handleBulkAction('pause')}
                  >
                    <Pause className="h-4 w-4 mr-1" />
                    Pause
                  </Button>
                  <Button 
                    variant="destructive" 
                    size="sm"
                    onClick={() => handleBulkAction('cancel')}
                  >
                    <Square className="h-4 w-4 mr-1" />
                    Cancel
                  </Button>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Jobs Table */}
        <Card>
          <CardHeader>
            <CardTitle>Processing Jobs ({filteredJobs.length})</CardTitle>
            <CardDescription>
              Monitor and manage document processing tasks
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Job</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Progress</TableHead>
                  <TableHead>Files</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredJobs.map((job) => (
                  <TableRow key={job.id} className="animate-fade-in">
                    <TableCell>
                      <div>
                        <div className="font-medium">{job.name}</div>
                        <div className="text-sm text-muted-foreground">
                          by {job.username}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>{getTypeBadge(job.type)}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {getStatusIcon(job.status)}
                        {getStatusBadge(job.status)}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="w-full">
                        <div className="flex justify-between text-sm mb-1">
                          <span>{job.progress}%</span>
                          <span className="text-muted-foreground">
                            {job.processed_files}/{job.total_files}
                          </span>
                        </div>
                        <Progress value={job.progress} className="h-2" />
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        <div>{job.total_files} total</div>
                        {job.failed_files > 0 && (
                          <div className="text-error-600">{job.failed_files} failed</div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>{getPriorityBadge(job.priority)}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {job.started_at ? formatTime(job.started_at) : 'Not started'}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {job.started_at ? formatDuration(job.started_at, job.completed_at) : '-'}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center gap-1">
                        {job.status === 'pending' && (
                          <Button 
                            size="icon" 
                            variant="ghost"
                            onClick={() => handleJobAction(job.id, 'start')}
                          >
                            <Play className="h-4 w-4" />
                          </Button>
                        )}
                        {job.status === 'processing' && (
                          <Button 
                            size="icon" 
                            variant="ghost"
                            onClick={() => handleJobAction(job.id, 'pause')}
                          >
                            <Pause className="h-4 w-4" />
                          </Button>
                        )}
                        {job.status === 'paused' && (
                          <Button 
                            size="icon" 
                            variant="ghost"
                            onClick={() => handleJobAction(job.id, 'resume')}
                          >
                            <Play className="h-4 w-4" />
                          </Button>
                        )}
                        {(job.status === 'pending' || job.status === 'processing' || job.status === 'paused') && (
                          <Button 
                            size="icon" 
                            variant="ghost"
                            onClick={() => handleJobAction(job.id, 'cancel')}
                          >
                            <Square className="h-4 w-4" />
                          </Button>
                        )}
                        <Button 
                          size="icon" 
                          variant="ghost"
                          onClick={() => {
                            setSelectedJob(job);
                            setShowJobModal(true);
                          }}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}