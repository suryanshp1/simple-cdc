import type { ConnectionStatus } from '../types/events';

interface ConnectionStatusProps {
  status: ConnectionStatus;
}

export default function ConnectionStatusIndicator({ status }: ConnectionStatusProps) {
  const config: Record<ConnectionStatus, { label: string; dotClass: string; textColor: string }> = {
    connected: {
      label: 'Connected',
      dotClass: 'status-dot status-dot-connected',
      textColor: '#00ff88',
    },
    disconnected: {
      label: 'Disconnected',
      dotClass: 'status-dot status-dot-disconnected',
      textColor: '#ff3366',
    },
    reconnecting: {
      label: 'Reconnecting...',
      dotClass: 'status-dot status-dot-reconnecting',
      textColor: '#ffaa00',
    },
  };

  const { label, dotClass, textColor } = config[status];

  return (
    <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-full" style={{ background: 'rgba(255,255,255,0.04)' }}>
      <span className={dotClass} />
      <span className="font-mono text-xs font-medium" style={{ color: textColor }}>
        {label}
      </span>
    </div>
  );
}
