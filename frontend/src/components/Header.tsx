import type { ConnectionStatus } from '../types/events';
import ConnectionStatusIndicator from './ConnectionStatus';

interface HeaderProps {
  connectionStatus: ConnectionStatus;
}

export default function Header({ connectionStatus }: HeaderProps) {
  return (
    <header className="glass-panel sticky top-0 z-50 px-6 py-4" style={{ borderRadius: '0 0 16px 16px' }}>
      <div className="flex items-center justify-between max-w-7xl mx-auto">
        <div className="flex items-center gap-3">
          <div className="relative">
            <span className="text-2xl" role="img" aria-label="lightning">
              ⚡
            </span>
            <div
              className="absolute inset-0 blur-lg opacity-40"
              style={{ background: 'radial-gradient(circle, #3b82f6 0%, transparent 70%)' }}
            />
          </div>
          <div>
            <h1 className="text-xl font-semibold tracking-tight">
              <span style={{ color: '#e2e8f0' }}>Simple</span>
              <span style={{ color: '#3b82f6' }}>CDC</span>
            </h1>
            <p className="text-xs font-mono" style={{ color: '#64748b' }}>
              Real-time Change Data Capture
            </p>
          </div>
        </div>
        <ConnectionStatusIndicator status={connectionStatus} />
      </div>
    </header>
  );
}
