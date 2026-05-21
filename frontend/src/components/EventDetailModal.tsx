import React from 'react';
import { CDCEvent } from '../types/events';

interface EventDetailModalProps {
  event: CDCEvent | null;
  onClose: () => void;
}

const highlightJson = (json: string) => {
  if (!json) return '';
  return json.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
    (match) => {
      let cls = 'text-amber-500'; // number
      if (/^"/.test(match)) {
        if (/:$/.test(match)) {
          cls = 'text-blue-400'; // key
        } else {
          cls = 'text-green-400'; // string
        }
      } else if (/true|false|null/.test(match)) {
        cls = 'text-coral-500'; // boolean/null
      }
      return `<span class="${cls}">${match}</span>`;
    }
  );
};

const EventDetailModal: React.FC<EventDetailModalProps> = ({ event, onClose }) => {
  if (!event) return null;

  const getBadgeClass = (op: string) => {
    switch (op) {
      case 'INSERT': return 'badge-insert';
      case 'UPDATE': return 'badge-update';
      case 'DELETE': return 'badge-delete';
      default: return 'bg-slate-700 text-slate-300';
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(event.payload, null, 2));
    // Could add a small toast notification here
  };

  const formattedJson = highlightJson(JSON.stringify(event.payload, null, 2));

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-[fadeIn_0.2s_ease-out]">
      {/* Background overlay click to close */}
      <div className="absolute inset-0" onClick={onClose}></div>
      
      {/* Modal content */}
      <div className="glass-panel w-full max-w-2xl max-h-[85vh] flex flex-col relative rounded-xl shadow-2xl shadow-black/50 border border-slate-700/50">
        
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700/50">
          <div className="flex items-center gap-3">
            <span className={`px-2.5 py-0.5 rounded text-xs font-bold tracking-wider ${getBadgeClass(event.operation)}`}>
              {event.operation}
            </span>
            <h2 className="text-lg font-semibold text-slate-200 flex items-center gap-2">
              <span className="text-slate-500">table:</span>
              <span className="text-blue-400 font-mono">{event.table_name}</span>
            </h2>
          </div>
          <button 
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors p-1 rounded-md hover:bg-slate-800"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
          </button>
        </div>

        {/* Body (scrollable) */}
        <div className="p-6 overflow-y-auto custom-scrollbar">
          
          {/* Metadata Grid */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-slate-800/30 p-3 rounded-lg border border-slate-700/30">
              <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Event ID</div>
              <div className="font-mono text-sm text-slate-300 break-all">{event.id}</div>
            </div>
            <div className="bg-slate-800/30 p-3 rounded-lg border border-slate-700/30">
              <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Timestamp</div>
              <div className="font-mono text-sm text-slate-300">
                {new Date(event.created_at).toLocaleString()}
              </div>
            </div>
          </div>

          {/* Payload JSON */}
          <div className="relative">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-slate-300">Payload</h3>
              <button 
                onClick={handleCopy}
                className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1 rounded border border-slate-600 transition-colors flex items-center gap-1"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                Copy JSON
              </button>
            </div>
            <div className="bg-[#0d1117] p-4 rounded-lg border border-slate-700/50 overflow-x-auto custom-scrollbar">
              <pre 
                className="font-mono text-sm leading-relaxed"
                dangerouslySetInnerHTML={{ __html: formattedJson }}
              />
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default EventDetailModal;
