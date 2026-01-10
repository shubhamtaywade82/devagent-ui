import { useState, useEffect, useRef } from "react";
import {
  TrendingUp,
  TrendingDown,
  Wifi,
  WifiOff,
  Activity,
} from "lucide-react";
import TradingWebSocket from "../../services/websocket";

// NIFTY and SENSEX Security IDs
// These are standard DhanHQ Security IDs for indices
// Source: DhanHQ instrument master data / API documentation
// These IDs are consistent across DhanHQ platform
//
// Note: These can also be found by searching the instrument list for:
// - "NIFTY 50" or "NIFTY" on NSE_EQ
// - "SENSEX" on BSE_EQ
// Default values - will be updated from instrument list lookup
// Note: Indices use IDX_I (Index segment) per DhanHQ Annexure
// Correct values from /v2/instrument/IDX_I API:
// - NIFTY 50: SecurityId=13, ExchangeSegment=IDX_I (NSE,I,13)
// - SENSEX: SecurityId=51, ExchangeSegment=IDX_I (BSE,I,51)
const INDEX_INSTRUMENTS = {
  NIFTY: {
    name: "NIFTY 50",
    securityId: 13, // Correct Security ID from DhanHQ API (/v2/instrument/IDX_I)
    exchange: 1, // NSE
    exchangeSegment: "IDX_I", // Index segment per Annexure (enum 0)
  },
  SENSEX: {
    name: "SENSEX",
    securityId: 51, // Correct Security ID from DhanHQ API (/v2/instrument/IDX_I)
    exchange: 2, // BSE
    exchangeSegment: "IDX_I", // Index segment per Annexure (enum 0)
  },
};

function IndexIndicators({ accessToken }) {
  const [niftyData, setNiftyData] = useState(null);
  const [sensexData, setSensexData] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState("");
  const wsRef = useRef(null);
  const [indexInstruments, setIndexInstruments] = useState(INDEX_INSTRUMENTS);

  // Try to find NIFTY and SENSEX Security IDs from instrument list
  // Better approach: Use the segmentwise API for IDX_I directly
  useEffect(() => {
    const findIndexSecurityIds = async () => {
      try {
        // Try segmentwise API for IDX_I first (faster and more accurate)
        try {
          const segmentData = await api.getInstrumentListSegmentwise("IDX_I");
          if (segmentData.success && segmentData.data?.instruments) {
            const instruments = segmentData.data.instruments;

            // Search for NIFTY 50 - Following Ruby implementation pattern
            // From API: NSE,I,13,NA,INDEX,13,NIFTY,NIFTY,Nifty 50
            // For indices, use exact match on SYMBOL_NAME (not UNDERLYING_SYMBOL)
            const nifty = instruments.find((inst) => {
              const symbolName = inst.SYMBOL_NAME?.toUpperCase();
              const exchange =
                inst.EXCH_ID || inst.SEM_EXM_EXCH_ID || inst.EXCHANGE_ID;
              const instrumentType = inst.INSTRUMENT || inst.INSTRUMENT_TYPE;
              // Exact match on symbol_name for indices (per Ruby implementation)
              return (
                symbolName === "NIFTY" &&
                exchange === "NSE" &&
                (instrumentType === "INDEX" ||
                  inst.SEGMENT === "I" ||
                  inst.SEM_SEGMENT === "I")
              );
            });

            // Search for SENSEX - Following Ruby implementation pattern
            // From API: BSE,I,51,NA,INDEX,51,SENSEX,SENSEX,Sensex
            // For indices, use exact match on SYMBOL_NAME (not UNDERLYING_SYMBOL)
            const sensex = instruments.find((inst) => {
              const symbolName = inst.SYMBOL_NAME?.toUpperCase();
              const exchange =
                inst.EXCH_ID || inst.SEM_EXM_EXCH_ID || inst.EXCHANGE_ID;
              const instrumentType = inst.INSTRUMENT || inst.INSTRUMENT_TYPE;
              // Exact match on symbol_name for indices (per Ruby implementation)
              return (
                symbolName === "SENSEX" &&
                exchange === "BSE" &&
                (instrumentType === "INDEX" ||
                  inst.SEGMENT === "I" ||
                  inst.SEM_SEGMENT === "I")
              );
            });

            if (nifty) {
              const niftyId =
                nifty.SECURITY_ID ||
                nifty.SEM_SECURITY_ID ||
                nifty.SM_SECURITY_ID;
              if (niftyId) {
                setIndexInstruments((prev) => ({
                  ...prev,
                  NIFTY: {
                    ...prev.NIFTY,
                    securityId: parseInt(niftyId),
                    exchangeSegment: "IDX_I",
                  },
                }));
                console.log("Found NIFTY from IDX_I segment:", {
                  securityId: niftyId,
                  exchangeSegment: "IDX_I",
                  instrument: nifty,
                });
              }
            }

            if (sensex) {
              const sensexId =
                sensex.SECURITY_ID ||
                sensex.SEM_SECURITY_ID ||
                sensex.SM_SECURITY_ID;
              if (sensexId) {
                setIndexInstruments((prev) => ({
                  ...prev,
                  SENSEX: {
                    ...prev.SENSEX,
                    securityId: parseInt(sensexId),
                    exchangeSegment: "IDX_I",
                  },
                }));
                console.log("Found SENSEX from IDX_I segment:", {
                  securityId: sensexId,
                  exchangeSegment: "IDX_I",
                  instrument: sensex,
                });
              }
            }
            return; // Successfully found from segmentwise API
          }
        } catch (segmentErr) {
          console.warn(
            "Could not fetch from segmentwise API, trying CSV:",
            segmentErr
          );
        }

        // Fallback to CSV search
        const data = await api.getInstrumentListCSV("detailed");
        if (data.success && data.data?.instruments) {
          const instruments = data.data.instruments;

          // Search for NIFTY 50 - Following Ruby implementation pattern
          // From /v2/instrument/IDX_I: NSE,I,13,NA,INDEX,13,NIFTY,NIFTY,Nifty 50
          // For indices, use exact match on SYMBOL_NAME (not UNDERLYING_SYMBOL)
          const nifty = instruments.find((inst) => {
            const symbolName = inst.SYMBOL_NAME?.toUpperCase();
            const exchange =
              inst.SEM_EXM_EXCH_ID || inst.EXCH_ID || inst.EXCHANGE_ID;
            const instrumentType = inst.INSTRUMENT || inst.INSTRUMENT_TYPE;
            const segment = inst.SEM_SEGMENT || inst.SEGMENT;
            // Exact match on symbol_name for indices (per Ruby implementation)
            return (
              symbolName === "NIFTY" &&
              exchange === "NSE" &&
              (instrumentType === "INDEX" ||
                segment === "I" ||
                segment?.toUpperCase() === "INDEX")
            );
          });

          // Search for SENSEX - Following Ruby implementation pattern
          // From /v2/instrument/IDX_I: BSE,I,51,NA,INDEX,51,SENSEX,SENSEX,Sensex
          // For indices, use exact match on SYMBOL_NAME (not UNDERLYING_SYMBOL)
          const sensex = instruments.find((inst) => {
            const symbolName = inst.SYMBOL_NAME?.toUpperCase();
            const exchange =
              inst.SEM_EXM_EXCH_ID || inst.EXCH_ID || inst.EXCHANGE_ID;
            const instrumentType = inst.INSTRUMENT || inst.INSTRUMENT_TYPE;
            const segment = inst.SEM_SEGMENT || inst.SEGMENT;
            // Exact match on symbol_name for indices (per Ruby implementation)
            return (
              symbolName === "SENSEX" &&
              exchange === "BSE" &&
              (instrumentType === "INDEX" ||
                segment === "I" ||
                segment?.toUpperCase() === "INDEX")
            );
          });

          if (nifty) {
            const niftyId =
              nifty.SEM_SECURITY_ID ||
              nifty.SECURITY_ID ||
              nifty.SM_SECURITY_ID;
            const niftySegment = nifty.SEM_SEGMENT || nifty.SEGMENT;
            const niftyExchange =
              nifty.SEM_EXM_EXCH_ID || nifty.EXCH_ID || nifty.EXCHANGE_ID;

            // Determine ExchangeSegment based on exchange and segment
            let exchangeSegment = "NSE_EQ"; // Default
            if (
              niftySegment === "I" ||
              niftySegment?.toUpperCase() === "INDEX"
            ) {
              // For indices, use IDX_I per Annexure (enum 0)
              exchangeSegment = "IDX_I";
            } else if (niftyExchange === "NSE") {
              exchangeSegment = "NSE_EQ";
            }

            if (niftyId) {
              setIndexInstruments((prev) => ({
                ...prev,
                NIFTY: {
                  ...prev.NIFTY,
                  securityId: parseInt(niftyId),
                  exchangeSegment: exchangeSegment,
                },
              }));
              console.log("Found NIFTY from instrument list:", {
                securityId: niftyId,
                exchangeSegment: exchangeSegment,
                instrument: nifty,
              });
            }
          }

          if (sensex) {
            const sensexId =
              sensex.SEM_SECURITY_ID ||
              sensex.SECURITY_ID ||
              sensex.SM_SECURITY_ID;
            const sensexSegment = sensex.SEM_SEGMENT || sensex.SEGMENT;
            const sensexExchange =
              sensex.SEM_EXM_EXCH_ID || sensex.EXCH_ID || sensex.EXCHANGE_ID;

            // Determine ExchangeSegment based on exchange and segment
            let exchangeSegment = "BSE_EQ"; // Default
            if (
              sensexSegment === "I" ||
              sensexSegment?.toUpperCase() === "INDEX"
            ) {
              // For indices, use IDX_I per Annexure (enum 0)
              exchangeSegment = "IDX_I";
            } else if (sensexExchange === "BSE") {
              exchangeSegment = "BSE_EQ";
            }

            if (sensexId) {
              setIndexInstruments((prev) => ({
                ...prev,
                SENSEX: {
                  ...prev.SENSEX,
                  securityId: parseInt(sensexId),
                  exchangeSegment: exchangeSegment,
                },
              }));
              console.log("Found SENSEX from instrument list:", {
                securityId: sensexId,
                exchangeSegment: exchangeSegment,
                instrument: sensex,
              });
            }
          }
        }
      } catch (err) {
        console.warn(
          "Could not fetch instrument list to find index Security IDs, using defaults:",
          err
        );
        // Continue with hardcoded values if lookup fails
      }
    };

    findIndexSecurityIds();
  }, []);

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
              if (!instrument) return;

              // Check which instrument this data is for
              // Try multiple field names and normalize to string for comparison
              // MarketFeed may return data in various formats - check all possible fields
              const securityId = String(
                instrument.securityId ||
                  instrument.security_id ||
                  instrument.SECURITY_ID ||
                  instrument.SecurityId ||
                  instrument.Security_ID ||
                  instrument.id ||
                  instrument.securityId ||
                  ""
              );

              const niftyId = indexInstruments.NIFTY.securityId
                ? String(indexInstruments.NIFTY.securityId)
                : "";
              const sensexId = indexInstruments.SENSEX.securityId
                ? String(indexInstruments.SENSEX.securityId)
                : "";

              // Debug logging for all incoming data
              if (
                securityId === niftyId ||
                securityId === sensexId ||
                securityId === "13" ||
                securityId === "51"
              ) {
                console.log("Index instrument data received:", {
                  securityId,
                  niftyId,
                  sensexId,
                  instrument,
                  rawData: data.data,
                });
              }

              // Match by security ID
              if (securityId === niftyId && niftyId) {
                console.log("✅ NIFTY data matched and updating:", instrument);
                setNiftyData(instrument);
              } else if (securityId === sensexId && sensexId) {
                console.log("✅ SENSEX data matched and updating:", instrument);
                setSensexData(instrument);
              }
            });
          }
          setError("");
        } else if (data.type === "connected") {
          console.log("Market feed connected:", data.message);
          setIsConnected(true);
        } else if (data.type === "error") {
          console.error("Market feed error:", data.message);
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
        // Only subscribe if we have valid security IDs
        if (
          !indexInstruments.NIFTY.securityId ||
          !indexInstruments.SENSEX.securityId
        ) {
          console.warn(
            "Waiting for Security IDs to be loaded from instrument list..."
          );
          return;
        }

        // Subscribe to both NIFTY and SENSEX using DhanHQ documented format
        // Format per DhanHQ docs: {RequestCode, InstrumentCount, InstrumentList: [{ExchangeSegment, SecurityId}]}
        // Note: Indices use IDX_I (Index segment) per Annexure, not NSE_EQ/BSE_EQ
        ws.send({
          RequestCode: 17, // 17 = Subscribe - Quote Packet (per DhanHQ Annexure)
          InstrumentCount: 2,
          InstrumentList: [
            {
              ExchangeSegment:
                indexInstruments.NIFTY.exchangeSegment || "IDX_I",
              SecurityId: indexInstruments.NIFTY.securityId.toString(),
            },
            {
              ExchangeSegment:
                indexInstruments.SENSEX.exchangeSegment || "IDX_I",
              SecurityId: indexInstruments.SENSEX.securityId.toString(),
            },
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
                  niftyData.lastPrice ||
                    niftyData.last_price ||
                    niftyData.ltp ||
                    niftyData.LTP ||
                    niftyData.close ||
                    niftyData.price
                )}
              </div>
              <div
                className={`text-xs ${getChangeColor(
                  niftyData.change || niftyData.changePercent
                )}`}
              >
                {formatChange(niftyData.change, niftyData.changePercent).value}{" "}
                (
                {
                  formatChange(niftyData.change, niftyData.changePercent)
                    .percent
                }
                )
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
                    sensexData.ltp ||
                    sensexData.LTP ||
                    sensexData.close ||
                    sensexData.price
                )}
              </div>
              <div
                className={`text-xs ${getChangeColor(
                  sensexData.change || sensexData.changePercent
                )}`}
              >
                {
                  formatChange(sensexData.change, sensexData.changePercent)
                    .value
                }{" "}
                (
                {
                  formatChange(sensexData.change, sensexData.changePercent)
                    .percent
                }
                )
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
        <div
          className="text-xs text-red-400 max-w-[200px] truncate"
          title={error}
        >
          {error}
        </div>
      )}
    </div>
  );
}

export default IndexIndicators;
