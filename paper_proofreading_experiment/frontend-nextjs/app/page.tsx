'use client';

import { useEffect, useState } from 'react';
import { useAppStore } from '@/lib/store';
import { papersAPI } from '@/lib/api';
import { WebSocketManager } from '@/lib/websocket';
import Header from '@/components/Header';
import PaperList from '@/components/PaperList';
import PhaseControls from '@/components/PhaseControls';
import Phase1Selector from '@/components/Phase1Selector';
import IssueCard from '@/components/IssueCard';
import LogOutput from '@/components/LogOutput';
import toast from 'react-hot-toast';

let wsManager: WebSocketManager | null = null;

export default function Home() {
  const [isLoading, setIsLoading] = useState(true);
  const { setPapers, addLog, currentPhase, selectedPaper } = useAppStore();

  useEffect(() => {
    // Initialize WebSocket
    if (!wsManager) {
      wsManager = new WebSocketManager();
      wsManager.connect();
      addLog('WebSocket接続を確立しました', 'info');
    }

    // Load papers
    const loadPapers = async () => {
      try {
        const papers = await papersAPI.list();
        setPapers(papers);
        addLog(`${papers.length}件の論文を読み込みました`, 'info');
      } catch (error) {
        addLog('論文の読み込みに失敗しました', 'error');
        toast.error('論文の読み込みに失敗しました');
      } finally {
        setIsLoading(false);
      }
    };

    loadPapers();

    // Cleanup on unmount
    return () => {
      if (wsManager) {
        wsManager.disconnect();
      }
    };
  }, [setPapers, addLog]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">読み込み中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column - Paper list and Phase controls */}
          <div className="lg:col-span-1 space-y-6">
            <PaperList />

            {selectedPaper && (
              <>
                <PhaseControls wsManager={wsManager} />
                {(currentPhase === 'phase2' || currentPhase === 'phase3') && (
                  <Phase1Selector />
                )}
              </>
            )}
          </div>

          {/* Right column - Issue display and logs */}
          <div className="lg:col-span-2 space-y-6">
            <IssueCard />
            <LogOutput />
          </div>
        </div>
      </main>
    </div>
  );
}
