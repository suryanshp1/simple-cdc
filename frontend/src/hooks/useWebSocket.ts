import { useState, useEffect, useRef, useCallback } from 'react';
import type { ConnectionStatus, CDCEvent, WebSocketMessage } from '../types/events';

export function useWebSocket() {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [lastEvent, setLastEvent] = useState<CDCEvent | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelayRef = useRef(1000);

  const connect = useCallback(() => {
    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws?token=changeme`;

    setConnectionStatus('reconnecting');

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnectionStatus('connected');
        reconnectDelayRef.current = 1000; // Reset backoff
      };

      ws.onclose = (event) => {
        setConnectionStatus('disconnected');
        wsRef.current = null;

        // Schedule reconnect with exponential backoff
        if (!event.wasClean) {
          const delay = reconnectDelayRef.current;
          reconnectTimerRef.current = setTimeout(() => {
            reconnectDelayRef.current = Math.min(delay * 2, 30000);
            connect();
          }, delay);
        }
      };

      ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          if (message.type === 'cdc_event' && message.data) {
            setLastEvent(message.data);
          }
        } catch (err) {
          console.error('[WebSocket] Failed to parse message:', err);
        }
      };
    } catch (err) {
      console.error('[WebSocket] Failed to connect:', err);
      setConnectionStatus('disconnected');
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return { connectionStatus, lastEvent };
}
