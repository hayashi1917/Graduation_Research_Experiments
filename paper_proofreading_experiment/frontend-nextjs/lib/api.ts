/**
 * API client for backend communication
 */
import axios from 'axios';
import { Paper, Phase1Session, DetectionRate } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Papers API
export const papersAPI = {
  list: async (): Promise<Paper[]> => {
    const response = await api.get('/api/papers/');
    return response.data;
  },

  upload: async (paperId: string, pdfFile: File, texFile: File) => {
    const formData = new FormData();
    formData.append('paper_id', paperId);
    formData.append('pdf_file', pdfFile);
    formData.append('tex_file', texFile);

    const response = await api.post('/api/papers/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getInfo: async (paperId: string): Promise<Paper> => {
    const response = await api.get(`/api/papers/${paperId}/info`);
    return response.data;
  },
};

// Data API
export const dataAPI = {
  reset: async (options: {
    reset_results?: boolean;
    reset_versions?: boolean;
    reset_progress?: boolean;
  }) => {
    const response = await api.post('/api/data/reset', options);
    return response.data;
  },

  getPhase1Sessions: async (paperId: string): Promise<Phase1Session[]> => {
    const response = await api.get(`/api/data/phase1_sessions/${paperId}`);
    return response.data;
  },

  getIterations: async (paperId: string) => {
    const response = await api.get(`/api/data/iterations/${paperId}`);
    return response.data;
  },

  getDetectionRate: async (paperId: string): Promise<DetectionRate> => {
    const response = await api.get(`/api/data/detection_rate/${paperId}`);
    return response.data;
  },
};

// Settings API
export const settingsAPI = {
  get: async () => {
    // TODO: Implement settings endpoint
    return {};
  },

  update: async (settings: any) => {
    // TODO: Implement settings update
    return {};
  },
};

export default api;
