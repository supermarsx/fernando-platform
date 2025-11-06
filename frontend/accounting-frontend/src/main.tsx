import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ErrorBoundary } from './components/ErrorBoundary.tsx'
import { TelemetryProvider } from './contexts/TelemetryContext.tsx'
import { ConsentBanner } from './components/ConsentManagement.tsx'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <TelemetryProvider>
        <App />
        <ConsentBanner 
          position="bottom"
          onConsentUpdate={(preferences) => {
            console.log('Consent updated:', preferences);
          }}
        />
      </TelemetryProvider>
    </ErrorBoundary>
  </StrictMode>,
)
