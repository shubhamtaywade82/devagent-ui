import { useState, useEffect, useRef } from "react";
import { Bell, Wifi, WifiOff, CheckCircle, XCircle, Clock } from "lucide-react";
import TradingWebSocket from "../../services/websocket";

function LiveOrderUpdates({ accessToken }) {
  const [orderUpdates, setOrderUpdates] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState("");
  const wsRef = useRef(null);

  useEffect(() => {
    if (!accessToken) return;

    const ws = new TradingWebSocket(
      "/ws/trading/order-updates/{access_token}",
      accessToken,
      (data) => {
        if (data.type === "order_update") {
          setOrderUpdates((prev) => [data.data, ...prev].slice(0, 20)); // Keep last 20 updates
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

    setTimeout(() => {
      if (ws.ws && ws.ws.readyState === WebSocket.OPEN) {
        setIsConnected(true);
      }
    }, 1000);

    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect();
      }
    };
  }, [accessToken]);

  const getStatusIcon = (status) => {
    switch (status) {
      case "TRADED":
      case "COMPLETE":
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case "REJECTED":
      case "CANCELLED":
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Clock className="w-4 h-4 text-yellow-500" />;
    }
  };

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-6xl mx-auto">
        <div className="glass rounded-xl p-8 mb-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <Bell className="w-6 h-6 text-green-500" />
              <h2 className="text-2xl font-bold font-manrope">Live Order Updates</h2>
            </div>
            <div className="flex items-center gap-2">
              {isConnected ? (
                <>
                  <Wifi className="w-5 h-5 text-green-500" />
                  <span className="text-sm text-green-500 font-medium">Connected</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-5 h-5 text-red-500" />
                  <span className="text-sm text-red-500 font-medium">Disconnected</span>
                </>
              )}
            </div>
          </div>

          {error && (
            <div className="mb-4 p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400">
              <div className="font-medium mb-1">WebSocket Connection Error</div>
              <div className="text-sm">{error}</div>
            </div>
          )}

          {!error && !isConnected && (
            <div className="mb-4 p-4 bg-yellow-500/20 border border-yellow-500/50 rounded-lg text-yellow-400 text-sm">
              Connecting to order updates stream...
            </div>
          )}
        </div>

        <div className="glass rounded-xl p-8">
          <h3 className="text-lg font-semibold mb-4">Recent Order Updates</h3>
          <div className="space-y-3">
            {orderUpdates.length === 0 ? (
              <div className="text-center text-zinc-500 py-12">
                <Bell className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
                <div className="text-lg mb-2">No order updates yet</div>
                <div className="text-sm">Orders will appear here in real-time as they are placed and executed</div>
              </div>
            ) : (
              orderUpdates.map((update, idx) => (
                <div
                  key={idx}
                  className="bg-zinc-900 rounded-lg p-4 border border-zinc-800 hover:border-zinc-700 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4 flex-1">
                      {getStatusIcon(update.orderStatus || update.status)}
                      <div className="flex-1">
                        <div className="text-sm font-medium text-white mb-1">
                          {update.tradingSymbol || update.symbol || "N/A"}
                        </div>
                        <div className="text-xs text-zinc-400">
                          Order ID: {update.orderId || update.order_id || "N/A"} •{" "}
                          {update.orderStatus || update.status || "PENDING"}
                        </div>
                      </div>
                    </div>
                    <div className="text-right ml-4">
                      <div className="text-sm font-medium text-white mb-1">
                        Qty: {update.quantity || update.qty || 0}
                      </div>
                      <div className="text-xs text-zinc-400">
                        ₹{update.price?.toFixed(2) || "0.00"}
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default LiveOrderUpdates;
