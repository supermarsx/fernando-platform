import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CreditCard, Check, X, Calendar, TrendingUp, DollarSign,
  FileText, AlertCircle, RefreshCw, Plus
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/contexts/AuthContext';
import { ThemeToggle } from '@/components/ThemeToggle';
import PaymentModal from '@/components/PaymentModal';
import api from '@/lib/api';

interface SubscriptionPlan {
  id: number;
  name: string;
  description: string;
  monthly_price: number;
  quarterly_price: number;
  annual_price: number;
  currency: string;
  max_documents_per_month: number;
  max_users: number;
  max_api_calls_per_month: number;
  features: Record<string, any>;
  trial_days: number;
}

interface Subscription {
  id: number;
  subscription_id: string;
  status: string;
  billing_cycle: string;
  start_date: string;
  current_period_end: string;
  trial_end: string | null;
  auto_renew: boolean;
  base_amount: number;
  currency: string;
  documents_used_this_period: number;
  api_calls_used_this_period: number;
  plan_id: number;
}

interface Invoice {
  id: number;
  invoice_number: string;
  status: string;
  total_amount: number;
  amount_due: number;
  currency: string;
  issue_date: string;
  due_date: string;
  paid_at: string | null;
}

export default function BillingPage() {
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'subscription' | 'invoices' | 'plans'>('subscription');
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [subsResponse, plansResponse, invoicesResponse] = await Promise.all([
        api.get('/api/v1/billing/subscriptions/my'),
        api.get('/api/v1/billing/plans'),
        api.get('/api/v1/billing/invoices/my?limit=10')
      ]);
      
      setSubscriptions(subsResponse.data);
      setPlans(plansResponse.data);
      setInvoices(invoicesResponse.data);
    } catch (error) {
      console.error('Failed to fetch billing data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      active: { variant: 'default' as const, color: 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300', label: 'Active' },
      trialing: { variant: 'secondary' as const, color: 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300', label: 'Trial' },
      canceled: { variant: 'destructive' as const, color: 'bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-300', label: 'Canceled' },
      past_due: { variant: 'destructive' as const, color: 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-300', label: 'Past Due' },
      paused: { variant: 'outline' as const, color: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300', label: 'Paused' },
      paid: { variant: 'default' as const, color: 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300', label: 'Paid' },
      pending: { variant: 'secondary' as const, color: 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-300', label: 'Pending' },
      overdue: { variant: 'destructive' as const, color: 'bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-300', label: 'Overdue' }
    };
    
    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.active;
    return <Badge className={config.color}>{config.label}</Badge>;
  };

  const handleSubscribe = async (planId: number, billingCycle: string) => {
    try {
      await api.post('/api/v1/billing/subscriptions', {
        plan_id: planId,
        billing_cycle: billingCycle,
        auto_renew: true,
        trial_enabled: true
      });
      
      fetchData();
      alert('Subscription created successfully!');
    } catch (error: any) {
      alert('Failed to create subscription: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleCancelSubscription = async (subscriptionId: number) => {
    if (!confirm('Are you sure you want to cancel this subscription?')) return;
    
    try {
      await api.post(`/api/v1/billing/subscriptions/${subscriptionId}/cancel`, {
        cancel_immediately: false,
        reason: 'User requested cancellation'
      });
      
      fetchData();
      alert('Subscription canceled successfully');
    } catch (error: any) {
      alert('Failed to cancel subscription: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handlePayInvoice = async (invoiceId: number) => {
    // Find the invoice
    const invoice = invoices.find(inv => inv.id === invoiceId);
    if (!invoice) {
      alert('Invoice not found');
      return;
    }
    
    // Open payment modal
    setSelectedInvoice(invoice);
    setShowPaymentModal(true);
  };

  const handlePaymentSuccess = () => {
    // Refresh data after successful payment
    fetchData();
    setShowPaymentModal(false);
    setSelectedInvoice(null);
    alert('Payment completed successfully!');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-soft">
        <div className="text-center">
          <div className="loading-spinner h-12 w-12 mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Loading billing information...</p>
        </div>
      </div>
    );
  }

  const activeSubscription = subscriptions.find(s => s.status === 'active' || s.status === 'trialing');

  return (
    <div className="min-h-screen bg-gradient-soft">
      {/* Header */}
      <header className="glass-effect border-b sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold bg-gradient-primary bg-clip-text text-transparent">
                Billing & Subscription
              </h1>
              <p className="text-sm text-muted-foreground">
                Manage your subscription and payment methods
              </p>
            </div>
            <div className="flex items-center gap-4">
              <ThemeToggle />
              <span className="text-sm font-medium">{user?.full_name}</span>
              <Button onClick={() => navigate('/dashboard')} variant="outline">
                Back to Dashboard
              </Button>
              <Button onClick={logout} variant="destructive">
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          <Button
            onClick={() => setActiveTab('subscription')}
            variant={activeTab === 'subscription' ? 'default' : 'outline'}
          >
            <CreditCard className="h-4 w-4 mr-2" />
            Subscription
          </Button>
          <Button
            onClick={() => setActiveTab('invoices')}
            variant={activeTab === 'invoices' ? 'default' : 'outline'}
          >
            <FileText className="h-4 w-4 mr-2" />
            Invoices
          </Button>
          <Button
            onClick={() => setActiveTab('plans')}
            variant={activeTab === 'plans' ? 'default' : 'outline'}
          >
            <TrendingUp className="h-4 w-4 mr-2" />
            Plans
          </Button>
        </div>

        {/* Subscription Tab */}
        {activeTab === 'subscription' && (
          <div className="space-y-6">
            {activeSubscription ? (
              <>
                {/* Current Subscription */}
                <Card className="card-hover">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle>Current Subscription</CardTitle>
                        <CardDescription>
                          Subscription ID: {activeSubscription.subscription_id}
                        </CardDescription>
                      </div>
                      {getStatusBadge(activeSubscription.status)}
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      <div>
                        <p className="text-sm text-muted-foreground">Billing Cycle</p>
                        <p className="text-lg font-semibold capitalize">{activeSubscription.billing_cycle}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Amount</p>
                        <p className="text-lg font-semibold">
                          {activeSubscription.base_amount} {activeSubscription.currency}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Next Billing Date</p>
                        <p className="text-lg font-semibold">
                          {new Date(activeSubscription.current_period_end).toLocaleDateString()}
                        </p>
                      </div>
                    </div>

                    {activeSubscription.trial_end && (
                      <div className="mt-4 p-4 bg-primary-50 dark:bg-primary-900/20 rounded-lg">
                        <p className="text-sm font-medium text-primary-700 dark:text-primary-300">
                          Trial Period Active
                        </p>
                        <p className="text-xs text-primary-600 dark:text-primary-400">
                          Ends on {new Date(activeSubscription.trial_end).toLocaleDateString()}
                        </p>
                      </div>
                    )}

                    <div className="mt-6 flex gap-2">
                      <Button
                        variant="outline"
                        onClick={() => handleCancelSubscription(activeSubscription.id)}
                      >
                        Cancel Subscription
                      </Button>
                      <Button onClick={() => setActiveTab('plans')}>
                        Upgrade Plan
                      </Button>
                    </div>
                  </CardContent>
                </Card>

                {/* Usage This Period */}
                <Card>
                  <CardHeader>
                    <CardTitle>Usage This Billing Period</CardTitle>
                    <CardDescription>
                      Period: {new Date(activeSubscription.start_date).toLocaleDateString()} - {new Date(activeSubscription.current_period_end).toLocaleDateString()}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div>
                        <div className="flex justify-between mb-1">
                          <span className="text-sm font-medium">Documents Processed</span>
                          <span className="text-sm font-bold">{activeSubscription.documents_used_this_period}</span>
                        </div>
                        <div className="w-full bg-muted rounded-full h-2">
                          <div
                            className="bg-primary-500 h-2 rounded-full transition-all"
                            style={{ width: `${Math.min(100, (activeSubscription.documents_used_this_period / 100) * 100)}%` }}
                          ></div>
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between mb-1">
                          <span className="text-sm font-medium">API Calls</span>
                          <span className="text-sm font-bold">{activeSubscription.api_calls_used_this_period}</span>
                        </div>
                        <div className="w-full bg-muted rounded-full h-2">
                          <div
                            className="bg-secondary-500 h-2 rounded-full transition-all"
                            style={{ width: `${Math.min(100, (activeSubscription.api_calls_used_this_period / 1000) * 100)}%` }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </>
            ) : (
              <Card>
                <CardContent className="pt-6 text-center">
                  <AlertCircle className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <h3 className="text-lg font-semibold mb-2">No Active Subscription</h3>
                  <p className="text-muted-foreground mb-4">
                    Choose a plan to get started
                  </p>
                  <Button onClick={() => setActiveTab('plans')}>
                    View Plans
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* Invoices Tab */}
        {activeTab === 'invoices' && (
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Invoice History</CardTitle>
                <CardDescription>View and manage your invoices</CardDescription>
              </CardHeader>
              <CardContent>
                {invoices.length > 0 ? (
                  <div className="space-y-3">
                    {invoices.map((invoice) => (
                      <div
                        key={invoice.id}
                        className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                      >
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <FileText className="h-4 w-4 text-muted-foreground" />
                            <span className="font-medium">{invoice.invoice_number}</span>
                            {getStatusBadge(invoice.status)}
                          </div>
                          <p className="text-sm text-muted-foreground mt-1">
                            Issued: {new Date(invoice.issue_date).toLocaleDateString()} | 
                            Due: {new Date(invoice.due_date).toLocaleDateString()}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-bold">
                            {invoice.total_amount} {invoice.currency}
                          </p>
                          {(invoice.status === 'pending' || invoice.status === 'overdue') && (
                            <Button
                              size="sm"
                              className="mt-2"
                              variant={invoice.status === 'overdue' ? 'destructive' : 'default'}
                              onClick={() => handlePayInvoice(invoice.id)}
                            >
                              <CreditCard className="h-4 w-4 mr-1" />
                              Pay Now
                            </Button>
                          )}
                          {invoice.status === 'paid' && invoice.paid_at && (
                            <p className="text-xs text-muted-foreground mt-1">
                              Paid: {new Date(invoice.paid_at).toLocaleDateString()}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-center text-muted-foreground py-8">
                    No invoices found
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Plans Tab */}
        {activeTab === 'plans' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {plans.map((plan) => (
              <Card key={plan.id} className="card-hover relative">
                <CardHeader>
                  <CardTitle>{plan.name}</CardTitle>
                  <CardDescription>{plan.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="mb-6">
                    <p className="text-3xl font-bold">
                      {plan.monthly_price} {plan.currency}
                    </p>
                    <p className="text-sm text-muted-foreground">per month</p>
                  </div>

                  <div className="space-y-2 mb-6">
                    <div className="flex items-center gap-2">
                      <Check className="h-4 w-4 text-success-600" />
                      <span className="text-sm">{plan.max_documents_per_month || 'Unlimited'} documents/month</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Check className="h-4 w-4 text-success-600" />
                      <span className="text-sm">{plan.max_users || 'Unlimited'} users</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Check className="h-4 w-4 text-success-600" />
                      <span className="text-sm">{plan.max_api_calls_per_month || 'Unlimited'} API calls/month</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Check className="h-4 w-4 text-success-600" />
                      <span className="text-sm">{plan.trial_days} days free trial</span>
                    </div>
                  </div>

                  <Button
                    className="w-full"
                    onClick={() => handleSubscribe(plan.id, 'monthly')}
                    disabled={activeSubscription?.plan_id === plan.id}
                  >
                    {activeSubscription?.plan_id === plan.id ? 'Current Plan' : 'Subscribe'}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>

      {/* Payment Modal */}
      {showPaymentModal && selectedInvoice && (
        <PaymentModal
          invoice={selectedInvoice}
          onClose={() => {
            setShowPaymentModal(false);
            setSelectedInvoice(null);
          }}
          onSuccess={handlePaymentSuccess}
        />
      )}
    </div>
  );
}
