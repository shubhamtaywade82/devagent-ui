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
    <div className="glass rounded-lg p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Market Indices</h3>
        <div className="flex items-center gap-2">
          {isConnected ? (
            <>
              <Wifi className="w-4 h-4 text-green-500" />
              <span className="text-xs text-green-500">Live</span>
            </>
          ) : (
            <>
              <WifiOff className="w-4 h-4 text-red-500" />
              <span className="text-xs text-red-500">Connecting...</span>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* NIFTY 50 */}
        <div className="bg-zinc-900 rounded-lg p-4 border border-zinc-800">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-blue-500" />
              <h4 className="text-lg font-semibold text-white">
                {INDEX_INSTRUMENTS.NIFTY.name}
              </h4>
            </div>
            {niftyData && (
              <Activity className="w-4 h-4 text-green-500 animate-pulse" />
            )}
          </div>

          {niftyData ? (
            <>
              <div className="text-3xl font-bold text-white mb-2">
                {formatPrice(
                  niftyData.lastPrice || niftyData.last_price || niftyData.ltp
                )}
              </div>
              <div className="flex items-center gap-4">
                <div
                  className={getChangeColor(
                    niftyData.change || niftyData.changePercent
                  )}
                >
                  <div className="text-lg font-semibold">
                    {
                      formatChange(niftyData.change, niftyData.changePercent)
                        .value
                    }
                  </div>
                  <div className="text-sm">
                    {
                      formatChange(niftyData.change, niftyData.changePercent)
                        .percent
                    }
                  </div>
                </div>
                {niftyData.ohlc && (
                  <div className="text-xs text-zinc-500">
                    <div>H: {formatPrice(niftyData.ohlc.high)}</div>
                    <div>L: {formatPrice(niftyData.ohlc.low)}</div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="text-zinc-500 text-sm">Waiting for data...</div>
          )}
        </div>

        {/* SENSEX */}
        <div className="bg-zinc-900 rounded-lg p-4 border border-zinc-800">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-orange-500" />
              <h4 className="text-lg font-semibold text-white">
                {INDEX_INSTRUMENTS.SENSEX.name}
              </h4>
            </div>
            {sensexData && (
              <Activity className="w-4 h-4 text-green-500 animate-pulse" />
            )}
          </div>

          {sensexData ? (
            <>
              <div className="text-3xl font-bold text-white mb-2">
                {formatPrice(
                  sensexData.lastPrice ||
                    sensexData.last_price ||
                    sensexData.ltp
                )}
              </div>
              <div className="flex items-center gap-4">
                <div
                  className={getChangeColor(
                    sensexData.change || sensexData.changePercent
                  )}
                >
                  <div className="text-lg font-semibold">
                    {
                      formatChange(sensexData.change, sensexData.changePercent)
                        .value
                    }
                  </div>
                  <div className="text-sm">
                    {
                      formatChange(sensexData.change, sensexData.changePercent)
                        .percent
                    }
                  </div>
                </div>
                {sensexData.ohlc && (
                  <div className="text-xs text-zinc-500">
                    <div>H: {formatPrice(sensexData.ohlc.high)}</div>
                    <div>L: {formatPrice(sensexData.ohlc.low)}</div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="text-zinc-500 text-sm">Waiting for data...</div>
          )}
        </div>
      </div>
    </div>
  );
}

export default IndexIndicators;
