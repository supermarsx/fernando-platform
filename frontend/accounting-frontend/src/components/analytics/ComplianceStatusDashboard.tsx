import React, { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Progress } from '../ui/progress';
import { 
  Radar, Doughnut, Bar, Line 
} from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  RadialLinearScale,
} from 'chart.js';
import { 
  Shield, 
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  FileText,
  Users,
  Lock,
  Globe,
  Clock,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  Download,
  Filter,
  Eye,
  Calendar,
  Award,
  Scale,
  Database,
  LockKeyhole,
  ShieldCheck,
  FileCheck,
  AlertCheckCircle
} from 'lucide-react';
import { format, subDays, subWeeks, subMonths, startOfDay, startOfWeek, startOfMonth } from 'date-fns';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  RadialLinearScale
);

interface ComplianceControl {
  id: string;
  name: string;
  framework: 'GDPR' | 'SOX' | 'PCI-DSS' | 'HIPAA' | 'ISO27001';
  status: 'compliant' | 'non-compliant' | 'partially-compliant' | 'pending' | 'not-applicable';
  score: number;
  lastAssessment: string;
  owner: string;
  description: string;
  evidenceRequired: boolean;
  evidenceProvided: boolean;
  nextReview: string;
  remediation?: string;
}

interface ComplianceMetrics {
  overallScore: number;
  totalControls: number;
  compliantControls: number;
  nonCompliantControls: number;
  pendingAssessments: number;
  expiredEvidence: number;
  upcomingDeadlines: number;
  trendDirection: 'up' | 'down' | 'stable';
  trendPercentage: number;
  lastUpdate: string;
}

interface ComplianceDashboardProps {
  timeRange?: '30d' | '90d' | '180d' | '365d';
  refreshInterval?: number;
  className?: string;
}

const ComplianceStatusDashboard: React.FC<ComplianceDashboardProps> = ({
  timeRange = '90d',
  refreshInterval = 60000,
  className = ''
}) => {
  const [complianceControls, setComplianceControls] = useState<ComplianceControl[]>([]);
  const [metrics, setMetrics] = useState<ComplianceMetrics | null>(null);
  const [selectedTimeRange, setSelectedTimeRange] = useState(timeRange);
  const [selectedFramework, setSelectedFramework] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Mock data generation for demonstration
  const generateMockData = (range: string): ComplianceControl[] => {
    const frameworks: ComplianceControl['framework'][] = ['GDPR', 'SOX', 'PCI-DSS', 'HIPAA', 'ISO27001'];
    const statuses: ComplianceControl['status'][] = ['compliant', 'non-compliant', 'partially-compliant', 'pending', 'not-applicable'];
    
    const controls: ComplianceControl[] = [
      // GDPR Controls
      {
        id: 'GDPR_001',
        name: 'Data Subject Rights Implementation',
        framework: 'GDPR',
        status: 'compliant',
        score: 95,
        lastAssessment: subDays(new Date(), 15).toISOString(),
        owner: 'Data Protection Officer',
        description: 'Ensure mechanisms for data subject rights are implemented',
        evidenceRequired: true,
        evidenceProvided: true,
        nextReview: addDaysSafe(new Date(), 90),
      },
      {
        id: 'GDPR_002',
        name: 'Privacy Impact Assessments',
        framework: 'GDPR',
        status: 'partially-compliant',
        score: 78,
        lastAssessment: subDays(new Date(), 30).toISOString(),
        owner: 'Legal Team',
        description: 'Conduct PIAs for high-risk processing activities',
        evidenceRequired: true,
        evidenceProvided: true,
        nextReview: addDaysSafe(new Date(), 60),
        remediation: 'Complete pending PIAs for new data processing activities',
      },
      {
        id: 'GDPR_003',
        name: 'Data Breach Notification Procedures',
        framework: 'GDPR',
        status: 'compliant',
        score: 88,
        lastAssessment: subDays(new Date(), 7).toISOString(),
        owner: 'Security Team',
        description: 'Establish procedures for breach notification within 72 hours',
        evidenceRequired: true,
        evidenceProvided: true,
        nextReview: addDaysSafe(new Date(), 120),
      },

      // SOX Controls
      {
        id: 'SOX_001',
        name: 'Financial Reporting Controls',
        framework: 'SOX',
        status: 'compliant',
        score: 92,
        lastAssessment: subDays(new Date(), 10).toISOString(),
        owner: 'CFO',
        description: 'Ensure accuracy and reliability of financial reporting',
        evidenceRequired: true,
        evidenceProvided: true,
        nextReview: addDaysSafe(new Date(), 90),
      },
      {
        id: 'SOX_002',
        name: 'IT General Controls',
        framework: 'SOX',
        status: 'partially-compliant',
        score: 82,
        lastAssessment: subDays(new Date(), 20).toISOString(),
        owner: 'IT Director',
        description: 'IT controls supporting financial reporting',
        evidenceRequired: true,
        evidenceProvided: false,
        nextReview: addDaysSafe(new Date(), 45),
        remediation: 'Update access control documentation',
      },
      {
        id: 'SOX_003',
        name: 'Change Management Controls',
        framework: 'SOX',
        status: 'pending',
        score: 45,
        lastAssessment: subDays(new Date(), 60).toISOString(),
        owner: 'Change Manager',
        description: 'Proper approval and documentation of system changes',
        evidenceRequired: true,
        evidenceProvided: false,
        nextReview: addDaysSafe(new Date(), 30),
        remediation: 'Implement automated change approval workflow',
      },

      // PCI-DSS Controls
      {
        id: 'PCI_001',
        name: 'Payment Data Encryption',
        framework: 'PCI-DSS',
        status: 'compliant',
        score: 96,
        lastAssessment: subDays(new Date(), 5).toISOString(),
        owner: 'Security Team',
        description: 'Encrypt payment card data in transit and at rest',
        evidenceRequired: true,
        evidenceProvided: true,
        nextReview: addDaysSafe(new Date(), 90),
      },
      {
        id: 'PCI_002',
        name: 'Access Control Measures',
        framework: 'PCI-DSS',
        status: 'non-compliant',
        score: 35,
        lastAssessment: subDays(new Date(), 45).toISOString(),
        owner: 'Access Manager',
        description: 'Restrict access to payment card data',
        evidenceRequired: true,
        evidenceProvided: false,
        nextReview: addDaysSafe(new Date(), 15),
        remediation: 'Implement role-based access control and remove inactive accounts',
      },
      {
        id: 'PCI_003',
        name: 'Network Security Monitoring',
        framework: 'PCI-DSS',
        status: 'compliant',
        score: 89,
        lastAssessment: subDays(new Date(), 12).toISOString(),
        owner: 'Network Security Team',
        description: 'Monitor and test network security',
        evidenceRequired: true,
        evidenceProvided: true,
        nextReview: addDaysSafe(new Date(), 75),
      },

      // HIPAA Controls
      {
        id: 'HIPAA_001',
        name: 'PHI Access Controls',
        framework: 'HIPAA',
        status: 'partially-compliant',
        score: 76,
        lastAssessment: subDays(new Date(), 25).toISOString(),
        owner: 'HIPAA Officer',
        description: 'Implement access controls for protected health information',
        evidenceRequired: true,
        evidenceProvided: true,
        nextReview: addDaysSafe(new Date(), 65),
        remediation: 'Conduct access review and remove unauthorized access',
      },
      {
        id: 'HIPAA_002',
        name: 'Audit Logging and Monitoring',
        framework: 'HIPAA',
        status: 'compliant',
        score: 91,
        lastAssessment: subDays(new Date(), 8).toISOString(),
        owner: 'Security Team',
        description: 'Maintain audit logs for PHI access',
        evidenceRequired: true,
        evidenceProvided: true,
        nextReview: addDaysSafe(new Date(), 110),
      },

      // ISO27001 Controls
      {
        id: 'ISO_001',
        name: 'Information Security Policies',
        framework: 'ISO27001',
        status: 'compliant',
        score: 94,
        lastAssessment: subDays(new Date(), 18).toISOString(),
        owner: 'CISO',
        description: 'Maintain comprehensive information security policies',
        evidenceRequired: true,
        evidenceProvided: true,
        nextReview: addDaysSafe(new Date(), 105),
      },
      {
        id: 'ISO_002',
        name: 'Risk Assessment and Management',
        framework: 'ISO27001',
        status: 'partially-compliant',
        score: 81,
        lastAssessment: subDays(new Date(), 35).toISOString(),
        owner: 'Risk Manager',
        description: 'Regular risk assessments and treatment plans',
        evidenceRequired: true,
        evidenceProvided: true,
        nextReview: addDaysSafe(new Date(), 55),
        remediation: 'Complete updated risk assessment for new assets',
      },
    ];

    return controls;
  };

  // Helper function to safely add days to avoid date issues
  function addDaysSafe(date: Date, days: number): string {
    const result = new Date(date);
    result.setDate(result.getDate() + days);
    return result.toISOString();
  }

  const calculateMetrics = (controls: ComplianceControl[]): ComplianceMetrics => {
    if (controls.length === 0) {
      return {
        overallScore: 0,
        totalControls: 0,
        compliantControls: 0,
        nonCompliantControls: 0,
        pendingAssessments: 0,
        expiredEvidence: 0,
        upcomingDeadlines: 0,
        trendDirection: 'stable',
        trendPercentage: 0,
        lastUpdate: new Date().toISOString(),
      };
    }

    const totalControls = controls.length;
    const compliantControls = controls.filter(c => c.status === 'compliant').length;
    const nonCompliantControls = controls.filter(c => c.status === 'non-compliant').length;
    const pendingAssessments = controls.filter(c => c.status === 'pending').length;
    const expiredEvidence = controls.filter(c => c.evidenceRequired && !c.evidenceProvided).length;
    
    // Calculate upcoming deadlines (within 30 days)
    const thirtyDaysFromNow = new Date();
    thirtyDaysFromNow.setDate(thirtyDaysFromNow.getDate() + 30);
    const upcomingDeadlines = controls.filter(c => 
      c.status === 'pending' && new Date(c.nextReview) <= thirtyDaysFromNow
    ).length;

    // Calculate overall score
    const overallScore = controls.reduce((sum, control) => sum + control.score, 0) / controls.length;

    // Calculate trend (mock calculation)
    const trendDirection: 'up' | 'down' | 'stable' = 'stable';
    const trendPercentage = 0; // In a real implementation, this would compare historical data

    return {
      overallScore,
      totalControls,
      compliantControls,
      nonCompliantControls,
      pendingAssessments,
      expiredEvidence,
      upcomingDeadlines,
      trendDirection,
      trendPercentage,
      lastUpdate: new Date().toISOString(),
    };
  };

  const fetchComplianceData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // In a real implementation, this would call the backend compliance services
      // For now, we'll generate mock data
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API call
      
      const data = generateMockData(selectedTimeRange);
      setComplianceControls(data);
      setMetrics(calculateMetrics(data));
      setLastUpdate(new Date());
    } catch (err) {
      setError('Failed to fetch compliance data');
      console.error('Error fetching compliance data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchComplianceData();
  }, [selectedTimeRange, selectedFramework, selectedStatus]);

  useEffect(() => {
    const interval = setInterval(() => {
      fetchComplianceData();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [refreshInterval]);

  const filteredControls = useMemo(() => {
    return complianceControls.filter(control => {
      if (selectedFramework !== 'all' && control.framework !== selectedFramework) return false;
      if (selectedStatus !== 'all' && control.status !== selectedStatus) return false;
      return true;
    });
  }, [complianceControls, selectedFramework, selectedStatus]);

  const frameworkScoreData = useMemo(() => {
    if (!filteredControls.length) return null;

    const frameworks = ['GDPR', 'SOX', 'PCI-DSS', 'HIPAA', 'ISO27001'];
    const frameworkScores = frameworks.map(framework => {
      const frameworkControls = filteredControls.filter(c => c.framework === framework);
      if (frameworkControls.length === 0) return 0;
      return frameworkControls.reduce((sum, control) => sum + control.score, 0) / frameworkControls.length;
    });

    return {
      labels: frameworks,
      datasets: [
        {
          label: 'Compliance Score',
          data: frameworkScores,
          backgroundColor: 'rgba(59, 130, 246, 0.8)',
          borderColor: 'rgb(59, 130, 246)',
          borderWidth: 1,
        },
      ],
    };
  }, [filteredControls]);

  const statusDistributionData = useMemo(() => {
    if (!filteredControls.length) return null;

    const statusCounts = filteredControls.reduce((acc, control) => {
      acc[control.status] = (acc[control.status] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return {
      labels: Object.keys(statusCounts).map(status => 
        status.split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
      ),
      datasets: [
        {
          data: Object.values(statusCounts),
          backgroundColor: [
            'rgba(34, 197, 94, 0.8)',   // compliant
            'rgba(239, 68, 68, 0.8)',   // non-compliant
            'rgba(245, 158, 11, 0.8)',  // partially-compliant
            'rgba(59, 130, 246, 0.8)',  // pending
            'rgba(156, 163, 175, 0.8)', // not-applicable
          ],
          borderColor: [
            'rgb(34, 197, 94)',
            'rgb(239, 68, 68)',
            'rgb(245, 158, 11)',
            'rgb(59, 130, 246)',
            'rgb(156, 163, 175)',
          ],
          borderWidth: 1,
        },
      ],
    };
  }, [filteredControls]);

  const radarData = useMemo(() => {
    if (!filteredControls.length) return null;

    const frameworks = ['GDPR', 'SOX', 'PCI-DSS', 'HIPAA', 'ISO27001'];
    const frameworkScores = frameworks.map(framework => {
      const frameworkControls = filteredControls.filter(c => c.framework === framework);
      if (frameworkControls.length === 0) return 0;
      return frameworkControls.reduce((sum, control) => sum + control.score, 0) / frameworkControls.length;
    });

    return {
      labels: frameworks,
      datasets: [
        {
          label: 'Compliance Score',
          data: frameworkScores,
          backgroundColor: 'rgba(59, 130, 246, 0.2)',
          borderColor: 'rgb(59, 130, 246)',
          pointBackgroundColor: 'rgb(59, 130, 246)',
          pointBorderColor: '#fff',
          pointHoverBackgroundColor: '#fff',
          pointHoverBorderColor: 'rgb(59, 130, 246)',
        },
      ],
    };
  }, [filteredControls]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      tooltip: {
        callbacks: {
          label: function(context: any) {
            return `${context.dataset.label}: ${context.parsed.y?.toFixed(1) || context.parsed.toFixed(1)}%`;
          }
        }
      },
    },
    scales: {
      x: {
        display: true,
      },
      y: {
        display: true,
        beginAtZero: true,
        max: 100,
        title: {
          display: true,
          text: 'Score (%)',
        },
      },
    },
  };

  const radarOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
    },
    scales: {
      r: {
        angleLines: {
          display: true,
        },
        suggestedMin: 0,
        suggestedMax: 100,
      },
    },
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'compliant': return 'text-green-600';
      case 'non-compliant': return 'text-red-600';
      case 'partially-compliant': return 'text-yellow-600';
      case 'pending': return 'text-blue-600';
      case 'not-applicable': return 'text-gray-600';
      default: return 'text-gray-600';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'compliant': return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'non-compliant': return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'partially-compliant': return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case 'pending': return <Clock className="h-4 w-4 text-blue-500" />;
      case 'not-applicable': return <AlertCheckCircle className="h-4 w-4 text-gray-500" />;
      default: return <AlertCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getFrameworkIcon = (framework: string) => {
    switch (framework) {
      case 'GDPR': return <Scale className="h-4 w-4" />;
      case 'SOX': return <FileText className="h-4 w-4" />;
      case 'PCI-DSS': return <LockKeyhole className="h-4 w-4" />;
      case 'HIPAA': return <Shield className="h-4 w-4" />;
      case 'ISO27001': return <ShieldCheck className="h-4 w-4" />;
      default: return <FileCheck className="h-4 w-4" />;
    }
  };

  const exportData = () => {
    const dataToExport = {
      controls: filteredControls,
      metrics,
      exportedAt: new Date().toISOString(),
      timeRange: selectedTimeRange,
      filters: {
        framework: selectedFramework,
        status: selectedStatus,
      },
    };

    const blob = new Blob([JSON.stringify(dataToExport, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `compliance-status-${selectedTimeRange}-${format(new Date(), 'yyyy-MM-dd')}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (error) {
    return (
      <div className={`bg-red-50 border border-red-200 rounded-lg p-4 ${className}`}>
        <div className="flex items-center">
          <AlertCircle className="h-5 w-5 text-red-500 mr-2" />
          <span className="text-red-700">{error}</span>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={fetchComplianceData}
            className="ml-auto"
          >
            <RefreshCw className="h-4 w-4 mr-1" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Compliance Status Dashboard</h2>
          <p className="text-muted-foreground">
            Monitor compliance status across multiple regulatory frameworks
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant="outline" className="text-xs">
            Last update: {format(lastUpdate, 'HH:mm:ss')}
          </Badge>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchComplianceData}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-1 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={exportData}>
            <Download className="h-4 w-4 mr-1" />
            Export
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center">
            <Filter className="h-5 w-5 mr-2" />
            Filters & Controls
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Time Range</label>
              <Select value={selectedTimeRange} onValueChange={setSelectedTimeRange}>
                <SelectTrigger>
                  <SelectValue placeholder="Select time range" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="30d">Last 30 Days</SelectItem>
                  <SelectItem value="90d">Last 90 Days</SelectItem>
                  <SelectItem value="180d">Last 180 Days</SelectItem>
                  <SelectItem value="365d">Last Year</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Framework</label>
              <Select value={selectedFramework} onValueChange={setSelectedFramework}>
                <SelectTrigger>
                  <SelectValue placeholder="Select framework" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Frameworks</SelectItem>
                  <SelectItem value="GDPR">GDPR</SelectItem>
                  <SelectItem value="SOX">SOX</SelectItem>
                  <SelectItem value="PCI-DSS">PCI-DSS</SelectItem>
                  <SelectItem value="HIPAA">HIPAA</SelectItem>
                  <SelectItem value="ISO27001">ISO 27001</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Status</label>
              <Select value={selectedStatus} onValueChange={setSelectedStatus}>
                <SelectTrigger>
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="compliant">Compliant</SelectItem>
                  <SelectItem value="non-compliant">Non-Compliant</SelectItem>
                  <SelectItem value="partially-compliant">Partially Compliant</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="not-applicable">Not Applicable</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Metrics Cards */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Overall Score</CardTitle>
              <Award className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.overallScore.toFixed(1)}%</div>
              <Progress value={metrics.overallScore} className="mt-2" />
              <div className="flex items-center text-xs text-muted-foreground mt-2">
                {metrics.trendDirection === 'up' && <TrendingUp className="h-3 w-3 text-green-500 mr-1" />}
                {metrics.trendDirection === 'down' && <TrendingDown className="h-3 w-3 text-red-500 mr-1" />}
                {metrics.trendDirection === 'stable' && <CheckCircle2 className="h-3 w-3 text-blue-500 mr-1" />}
                {metrics.trendPercentage.toFixed(1)}% {metrics.trendDirection}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Compliant Controls</CardTitle>
              <CheckCircle2 className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.compliantControls}</div>
              <div className="text-xs text-muted-foreground">
                of {metrics.totalControls} total controls
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Non-Compliant</CardTitle>
              <AlertCircle className="h-4 w-4 text-red-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.nonCompliantControls}</div>
              <div className="text-xs text-muted-foreground">
                Require attention
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Pending Reviews</CardTitle>
              <Clock className="h-4 w-4 text-orange-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.pendingAssessments}</div>
              <div className="text-xs text-muted-foreground">
                {metrics.upcomingDeadlines} due within 30 days
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Charts */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="frameworks">Frameworks</TabsTrigger>
          <TabsTrigger value="controls">Controls</TabsTrigger>
        </TabsList>
        
        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Compliance Status Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  {statusDistributionData && <Doughnut data={statusDistributionData} options={{ responsive: true, maintainAspectRatio: false }} />}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Framework Performance Radar</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  {radarData && <Radar data={radarData} options={radarOptions} />}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="frameworks" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Framework Compliance Scores</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                {frameworkScoreData && <Bar data={frameworkScoreData} options={chartOptions} />}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="controls" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Compliance Controls</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4 max-h-96 overflow-y-auto">
                {filteredControls.map(control => (
                  <div key={control.id} className="flex items-start justify-between p-4 border rounded-lg">
                    <div className="flex items-start space-x-3">
                      <div className="flex items-center space-x-2">
                        {getFrameworkIcon(control.framework)}
                        {getStatusIcon(control.status)}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center space-x-2">
                          <h4 className="font-medium">{control.name}</h4>
                          <Badge variant="outline">{control.framework}</Badge>
                          <Badge 
                            variant={control.status === 'compliant' ? 'default' : control.status === 'non-compliant' ? 'destructive' : 'secondary'}
                            className={getStatusColor(control.status)}
                          >
                            {control.status}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">{control.description}</p>
                        <div className="flex items-center space-x-4 text-xs text-muted-foreground mt-2">
                          <span>Owner: {control.owner}</span>
                          <span>Score: {control.score}%</span>
                          <span>Next Review: {format(new Date(control.nextReview), 'MMM dd, yyyy')}</span>
                        </div>
                        {control.remediation && (
                          <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs">
                            <strong>Remediation:</strong> {control.remediation}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-col items-end space-y-2">
                      <Progress value={control.score} className="w-24" />
                      <div className="flex items-center space-x-1">
                        {control.evidenceRequired && (
                          <span className="text-xs">
                            {control.evidenceProvided ? (
                              <FileCheck className="h-3 w-3 text-green-500" />
                            ) : (
                              <AlertTriangle className="h-3 w-3 text-yellow-500" />
                            )}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                
                {filteredControls.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    No compliance controls found for the selected filters.
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default ComplianceStatusDashboard;