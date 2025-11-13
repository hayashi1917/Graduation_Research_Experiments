'use client';

import { useEffect, useState } from 'react';
import { useAppStore } from '@/lib/store';
import { dataAPI } from '@/lib/api';
import { Clock, Check, AlertCircle } from 'lucide-react';
import { formatDateTime } from '@/lib/utils';
import toast from 'react-hot-toast';

export default function Phase1Selector() {
  const {
    selectedPaper,
    phase1Sessions,
    setPhase1Sessions,
    selectedPhase1,
    setSelectedPhase1,
    addLog,
  } = useAppStore();

  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (selectedPaper) {
      loadPhase1Sessions();
    }
  }, [selectedPaper]);

  const loadPhase1Sessions = async () => {
    if (!selectedPaper) return;

    setIsLoading(true);
    try {
      const sessions = await dataAPI.getPhase1Sessions(selectedPaper.id);
      setPhase1Sessions(sessions);

      // Auto-select the most recent completed session
      const completedSessions = sessions.filter(
        (s) => s.status === 'completed'
      );
      if (completedSessions.length > 0 && !selectedPhase1) {
        setSelectedPhase1(completedSessions[0]);
      }
    } catch (error) {
      toast.error('Phase1セッションの読み込みに失敗しました');
      addLog('Phase1セッションの読み込みに失敗しました', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusInfo = (status: string) => {
    switch (status) {
      case 'completed':
        return { icon: Check, color: 'text-green-600', label: '完了' };
      case 'in_progress':
        return { icon: Clock, color: 'text-blue-600', label: '実行中' };
      case 'aborted':
        return { icon: AlertCircle, color: 'text-red-600', label: '中止' };
      default:
        return { icon: Clock, color: 'text-gray-600', label: '不明' };
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">
          Phase1セッション選択
        </h2>
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">
        Phase1セッション選択
      </h2>

      {phase1Sessions.length === 0 ? (
        <p className="text-gray-500 text-center py-8">
          Phase1セッションがありません
          <br />
          <span className="text-sm">先にPhase1を実行してください</span>
        </p>
      ) : (
        <div className="space-y-2">
          {phase1Sessions.map((session) => {
            const statusInfo = getStatusInfo(session.status);
            const StatusIcon = statusInfo.icon;

            return (
              <button
                key={session.phase1_id}
                onClick={() => {
                  setSelectedPhase1(session);
                  addLog(`Phase1セッション ${session.phase1_id} を選択しました`, 'info');
                }}
                className={`w-full p-4 rounded-lg transition-colors ${
                  selectedPhase1?.phase1_id === session.phase1_id
                    ? 'bg-blue-50 border-2 border-blue-500'
                    : 'bg-gray-50 border-2 border-transparent hover:bg-gray-100'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 text-left">
                    <div className="flex items-center space-x-2 mb-2">
                      <StatusIcon className={`w-4 h-4 ${statusInfo.color}`} />
                      <span className={`text-sm font-medium ${statusInfo.color}`}>
                        {statusInfo.label}
                      </span>
                    </div>
                    <p className="text-sm text-gray-900 font-medium mb-1">
                      {session.phase1_id}
                    </p>
                    <p className="text-xs text-gray-600">
                      開始: {formatDateTime(session.started_at)}
                    </p>
                    {session.completed_at && (
                      <p className="text-xs text-gray-600">
                        完了: {formatDateTime(session.completed_at)}
                      </p>
                    )}
                    <p className="text-xs text-gray-600 mt-1">
                      Iterations: {session.iterations}
                    </p>
                  </div>
                  {selectedPhase1?.phase1_id === session.phase1_id && (
                    <Check className="w-5 h-5 text-blue-600 flex-shrink-0" />
                  )}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
