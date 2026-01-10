/**
 * WebSocket service for real-time trading data
 */

class TradingWebSocket {
  constructor(url, accessToken, onMessage, onError, onClose) {
    this.url = url;
    this.accessToken = accessToken;
    this.onMessage = onMessage;
    this.onError = onError;
    this.onClose = onClose;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 3000;
  }

  connect() {
    try {
      const wsUrl = this.url.replace("{access_token}", this.accessToken);
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host =
        import.meta.env.VITE_BACKEND_URL?.replace(/^https?:\/\//, "") ||
        "localhost:8001";
      const fullUrl = `${protocol}//${host}${wsUrl}`;

      this.ws = new WebSocket(fullUrl);

      this.ws.onopen = () => {
        console.log("WebSocket connected");
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (this.onMessage) {
            this.onMessage(data);
          }
        } catch (error) {
          console.error("Error parsing WebSocket message:", error);
        }
      };

      this.ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        if (this.onError) {
          this.onError(error);
        }
      };

      this.ws.onclose = () => {
        console.log("WebSocket disconnected");
        if (this.onClose) {
          this.onClose();
        }
        this.attemptReconnect();
      };
    } catch (error) {
      console.error("Error creating WebSocket:", error);
      if (this.onError) {
        this.onError(error);
      }
    }
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(
        `Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`
      );
      setTimeout(() => {
        this.connect();
      }, this.reconnectDelay);
    } else {
      console.error("Max reconnection attempts reached");
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.error("WebSocket is not open");
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export default TradingWebSocket;
