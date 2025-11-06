import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  CreditCard, 
  ShoppingCart, 
  Star, 
  Clock,
  Check,
  AlertCircle,
  Gift,
  Zap
} from 'lucide-react';

interface CreditPackage {
  id: number;
  name: string;
  description: string;
  base_credits: number;
  bonus_credits: number;
  total_credits: number;
  price_usd: number;
  price_eur?: number;
  price_gbp?: number;
  currency: string;
  discount_percentage: number;
  validity_days: number;
  is_bulk_discount: boolean;
  is_featured: boolean;
  target_tier?: string;
  features: {
    priority_support: boolean;
    advanced_analytics: boolean;
    api_access: boolean;
  };
  cost_per_credit: number;
  savings_amount: number;
}

interface PurchaseTransaction {
  purchase_id: string;
  package_details: {
    name: string;
    base_credits: number;
    bonus_credits: number;
    total_credits: number;
  };
  pricing: {
    subtotal: number;
    discount_amount: number;
    tax_amount: number;
    total_amount: number;
    currency: string;
    cost_per_credit: number;
  };
  validity: {
    expires_at: string;
    validity_days: number;
  };
}

interface CreditPurchaseProps {
  userId: number;
  organizationId?: number;
  onPurchaseComplete?: (transactionId: string) => void;
}

const CreditPurchase: React.FC<CreditPurchaseProps> = ({ 
  userId, 
  organizationId, 
  onPurchaseComplete 
}) => {
  const [packages, setPackages] = useState<CreditPackage[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPackage, setSelectedPackage] = useState<CreditPackage | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [currency, setCurrency] = useState('USD');
  const [showPurchaseDialog, setShowPurchaseDialog] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [purchaseResult, setPurchaseResult] = useState<PurchaseTransaction | null>(null);
  const [paymentMethod, setPaymentMethod] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    loadPackages();
  }, [userId, organizationId]);

  const loadPackages = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/credits/packages?user_tier=professional${organizationId ? `&organization_only=${true}` : ''}`);
      if (response.ok) {
        const data = await response.json();
        setPackages(data);
      }
    } catch (error) {
      console.error('Failed to load packages:', error);
      setError('Failed to load credit packages');
    } finally {
      setLoading(false);
    }
  };

  const handlePurchase = async () => {
    if (!selectedPackage) return;

    try {
      setProcessing(true);
      setError('');

      // Initiate purchase
      const initiateResponse = await fetch('/api/credits/purchase/initiate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          package_id: selectedPackage.id,
          quantity,
          organization_id: organizationId,
        }),
      });

      if (!initiateResponse.ok) {
        throw new Error('Failed to initiate purchase');
      }

      const purchaseData = await initiateResponse.json();

      if (!purchaseData.success) {
        throw new Error(purchaseData.error || 'Purchase initiation failed');
      }

      // Process payment (simplified - in real implementation, this would integrate with payment processors)
      const paymentResponse = await fetch('/api/credits/purchase/process-payment', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          purchase_id: purchaseData.purchase_id,
          payment_data: {
            payment_successful: true, // Mock payment success
            payment_method_id: paymentMethod,
          },
        }),
      });

      if (!paymentResponse.ok) {
        throw new Error('Payment processing failed');
      }

      const paymentResult = await paymentResponse.json();

      if (paymentResult.success) {
        setPurchaseResult(purchaseData);
        setShowPurchaseDialog(false);
        onPurchaseComplete?.(purchaseData.purchase_id);
      } else {
        throw new Error(paymentResult.error || 'Payment failed');
      }

    } catch (error) {
      console.error('Purchase error:', error);
      setError(error instanceof Error ? error.message : 'Purchase failed');
    } finally {
      setProcessing(false);
    }
  };

  const getPrice = (pkg: CreditPackage) => {
    switch (currency) {
      case 'EUR':
        return pkg.price_eur || pkg.price_usd * 0.85;
      case 'GBP':
        return pkg.price_gbp || pkg.price_usd * 0.73;
      default:
        return pkg.price_usd;
    }
  };

  const calculateTotal = () => {
    if (!selectedPackage) return 0;
    return getPrice(selectedPackage) * quantity;
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
    }).format(amount);
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat().format(num);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center space-y-4">
        <h1 className="text-3xl font-bold">Purchase Credits</h1>
        <p className="text-muted-foreground">
          Choose a credit package that fits your needs
        </p>
        
        {/* Currency Selector */}
        <div className="flex justify-center">
          <div className="flex space-x-2">
            {['USD', 'EUR', 'GBP'].map((curr) => (
              <Button
                key={curr}
                variant={currency === curr ? 'default' : 'outline'}
                size="sm"
                onClick={() => setCurrency(curr)}
              >
                {curr}
              </Button>
            ))}
          </div>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Success Alert */}
      {purchaseResult && (
        <Alert>
          <Check className="h-4 w-4" />
          <AlertDescription>
            Purchase successful! {formatNumber(purchaseResult.package_details.total_credits)} credits added to your account.
            Purchase ID: {purchaseResult.purchase_id}
          </AlertDescription>
        </Alert>
      )}

      {/* Package Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {packages.map((pkg) => (
          <Card 
            key={pkg.id} 
            className={`relative cursor-pointer transition-all hover:shadow-lg ${
              selectedPackage?.id === pkg.id ? 'ring-2 ring-primary' : ''
            } ${pkg.is_featured ? 'border-primary' : ''}`}
            onClick={() => setSelectedPackage(pkg)}
          >
            {pkg.is_featured && (
              <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                <Badge className="bg-primary">
                  <Star className="h-3 w-3 mr-1" />
                  Featured
                </Badge>
              </div>
            )}
            
            {pkg.discount_percentage > 0 && (
              <div className="absolute top-4 right-4">
                <Badge variant="destructive">
                  {pkg.discount_percentage}% OFF
                </Badge>
              </div>
            )}

            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                {pkg.name}
                {pkg.is_bulk_discount && (
                  <Zap className="h-4 w-4 text-yellow-500" />
                )}
              </CardTitle>
              <CardDescription>{pkg.description}</CardDescription>
            </CardHeader>
            
            <CardContent className="space-y-4">
              {/* Credits */}
              <div className="text-center">
                <div className="text-3xl font-bold text-primary">
                  {formatNumber(pkg.total_credits)}
                </div>
                <div className="text-sm text-muted-foreground">
                  {formatNumber(pkg.base_credits)} base
                  {pkg.bonus_credits > 0 && ` + ${formatNumber(pkg.bonus_credits)} bonus`}
                </div>
              </div>

              {/* Pricing */}
              <div className="text-center">
                <div className="text-2xl font-bold">
                  {formatCurrency(getPrice(pkg))}
                </div>
                {pkg.discount_percentage > 0 && (
                  <div className="text-sm text-muted-foreground line-through">
                    {formatCurrency(getPrice(pkg) / (1 - pkg.discount_percentage / 100))}
                  </div>
                )}
                <div className="text-xs text-muted-foreground">
                  {formatCurrency(pkg.cost_per_credit)} per credit
                </div>
                {pkg.savings_amount > 0 && (
                  <div className="text-xs text-green-600 font-medium">
                    Save {formatCurrency(pkg.savings_amount)}
                  </div>
                )}
              </div>

              {/* Validity */}
              <div className="flex items-center justify-center text-sm text-muted-foreground">
                <Clock className="h-4 w-4 mr-1" />
                Valid for {pkg.validity_days} days
              </div>

              {/* Features */}
              <div className="space-y-1">
                {pkg.features.priority_support && (
                  <div className="flex items-center text-sm">
                    <Check className="h-3 w-3 mr-2 text-green-500" />
                    Priority Support
                  </div>
                )}
                {pkg.features.advanced_analytics && (
                  <div className="flex items-center text-sm">
                    <Check className="h-3 w-3 mr-2 text-green-500" />
                    Advanced Analytics
                  </div>
                )}
                {pkg.features.api_access && (
                  <div className="flex items-center text-sm">
                    <Check className="h-3 w-3 mr-2 text-green-500" />
                    API Access
                  </div>
                )}
              </div>

              {/* Select Button */}
              <Button 
                className="w-full" 
                variant={selectedPackage?.id === pkg.id ? "default" : "outline"}
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedPackage(pkg);
                }}
              >
                {selectedPackage?.id === pkg.id ? 'Selected' : 'Select Package'}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Purchase Summary */}
      {selectedPackage && (
        <Card>
          <CardHeader>
            <CardTitle>Purchase Summary</CardTitle>
            <CardDescription>
              Review your selection before proceeding to payment
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-sm font-medium">Package</Label>
                <p className="text-sm text-muted-foreground">{selectedPackage.name}</p>
              </div>
              <div>
                <Label className="text-sm font-medium">Quantity</Label>
                <Select value={quantity.toString()} onValueChange={(value) => setQuantity(parseInt(value))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[1, 2, 3, 5, 10].map((qty) => (
                      <SelectItem key={qty} value={qty.toString()}>
                        {qty}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="border-t pt-4 space-y-2">
              <div className="flex justify-between">
                <span>Credits ({quantity}x)</span>
                <span>{formatNumber(selectedPackage.total_credits * quantity)}</span>
              </div>
              <div className="flex justify-between">
                <span>Subtotal</span>
                <span>{formatCurrency(getPrice(selectedPackage) * quantity)}</span>
              </div>
              {selectedPackage.discount_percentage > 0 && (
                <div className="flex justify-between text-green-600">
                  <span>Discount ({selectedPackage.discount_percentage}%)</span>
                  <span>-{formatCurrency((getPrice(selectedPackage) * quantity) * selectedPackage.discount_percentage / 100)}</span>
                </div>
              )}
              <div className="flex justify-between font-bold border-t pt-2">
                <span>Total</span>
                <span>{formatCurrency(calculateTotal())}</span>
              </div>
            </div>

            <Dialog open={showPurchaseDialog} onOpenChange={setShowPurchaseDialog}>
              <DialogTrigger asChild>
                <Button 
                  className="w-full" 
                  size="lg"
                  onClick={() => setShowPurchaseDialog(true)}
                >
                  <ShoppingCart className="h-4 w-4 mr-2" />
                  Purchase Credits
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Complete Purchase</DialogTitle>
                  <DialogDescription>
                    Review your purchase details and select payment method
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div className="bg-muted p-4 rounded-lg space-y-2">
                    <div className="flex justify-between">
                      <span>{selectedPackage.name} x{quantity}</span>
                      <span>{formatCurrency(calculateTotal())}</span>
                    </div>
                    <div className="flex justify-between text-sm text-muted-foreground">
                      <span>Credits</span>
                      <span>{formatNumber(selectedPackage.total_credits * quantity)}</span>
                    </div>
                    <div className="flex justify-between text-sm text-muted-foreground">
                      <span>Valid until</span>
                      <span>{new Date(Date.now() + selectedPackage.validity_days * 24 * 60 * 60 * 1000).toLocaleDateString()}</span>
                    </div>
                  </div>

                  <div>
                    <Label htmlFor="payment-method">Payment Method</Label>
                    <Select value={paymentMethod} onValueChange={setPaymentMethod}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select payment method" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="card">Credit Card</SelectItem>
                        <SelectItem value="paypal">PayPal</SelectItem>
                        <SelectItem value="bank">Bank Transfer</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {paymentMethod && (
                    <Alert>
                      <CreditCard className="h-4 w-4" />
                      <AlertDescription>
                        Payment will be processed securely through our payment processor.
                      </AlertDescription>
                    </Alert>
                  )}

                  <div className="flex space-x-2">
                    <Button 
                      variant="outline" 
                      onClick={() => setShowPurchaseDialog(false)}
                      disabled={processing}
                    >
                      Cancel
                    </Button>
                    <Button 
                      onClick={handlePurchase}
                      disabled={!paymentMethod || processing}
                      className="flex-1"
                    >
                      {processing ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                          Processing...
                        </>
                      ) : (
                        <>
                          <CreditCard className="h-4 w-4 mr-2" />
                          Pay {formatCurrency(calculateTotal())}
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          </CardContent>
        </Card>
      )}

      {/* Information Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Gift className="h-5 w-5 mr-2" />
              How Credits Work
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Credits are used to pay for LLM operations. Different models have different credit costs.
            </p>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>GPT-4:</span>
                <span>100 credits per 1K tokens</span>
              </div>
              <div className="flex justify-between text-sm">
                <span>Claude-3:</span>
                <span>40-80 credits per 1K tokens</span>
              </div>
              <div className="flex justify-between text-sm">
                <span>Gemini Pro:</span>
                <span>50 credits per 1K tokens</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Need Help?</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Not sure which package is right for you? Our team can help you choose.
            </p>
            <div className="flex space-x-2">
              <Button variant="outline" size="sm">
                Contact Support
              </Button>
              <Button variant="outline" size="sm">
                View Usage Guide
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default CreditPurchase;