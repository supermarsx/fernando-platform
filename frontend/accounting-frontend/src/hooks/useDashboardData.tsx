import { useState, useEffect, useCallback } from 'react';
import { telemetryAPI } from '../lib/api';

interface DashboardData {
  [key: string]: any;
}

interface UseDashboardDataOptions {
  autoRefresh?: boolean;
  refreshInterval?: number;
  enableCache?: boolean;
  cacheTimeout?: number;
}

interface UseDashboardDataReturn {
  data: DashboardData;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  updateData: (key: string, value: any) => void;
  clearCache: () => void;
}

export const useDashboardData = (options: UseDashboardDataOptions = {}): UseDashboardDataReturn => {
  const {
    autoRefresh = true,
    refreshInterval = 30000,
    enableCache = true,
    cacheTimeout = 300000, // 5 minutes
  } = options;

  const [data, setData] = useState<DashboardData>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cache, setCache] = useState<Map<string, { data: any; timestamp: number }>>(new Map());

  // Cache key generator
  const getCacheKey = useCallback((endpoint: string, params?: any) => {
    const paramsStr = params ? JSON.stringify(params) : '';
    return `${endpoint}_${paramsStr}`;
  }, []);

  // Check if cache is still valid
  const isCacheValid = useCallback((timestamp: number) => {
    return Date.now() - timestamp < cacheTimeout;
  }, [cacheTimeout]);

  // Fetch data from API or cache
  const fetchData = useCallback(async (endpoint: string, params?: any, useCache: boolean = true) => {
    const cacheKey = getCacheKey(endpoint, params);
    
    // Check cache first
    if (enableCache && useCache) {
      const cached = cache.get(cacheKey);
      if (cached && isCacheValid(cached.timestamp)) {
        return cached.data;
      }
    }

    try {
      let response;
      switch (endpoint) {
        case 'system-metrics':
          response = await telemetryAPI.getSystemMetrics(params);
          break;
        case 'system-health':
          response = await telemetryAPI.getSystemHealth();
          break;
        case 'system-resources':
          response = await telemetryAPI.getSystemResources();
          break;
        case 'business-metrics':
          response = await telemetryAPI.getBusinessMetrics(params);
          break;
        case 'revenue-metrics':
          response = await telemetryAPI.getRevenueMetrics(params);
          break;
        case 'user-metrics':
          response = await telemetryAPI.getUserMetrics(params);
          break;
        case 'performance-metrics':
          response = await telemetryAPI.getPerformanceMetrics(params);
          break;
        case 'api-performance':
          response = await telemetryAPI.getAPIPerformance(params);
          break;
        case 'active-alerts':
          response = await telemetryAPI.getActiveAlerts();
          break;
        default:
          throw new Error(`Unknown endpoint: ${endpoint}`);
      }

      const result = response.data;

      // Cache the result
      if (enableCache) {
        setCache(prev => new Map(prev.set(cacheKey, { data: result, timestamp: Date.now() })));
      }

      return result;
    } catch (err) {
      console.error(`Error fetching ${endpoint}:`, err);
      throw err;
    }
  }, [cache, enableCache, cacheTimeout, getCacheKey, isCacheValid]);

  // Load all dashboard data
  const loadAllData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // Load data in parallel
      const [
        systemMetrics,
        systemHealth,
        businessMetrics,
        performanceMetrics,
        activeAlerts,
      ] = await Promise.allSettled([
        fetchData('system-metrics', { time_range: '24h' }),
        fetchData('system-health'),
        fetchData('business-metrics', { time_range: '7d' }),
        fetchData('performance-metrics', { time_range: '24h' }),
        fetchData('active-alerts'),
      ]);

      const newData: DashboardData = {};

      // Process system metrics
      if (systemMetrics.status === 'fulfilled') {
        newData.systemMetrics = systemMetrics.value;
      }

      // Process system health
      if (systemHealth.status === 'fulfilled') {
        newData.systemHealth = systemHealth.value;
      }

      // Process business metrics
      if (businessMetrics.status === 'fulfilled') {
        newData.businessMetrics = businessMetrics.value;
      }

      // Process performance metrics
      if (performanceMetrics.status === 'fulfilled') {
        newData.performanceMetrics = performanceMetrics.value;
      }

      // Process active alerts
      if (activeAlerts.status === 'fulfilled') {
        newData.activeAlerts = activeAlerts.value;
      }

      setData(newData);

      // Check for any failed requests
      const failures = [
        systemMetrics,
        systemHealth,
        businessMetrics,
        performanceMetrics,
        activeAlerts,
      ].filter(result => result.status === 'rejected');

      if (failures.length > 0) {
        setError(`${failures.length} data source(s) failed to load`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setLoading(false);
    }
  }, [fetchData]);

  // Manual refresh
  const refresh = useCallback(async () => {
    await loadAllData();
  }, [loadAllData]);

  // Update specific data point
  const updateData = useCallback((key: string, value: any) => {
    setData(prev => ({ ...prev, [key]: value }));
  }, []);

  // Clear cache
  const clearCache = useCallback(() => {
    setCache(new Map());
  }, []);

  // Auto-refresh setup
  useEffect(() => {
    if (autoRefresh) {
      loadAllData();
      const interval = setInterval(loadAllData, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval, loadAllData]);

  // Initial load
  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  return {
    data,
    loading,
    error,
    refresh,
    updateData,
    clearCache,
  };
};

export default useDashboardData;