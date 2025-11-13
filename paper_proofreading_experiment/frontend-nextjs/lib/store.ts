/**
 * Global state management with Zustand
 */
import { create } from 'zustand';
import { Paper, Phase1Session, ProofreadingIssue } from '@/types';

interface AppState {
  // Selected paper
  selectedPaper: Paper | null;
  setSelectedPaper: (paper: Paper | null) => void;

  // Papers list
  papers: Paper[];
  setPapers: (papers: Paper[]) => void;

  // Phase1 sessions
  phase1Sessions: Phase1Session[];
  setPhase1Sessions: (sessions: Phase1Session[]) => void;
  selectedPhase1: Phase1Session | null;
  setSelectedPhase1: (session: Phase1Session | null) => void;

  // Current phase execution
  currentPhase: string | null;
  setCurrentPhase: (phase: string | null) => void;
  currentIteration: number;
  setCurrentIteration: (iteration: number) => void;
  isRunning: boolean;
  setIsRunning: (running: boolean) => void;

  // Current issue
  currentIssue: ProofreadingIssue | null;
  setCurrentIssue: (issue: ProofreadingIssue | null) => void;
  totalIssues: number;
  setTotalIssues: (total: number) => void;

  // Logs
  logs: Array<{ timestamp: string; message: string; level: string }>;
  addLog: (message: string, level?: string) => void;
  clearLogs: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Selected paper
  selectedPaper: null,
  setSelectedPaper: (paper) => set({ selectedPaper: paper }),

  // Papers list
  papers: [],
  setPapers: (papers) => set({ papers }),

  // Phase1 sessions
  phase1Sessions: [],
  setPhase1Sessions: (sessions) => set({ phase1Sessions: sessions }),
  selectedPhase1: null,
  setSelectedPhase1: (session) => set({ selectedPhase1: session }),

  // Current phase execution
  currentPhase: null,
  setCurrentPhase: (phase) => set({ currentPhase: phase }),
  currentIteration: 0,
  setCurrentIteration: (iteration) => set({ currentIteration: iteration }),
  isRunning: false,
  setIsRunning: (running) => set({ isRunning: running }),

  // Current issue
  currentIssue: null,
  setCurrentIssue: (issue) => set({ currentIssue: issue }),
  totalIssues: 0,
  setTotalIssues: (total) => set({ totalIssues: total }),

  // Logs
  logs: [],
  addLog: (message, level = 'info') =>
    set((state) => ({
      logs: [
        ...state.logs,
        {
          timestamp: new Date().toLocaleTimeString(),
          message,
          level,
        },
      ],
    })),
  clearLogs: () => set({ logs: [] }),
}));
