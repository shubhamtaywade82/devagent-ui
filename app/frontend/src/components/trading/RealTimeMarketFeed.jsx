import { useState, useEffect, useRef } from "react";
import { Activity, Wifi, WifiOff } from "lucide-react";
import TradingWebSocket from "../../services/websocket";

function RealTimeMarketFeed({ accessToken, securityId }) {
  const [feedData, setFeedData] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState("");
  const wsRef = useRef(null);

  useEffect(() => {
    if (!accessToken || !securityId) return;

    // Create WebSocket connection
    const ws = new TradingWebSocket(
      "/ws/trading/market-feed/{access_token}",
      accessToken,
      (data) => {
        if (data.type === "market_feed") {
          setFeedData(data.data);
          setError("");
        } else if (data.type === "error") {
          setError(data.message);
        }
      },
      (err) => {
        setError("WebSocket connection error");
        setIsConnected(false);
      },
      () => {
        setIsConnected(false);
      }
    );

    ws.connect();
    wsRef.current = ws;

    // Send subscription request after connection
    setTimeout(() => {
      if (ws.ws && ws.ws.readyState === WebSocket.OPEN) {
        ws.send({
          instruments: [
            [1, securityId.toString(), 1], // NSE, security_id, Ticker mode
            [1, securityId.toString(), 2], // NSE, security_id, Quote mode
          ],
          version: "v2",
        });
        setIsConnected(true);
      }
    }, 1000);

    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect();
      }
    };
  }, [accessToken, securityId]);

  return (
    <div className="glass rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Real-Time Market Feed</h3>
        <div className="flex items-center gap-2">
          {isConnected ? (
            <>
              <Wifi className="w-4 h-4 text-green-500" />
              <span className="text-xs text-green-500">Connected</span>
            </>
          ) : (
            <>
              <WifiOff className="w-4 h-4 text-red-500" />
              <span className="text-xs text-red-500">Disconnected</span>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {feedData && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-zinc-900 rounded-lg p-4">
              <div className="text-sm text-zinc-400 mb-1">Last Price</div>
              <div className="text-2xl font-bold text-green-500">
                ₹{feedData.lastPrice?.toFixed(2) || "0.00"}
              </div>
            </div>
            <div className="bg-zinc-900 rounded-lg p-4">
              <div className="text-sm text-zinc-400 mb-1">Change</div>
              <div
                className={`text-2xl font-bold ${
                  (feedData.change || 0) >= 0
                    ? "text-green-500"
                    : "text-red-500"
                }`}
              >
                {feedData.change >= 0 ? "+" : ""}
                {feedData.change?.toFixed(2) || "0.00"}
              </div>
            </div>
          </div>
          <div className="text-xs text-zinc-500">
            <Activity className="w-3 h-3 inline mr-1" />
            Live data streaming
          </div>
        </div>
      )}

      {!feedData && !error && (
        <div className="text-center text-zinc-500 py-8">
          Waiting for market data...
        </div>
      )}
    </div>
  );
}

export default RealTimeMarketFeed;
