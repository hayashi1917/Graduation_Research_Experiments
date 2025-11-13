'use client';

import { useState } from 'react';
import { RotateCcw, FileText } from 'lucide-react';
import ResetModal from './ResetModal';

export default function Header() {
  const [showResetModal, setShowResetModal] = useState(false);

  return (
    <>
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <FileText className="w-8 h-8 text-blue-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  Paper Proofreading Experiment
                </h1>
                <p className="text-sm text-gray-600">
                  学術論文校正実験システム
                </p>
              </div>
            </div>

            <button
              onClick={() => setShowResetModal(true)}
              className="flex items-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
              <span>リセット</span>
            </button>
          </div>
        </div>
      </header>

      {showResetModal && (
        <ResetModal onClose={() => setShowResetModal(false)} />
      )}
    </>
  );
}
