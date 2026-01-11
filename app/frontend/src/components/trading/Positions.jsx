import { useState, useEffect } from "react";
import { TrendingUp, TrendingDown, RefreshCw, Loader2 } from "lucide-react";
import api from "../../services/api";

function Positions({ accessToken }) {
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadPositions = async () => {
    if (!accessToken) return;

    setLoading(true);
    setError("");
    try {
      const positionsData = await api.getPositions(accessToken);

      if (positionsData.success) {
        const positionsArray = Array.isArray(positionsData.data)
          ? positionsData.data
          : positionsData.data?.data ||
            positionsData.data?.positions ||
            positionsData.data?.position ||
            [];
        setPositions(positionsArray);
      } else {
        setError(positionsData.error || "Failed to load positions");
        setPositions([]);
      }
    } catch (err) {
      setError(err.message || "Failed to load positions");
      setPositions([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPositions();
    // Refresh every 30 seconds
    const interval = setInterval(loadPositions, 30000);
    return () => clearInterval(interval);
  }, [accessToken]);

  const totalPnL = positions.reduce((sum, pos) => {
    const pnl = pos.unrealizedPnL || pos.unrealisedPnL || pos.pnl || pos.unrealized_pnl || 0;
    return sum + (parseFloat(pnl) || 0);
  }, 0);

  return (
    <div className="h-full flex flex-col bg-zinc-900">
      {/* Header */}
      <div className="p-4 border-b border-zinc-800">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold text-white">Positions</h3>
          <button
            onClick={loadPositions}
            disabled={loading}
            className="p-1.5 rounded hover:bg-zinc-800 transition-colors"
            title="Refresh positions"
          >
            <RefreshCw
              className={`w-4 h-4 text-zinc-400 ${loading ? "animate-spin" : ""}`}
            />
          </button>
        </div>
        {positions.length > 0 && (
          <div className="mt-2">
            <div className="text-xs text-zinc-400 mb-1">Total P&L</div>
            <div
              className={`text-lg font-semibold ${
                totalPnL >= 0 ? "text-green-500" : "text-red-500"
              }`}
            >
              {totalPnL >= 0 ? (
                <TrendingUp className="w-4 h-4 inline mr-1" />
              ) : (
                <TrendingDown className="w-4 h-4 inline mr-1" />
              )}
              ₹{Math.abs(totalPnL).toFixed(2)}
            </div>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading && positions.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-green-500" />
            <span className="ml-2 text-zinc-400 text-sm">Loading positions...</span>
          </div>
        ) : error ? (
          <div className="text-center py-8">
            <div className="text-red-400 text-sm mb-2">{error}</div>
            <button
              onClick={loadPositions}
              className="text-xs text-zinc-400 hover:text-zinc-300 underline"
            >
              Retry
            </button>
          </div>
        ) : !Array.isArray(positions) || positions.length === 0 ? (
          <div className="text-center py-8">
            <div className="text-zinc-500 text-sm mb-2">No open positions</div>
            <div className="text-zinc-600 text-xs">
              Your positions will appear here
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {positions.map((pos, idx) => {
              const avgPrice = pos.averagePrice || pos.avgPrice || pos.average_price || 0;
              const lastPrice = pos.lastPrice || pos.ltp || pos.currentPrice || 0;
              const quantity = pos.quantity || pos.qty || 0;
              const pnl = pos.unrealizedPnL || pos.unrealisedPnL || pos.pnl || pos.unrealized_pnl || 0;
              const symbol = pos.tradingSymbol || pos.symbol || pos.securityId || "N/A";

              return (
                <div
                  key={idx}
                  className="bg-zinc-800/50 rounded-lg p-3 border border-zinc-800/50 hover:border-zinc-700 transition-colors"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-white font-medium text-sm truncate flex-1">
                      {symbol}
                    </div>
                    <div
                      className={`text-sm font-semibold ml-2 ${
                        pnl >= 0 ? "text-green-500" : "text-red-500"
                      }`}
                    >
                      {pnl >= 0 ? "+" : ""}₹{Math.abs(parseFloat(pnl) || 0).toFixed(2)}
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <div className="text-zinc-500">Qty</div>
                      <div className="text-zinc-300">{quantity}</div>
                    </div>
                    <div>
                      <div className="text-zinc-500">Avg Price</div>
                      <div className="text-zinc-300">₹{parseFloat(avgPrice).toFixed(2)}</div>
                    </div>
                    <div>
                      <div className="text-zinc-500">LTP</div>
                      <div className="text-zinc-300">₹{parseFloat(lastPrice).toFixed(2)}</div>
                    </div>
                    <div>
                      <div className="text-zinc-500">Value</div>
                      <div className="text-zinc-300">
                        ₹{(parseFloat(lastPrice) * quantity).toFixed(2)}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default Positions;

