import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { Badge } from '../ui/badge';
import { Alert, AlertDescription } from '../ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { 
  License, 
  Plus, 
  Edit, 
  Trash2, 
  CheckCircle, 
  XCircle, 
  Clock, 
  DollarSign,
  Users,
  Server,
  Calendar,
  TrendingUp,
  AlertTriangle
} from 'lucide-react';

interface LicenseTemplate {
  id: string;
  name: string;
  license_type: 'basic' | 'professional' | 'enterprise' | 'custom';
  monthly_price: number;
  yearly_price: number;
  commission_rate: number;
  features: string[];
  limits: {
    documents_per_month: number;
    api_calls_per_month: number;
    customers: number;
    storage_gb: number;
  };
}

interface LicenseInstance {
  id: string;
  client_server_id: string;
  client_server_name: string;
  license_type: string;
  status: 'active' | 'expired' | 'suspended' | 'trial';
  billing_cycle: string;
  amount: number;
  commission_rate: number;
  start_date: string;
  end_date: string;
  activation_date?: string;
}

interface RevenueData {
  total_revenue: number;
  commission_earned: number;
  active_licenses: number;
  expired_licenses: number;
  monthly_recurring_revenue: number;
}

export const SupplierLicensing: React.FC = () => {
  const [licenseTemplates, setLicenseTemplates] = useState<LicenseTemplate[]>([]);
  const [licenseInstances, setLicenseInstances] = useState<LicenseInstance[]>([]);
  const [revenueData, setRevenueData] = useState<RevenueData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedTemplate, setSelectedTemplate] = useState<LicenseTemplate | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);

  useEffect(() => {
    fetchLicensingData();
  }, []);

  const fetchLicensingData = async () => {
    try {
      setLoading(true);
      
      // Fetch license templates
      const templatesResponse = await fetch('/api/licensing/templates');
      if (templatesResponse.ok) {
        const templates = await templatesResponse.json();
        setLicenseTemplates(templates);
      }

      // Fetch license instances
      const instancesResponse = await fetch('/api/licensing/instances');
      if (instancesResponse.ok) {
        const instances = await instancesResponse.json();
        setLicenseInstances(instances);
      }

      // Fetch revenue data
      const revenueResponse = await fetch('/api/licensing/revenue');
      if (revenueResponse.ok) {
        const revenue = await revenueResponse.json();
        setRevenueData(revenue);
      }

    } catch (error) {
      console.error('Error fetching licensing data:', error);
    } finally {
      setLoading(false);
    }
  };

  const createTemplate = async (templateData: Partial<LicenseTemplate>) => {
    try {
      const response = await fetch('/api/licensing/templates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(templateData)
      });

      if (response.ok) {
        await fetchLicensingData();
        setCreateDialogOpen(false);
      }
    } catch (error) {
      console.error('Error creating template:', error);
    }
  };

  const activateLicense = async (licenseId: string) => {
    try {
      const response = await fetch(`/api/licensing/instances/${licenseId}/activate`, {
        method: 'POST'
      });

      if (response.ok) {
        await fetchLicensingData();
      }
    } catch (error) {
      console.error('Error activating license:', error);
    }
  };

  const suspendLicense = async (licenseId: string, reason: string) => {
    try {
      const response = await fetch(`/api/licensing/instances/${licenseId}/suspend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason })
      });

      if (response.ok) {
        await fetchLicensingData();
      }
    } catch (error) {
      console.error('Error suspending license:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-500';
      case 'trial': return 'bg-blue-500';
      case 'expired': return 'bg-red-500';
      case 'suspended': return 'bg-yellow-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active': return <CheckCircle className="h-4 w-4" />;
      case 'trial': return <Clock className="h-4 w-4" />;
      case 'expired': return <XCircle className="h-4 w-4" />;
      case 'suspended': return <AlertTriangle className="h-4 w-4" />;
      default: return <License className="h-4 w-4" />;
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const isExpiringSoon = (endDate: string) => {
    const end = new Date(endDate);
    const now = new Date();
    const daysUntilExpiry = Math.ceil((end.getTime() - now.getTime()) / (1000 * 3600 * 24));
    return daysUntilExpiry <= 30 && daysUntilExpiry > 0;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Supplier Licensing Management</h1>
        <p className="text-gray-600 mt-1">
          Manage licenses for client servers and track revenue from the supplier network.
        </p>
      </div>

      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="templates">License Templates</TabsTrigger>
          <TabsTrigger value="instances">Active Licenses</TabsTrigger>
          <TabsTrigger value="revenue">Revenue Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {revenueData && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Revenue</CardTitle>
                  <DollarSign className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{formatCurrency(revenueData.total_revenue)}</div>
                  <p className="text-xs text-muted-foreground">
                    All-time earnings
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Commission Earned</CardTitle>
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{formatCurrency(revenueData.commission_earned)}</div>
                  <p className="text-xs text-muted-foreground">
                    Total commissions
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Active Licenses</CardTitle>
                  <License className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{revenueData.active_licenses}</div>
                  <p className="text-xs text-muted-foreground">
                    Currently active
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">MRR</CardTitle>
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{formatCurrency(revenueData.monthly_recurring_revenue)}</div>
                  <p className="text-xs text-muted-foreground">
                    Monthly recurring
                  </p>
                </CardContent>
              </Card>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Recent License Activity</CardTitle>
                <CardDescription>Latest license changes and activations</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {licenseInstances.slice(0, 5).map((license) => (
                    <div key={license.id} className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        {getStatusIcon(license.status)}
                        <div>
                          <p className="text-sm font-medium">{license.client_server_name}</p>
                          <p className="text-xs text-gray-600 capitalize">{license.license_type} License</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-medium">{formatCurrency(license.amount)}</p>
                        <Badge variant="outline" className={`${getStatusColor(license.status)} text-white`}>
                          {license.status}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>License Expiry Alerts</CardTitle>
                <CardDescription>Licenses expiring soon</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {licenseInstances
                    .filter(license => isExpiringSoon(license.end_date))
                    .slice(0, 5)
                    .map((license) => (
                    <div key={license.id} className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <AlertTriangle className="h-4 w-4 text-yellow-500" />
                        <div>
                          <p className="text-sm font-medium">{license.client_server_name}</p>
                          <p className="text-xs text-gray-600">
                            Expires {formatDate(license.end_date)}
                          </p>
                        </div>
                      </div>
                      <Button size="sm" variant="outline">
                        Renew
                      </Button>
                    </div>
                  ))}
                  {licenseInstances.filter(license => isExpiringSoon(license.end_date)).length === 0 && (
                    <p className="text-sm text-gray-600">No licenses expiring soon.</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="templates" className="space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-semibold">License Templates</h2>
              <p className="text-gray-600">Configure available license tiers for client servers</p>
            </div>
            <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Template
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Create License Template</DialogTitle>
                  <DialogDescription>
                    Create a new license template for client servers
                  </DialogDescription>
                </DialogHeader>
                <LicenseTemplateForm onSubmit={createTemplate} />
              </DialogContent>
            </Dialog>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {licenseTemplates.map((template) => (
              <Card key={template.id}>
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className="capitalize">{template.name}</CardTitle>
                      <CardDescription className="capitalize">{template.license_type} License</CardDescription>
                    </div>
                    <Badge variant="outline">{template.commission_rate * 100}% Commission</Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex justify-between">
                      <span className="text-sm">Monthly Price:</span>
                      <span className="text-sm font-medium">{formatCurrency(template.monthly_price)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Yearly Price:</span>
                      <span className="text-sm font-medium">{formatCurrency(template.yearly_price)}</span>
                    </div>
                    
                    <div className="pt-2 border-t">
                      <p className="text-sm font-medium mb-2">Features:</p>
                      <div className="space-y-1">
                        {template.features.slice(0, 3).map((feature) => (
                          <p key={feature} className="text-xs text-gray-600">• {feature.replace(/_/g, ' ')}</p>
                        ))}
                        {template.features.length > 3 && (
                          <p className="text-xs text-gray-500">+{template.features.length - 3} more</p>
                        )}
                      </div>
                    </div>

                    <div className="flex space-x-2">
                      <Button size="sm" variant="outline" className="flex-1">
                        <Edit className="h-4 w-4 mr-1" />
                        Edit
                      </Button>
                      <Button size="sm" variant="outline" className="flex-1">
                        <Users className="h-4 w-4 mr-1" />
                        View Usage
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="instances" className="space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-semibold">Active Licenses</h2>
              <p className="text-gray-600">Manage licenses issued to client servers</p>
            </div>
            <Button onClick={fetchLicensingData}>
              Refresh
            </Button>
          </div>

          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b">
                    <tr className="text-left">
                      <th className="p-4">Client Server</th>
                      <th className="p-4">License Type</th>
                      <th className="p-4">Status</th>
                      <th className="p-4">Amount</th>
                      <th className="p-4">Commission</th>
                      <th className="p-4">Start Date</th>
                      <th className="p-4">End Date</th>
                      <th className="p-4">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {licenseInstances.map((license) => (
                      <tr key={license.id} className="border-b hover:bg-gray-50">
                        <td className="p-4">
                          <div className="flex items-center space-x-2">
                            <Server className="h-4 w-4 text-gray-400" />
                            <span className="font-medium">{license.client_server_name}</span>
                          </div>
                        </td>
                        <td className="p-4 capitalize">{license.license_type}</td>
                        <td className="p-4">
                          <Badge className={`${getStatusColor(license.status)} text-white`}>
                            {getStatusIcon(license.status)}
                            <span className="ml-1 capitalize">{license.status}</span>
                          </Badge>
                        </td>
                        <td className="p-4">
                          <span className="font-medium">{formatCurrency(license.amount)}</span>
                          <span className="text-gray-600 text-sm">/{license.billing_cycle}</span>
                        </td>
                        <td className="p-4">
                          <span className="text-green-600 font-medium">
                            {formatCurrency(license.amount * license.commission_rate)}
                          </span>
                        </td>
                        <td className="p-4 text-gray-600">
                          {formatDate(license.start_date)}
                        </td>
                        <td className="p-4">
                          <div className="flex items-center space-x-2">
                            <span className={`text-gray-600 ${isExpiringSoon(license.end_date) ? 'text-yellow-600' : ''}`}>
                              {formatDate(license.end_date)}
                            </span>
                            {isExpiringSoon(license.end_date) && (
                              <AlertTriangle className="h-4 w-4 text-yellow-500" />
                            )}
                          </div>
                        </td>
                        <td className="p-4">
                          <div className="flex space-x-1">
                            {license.status === 'trial' && (
                              <Button size="sm" onClick={() => activateLicense(license.id)}>
                                Activate
                              </Button>
                            )}
                            {license.status === 'active' && (
                              <Button 
                                size="sm" 
                                variant="outline"
                                onClick={() => suspendLicense(license.id, 'Manual suspension')}
                              >
                                Suspend
                              </Button>
                            )}
                            <Button size="sm" variant="outline">
                              <Edit className="h-4 w-4" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="revenue" className="space-y-6">
          {revenueData && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Revenue Breakdown</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex justify-between">
                        <span className="text-sm">Gross Revenue</span>
                        <span className="font-medium">{formatCurrency(revenueData.total_revenue)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm">Commission Earned</span>
                        <span className="font-medium text-green-600">
                          {formatCurrency(revenueData.commission_earned)}
                        </span>
                      </div>
                      <div className="flex justify-between border-t pt-2">
                        <span className="text-sm">Net Revenue</span>
                        <span className="font-medium">
                          {formatCurrency(revenueData.total_revenue - revenueData.commission_earned)}
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>License Distribution</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex justify-between">
                        <span className="text-sm">Active Licenses</span>
                        <Badge variant="default">{revenueData.active_licenses}</Badge>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm">Expired Licenses</span>
                        <Badge variant="secondary">{revenueData.expired_licenses}</Badge>
                      </div>
                      <div className="flex justify-between border-t pt-2">
                        <span className="text-sm">Total Licenses</span>
                        <span className="font-medium">
                          {revenueData.active_licenses + revenueData.expired_licenses}
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Monthly Recurring Revenue</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold text-green-600">
                      {formatCurrency(revenueData.monthly_recurring_revenue)}
                    </div>
                    <p className="text-sm text-gray-600 mt-2">
                      Predictable monthly revenue
                    </p>
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>Revenue Trends</CardTitle>
                  <CardDescription>Historical revenue performance</CardDescription>
                </CardHeader>
                <CardContent>
                  <Alert>
                    <TrendingUp className="h-4 w-4" />
                    <AlertDescription>
                      Revenue analytics dashboard will be implemented with chart visualization.
                    </AlertDescription>
                  </Alert>
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

// License Template Form Component
interface LicenseTemplateFormProps {
  onSubmit: (data: Partial<LicenseTemplate>) => void;
}

const LicenseTemplateForm: React.FC<LicenseTemplateFormProps> = ({ onSubmit }) => {
  const [formData, setFormData] = useState({
    name: '',
    license_type: 'basic',
    monthly_price: 0,
    yearly_price: 0,
    commission_rate: 0.20,
    features: [] as string[],
    limits: {
      documents_per_month: 100,
      api_calls_per_month: 1000,
      customers: 10,
      storage_gb: 5
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="name">Template Name</Label>
          <Input
            id="name"
            value={formData.name}
            onChange={(e) => setFormData({...formData, name: e.target.value})}
            placeholder="Professional License"
            required
          />
        </div>
        <div>
          <Label htmlFor="license_type">License Type</Label>
          <Select 
            value={formData.license_type} 
            onValueChange={(value) => setFormData({...formData, license_type: value})}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="basic">Basic</SelectItem>
              <SelectItem value="professional">Professional</SelectItem>
              <SelectItem value="enterprise">Enterprise</SelectItem>
              <SelectItem value="custom">Custom</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <Label htmlFor="monthly_price">Monthly Price ($)</Label>
          <Input
            id="monthly_price"
            type="number"
            value={formData.monthly_price}
            onChange={(e) => setFormData({...formData, monthly_price: Number(e.target.value)})}
            required
          />
        </div>
        <div>
          <Label htmlFor="yearly_price">Yearly Price ($)</Label>
          <Input
            id="yearly_price"
            type="number"
            value={formData.yearly_price}
            onChange={(e) => setFormData({...formData, yearly_price: Number(e.target.value)})}
            required
          />
        </div>
        <div>
          <Label htmlFor="commission_rate">Commission Rate (%)</Label>
          <Input
            id="commission_rate"
            type="number"
            step="0.01"
            value={formData.commission_rate * 100}
            onChange={(e) => setFormData({...formData, commission_rate: Number(e.target.value) / 100})}
            required
          />
        </div>
      </div>

      <div className="flex justify-end space-x-2">
        <Button type="button" variant="outline">Cancel</Button>
        <Button type="submit">Create Template</Button>
      </div>
    </form>
  );
};

export default SupplierLicensing;