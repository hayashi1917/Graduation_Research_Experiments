/**
 * WebSocket接続管理
 */

class WebSocketManager {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000;
        this.messageHandlers = [];
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        console.log('WebSocket接続を試みています:', wsUrl);

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket接続成功');
            this.reconnectAttempts = 0;
            this.updateConnectionStatus(true);
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('WebSocketメッセージ受信:', data);
                this.handleMessage(data);
            } catch (error) {
                console.error('メッセージのパースエラー:', error);
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocketエラー:', error);
        };

        this.ws.onclose = () => {
            console.log('WebSocket接続が切断されました');
            this.updateConnectionStatus(false);
            this.attemptReconnect();
        };
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`再接続試行 ${this.reconnectAttempts}/${this.maxReconnectAttempts}...`);

            setTimeout(() => {
                this.connect();
            }, this.reconnectDelay * this.reconnectAttempts);
        } else {
            console.error('WebSocket再接続の最大試行回数に達しました');
            addLogMessage('WebSocket接続が失敗しました。ページをリロードしてください。', 'error');
        }
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        } else {
            console.error('WebSocketが接続されていません');
        }
    }

    handleMessage(data) {
        // メッセージハンドラーを実行
        this.messageHandlers.forEach(handler => {
            try {
                handler(data);
            } catch (error) {
                console.error('メッセージハンドラーエラー:', error);
            }
        });
    }

    addMessageHandler(handler) {
        this.messageHandlers.push(handler);
    }

    updateConnectionStatus(connected) {
        const statusBadge = document.getElementById('connection-status');
        if (statusBadge) {
            if (connected) {
                statusBadge.textContent = '接続中';
                statusBadge.classList.remove('bg-secondary', 'disconnected');
                statusBadge.classList.add('bg-success', 'connected');
            } else {
                statusBadge.textContent = '切断';
                statusBadge.classList.remove('bg-success', 'connected');
                statusBadge.classList.add('bg-danger', 'disconnected');
            }
        }
    }

    close() {
        if (this.ws) {
            this.ws.close();
        }
    }
}

// グローバルインスタンス
const wsManager = new WebSocketManager();
