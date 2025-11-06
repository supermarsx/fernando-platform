import { useState, useEffect, useRef, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';

interface UseWebSocketOptions {
  url: string;
  autoConnect?: boolean;
  reconnect?: boolean;
  onMessage?: (data: any) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: any) => void;
}

interface UseWebSocketReturn {
  socket: Socket | null;
  connected: boolean;
  connect: () => void;
  disconnect: () => void;
  send: (event: string, data: any) => void;
  subscribe: (channel: string) => void;
  unsubscribe: (channel: string) => void;
}

export const useWebSocket = (options: UseWebSocketOptions): UseWebSocketReturn => {
  const { 
    url, 
    autoConnect = true, 
    reconnect = true, 
    onMessage, 
    onConnect, 
    onDisconnect, 
    onError 
  } = options;

  const [socket, setSocket] = useState<Socket | null>(null);
  const [connected, setConnected] = useState(false);
  const socketRef = useRef<Socket | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    if (socketRef.current?.connected) {
      return;
    }

    const newSocket = io(url, {
      autoConnect: true,
      reconnection: reconnect,
      reconnectionAttempts: maxReconnectAttempts,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
    });

    // Connection event handlers
    newSocket.on('connect', () => {
      setConnected(true);
      reconnectAttempts.current = 0;
      onConnect?.();
    });

    newSocket.on('disconnect', (reason) => {
      setConnected(false);
      onDisconnect?.();
    });

    newSocket.on('connect_error', (error) => {
      onError?.(error);
    });

    newSocket.on('reconnect', (attemptNumber) => {
      setConnected(true);
      reconnectAttempts.current = attemptNumber;
    });

    newSocket.on('reconnect_failed', () => {
      console.warn('WebSocket reconnection failed after', maxReconnectAttempts, 'attempts');
    });

    // Message handler
    newSocket.on('message', (data) => {
      onMessage?.(data);
    });

    // Telemetry-specific event handlers
    newSocket.on('system_metrics', (data) => {
      onMessage?.({ type: 'system_metrics', data });
    });

    newSocket.on('business_metrics', (data) => {
      onMessage?.({ type: 'business_metrics', data });
    });

    newSocket.on('performance_metrics', (data) => {
      onMessage?.({ type: 'performance_metrics', data });
    });

    newSocket.on('alert', (data) => {
      onMessage?.({ type: 'alert', data });
    });

    socketRef.current = newSocket;
    setSocket(newSocket);
  }, [url, reconnect, onConnect, onDisconnect, onError, onMessage]);

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
      setSocket(null);
      setConnected(false);
    }
  }, []);

  const send = useCallback((event: string, data: any) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit(event, data);
    }
  }, []);

  const subscribe = useCallback((channel: string) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('subscribe', { channel });
    }
  }, []);

  const unsubscribe = useCallback((channel: string) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('unsubscribe', { channel });
    }
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    socket,
    connected,
    connect,
    disconnect,
    send,
    subscribe,
    unsubscribe,
  };
};

export default useWebSocket;