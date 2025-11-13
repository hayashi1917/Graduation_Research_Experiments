/**
 * WebSocket manager for real-time communication
 */
import { WebSocketMessage } from '@/types';

type MessageHandler = (message: WebSocketMessage) => void;

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private clientId: string;
  private messageHandlers: MessageHandler[] = [];
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;

  constructor() {
    this.clientId = this.generateClientId();
  }

  private generateClientId(): string {
    return `client_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('[WebSocket] 既に接続済み');
      return;
    }

    const wsUrl = `ws://localhost:8000/ws/${this.clientId}`;
    console.log(`[WebSocket] 接続開始: ${wsUrl}`);

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('[WebSocket] 接続成功');
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        console.log('[WebSocket] メッセージ受信:', event.data);
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          console.log('[WebSocket] パース成功:', message);
          console.log(`[WebSocket] メッセージハンドラー数: ${this.messageHandlers.length}`);
          this.messageHandlers.forEach((handler, index) => {
            console.log(`[WebSocket] ハンドラー ${index} を実行中`);
            handler(message);
          });
        } catch (error) {
          console.error('[WebSocket] メッセージパース失敗:', error, 'データ:', event.data);
        }
      };

      this.ws.onerror = (error) => {
        console.error('[WebSocket] エラー:', error);
      };

      this.ws.onclose = () => {
        console.log('[WebSocket] 切断');
        this.attemptReconnect();
      };
    } catch (error) {
      console.error('[WebSocket] WebSocket作成失敗:', error);
      this.attemptReconnect();
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(
        `Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`
      );
      setTimeout(() => this.connect(), this.reconnectDelay);
    } else {
      console.error('Max reconnection attempts reached');
    }
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  addMessageHandler(handler: MessageHandler): void {
    this.messageHandlers.push(handler);
  }

  removeMessageHandler(handler: MessageHandler): void {
    this.messageHandlers = this.messageHandlers.filter((h) => h !== handler);
  }

  sendMessage(message: any): void {
    console.log('[WebSocket] メッセージ送信:', message);
    if (this.ws?.readyState === WebSocket.OPEN) {
      const jsonStr = JSON.stringify(message);
      console.log('[WebSocket] JSON送信:', jsonStr);
      this.ws.send(jsonStr);
      console.log('[WebSocket] 送信完了');
    } else {
      console.error('[WebSocket] 接続されていません。readyState:', this.ws?.readyState);
    }
  }

  sendAction(action: string): void {
    console.log('[WebSocket] アクション送信:', action);
    this.sendMessage({
      type: 'action',
      action,
    });
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  getClientId(): string {
    return this.clientId;
  }
}

// Singleton instance
const wsManager = new WebSocketManager();

export default wsManager;
