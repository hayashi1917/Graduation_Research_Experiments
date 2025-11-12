/**
 * API通信モジュール
 */

const API = {
    baseUrl: '',

    /**
     * 論文リストを取得
     */
    async getPapers() {
        try {
            const response = await fetch(`${this.baseUrl}/api/papers`);
            if (!response.ok) throw new Error('論文リストの取得に失敗しました');
            return await response.json();
        } catch (error) {
            console.error('getPapers error:', error);
            throw error;
        }
    },

    /**
     * 論文をアップロード
     */
    async uploadPaper(paperId, pdfFile, texFile) {
        try {
            const formData = new FormData();
            formData.append('paper_id', paperId);
            formData.append('pdf_file', pdfFile);
            formData.append('tex_file', texFile);

            const response = await fetch(`${this.baseUrl}/api/papers/upload`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) throw new Error('論文のアップロードに失敗しました');
            return await response.json();
        } catch (error) {
            console.error('uploadPaper error:', error);
            throw error;
        }
    },

    /**
     * 設定を取得
     */
    async getConfig() {
        try {
            const response = await fetch(`${this.baseUrl}/api/config`);
            if (!response.ok) throw new Error('設定の取得に失敗しました');
            return await response.json();
        } catch (error) {
            console.error('getConfig error:', error);
            throw error;
        }
    },

    /**
     * 設定を更新
     */
    async updateSettings(settings) {
        try {
            const response = await fetch(`${this.baseUrl}/api/config/settings`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(settings),
            });

            if (!response.ok) throw new Error('設定の更新に失敗しました');
            return await response.json();
        } catch (error) {
            console.error('updateSettings error:', error);
            throw error;
        }
    },

    /**
     * ログを取得
     */
    async getLogs(paperId, phase = null) {
        try {
            const url = phase
                ? `${this.baseUrl}/api/logs/${paperId}?phase=${phase}`
                : `${this.baseUrl}/api/logs/${paperId}`;

            const response = await fetch(url);
            if (!response.ok) throw new Error('ログの取得に失敗しました');
            return await response.json();
        } catch (error) {
            console.error('getLogs error:', error);
            throw error;
        }
    },

    /**
     * イテレーション履歴を取得
     */
    async getIterations(paperId) {
        try {
            const response = await fetch(`${this.baseUrl}/api/iterations/${paperId}`);
            if (!response.ok) throw new Error('イテレーション履歴の取得に失敗しました');
            return await response.json();
        } catch (error) {
            console.error('getIterations error:', error);
            throw error;
        }
    },
};
