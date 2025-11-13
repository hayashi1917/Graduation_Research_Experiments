'use client';

import { useState } from 'react';
import { useAppStore } from '@/lib/store';
import { Play, Square } from 'lucide-react';
import { WebSocketManager } from '@/lib/websocket';
import toast from 'react-hot-toast';

interface PhaseControlsProps {
  wsManager: WebSocketManager | null;
}

export default function PhaseControls({ wsManager }: PhaseControlsProps) {
  const { selectedPaper, currentPhase, setCurrentPhase, addLog } = useAppStore();
  const [isExecuting, setIsExecuting] = useState(false);

  const executePhase = (phase: string) => {
    if (!selectedPaper) {
      toast.error('論文を選択してください');
      return;
    }

    if (!wsManager) {
      toast.error('WebSocket接続がありません');
      return;
    }

    setIsExecuting(true);
    setCurrentPhase(phase);
    addLog(`${phase}を開始します`, 'info');

    // Send start command through WebSocket
    wsManager.sendMessage({
      type: 'start_phase',
      phase,
      paper_id: selectedPaper.id,
    });
  };

  const stopExecution = () => {
    if (wsManager) {
      wsManager.sendAction('abort');
      addLog('実行を中止しました', 'warning');
    }
    setIsExecuting(false);
    setCurrentPhase(null);
  };

  const phases = [
    { id: 'phase1', label: 'Phase 1 - 初回校正', color: 'blue' },
    { id: 'phase2', label: 'Phase 2 - 埋め込み誤り検出', color: 'green' },
    { id: 'phase3', label: 'Phase 3 - クリーン化', color: 'purple' },
  ];

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">Phase実行</h2>

      <div className="space-y-3">
        {phases.map((phase) => (
          <button
            key={phase.id}
            onClick={() => executePhase(phase.id)}
            disabled={isExecuting || !selectedPaper}
            className={`w-full flex items-center justify-between p-4 rounded-lg transition-colors ${
              currentPhase === phase.id
                ? `bg-${phase.color}-100 border-2 border-${phase.color}-500`
                : `bg-gray-50 hover:bg-gray-100 border-2 border-transparent ${
                    !selectedPaper || isExecuting
                      ? 'opacity-50 cursor-not-allowed'
                      : ''
                  }`
            }`}
          >
            <span className="font-medium text-gray-900">{phase.label}</span>
            {currentPhase === phase.id ? (
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                <span className="text-sm text-gray-600">実行中</span>
              </div>
            ) : (
              <Play className="w-5 h-5 text-gray-400" />
            )}
          </button>
        ))}
      </div>

      {isExecuting && (
        <button
          onClick={stopExecution}
          className="w-full mt-4 flex items-center justify-center space-x-2 px-4 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
        >
          <Square className="w-4 h-4" />
          <span>中止</span>
        </button>
      )}

      {!selectedPaper && (
        <p className="mt-4 text-sm text-gray-500 text-center">
          論文を選択してください
        </p>
      )}
    </div>
  );
}
