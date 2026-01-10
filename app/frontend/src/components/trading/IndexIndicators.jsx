import { useState, useEffect, useRef } from "react";
import {
  TrendingUp,
  TrendingDown,
  Wifi,
  WifiOff,
  Activity,
} from "lucide-react";
import TradingWebSocket from "../../services/websocket";

// NIFTY and SENSEX Security IDs (standard DhanHQ IDs)
const INDEX_INSTRUMENTS = {
  NIFTY: {
    name: "NIFTY 50",
    securityId: 99926000, // NIFTY 50 index
    exchange: 1, // NSE
  },
  SENSEX: {
    name: "SENSEX",
    securityId: 99919000, // SENSEX index
    exchange: 2, // BSE
  },
};

function IndexIndicators({ accessToken }) {
  const [niftyData, setNiftyData] = useState(null);
  const [sensexData, setSensexData] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState("");
  const wsRef = useRef(null);

  useEffect(() => {
    if (!accessToken) return;

    // Create WebSocket connection
    const ws = new TradingWebSocket(
      "/ws/trading/market-feed/{access_token}",
      accessToken,
      (data) => {
        if (data.type === "market_feed") {
          // Handle market feed data - DhanHQ returns data in various formats
          const feedData = data.data;
          if (feedData) {
            // Market feed can return single instrument or array of instruments
            const instruments = Array.isArray(feedData) ? feedData : [feedData];

            instruments.forEach((instrument) => {
              // Check which instrument this data is for
              const securityId =
                instrument.securityId ||
                instrument.security_id ||
                instrument.SECURITY_ID ||
                instrument.securityId?.toString();

              const niftyId = INDEX_INSTRUMENTS.NIFTY.securityId.toString();
              const sensexId = INDEX_INSTRUMENTS.SENSEX.securityId.toString();

              if (
                securityId === niftyId ||
                securityId === INDEX_INSTRUMENTS.NIFTY.securityId
              ) {
                setNiftyData(instrument);
              } else if (
                securityId === sensexId ||
                securityId === INDEX_INSTRUMENTS.SENSEX.securityId
              ) {
                setSensexData(instrument);
              }
            });
          }
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
    const subscribeToIndices = () => {
      if (ws.ws && ws.ws.readyState === WebSocket.OPEN) {
        // Subscribe to both NIFTY and SENSEX
        // Format: [exchange_id, security_id, mode]
        // Mode: 1 = Ticker, 2 = Quote
        ws.send({
          instruments: [
            [
              INDEX_INSTRUMENTS.NIFTY.exchange,
              INDEX_INSTRUMENTS.NIFTY.securityId.toString(),
              2,
            ], // NIFTY Quote mode
            [
              INDEX_INSTRUMENTS.SENSEX.exchange,
              INDEX_INSTRUMENTS.SENSEX.securityId.toString(),
              2,
            ], // SENSEX Quote mode
          ],
          version: "v2",
        });
        setIsConnected(true);
        setError("");
      }
    };

    // Try to subscribe after connection is established
    setTimeout(subscribeToIndices, 1000);

    // Retry subscription if not connected
    const retryInterval = setInterval(() => {
      if (ws.ws && ws.ws.readyState === WebSocket.OPEN && !isConnected) {
        subscribeToIndices();
      }
    }, 3000);

    return () => {
      clearInterval(retryInterval);
      if (wsRef.current) {
        wsRef.current.disconnect();
      }
    };
  }, [accessToken]);

  const formatPrice = (price) => {
    if (!price) return "0.00";
    return parseFloat(price).toFixed(2);
  };

  const formatChange = (change, changePercent) => {
    if (change === undefined && changePercent === undefined)
      return { value: "0.00", percent: "0.00%" };
    const changeValue = change || 0;
    const percentValue = changePercent || 0;
    return {
      value:
        changeValue >= 0
          ? `+${changeValue.toFixed(2)}`
          : changeValue.toFixed(2),
      percent:
        changePercent >= 0
          ? `+${changePercent.toFixed(2)}%`
          : `${changePercent.toFixed(2)}%`,
    };
  };

  const getChangeColor = (change) => {
    if (change === undefined || change === null) return "text-zinc-400";
    return change >= 0 ? "text-green-500" : "text-red-500";
  };

  return (
    <div className="flex items-center gap-4">
      {/* Compact NIFTY 50 */}
      <div className="bg-zinc-900/80 rounded-lg px-3 py-2 border border-zinc-800/50 flex items-center gap-3 min-w-[140px]">
        <TrendingUp className="w-4 h-4 text-blue-500 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="text-xs text-zinc-400 mb-0.5">NIFTY 50</div>
          {niftyData ? (
            <>
              <div className="text-sm font-bold text-white">
                {formatPrice(
                  niftyData.lastPrice || niftyData.last_price || niftyData.ltp
                )}
              </div>
              <div className={`text-xs ${getChangeColor(
                niftyData.change || niftyData.changePercent
              )}`}>
                {
                  formatChange(niftyData.change, niftyData.changePercent)
                    .value
                } ({formatChange(niftyData.change, niftyData.changePercent).percent})
              </div>
            </>
          ) : (
            <div className="text-xs text-zinc-500">Loading...</div>
          )}
        </div>
        {niftyData && (
          <Activity className="w-3 h-3 text-green-500 animate-pulse flex-shrink-0" />
        )}
      </div>

      {/* Compact SENSEX */}
      <div className="bg-zinc-900/80 rounded-lg px-3 py-2 border border-zinc-800/50 flex items-center gap-3 min-w-[140px]">
        <TrendingUp className="w-4 h-4 text-orange-500 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="text-xs text-zinc-400 mb-0.5">SENSEX</div>
          {sensexData ? (
            <>
              <div className="text-sm font-bold text-white">
                {formatPrice(
                  sensexData.lastPrice ||
                    sensexData.last_price ||
                    sensexData.ltp
                )}
              </div>
              <div className={`text-xs ${getChangeColor(
                sensexData.change || sensexData.changePercent
              )}`}>
                {
                  formatChange(sensexData.change, sensexData.changePercent)
                    .value
                } ({formatChange(sensexData.change, sensexData.changePercent).percent})
              </div>
            </>
          ) : (
            <div className="text-xs text-zinc-500">Loading...</div>
          )}
        </div>
        {sensexData && (
          <Activity className="w-3 h-3 text-green-500 animate-pulse flex-shrink-0" />
        )}
      </div>

      {/* Connection Status */}
      <div className="flex items-center gap-1.5">
        {isConnected ? (
          <>
            <Wifi className="w-3.5 h-3.5 text-green-500" />
            <span className="text-xs text-green-500">Live</span>
          </>
        ) : (
          <>
            <WifiOff className="w-3.5 h-3.5 text-red-500" />
            <span className="text-xs text-red-500">Connecting</span>
          </>
        )}
      </div>

      {error && (
        <div className="text-xs text-red-400 max-w-[200px] truncate" title={error}>
          {error}
        </div>
      )}
    </div>
  );
}

export default IndexIndicators;
