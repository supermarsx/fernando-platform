import React, { useState, useEffect } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, CardElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { PayPalScriptProvider, PayPalButtons } from '@paypal/react-paypal-js';
import { billingAPI } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { CreditCard, Wallet, Bitcoin, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';

// Initialize Stripe (replace with your publishable key)
const stripePromise = loadStripe(process.env.REACT_APP_STRIPE_PUBLISHABLE_KEY || 'pk_test_...');

interface PaymentFormProps {
  invoiceId: number;
  amount: number;
  currency: string;
  onSuccess: () => void;
  onCancel: () => void;
}

// Stripe Card Payment Component
const StripeCardPayment: React.FC<PaymentFormProps> = ({ invoiceId, amount, currency, onSuccess }) => {
  const stripe = useStripe();
  const elements = useElements();
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [clientSecret, setClientSecret] = useState<string | null>(null);

  useEffect(() => {
    // Create payment intent on component mount
    const createPaymentIntent = async () => {
      try {
        const response = await billingAPI.createStripePaymentIntent(invoiceId);
        setClientSecret(response.data.client_secret);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to initialize payment');
      }
    };

    createPaymentIntent();
  }, [invoiceId]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!stripe || !elements || !clientSecret) {
      return;
    }

    setProcessing(true);
    setError(null);

    const cardElement = elements.getElement(CardElement);
    if (!cardElement) {
      setError('Card element not found');
      setProcessing(false);
      return;
    }

    try {
      const { error, paymentIntent } = await stripe.confirmCardPayment(clientSecret, {
        payment_method: {
          card: cardElement,
        },
      });

      if (error) {
        setError(error.message || 'Payment failed');
        setProcessing(false);
      } else if (paymentIntent && paymentIntent.status === 'succeeded') {
        onSuccess();
      }
    } catch (err: any) {
      setError(err.message || 'An error occurred');
      setProcessing(false);
    }
  };

  const cardElementOptions = {
    style: {
      base: {
        fontSize: '16px',
        color: '#424770',
        '::placeholder': {
          color: '#aab7c4',
        },
      },
      invalid: {
        color: '#9e2146',
      },
    },
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="p-4 border rounded-lg">
        <CardElement options={cardElementOptions} />
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Button
        type="submit"
        disabled={!stripe || processing || !clientSecret}
        className="w-full"
      >
        {processing ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Processing...
          </>
        ) : (
          `Pay ${currency} ${amount.toFixed(2)}`
        )}
      </Button>

      <p className="text-xs text-muted-foreground text-center">
        Secured by Stripe. Your card details are encrypted.
      </p>
    </form>
  );
};

// PayPal Payment Component
const PayPalPayment: React.FC<PaymentFormProps> = ({ invoiceId, amount, currency, onSuccess }) => {
  const [error, setError] = useState<string | null>(null);
  const [orderId, setOrderId] = useState<string | null>(null);

  const createOrder = async () => {
    try {
      const response = await billingAPI.createPayPalOrder(invoiceId);
      setOrderId(response.data.order_id);
      return response.data.order_id;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create PayPal order');
      throw err;
    }
  };

  const onApprove = async (data: any) => {
    try {
      await billingAPI.capturePayPalOrder(data.orderID);
      onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to capture payment');
    }
  };

  return (
    <div className="space-y-4">
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <PayPalButtons
        createOrder={createOrder}
        onApprove={onApprove}
        onError={(err) => setError('PayPal error occurred')}
        style={{ layout: 'vertical' }}
      />

      <p className="text-xs text-muted-foreground text-center">
        You will be redirected to PayPal to complete the payment.
      </p>
    </div>
  );
};

// Cryptocurrency Payment Component
const CryptoPayment: React.FC<PaymentFormProps> = ({ invoiceId, amount, currency, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [charge, setCharge] = useState<any>(null);
  const [status, setStatus] = useState<string>('');

  const createCharge = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await billingAPI.createCryptoCharge(invoiceId);
      setCharge(response.data);
      
      // Open hosted payment page in new window
      window.open(response.data.hosted_url, '_blank');

      // Start polling for payment status
      pollPaymentStatus(response.data.charge_id);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create crypto charge');
      setLoading(false);
    }
  };

  const pollPaymentStatus = async (chargeId: string) => {
    const interval = setInterval(async () => {
      try {
        const response = await billingAPI.getCryptoChargeStatus(chargeId);
        setStatus(response.data.status);

        if (response.data.status === 'COMPLETED') {
          clearInterval(interval);
          onSuccess();
        } else if (response.data.status === 'EXPIRED' || response.data.status === 'CANCELED') {
          clearInterval(interval);
          setError('Payment expired or canceled');
          setLoading(false);
        }
      } catch (err) {
        clearInterval(interval);
        setError('Failed to check payment status');
        setLoading(false);
      }
    }, 5000); // Poll every 5 seconds

    // Stop polling after 30 minutes
    setTimeout(() => clearInterval(interval), 30 * 60 * 1000);
  };

  return (
    <div className="space-y-4">
      {!charge ? (
        <>
          <div className="text-center space-y-2">
            <Bitcoin className="h-12 w-12 mx-auto text-primary" />
            <h3 className="font-semibold">Pay with Cryptocurrency</h3>
            <p className="text-sm text-muted-foreground">
              Accept Bitcoin, Ethereum, and USDT
            </p>
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <Button
            onClick={createCharge}
            disabled={loading}
            className="w-full"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating charge...
              </>
            ) : (
              `Pay ${currency} ${amount.toFixed(2)} with Crypto`
            )}
          </Button>
        </>
      ) : (
        <div className="space-y-4">
          <Alert>
            <CheckCircle className="h-4 w-4" />
            <AlertDescription>
              Payment window opened. Complete payment in the new window.
            </AlertDescription>
          </Alert>

          <div className="p-4 border rounded-lg space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Status:</span>
              <Badge variant={status === 'COMPLETED' ? 'default' : 'secondary'}>
                {status || 'Pending'}
              </Badge>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Amount:</span>
              <span className="text-sm font-medium">
                {currency} {amount.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Charge ID:</span>
              <span className="text-xs font-mono">{charge.charge_id}</span>
            </div>
          </div>

          {loading && (
            <div className="flex items-center justify-center space-x-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Waiting for payment confirmation...</span>
            </div>
          )}

          <Button
            variant="outline"
            className="w-full"
            onClick={() => window.open(charge.hosted_url, '_blank')}
          >
            Reopen Payment Window
          </Button>
        </div>
      )}

      <p className="text-xs text-muted-foreground text-center">
        Powered by Coinbase Commerce. Payment detected automatically.
      </p>
    </div>
  );
};

// Main Payment Modal Component
export const PaymentModal: React.FC<{
  invoice: any;
  onClose: () => void;
  onSuccess: () => void;
}> = ({ invoice, onClose, onSuccess }) => {
  const [selectedMethod, setSelectedMethod] = useState<string>('card');

  const handleSuccess = () => {
    onSuccess();
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <Card className="w-full max-w-2xl m-4">
        <CardHeader>
          <CardTitle>Pay Invoice #{invoice.invoice_number}</CardTitle>
          <CardDescription>
            Amount due: {invoice.currency} {invoice.amount_due.toFixed(2)}
          </CardDescription>
        </CardHeader>

        <CardContent>
          <Tabs value={selectedMethod} onValueChange={setSelectedMethod}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="card">
                <CreditCard className="h-4 w-4 mr-2" />
                Card
              </TabsTrigger>
              <TabsTrigger value="paypal">
                <Wallet className="h-4 w-4 mr-2" />
                PayPal
              </TabsTrigger>
              <TabsTrigger value="crypto">
                <Bitcoin className="h-4 w-4 mr-2" />
                Crypto
              </TabsTrigger>
            </TabsList>

            <TabsContent value="card" className="mt-4">
              <Elements stripe={stripePromise}>
                <StripeCardPayment
                  invoiceId={invoice.id}
                  amount={invoice.amount_due}
                  currency={invoice.currency}
                  onSuccess={handleSuccess}
                  onCancel={onClose}
                />
              </Elements>
            </TabsContent>

            <TabsContent value="paypal" className="mt-4">
              <PayPalScriptProvider
                options={{
                  'client-id': process.env.REACT_APP_PAYPAL_CLIENT_ID || 'test',
                  currency: invoice.currency,
                }}
              >
                <PayPalPayment
                  invoiceId={invoice.id}
                  amount={invoice.amount_due}
                  currency={invoice.currency}
                  onSuccess={handleSuccess}
                  onCancel={onClose}
                />
              </PayPalScriptProvider>
            </TabsContent>

            <TabsContent value="crypto" className="mt-4">
              <CryptoPayment
                invoiceId={invoice.id}
                amount={invoice.amount_due}
                currency={invoice.currency}
                onSuccess={handleSuccess}
                onCancel={onClose}
              />
            </TabsContent>
          </Tabs>

          <div className="mt-6 flex justify-end space-x-2">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default PaymentModal;
