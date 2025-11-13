'use client';

import { useState } from 'react';
import { useAppStore } from '@/lib/store';
import { FileText, Upload, Check } from 'lucide-react';
import PaperUploadModal from './PaperUploadModal';

export default function PaperList() {
  const { papers, selectedPaper, setSelectedPaper, addLog } = useAppStore();
  const [showUploadModal, setShowUploadModal] = useState(false);

  const handleSelectPaper = (paper: typeof papers[0]) => {
    setSelectedPaper(paper);
    addLog(`論文を選択しました: ${paper.id}`, 'info');
  };

  return (
    <>
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-900">論文一覧</h2>
          <button
            onClick={() => setShowUploadModal(true)}
            className="flex items-center space-x-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
          >
            <Upload className="w-4 h-4" />
            <span>アップロード</span>
          </button>
        </div>

        <div className="space-y-2">
          {papers.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              論文がありません
            </p>
          ) : (
            papers.map((paper) => (
              <button
                key={paper.id}
                onClick={() => handleSelectPaper(paper)}
                className={`w-full flex items-center space-x-3 p-3 rounded-lg transition-colors ${
                  selectedPaper?.id === paper.id
                    ? 'bg-blue-50 border-2 border-blue-500'
                    : 'bg-gray-50 border-2 border-transparent hover:bg-gray-100'
                }`}
              >
                <FileText
                  className={`w-5 h-5 ${
                    selectedPaper?.id === paper.id
                      ? 'text-blue-600'
                      : 'text-gray-400'
                  }`}
                />
                <span className="flex-1 text-left font-medium text-gray-900">
                  {paper.id}
                </span>
                {selectedPaper?.id === paper.id && (
                  <Check className="w-5 h-5 text-blue-600" />
                )}
              </button>
            ))
          )}
        </div>
      </div>

      {showUploadModal && (
        <PaperUploadModal onClose={() => setShowUploadModal(false)} />
      )}
    </>
  );
}
