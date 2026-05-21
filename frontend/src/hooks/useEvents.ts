import { useState, useEffect, useCallback } from 'react';
import type { CDCEvent, TableInfo, StatsData } from '../types/events';
import { fetchEvents, fetchTables, fetchStats } from '../services/api';

interface Filters {
  table_name: string;
  operation: string;
}

const MAX_EVENTS_IN_MEMORY = 200;

export function useEvents(newEvent: CDCEvent | null) {
  const [events, setEvents] = useState<CDCEvent[]>([]);
  const [tables, setTables] = useState<TableInfo[]>([]);
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<Filters>({ table_name: '', operation: '' });

  const loadEvents = useCallback(async (currentFilters: Filters) => {
    try {
      setLoading(true);
      const params: Record<string, string | number> = { limit: 50, offset: 0 };
      if (currentFilters.table_name) params.table_name = currentFilters.table_name;
      if (currentFilters.operation) params.operation = currentFilters.operation;

      const data = await fetchEvents(params);
      setEvents(data.events);
    } catch (err) {
      console.error('[useEvents] Failed to load events:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshTables = useCallback(async () => {
    try {
      const data = await fetchTables();
      setTables(data);
    } catch (err) {
      console.error('[useEvents] Failed to load tables:', err);
    }
  }, []);

  const refreshStats = useCallback(async () => {
    try {
      const data = await fetchStats();
      setStats(data);
    } catch (err) {
      console.error('[useEvents] Failed to load stats:', err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadEvents(filters);
    refreshTables();
    refreshStats();
  }, []);

  // Re-fetch when filters change
  useEffect(() => {
    loadEvents(filters);
  }, [filters, loadEvents]);

  // Handle new WebSocket events
  useEffect(() => {
    if (!newEvent) return;

    // Check if event matches current filters
    const matchesFilter =
      (!filters.table_name || newEvent.table_name === filters.table_name) &&
      (!filters.operation || newEvent.operation === filters.operation);

    if (matchesFilter) {
      setEvents(prev => {
        const updated = [newEvent, ...prev];
        return updated.slice(0, MAX_EVENTS_IN_MEMORY);
      });
    }
  }, [newEvent]);

  return {
    events,
    tables,
    stats,
    loading,
    filters,
    setFilters,
    refreshTables,
    refreshStats,
  };
}
