/**
 * Enhanced Dashboard Page with Telemetry Integration
 * Example showing how to integrate telemetry into existing components
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { jobsAPI } from '../lib/api';
import {
  useComponentTelemetry,
  useInteractionTracking,
  useFeatureTelemetry,
  usePerformanceTelemetry,
  useFormTelemetry,
  useJourneyTracking,
} from '../hooks/useTelemetry';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { LoadingSpinner } from '../components/ui/loading-spinner';
import { ThemeToggle } from '../components/ThemeToggle';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { 
  FileText, 
  Upload, 
  Eye, 
  LogOut, 
  LayoutDashboard, 
  Settings, 
  Plus, 
  BarChart3, 
  Clock, 
  CheckCircle, 
  AlertCircle, 
  CreditCard, 
  Activity,
  Search,
  Filter
} from 'lucide-react';

interface Job {
  job_id: string;
  status: string;
  priority: number;
  queue_name: string;
  created_at: string;
  updated_at: string;
}

export default function EnhancedDashboardPage() {
  // Telemetry hooks
  useComponentTelemetry('EnhancedDashboard', { 
    version: '2.0',
    theme: 'dark',
  });
  
  const { trackFeatureOpen, trackFeatureUse, trackFeatureClose } = useFeatureTelemetry('dashboard');
  const { trackInteraction, trackClick } = useInteractionTracking('dashboard-main', 'main-content');
  const { startOperation, endOperation, trackApiCall } = usePerformanceTelemetry('dashboard_operations');
  const { startJourney, nextStep, completeJourney } = useJourneyTracking('user_dashboard');
  const { trackFieldChange, trackFormSubmit } = useFormTelemetry('dashboard_search', 'search');

  // Component state
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const { user, logout, hasRole } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Start user journey tracking
    startJourney('dashboard_visit');
    
    // Track page view
    trackFeatureOpen();
    
    loadJobs();
    
    return () => {
      trackFeatureClose(true);
    };
  }, []);

  const loadJobs = async () => {
    startOperation('load_jobs');
    
    try {
      const response = await trackApiCall(
        () => jobsAPI.list({ limit: 50 }),
        'GET /jobs',
        { searchTerm, filterStatus }
      );
      
      setJobs(response.data);
      trackFeatureUse('jobs_loaded', { 
        count: response.data.length,
        hasFilters: searchTerm !== '' || filterStatus !== 'all'
      });
      
      nextStep('jobs_loaded', { 
        jobCount: response.data.length,
        hasSearch: !!searchTerm 
      });
    } catch (error) {
      console.error('Error loading jobs:', error);
      trackFeatureUse('jobs_loading_error', { 
        error: error instanceof Error ? error.message : 'Unknown error' 
      });
    } finally {
      endOperation();
      setLoading(false);
    }
  };

  const handleSearch = (value: string) => {
    setSearchTerm(value);
    trackFieldChange('search', 'text', value);
    trackInteraction('search', 'dashboard', { searchTerm: value });
  };

  const handleFilterChange = (status: string) => {
    setFilterStatus(status);
    trackInteraction('filter', 'dashboard', { filterStatus: status });
  };

  const handleUpload = () => {
    trackClick();
    trackFeatureUse('navigate_upload');
    nextStep('upload_clicked');
    navigate('/upload');
  };

  const handleViewJob = (jobId: string) => {
    trackClick();
    trackFeatureUse('view_job', { jobId });
    // In a real app, this would navigate to job details
    console.log('View job:', jobId);
  };

  const handleLogout = async () => {
    trackClick();
    trackFeatureUse('logout');
    completeJourney(true, { action: 'logout' });
    
    try {
      await logout();
      navigate('/login');
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  const handleAnalyticsClick = () => {
    trackClick();
    trackFeatureUse('navigate_analytics');
    navigate('/analytics');
  };

  const getStatusVariant = (status: string) => {
    const variants: Record<string, any> = {
      queued: 'secondary',
      processing: 'default',
      needs_review: 'warning',
      posted: 'success',
      failed: 'destructive',
      canceled: 'outline',
    };
    return variants[status] || 'secondary';
  };

  const filteredJobs = jobs.filter(job => {
    const matchesSearch = searchTerm === '' || 
      job.job_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      job.queue_name.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesFilter = filterStatus === 'all' || job.status === filterStatus;
    
    return matchesSearch && matchesFilter;
  });

  const statusCounts = jobs.reduce((acc, job) => {
    acc[job.status] = (acc[job.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <LoadingSpinner />
          <p className="mt-4 text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <LayoutDashboard className="h-8 w-8 text-indigo-600" />
              <h1 className="ml-3 text-xl font-semibold text-gray-900">
                Dashboard
              </h1>
            </div>

            <div className="flex items-center space-x-4">
              <Button
                variant="outline"
                size="sm"
                onClick={handleAnalyticsClick}
                className="flex items-center gap-2"
              >
                <BarChart3 className="h-4 w-4" />
                Analytics
              </Button>
              
              <ThemeToggle />
              
              <Button
                variant="outline"
                size="sm"
                onClick={handleLogout}
                className="flex items-center gap-2"
              >
                <LogOut className="h-4 w-4" />
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Jobs</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{jobs.length}</div>
              <p className="text-xs text-muted-foreground">
                +12% from last month
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {(statusCounts.processing || 0) + (statusCounts.queued || 0)}
              </div>
              <p className="text-xs text-muted-foreground">
                Currently processing
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Completed</CardTitle>
              <CheckCircle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statusCounts.posted || 0}</div>
              <p className="text-xs text-muted-foreground">
                Successfully posted
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Issues</CardTitle>
              <AlertCircle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statusCounts.failed || 0}</div>
              <p className="text-xs text-muted-foreground">
                Require attention
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Search and Filter */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Job Management</CardTitle>
            <CardDescription>
              Search and filter through your document processing jobs
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1">
                <Label htmlFor="search">Search Jobs</Label>
                <div className="relative">
                  <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <Input
                    id="search"
                    placeholder="Search by job ID or queue name..."
                    value={searchTerm}
                    onChange={(e) => handleSearch(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>
              
              <div className="w-full sm:w-48">
                <Label htmlFor="filter">Filter by Status</Label>
                <select
                  id="filter"
                  value={filterStatus}
                  onChange={(e) => handleFilterChange(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="all">All Status</option>
                  <option value="queued">Queued</option>
                  <option value="processing">Processing</option>
                  <option value="needs_review">Needs Review</option>
                  <option value="posted">Posted</option>
                  <option value="failed">Failed</option>
                  <option value="canceled">Canceled</option>
                </select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Jobs List */}
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-medium">
              Recent Jobs ({filteredJobs.length})
            </h2>
            <Button onClick={handleUpload} className="flex items-center gap-2">
              <Plus className="h-4 w-4" />
              Upload Documents
            </Button>
          </div>

          {filteredJobs.length === 0 ? (
            <Card>
              <CardContent className="py-8">
                <div className="text-center">
                  <FileText className="mx-auto h-12 w-12 text-gray-400" />
                  <h3 className="mt-2 text-sm font-medium text-gray-900">No jobs found</h3>
                  <p className="mt-1 text-sm text-gray-500">
                    {searchTerm || filterStatus !== 'all' 
                      ? 'Try adjusting your search or filter criteria.'
                      : 'Get started by uploading your first document.'
                    }
                  </p>
                  <div className="mt-6">
                    <Button onClick={handleUpload}>
                      <Upload className="h-4 w-4 mr-2" />
                      Upload Documents
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4">
              {filteredJobs.map((job) => (
                <Card key={job.job_id} className="hover:shadow-md transition-shadow">
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="font-medium">{job.job_id}</h3>
                          <Badge variant={getStatusVariant(job.status)}>
                            {job.status.replace('_', ' ')}
                          </Badge>
                          <Badge variant="outline">
                            Priority: {job.priority}
                          </Badge>
                        </div>
                        <p className="text-sm text-gray-600 mb-1">
                          Queue: {job.queue_name}
                        </p>
                        <p className="text-xs text-gray-500">
                          Created: {new Date(job.created_at).toLocaleDateString()} • 
                          Updated: {new Date(job.updated_at).toLocaleDateString()}
                        </p>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleViewJob(job.job_id)}
                          className="flex items-center gap-2"
                        >
                          <Eye className="h-4 w-4" />
                          View
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
