import { useState, useEffect, useRef, useCallback } from 'react';
import { useWebSocket } from './useWebSocket';
import { telemetryAPI } from '../lib/api';

interface RealtimeDataState {
  systemMetrics: any[];
  businessMetrics: any[];
  performanceMetrics: any[];
  alerts: any[];
  connectionStatus: 'connected' | 'disconnected' | 'connecting' | 'error';
}

interface UseRealtimeDataOptions {
  enabled?: boolean;
  updateInterval?: number;
  maxDataPoints?: number;
  onAlert?: (alert: any) => void;
}

const useRealtimeData = (options: UseRealtimeDataOptions = {}): RealtimeDataState & {
  startStreaming: () => void;
  stopStreaming: () => void;
  clearData: () => void;
} => {
  const {
    enabled = true,
    updateInterval = 10000,
    maxDataPoints = 100,
    onAlert,
  } = options;

  const [data, setData] = useState<RealtimeDataState>({
    systemMetrics: [],
    businessMetrics: [],
    performanceMetrics: [],
    alerts: [],
    connectionStatus: 'disconnected',
  });

  const dataBuffers = useRef({
    systemMetrics: [] as any[],
    businessMetrics: [] as any[],
    performanceMetrics: [] as any[],
    alerts: [] as any[],
  });

  const updateTimer = useRef<NodeJS.Timeout | null>(null);

  // Handle WebSocket messages
  const handleMessage = useCallback((message: any) => {
    const { type, data: messageData } = message;

    switch (type) {
      case 'system_metrics':
        dataBuffers.current.systemMetrics.push(messageData);
        if (dataBuffers.current.systemMetrics.length > maxDataPoints) {
          dataBuffers.current.systemMetrics.shift();
        }
        break;

      case 'business_metrics':
        dataBuffers.current.businessMetrics.push(messageData);
        if (dataBuffers.current.businessMetrics.length > maxDataPoints) {
          dataBuffers.current.businessMetrics.shift();
        }
        break;

      case 'performance_metrics':
        dataBuffers.current.performanceMetrics.push(messageData);
        if (dataBuffers.current.performanceMetrics.length > maxDataPoints) {
          dataBuffers.current.performanceMetrics.shift();
        }
        break;

      case 'alert':
        dataBuffers.current.alerts.unshift(messageData);
        if (dataBuffers.current.alerts.length > maxDataPoints) {
          dataBuffers.current.alerts.pop();
        }
        // Trigger alert callback
        onAlert?.(messageData);
        break;

      default:
        console.log('Unknown message type:', type);
    }

    // Update state with new data
    setData(prev => ({
      ...prev,
      systemMetrics: [...dataBuffers.current.systemMetrics],
      businessMetrics: [...dataBuffers.current.businessMetrics],
      performanceMetrics: [...dataBuffers.current.performanceMetrics],
      alerts: [...dataBuffers.current.alerts],
    }));
  }, [maxDataPoints, onAlert]);

  // WebSocket connection
  const { connected, connect, disconnect, subscribe, unsubscribe } = useWebSocket({
    url: 'ws://localhost:8000',
    autoConnect: false,
    onMessage: handleMessage,
    onConnect: () => {
      setData(prev => ({ ...prev, connectionStatus: 'connected' }));
      // Subscribe to all telemetry channels
      subscribe('system_metrics');
      subscribe('business_metrics');
      subscribe('performance_metrics');
      subscribe('alerts');
    },
    onDisconnect: () => {
      setData(prev => ({ ...prev, connectionStatus: 'disconnected' }));
    },
    onError: (error) => {
      console.error('WebSocket error:', error);
      setData(prev => ({ ...prev, connectionStatus: 'error' }));
    },
  });

  // Periodic data updates (fallback for when WebSocket is not available)
  const fetchDataUpdates = useCallback(async () => {
    try {
      // Fetch system metrics
      const systemResponse = await telemetryAPI.getSystemMetrics({ time_range: '1h' });
      if (systemResponse.data) {
        dataBuffers.current.systemMetrics.push(systemResponse.data);
        if (dataBuffers.current.systemMetrics.length > maxDataPoints) {
          dataBuffers.current.systemMetrics.shift();
        }
      }

      // Fetch performance metrics
      const performanceResponse = await telemetryAPI.getPerformanceMetrics({ time_range: '1h' });
      if (performanceResponse.data) {
        dataBuffers.current.performanceMetrics.push(performanceResponse.data);
        if (dataBuffers.current.performanceMetrics.length > maxDataPoints) {
          dataBuffers.current.performanceMetrics.shift();
        }
      }

      // Fetch alerts
      const alertsResponse = await telemetryAPI.getActiveAlerts();
      if (alertsResponse.data) {
        dataBuffers.current.alerts = alertsResponse.data;
      }

      // Update state
      setData(prev => ({
        ...prev,
        systemMetrics: [...dataBuffers.current.systemMetrics],
        performanceMetrics: [...dataBuffers.current.performanceMetrics],
        alerts: [...dataBuffers.current.alerts],
        connectionStatus: connected ? 'connected' : 'connected',
      }));
    } catch (error) {
      console.error('Failed to fetch data updates:', error);
    }
  }, [connected, maxDataPoints]);

  // Start streaming
  const startStreaming = useCallback(() => {
    connect();
    
    // Start periodic updates as fallback
    updateTimer.current = setInterval(fetchDataUpdates, updateInterval);
  }, [connect, fetchDataUpdates, updateInterval]);

  // Stop streaming
  const stopStreaming = useCallback(() => {
    disconnect();
    
    if (updateTimer.current) {
      clearInterval(updateTimer.current);
      updateTimer.current = null;
    }
  }, [disconnect]);

  // Clear all data
  const clearData = useCallback(() => {
    dataBuffers.current = {
      systemMetrics: [],
      businessMetrics: [],
      performanceMetrics: [],
      alerts: [],
    };
    
    setData(prev => ({
      ...prev,
      systemMetrics: [],
      businessMetrics: [],
      performanceMetrics: [],
      alerts: [],
    }));
  }, []);

  // Initialize streaming based on enabled flag
  useEffect(() => {
    if (enabled) {
      startStreaming();
    } else {
      stopStreaming();
    }

    return () => {
      stopStreaming();
    };
  }, [enabled, startStreaming, stopStreaming]);

  // Update connection status
  useEffect(() => {
    setData(prev => ({
      ...prev,
      connectionStatus: connected ? 'connected' : 'disconnected',
    }));
  }, [connected]);

  return {
    ...data,
    startStreaming,
    stopStreaming,
    clearData,
  };
};

export default useRealtimeData;