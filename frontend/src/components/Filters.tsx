import type { TableInfo } from '../types/events';

interface FiltersProps {
  tables: TableInfo[];
  filters: { table_name: string; operation: string };
  onFilterChange: (filters: { table_name: string; operation: string }) => void;
}

const OPERATIONS = [
  { value: '', label: 'ALL', color: '#e2e8f0', bg: 'rgba(255,255,255,0.06)' },
  { value: 'INSERT', label: 'INSERT', color: '#00ff88', bg: 'rgba(0,255,136,0.1)' },
  { value: 'UPDATE', label: 'UPDATE', color: '#ffaa00', bg: 'rgba(255,170,0,0.1)' },
  { value: 'DELETE', label: 'DELETE', color: '#ff3366', bg: 'rgba(255,51,102,0.1)' },
];

export default function Filters({ tables, filters, onFilterChange }: FiltersProps) {
  return (
    <div className="glass-panel px-5 py-4">
      <div className="flex flex-wrap items-center gap-4">
        {/* Table Filter */}
        <div className="flex items-center gap-2">
          <label className="text-xs font-mono uppercase tracking-wider" style={{ color: '#64748b' }}>
            Table
          </label>
          <select
            id="table-filter"
            value={filters.table_name}
            onChange={(e) => onFilterChange({ ...filters, table_name: e.target.value })}
            className="font-mono text-sm px-3 py-1.5 rounded-lg outline-none cursor-pointer"
            style={{
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.1)',
              color: '#e2e8f0',
            }}
          >
            <option value="">All Tables</option>
            {tables.map((t) => (
              <option key={t.name} value={t.name}>
                {t.name} ({t.event_count})
              </option>
            ))}
          </select>
        </div>

        {/* Operation Filter */}
        <div className="flex items-center gap-2">
          <label className="text-xs font-mono uppercase tracking-wider" style={{ color: '#64748b' }}>
            Operation
          </label>
          <div className="flex gap-1">
            {OPERATIONS.map((op) => {
              const isActive = filters.operation === op.value;
              return (
                <button
                  key={op.value}
                  id={`op-filter-${op.value || 'all'}`}
                  onClick={() => onFilterChange({ ...filters, operation: op.value })}
                  className="font-mono text-xs px-3 py-1.5 rounded-md transition-all duration-200"
                  style={{
                    background: isActive ? op.bg : 'transparent',
                    color: isActive ? op.color : '#64748b',
                    border: isActive ? `1px solid ${op.color}40` : '1px solid transparent',
                    boxShadow: isActive ? `0 0 8px ${op.color}20` : 'none',
                  }}
                >
                  {op.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Clear Filters */}
        {(filters.table_name || filters.operation) && (
          <button
            id="clear-filters"
            onClick={() => onFilterChange({ table_name: '', operation: '' })}
            className="font-mono text-xs px-3 py-1.5 rounded-md transition-all duration-200"
            style={{
              background: 'rgba(255,255,255,0.04)',
              color: '#64748b',
              border: '1px solid rgba(255,255,255,0.08)',
            }}
          >
            ✕ Clear
          </button>
        )}
      </div>
    </div>
  );
}
