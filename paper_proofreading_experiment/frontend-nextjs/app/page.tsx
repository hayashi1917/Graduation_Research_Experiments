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
import UserChoiceDialog from '@/components/UserChoiceDialog';
import toast from 'react-hot-toast';

let wsManager: WebSocketManager | null = null;

export default function Home() {
  const [isLoading, setIsLoading] = useState(true);
  const [showChoiceDialog, setShowChoiceDialog] = useState(false);
  const [choiceMessage, setChoiceMessage] = useState('');
  const [choiceOptions, setChoiceOptions] = useState<string[]>([]);
  const {
    setPapers,
    addLog,
    currentPhase,
    selectedPaper,
    setCurrentIssue,
    setTotalIssues,
    setCurrentIteration,
    setIsRunning,
    setCurrentPhase,
  } = useAppStore();

  useEffect(() => {
    console.log('[Page] useEffect開始');

    // Initialize WebSocket
    if (!wsManager) {
      console.log('[Page] WebSocketマネージャーを初期化');
      wsManager = new WebSocketManager();

      // Register message handler
      const handleMessage = (message: any) => {
        console.log('[Page] メッセージハンドラー実行:', message);

        switch (message.type) {
          case 'phase_start':
            console.log('[Page] フェーズ開始メッセージ:', message);
            addLog(message.message || 'フェーズを開始しました', 'info');
            setIsRunning(true);
            break;

          case 'phase_complete':
            console.log('[Page] フェーズ完了メッセージ:', message);
            addLog(message.message || 'フェーズが完了しました', 'success');
            setIsRunning(false);
            setCurrentPhase(null);
            setCurrentIssue(null);  // 指摘事項をクリア
            toast.success(message.message || 'フェーズが完了しました');
            break;

          case 'iteration_start':
            console.log('[Page] イテレーション開始:', message);
            addLog(`イテレーション ${message.iteration} を開始`, 'info');
            setCurrentIteration(message.iteration || 0);
            break;

          case 'user_action_required':
            console.log('[Page] ユーザーアクション要求:', message);
            addLog('ユーザーの判断が必要です', 'warning');
            if (message.issue) {
              setCurrentIssue(message.issue);
            }
            break;

          case 'user_choice_required':
            console.log('[Page] ユーザー選択要求:', message);
            addLog(message.message || 'ユーザーの選択が必要です', 'warning');
            setChoiceMessage(message.message || '選択してください');
            setChoiceOptions(message.choices || ['Y', 'N']);
            setShowChoiceDialog(true);
            break;

          case 'issue_detected':
            console.log('[Page] 指摘事項検出:', message);
            if (message.issue) {
              setCurrentIssue(message.issue);
            }
            if (message.total_issues) {
              setTotalIssues(message.total_issues);
            }
            if (message.issue_number && message.total_issues) {
              addLog(`指摘事項 ${message.issue_number}/${message.total_issues} を検出`, 'info');
            }
            break;

          case 'action_received':
            console.log('[Page] アクション受信確認:', message);
            addLog(`アクション受信: ${message.action}`, 'info');
            break;

          case 'error':
            console.error('[Page] エラーメッセージ:', message);
            addLog(`エラー: ${message.message}`, 'error');
            toast.error(message.message || 'エラーが発生しました');
            setIsRunning(false);
            break;

          case 'log':
            console.log('[Page] ログメッセージ:', message);
            addLog(message.message, message.level || 'info');
            break;

          default:
            console.warn('[Page] 不明なメッセージタイプ:', message.type, message);
        }
      };

      wsManager.addMessageHandler(handleMessage);
      console.log('[Page] メッセージハンドラーを登録しました');

      wsManager.connect();
      addLog('WebSocket接続を確立しました', 'info');
    }

    // Load papers
    const loadPapers = async () => {
      console.log('[Page] 論文読み込み開始');
      try {
        const papers = await papersAPI.list();
        setPapers(papers);
        addLog(`${papers.length}件の論文を読み込みました`, 'info');
        console.log(`[Page] ${papers.length}件の論文を読み込みました`);
      } catch (error) {
        console.error('[Page] 論文読み込みエラー:', error);
        addLog('論文の読み込みに失敗しました', 'error');
        toast.error('論文の読み込みに失敗しました');
      } finally {
        setIsLoading(false);
      }
    };

    loadPapers();

    // Cleanup on unmount
    return () => {
      console.log('[Page] クリーンアップ');
      if (wsManager) {
        wsManager.disconnect();
      }
    };
  }, [setPapers, addLog, setCurrentIssue, setTotalIssues, setCurrentIteration, setIsRunning, setCurrentPhase]);

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

  const handleChoice = (choice: string) => {
    if (wsManager) {
      wsManager.sendAction(choice);
      addLog(`選択: ${choice}`, 'info');
    }
  };

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
            <IssueCard wsManager={wsManager} />
            <LogOutput />
          </div>
        </div>
      </main>

      {/* User choice dialog */}
      {showChoiceDialog && (
        <UserChoiceDialog
          message={choiceMessage}
          choices={choiceOptions}
          onChoice={handleChoice}
          onClose={() => setShowChoiceDialog(false)}
        />
      )}
    </div>
  );
}
