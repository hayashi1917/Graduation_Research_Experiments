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
    console.log(`[PhaseControls] executePhase呼び出し: phase=${phase}`);

    if (!selectedPaper) {
      console.error('[PhaseControls] 論文が選択されていません');
      toast.error('論文を選択してください');
      return;
    }
    console.log(`[PhaseControls] 選択された論文: ${selectedPaper.id}`);

    if (!wsManager) {
      console.error('[PhaseControls] WebSocketマネージャーがありません');
      toast.error('WebSocket接続がありません');
      return;
    }
    console.log(`[PhaseControls] WebSocket接続状態: ${wsManager.isConnected()}`);

    setIsExecuting(true);
    setCurrentPhase(phase);
    addLog(`${phase}を開始します`, 'info');

    // Send start command through WebSocket
    const message = {
      type: 'start_phase',
      phase,
      paper_id: selectedPaper.id,
    };
    console.log('[PhaseControls] メッセージ送信:', message);
    wsManager.sendMessage(message);
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
    { id: 'phase1', label: 'Phase 1 - クリーン化', color: 'blue' },
    { id: 'phase2', label: 'Phase 2 - 誤り埋め込み', color: 'green' },
    { id: 'phase3', label: 'Phase 3 - 校正', color: 'purple' },
  ];

  // Tailwind CSS requires complete class names (can't use template literals)
  const phaseStyles: Record<string, string> = {
    blue: 'bg-blue-100 border-2 border-blue-500',
    green: 'bg-green-100 border-2 border-green-500',
    purple: 'bg-purple-100 border-2 border-purple-500',
  };

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
                ? phaseStyles[phase.color]
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
