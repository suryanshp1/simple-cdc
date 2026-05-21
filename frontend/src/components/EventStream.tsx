import { useRef, useEffect } from 'react';
import type { CDCEvent } from '../types/events';

interface EventStreamProps {
  events: CDCEvent[];
  onEventClick: (event: CDCEvent) => void;
}

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = Math.max(0, Math.floor((now - then) / 1000));

  if (diff < 5) return 'just now';
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function getPayloadPreview(payload: Record<string, unknown>): string {
  const entries = Object.entries(payload).slice(0, 3);
  const parts = entries.map(([key, val]) => {
    const valStr = typeof val === 'string' ? `"${val}"` : String(val);
    const truncated = valStr.length > 20 ? valStr.slice(0, 20) + '…' : valStr;
    return `${key}: ${truncated}`;
  });
  return parts.join(', ');
}

function getBadgeClass(operation: string): string {
  switch (operation) {
    case 'INSERT': return 'badge-insert';
    case 'UPDATE': return 'badge-update';
    case 'DELETE': return 'badge-delete';
    default: return '';
  }
}

export default function EventStream({ events, onEventClick }: EventStreamProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = 0;
    }
  }, [events.length]);

  if (events.length === 0) {
    return (
      <div className="glass-panel px-8 py-16 text-center">
        <div className="text-4xl mb-4">📡</div>
        <h3 className="text-lg font-medium mb-2" style={{ color: '#e2e8f0' }}>
          Waiting for events...
        </h3>
        <p className="font-mono text-sm" style={{ color: '#64748b' }}>
          CDC events will appear here in real-time as database changes are captured.
        </p>
      </div>
    );
  }

  return (
    <div className="glass-panel overflow-hidden">
      {/* Table Header */}
      <div
        className="hidden sm:grid gap-4 px-5 py-3 text-xs font-mono uppercase tracking-wider"
        style={{
          gridTemplateColumns: '100px 140px 100px 1fr 40px',
          color: '#64748b',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
        }}
      >
        <span>Time</span>
        <span>Table</span>
        <span>Operation</span>
        <span>Preview</span>
        <span></span>
      </div>

      {/* Event Rows */}
      <div ref={containerRef} className="overflow-y-auto" style={{ maxHeight: 'calc(100vh - 380px)' }}>
        {events.map((event, index) => (
          <div
            key={event.id || index}
            className="event-row grid gap-4 px-5 py-3.5 cursor-pointer transition-colors duration-150"
            style={{
              gridTemplateColumns: '100px 140px 100px 1fr 40px',
              borderBottom: '1px solid rgba(255,255,255,0.03)',
              animationDelay: `${Math.min(index * 0.02, 0.4)}s`,
            }}
            onClick={() => onEventClick(event)}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.background = 'transparent';
            }}
          >
            {/* Time */}
            <span className="font-mono text-xs self-center" style={{ color: '#64748b' }}>
              {formatRelativeTime(event.created_at)}
            </span>

            {/* Table Name */}
            <span className="self-center">
              <span
                className="font-mono text-xs px-2 py-0.5 rounded-md"
                style={{
                  background: 'rgba(59,130,246,0.1)',
                  color: '#3b82f6',
                  border: '1px solid rgba(59,130,246,0.2)',
                }}
              >
                {event.table_name}
              </span>
            </span>

            {/* Operation Badge */}
            <span className="self-center">
              <span
                className={`${getBadgeClass(event.operation)} font-mono text-xs px-2.5 py-0.5 rounded-md font-medium`}
              >
                {event.operation}
              </span>
            </span>

            {/* Preview */}
            <span
              className="font-mono text-xs self-center truncate hidden sm:block"
              style={{ color: '#64748b' }}
            >
              {getPayloadPreview(event.payload)}
            </span>

            {/* Arrow */}
            <span className="self-center text-right" style={{ color: '#64748b' }}>
              →
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
