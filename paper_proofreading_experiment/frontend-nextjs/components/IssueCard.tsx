'use client';

import { useState } from 'react';
import { useAppStore } from '@/lib/store';
import { Copy, CheckCircle, AlertCircle, Edit, SkipForward, XCircle } from 'lucide-react';
import { copyToClipboard } from '@/lib/utils';
import { WebSocketManager } from '@/lib/websocket';
import toast from 'react-hot-toast';

interface IssueCardProps {
  wsManager: WebSocketManager | null;
}

export default function IssueCard({ wsManager }: IssueCardProps) {
  const { currentIssue, currentPhase, isRunning } = useAppStore();
  const [copiedField, setCopiedField] = useState<string | null>(null);

  // デバッグ用ログ
  console.log('[IssueCard] 状態:', {
    hasIssue: !!currentIssue,
    isRunning,
    hasWsManager: !!wsManager,
    shouldShowButtons: isRunning && !!wsManager,
    currentPhase,
  });

  if (!currentIssue) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">指摘事項</h2>
        <div className="text-center py-12 text-gray-500">
          <AlertCircle className="w-12 h-12 mx-auto mb-4 text-gray-300" />
          <p>指摘事項がありません</p>
          <p className="text-sm mt-2">Phaseを実行すると表示されます</p>
        </div>
      </div>
    );
  }

  const handleCopy = async (text: string, field: string) => {
    const success = await copyToClipboard(text);
    if (success) {
      setCopiedField(field);
      toast.success('コピーしました');
      setTimeout(() => setCopiedField(null), 1500);
    } else {
      toast.error('コピーに失敗しました');
    }
  };

  const handleAction = (action: string, label: string) => {
    if (!wsManager) {
      toast.error('WebSocket接続がありません');
      return;
    }

    wsManager.sendAction(action);
    toast.success(`${label}を選択しました`);
  };

  const CopyButton = ({ text, field }: { text: string; field: string }) => {
    const isCopied = copiedField === field;

    return (
      <button
        onClick={() => handleCopy(text, field)}
        className={`flex items-center space-x-1 px-3 py-1 rounded-md transition-colors text-sm ${
          isCopied
            ? 'bg-green-100 text-green-700'
            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
        }`}
      >
        {isCopied ? (
          <>
            <CheckCircle className="w-4 h-4" />
            <span>コピー完了</span>
          </>
        ) : (
          <>
            <Copy className="w-4 h-4" />
            <span>コピー</span>
          </>
        )}
      </button>
    );
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-900">指摘事項</h2>
        <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
          Issue #{currentIssue.issue_number}
        </span>
      </div>

      <div className="space-y-6">
        {/* Before */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-semibold text-gray-700">
              修正前の文:
            </label>
            <CopyButton text={currentIssue.before} field="before" />
          </div>
          <pre className="bg-red-50 border border-red-200 p-4 rounded-lg text-sm whitespace-pre-wrap break-words font-mono text-gray-900">
            {currentIssue.before}
          </pre>
        </div>

        {/* Reasoning */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-semibold text-gray-700">
              理由:
            </label>
            <CopyButton text={currentIssue.reasoning} field="reasoning" />
          </div>
          <div className="bg-yellow-50 border border-yellow-200 p-4 rounded-lg text-sm text-gray-900">
            {currentIssue.reasoning}
          </div>
        </div>

        {/* After */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-semibold text-gray-700">
              修正後の文:
            </label>
            <CopyButton text={currentIssue.after} field="after" />
          </div>
          <pre className="bg-green-50 border border-green-200 p-4 rounded-lg text-sm whitespace-pre-wrap break-words font-mono text-gray-900">
            {currentIssue.after}
          </pre>
        </div>
      </div>

      <div className="mt-6 p-4 bg-gray-50 rounded-lg">
        <p className="text-sm text-gray-600">
          <span className="font-semibold">現在のPhase:</span>{' '}
          {currentPhase || '実行中ではありません'}
        </p>
      </div>

      {/* Action Buttons */}
      {isRunning && wsManager && (
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">この指摘への対応を選択してください：</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
            {/* Manual */}
            <button
              onClick={() => handleAction('M', '手動修正')}
              className="flex items-center justify-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              <Edit className="w-4 h-4" />
              <span>手動修正 (M)</span>
            </button>

            {/* Skip */}
            <button
              onClick={() => handleAction('S', 'スキップ')}
              className="flex items-center justify-center space-x-2 px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 transition-colors"
            >
              <SkipForward className="w-4 h-4" />
              <span>スキップ (S)</span>
            </button>

            {/* Quit */}
            <button
              onClick={() => handleAction('Q', '中断')}
              className="flex items-center justify-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
            >
              <XCircle className="w-4 h-4" />
              <span>中断 (Q)</span>
            </button>
          </div>
          <p className="text-xs text-gray-600 mt-3">
            ※ 手動修正: 後で手動で修正 | スキップ: 誤検出として該当項目を除外 | 中断: フェーズを終了
          </p>
        </div>
      )}
    </div>
  );
}
