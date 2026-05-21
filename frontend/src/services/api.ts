import type { PaginatedEvents, CDCEvent, TableInfo, StatsData } from '../types/events';

const API_TOKEN = 'changeme';
const BASE_URL = '/api';

function headers(): Record<string, string> {
  return {
    'X-API-Token': API_TOKEN,
    'Content-Type': 'application/json',
  };
}

export async function fetchEvents(params: {
  table_name?: string;
  operation?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<PaginatedEvents> {
  const searchParams = new URLSearchParams();
  if (params.table_name) searchParams.set('table_name', params.table_name);
  if (params.operation) searchParams.set('operation', params.operation);
  if (params.limit !== undefined) searchParams.set('limit', String(params.limit));
  if (params.offset !== undefined) searchParams.set('offset', String(params.offset));

  const query = searchParams.toString();
  const url = `${BASE_URL}/events${query ? `?${query}` : ''}`;

  const res = await fetch(url, { headers: headers() });
  if (!res.ok) throw new Error(`Failed to fetch events: ${res.status}`);
  return res.json();
}

export async function fetchEvent(id: string): Promise<CDCEvent> {
  const res = await fetch(`${BASE_URL}/events/${id}`, { headers: headers() });
  if (!res.ok) throw new Error(`Failed to fetch event: ${res.status}`);
  return res.json();
}

export async function fetchTables(): Promise<TableInfo[]> {
  const res = await fetch(`${BASE_URL}/tables`, { headers: headers() });
  if (!res.ok) throw new Error(`Failed to fetch tables: ${res.status}`);
  return res.json();
}

export async function fetchHealth(): Promise<Record<string, unknown>> {
  const res = await fetch(`${BASE_URL}/health`, { headers: headers() });
  if (!res.ok) throw new Error(`Failed to fetch health: ${res.status}`);
  return res.json();
}

export async function fetchStats(): Promise<StatsData> {
  const res = await fetch(`${BASE_URL}/stats`, { headers: headers() });
  if (!res.ok) throw new Error(`Failed to fetch stats: ${res.status}`);
  return res.json();
}
