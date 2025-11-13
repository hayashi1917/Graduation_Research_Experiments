'use client';

import { useEffect, useRef } from 'react';
import { useAppStore } from '@/lib/store';
import { Terminal, AlertCircle, Info, CheckCircle, AlertTriangle } from 'lucide-react';

export default function LogOutput() {
  const { logs } = useAppStore();
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Auto-scroll to bottom when new logs arrive
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const getLogIcon = (level: string) => {
    switch (level) {
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-yellow-400 flex-shrink-0" />;
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />;
      default:
        return <Info className="w-4 h-4 text-blue-400 flex-shrink-0" />;
    }
  };

  const getLogColor = (level: string) => {
    switch (level) {
      case 'error':
        return 'text-red-400';
      case 'warning':
        return 'text-yellow-400';
      case 'success':
        return 'text-green-400';
      default:
        return 'text-gray-300';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      <div className="flex items-center space-x-2 px-4 py-3 bg-gray-800 border-b border-gray-700">
        <Terminal className="w-5 h-5 text-green-400" />
        <h2 className="text-lg font-semibold text-white">ログ出力</h2>
      </div>

      <div className="log-output h-96 overflow-y-auto p-4 space-y-1">
        {logs.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-500">ログがありません</p>
          </div>
        ) : (
          logs.map((log, index) => (
            <div key={index} className="flex items-start space-x-3 py-1 hover:bg-gray-800 px-2 rounded">
              {getLogIcon(log.level)}
              <span className="text-xs text-gray-500 flex-shrink-0 w-20 font-mono">
                {log.timestamp}
              </span>
              <span className={`text-sm flex-1 ${getLogColor(log.level)} break-words`}>
                {log.message}
              </span>
            </div>
          ))
        )}
        <div ref={logEndRef} />
      </div>
    </div>
  );
}
