export interface CDCEvent {
  id: string;
  table_name: string;
  operation: 'INSERT' | 'UPDATE' | 'DELETE';
  payload: Record<string, unknown>;
  created_at: string;
}

export interface PaginatedEvents {
  events: CDCEvent[];
  total: number;
  limit: number;
  offset: number;
}

export interface TableInfo {
  name: string;
  event_count: number;
}

export interface StatsData {
  total_events: number;
  events_last_minute: number;
  tables_count: number;
}

export type ConnectionStatus = 'connected' | 'disconnected' | 'reconnecting';

export interface WebSocketMessage {
  type: 'cdc_event' | 'connected' | 'error';
  data?: CDCEvent;
  message?: string;
}
