'use client';

import { useState, FormEvent } from 'react';
import { X, Upload } from 'lucide-react';
import { papersAPI } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import toast from 'react-hot-toast';

interface PaperUploadModalProps {
  onClose: () => void;
}

export default function PaperUploadModal({ onClose }: PaperUploadModalProps) {
  const [paperId, setPaperId] = useState('');
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [texFile, setTexFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const { addLog, setPapers } = useAppStore();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (!paperId || !pdfFile || !texFile) {
      toast.error('すべての項目を入力してください');
      return;
    }

    setIsUploading(true);
    try {
      await papersAPI.upload(paperId, pdfFile, texFile);
      toast.success(`論文 ${paperId} をアップロードしました`);
      addLog(`論文 ${paperId} をアップロードしました`, 'success');

      // Reload papers
      const papers = await papersAPI.list();
      setPapers(papers);

      onClose();
    } catch (error) {
      toast.error('アップロードに失敗しました');
      addLog('アップロードに失敗しました', 'error');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h3 className="text-xl font-bold text-gray-900">論文アップロード</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              論文ID
            </label>
            <input
              type="text"
              value={paperId}
              onChange={(e) => setPaperId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="例: paper001"
              disabled={isUploading}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              PDFファイル
            </label>
            <input
              type="file"
              accept=".pdf"
              onChange={(e) => setPdfFile(e.target.files?.[0] || null)}
              className="w-full"
              disabled={isUploading}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              TeXファイル
            </label>
            <input
              type="file"
              accept=".tex"
              onChange={(e) => setTexFile(e.target.files?.[0] || null)}
              className="w-full"
              disabled={isUploading}
            />
          </div>

          <div className="flex space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              disabled={isUploading}
            >
              キャンセル
            </button>
            <button
              type="submit"
              className="flex-1 flex items-center justify-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400"
              disabled={isUploading}
            >
              {isUploading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>アップロード中...</span>
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  <span>アップロード</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
