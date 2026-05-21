import type { StatsData, ConnectionStatus } from '../types/events';

interface StatsBarProps {
  stats: StatsData | null;
  connectionStatus: ConnectionStatus;
  eventsInView: number;
}

interface StatCardProps {
  icon: string;
  label: string;
  value: string | number;
  accentColor?: string;
}

function StatCard({ icon, label, value, accentColor }: StatCardProps) {
  return (
    <div className="glass-panel hover-lift px-5 py-4 flex-1 min-w-[140px]">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg">{icon}</span>
        <span className="text-xs font-mono uppercase tracking-wider" style={{ color: '#64748b' }}>
          {label}
        </span>
      </div>
      <div
        className="text-2xl font-mono font-semibold tracking-tight"
        style={{ color: accentColor || '#e2e8f0', transition: 'all 0.3s ease' }}
      >
        {value}
      </div>
    </div>
  );
}

export default function StatsBar({ stats, connectionStatus, eventsInView }: StatsBarProps) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <StatCard
        icon="🗄️"
        label="Total Events"
        value={stats?.total_events?.toLocaleString() ?? '—'}
        accentColor="#e2e8f0"
      />
      <StatCard
        icon="📊"
        label="Live Rate"
        value={stats ? `${stats.events_last_minute}/min` : '—'}
        accentColor={connectionStatus === 'connected' ? '#00ff88' : '#64748b'}
      />
      <StatCard
        icon="📋"
        label="Tables Tracked"
        value={stats?.tables_count ?? '—'}
        accentColor="#3b82f6"
      />
      <StatCard
        icon="👁️"
        label="In View"
        value={eventsInView}
        accentColor="#ffaa00"
      />
    </div>
  );
}
