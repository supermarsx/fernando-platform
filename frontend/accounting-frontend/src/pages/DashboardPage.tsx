import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { jobsAPI } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { ThemeToggle } from '@/components/ThemeToggle';
import { FileText, Upload, Eye, LogOut, LayoutDashboard, Settings, Plus, BarChart3, Clock, CheckCircle, AlertCircle, CreditCard, Activity } from 'lucide-react';

interface Job {
  job_id: string;
  status: string;
  priority: number;
  queue_name: string;
  created_at: string;
  updated_at: string;
}

export default function DashboardPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const { user, logout, hasRole } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    loadJobs();
  }, []);

  const loadJobs = async () => {
    try {
      const response = await jobsAPI.list({ limit: 50 });
      setJobs(response.data);
    } catch (error) {
      console.error('Error loading jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusVariant = (status: string) => {
    const variants: Record<string, any> = {
      queued: 'secondary',
      processing: 'primary',
      needs_review: 'warning',
      posted: 'success',
      failed: 'error',
      canceled: 'outline',
    };
    return variants[status] || 'outline';
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-soft">
        <div className="text-center">
          <LoadingSpinner size="lg" />
          <p className="mt-4 text-muted-foreground">Loading dashboard...</p>
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
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-primary-100 dark:bg-primary-900/30 rounded-lg">
                <FileText className="h-6 w-6 text-primary-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-primary bg-clip-text text-transparent">
                  Fernando
                </h1>
                <p className="text-sm text-muted-foreground">{user?.full_name} ({user?.email})</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <ThemeToggle />
              <Button variant="pastel-primary" onClick={() => navigate('/upload')}>
                <Plus className="h-4 w-4 mr-2" />
                Upload Documents
              </Button>
              <Button variant="outline" onClick={() => navigate('/billing')}>
                <CreditCard className="h-4 w-4 mr-2" />
                Billing
              </Button>
              <Button variant="outline" onClick={() => navigate('/telemetry')}>
                <Activity className="h-4 w-4 mr-2" />
                Telemetry
              </Button>
              {hasRole('admin') && (
                <Button variant="pastel-secondary" onClick={() => navigate('/admin')}>
                  <Settings className="h-4 w-4 mr-2" />
                  Admin
                </Button>
              )}
              <Button variant="pastel-error" onClick={handleLogout}>
                <LogOut className="h-4 w-4 mr-2" />
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card className="card-hover animate-fade-in">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Total Jobs</CardTitle>
              <BarChart3 className="h-4 w-4 text-primary-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{jobs.length}</div>
              <p className="text-xs text-muted-foreground mt-1">All processing jobs</p>
            </CardContent>
          </Card>
          <Card className="card-hover animate-fade-in" style={{animationDelay: '0.1s'}}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Needs Review</CardTitle>
              <AlertCircle className="h-4 w-4 text-warning-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-warning-600">
                {jobs.filter(j => j.status === 'needs_review').length}
              </div>
              <p className="text-xs text-muted-foreground mt-1">Awaiting your attention</p>
            </CardContent>
          </Card>
          <Card className="card-hover animate-fade-in" style={{animationDelay: '0.2s'}}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Posted</CardTitle>
              <CheckCircle className="h-4 w-4 text-success-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-success-600">
                {jobs.filter(j => j.status === 'posted').length}
              </div>
              <p className="text-xs text-muted-foreground mt-1">Successfully processed</p>
            </CardContent>
          </Card>
          <Card className="card-hover animate-fade-in" style={{animationDelay: '0.3s'}}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Failed</CardTitle>
              <AlertCircle className="h-4 w-4 text-error-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-error-600">
                {jobs.filter(j => j.status === 'failed').length}
              </div>
              <p className="text-xs text-muted-foreground mt-1">Require attention</p>
            </CardContent>
          </Card>
        </div>

        {/* Jobs List */}
        <Card className="animate-fade-in" style={{animationDelay: '0.4s'}}>
          <CardHeader>
            <CardTitle>Recent Jobs</CardTitle>
            <CardDescription>View and manage your processing jobs</CardDescription>
          </CardHeader>
          <CardContent>
            {jobs.length === 0 ? (
              <div className="text-center py-12 animate-bounce-in">
                <div className="p-4 bg-muted/50 rounded-full w-20 h-20 mx-auto mb-4 flex items-center justify-center">
                  <FileText className="h-10 w-10 text-muted-foreground" />
                </div>
                <p className="text-muted-foreground mb-4 text-lg">No jobs yet</p>
                <Button variant="pastel-primary" size="lg" onClick={() => navigate('/upload')} className="animate-float">
                  <Upload className="h-5 w-5 mr-2" />
                  Upload Your First Document
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                {jobs.map((job, index) => (
                  <div
                    key={job.job_id}
                    className="flex items-center justify-between p-4 border rounded-lg hover:shadow-lg cursor-pointer transition-all duration-300 hover:scale-[1.02] animate-slide-up"
                    style={{animationDelay: `${index * 0.1}s`}}
                    onClick={() => navigate(`/jobs/${job.job_id}`)}
                  >
                    <div className="flex items-center space-x-4">
                      <div className="p-2 bg-primary-100 dark:bg-primary-900/30 rounded-lg">
                        <FileText className="h-5 w-5 text-primary-600" />
                      </div>
                      <div>
                        <p className="font-medium">Job {job.job_id.substring(0, 8)}</p>
                        <p className="text-sm text-muted-foreground">
                          Created {new Date(job.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-4">
                      <Badge variant={getStatusVariant(job.status)}>
                        {job.status.replace('_', ' ').toUpperCase()}
                      </Badge>
                      <Button variant="ghost" size="icon">
                        <Eye className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}