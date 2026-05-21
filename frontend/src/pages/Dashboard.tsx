import React, { useState, useEffect } from 'react';
import Header from '../components/Header';
import StatsBar from '../components/StatsBar';
import Filters from '../components/Filters';
import EventStream from '../components/EventStream';
import EventDetailModal from '../components/EventDetailModal';
import { useWebSocket } from '../hooks/useWebSocket';
import { useEvents } from '../hooks/useEvents';
import { CDCEvent } from '../types/events';

const Dashboard: React.FC = () => {
  const { connectionStatus, lastEvent } = useWebSocket();
  
  const {
    events,
    tables,
    stats,
    loading,
    filters,
    setFilters,
    refreshTables,
    refreshStats,
  } = useEvents(lastEvent);

  const [selectedEvent, setSelectedEvent] = useState<CDCEvent | null>(null);

  // Periodic refresh of stats and tables
  useEffect(() => {
    const interval = setInterval(() => {
      refreshStats();
      refreshTables();
    }, 30000); // Every 30 seconds
    return () => clearInterval(interval);
  }, [refreshStats, refreshTables]);

  return (
    <div className="min-h-screen flex flex-col text-slate-200">
      <Header connectionStatus={connectionStatus} />
      
      <main className="flex-1 p-4 md:p-6 max-w-7xl mx-auto w-full flex flex-col gap-6 relative z-10">
        <StatsBar 
          stats={stats} 
          connectionStatus={connectionStatus} 
          eventsInView={events.length} 
        />
        
        <Filters 
          tables={tables}
          filters={filters}
          onFilterChange={setFilters}
        />
        
        <div className="flex-1 flex flex-col min-h-[500px]">
          <EventStream 
            events={events}
            onEventClick={setSelectedEvent}
          />
        </div>
      </main>

      <EventDetailModal 
        event={selectedEvent}
        onClose={() => setSelectedEvent(null)}
      />
    </div>
  );
};

export default Dashboard;
