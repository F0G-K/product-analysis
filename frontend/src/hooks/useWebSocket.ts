import { useEffect, useRef, useState, useCallback } from 'react';
import { useAuthStore } from '@/stores/authStore';

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected';
type EventHandler = (payload: unknown) => void;

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
  const reconnectAttemptRef = useRef(0);
  const handlersRef = useRef<Map<string, Set<EventHandler>>>(new Map());
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');

  const connect = useCallback(() => {
    const token = useAuthStore.getState().accessToken;
    if (!token) return;

    const wsUrl = `${import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'}?token=${token}`;

    setConnectionStatus('connecting');
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus('connected');
      reconnectAttemptRef.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const eventType = data?.event || data?.type;
        if (eventType && handlersRef.current.has(eventType)) {
          handlersRef.current.get(eventType)?.forEach((handler) => handler(data.payload || data));
        }
      } catch { /* ignore parse errors */ }
    };

    ws.onclose = () => {
      setConnectionStatus('disconnected');
      wsRef.current = null;
      // Auto-reconnect with exponential backoff
      const delay = Math.min(1000 * 2 ** reconnectAttemptRef.current, 30_000);
      reconnectAttemptRef.current += 1;
      reconnectTimeoutRef.current = setTimeout(() => {
        if (useAuthStore.getState().isAuthenticated) {
          connect();
        }
      }, delay);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimeoutRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const subscribe = useCallback((event: string, handler: EventHandler): (() => void) => {
    if (!handlersRef.current.has(event)) {
      handlersRef.current.set(event, new Set());
    }
    handlersRef.current.get(event)?.add(handler);

    return () => {
      handlersRef.current.get(event)?.delete(handler);
    };
  }, []);

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  // Re-connect when token changes
  useEffect(() => {
    const unsub = useAuthStore.subscribe((state, prev) => {
      if (state.accessToken !== prev.accessToken && state.accessToken) {
        wsRef.current?.close();
        connect();
      }
    });
    return unsub;
  }, [connect]);

  return { connectionStatus, subscribe, send };
}
