'use client';

import { useState } from 'react';
import { X, Trash2 } from 'lucide-react';
import { dataAPI } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import toast from 'react-hot-toast';

interface ResetModalProps {
  onClose: () => void;
}

export default function ResetModal({ onClose }: ResetModalProps) {
  const [resetResults, setResetResults] = useState(false);
  const [resetVersions, setResetVersions] = useState(false);
  const [resetProgress, setResetProgress] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const { addLog } = useAppStore();

  const handleReset = async () => {
    if (!resetResults && !resetVersions && !resetProgress) {
      toast.error('削除する項目を選択してください');
      return;
    }

    if (!confirm('本当にデータを削除しますか？この操作は取り消せません。')) {
      return;
    }

    setIsResetting(true);
    try {
      const response = await dataAPI.reset({
        reset_results: resetResults,
        reset_versions: resetVersions,
        reset_progress: resetProgress,
      });

      if (response.success) {
        toast.success('データを削除しました');
        addLog(`データを削除しました: ${response.deleted_items.join(', ')}`, 'success');
        onClose();
      } else {
        toast.error(response.error || 'データの削除に失敗しました');
        addLog(`データの削除に失敗しました: ${response.error}`, 'error');
      }
    } catch (error) {
      toast.error('データの削除に失敗しました');
      addLog('データの削除に失敗しました', 'error');
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h3 className="text-xl font-bold text-gray-900">データリセット</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <p className="text-sm text-gray-600 mb-4">
            削除する項目を選択してください。この操作は取り消せません。
          </p>

          <label className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 cursor-pointer">
            <input
              type="checkbox"
              checked={resetResults}
              onChange={(e) => setResetResults(e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              disabled={isResetting}
            />
            <div className="flex-1">
              <p className="font-medium text-gray-900">実験結果</p>
              <p className="text-xs text-gray-500">
                CSV/JSONファイル (results/*.csv, results/*.json)
              </p>
            </div>
          </label>

          <label className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 cursor-pointer">
            <input
              type="checkbox"
              checked={resetVersions}
              onChange={(e) => setResetVersions(e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              disabled={isResetting}
            />
            <div className="flex-1">
              <p className="font-medium text-gray-900">バージョン履歴</p>
              <p className="text-xs text-gray-500">versions/ ディレクトリ</p>
            </div>
          </label>

          <label className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 cursor-pointer">
            <input
              type="checkbox"
              checked={resetProgress}
              onChange={(e) => setResetProgress(e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              disabled={isResetting}
            />
            <div className="flex-1">
              <p className="font-medium text-gray-900">進捗情報</p>
              <p className="text-xs text-gray-500">progress.json ファイル</p>
            </div>
          </label>
        </div>

        <div className="flex space-x-3 p-6 border-t border-gray-200">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            disabled={isResetting}
          >
            キャンセル
          </button>
          <button
            onClick={handleReset}
            className="flex-1 flex items-center justify-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:bg-gray-400"
            disabled={isResetting}
          >
            {isResetting ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>削除中...</span>
              </>
            ) : (
              <>
                <Trash2 className="w-4 h-4" />
                <span>削除</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
