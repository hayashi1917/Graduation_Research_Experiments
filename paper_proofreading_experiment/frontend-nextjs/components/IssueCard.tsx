'use client';

import { useState } from 'react';
import { useAppStore } from '@/lib/store';
import { Copy, CheckCircle, AlertCircle } from 'lucide-react';
import { copyToClipboard } from '@/lib/utils';
import toast from 'react-hot-toast';

export default function IssueCard() {
  const { currentIssue, currentPhase } = useAppStore();
  const [copiedField, setCopiedField] = useState<string | null>(null);

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
    </div>
  );
}
