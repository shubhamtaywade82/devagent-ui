import { useState, useEffect, useRef } from "react";
import { TrendingUp, Wifi, WifiOff, Activity } from "lucide-react";
import api from "../../services/api";
import TradingWebSocket from "../../services/websocket";
import OptionChain from "./OptionChain";

function MarketData({ accessToken, initialInstrument = null, onInstrumentCleared }) {
  const [selectedInstrument, setSelectedInstrument] = useState(null);
  const [quoteData, setQuoteData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const fetchTimeoutRef = useRef(null);

  // Real-time feed state
  const [realTimeData, setRealTimeData] = useState(null);
  const [isFeedConnected, setIsFeedConnected] = useState(false);
  const [feedError, setFeedError] = useState("");
  const wsRef = useRef(null);

  // Intraday historical data state
  const [intradayData, setIntradayData] = useState(null);
  const [loadingIntraday, setLoadingIntraday] = useState(false);
  const [intradayError, setIntradayError] = useState("");
  const [intradayDate, setIntradayDate] = useState(null);

  // Real-time feed WebSocket connection
  useEffect(() => {
    if (!accessToken || !selectedInstrument?.securityId || !selectedInstrument?.exchangeSegment) {
      // Disconnect if no instrument selected
      if (wsRef.current) {
        wsRef.current.disconnect();
        wsRef.current = null;
      }
      setRealTimeData(null);
      setIsFeedConnected(false);
      return;
    }

    // Create WebSocket connection
    const ws = new TradingWebSocket(
      "/ws/trading/market-feed/{access_token}",
      accessToken,
      (data) => {
        if (data.type === "market_feed") {
          // Handle different data structures from backend
          let feedData = data.data;

          // If data is an array, find the matching security ID
          if (Array.isArray(feedData)) {
            const securityIdStr = selectedInstrument.securityId.toString();
            feedData = feedData.find(
              (item) =>
                item.security_id === securityIdStr ||
                item.securityId === securityIdStr ||
                item.SECURITY_ID === securityIdStr ||
                item.id === securityIdStr
            ) || feedData[0]; // Fallback to first item if no match
          }

          // Normalize field names - handle various formats
          if (feedData && typeof feedData === "object") {
            const normalizedData = {
              lastPrice: feedData.lastPrice || feedData.LTP || feedData.last_price || feedData.last_traded_price || feedData.currentPrice || feedData.CURRENT_PRICE,
              change: feedData.change || feedData.CHANGE || feedData.priceChange || feedData.price_change,
              changePercent: feedData.changePercent || feedData.change_percent || feedData.CHANGE_PERCENT || feedData.priceChangePercent,
              ...feedData
            };
            setRealTimeData(normalizedData);
          } else {
            setRealTimeData(feedData);
          }
          setFeedError("");
        } else if (data.type === "connected") {
          setIsFeedConnected(true);
        } else if (data.type === "market_status") {
          if (data.status === "no_data") {
            setFeedError(data.message || "No market data updates. Market may be closed.");
          }
        } else if (data.type === "error") {
          setFeedError(data.message);
        }
      },
      (err) => {
        setFeedError("WebSocket connection error");
        setIsFeedConnected(false);
      },
      () => {
        setIsFeedConnected(false);
      }
    );

    ws.connect();
    wsRef.current = ws;

    // Send subscription request after connection
    setTimeout(() => {
      if (ws.ws && ws.ws.readyState === WebSocket.OPEN) {
        ws.send({
          RequestCode: 17, // 17 = Subscribe - Quote Packet (per DhanHQ Annexure)
          InstrumentCount: 1,
          InstrumentList: [
            {
              ExchangeSegment: selectedInstrument.exchangeSegment || "NSE_EQ",
              SecurityId: selectedInstrument.securityId.toString(),
            },
          ],
          version: "v2",
        });
        setIsFeedConnected(true);
      }
    }, 1000);

    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect();
        wsRef.current = null;
      }
    };
  }, [accessToken, selectedInstrument?.securityId, selectedInstrument?.exchangeSegment]);

  // Handle initial instrument from header search
  useEffect(() => {
    if (initialInstrument) {
      // Validate instrument has required fields
      if (initialInstrument.securityId && initialInstrument.securityId.trim() !== "") {
        // Only update if it's a different instrument
        const currentId = selectedInstrument?.securityId;
        const newId = initialInstrument.securityId;
        if (currentId !== newId) {
          setSelectedInstrument(initialInstrument);
          // Add small delay to prevent rapid duplicate calls
          if (fetchTimeoutRef.current) {
            clearTimeout(fetchTimeoutRef.current);
          }
          fetchTimeoutRef.current = setTimeout(() => {
            fetchMarketQuote(initialInstrument);
          }, 150); // 150ms debounce
        }
      } else {
        setError(
          "Selected instrument has invalid Security ID. Please select another instrument."
        );
      }
    } else if (initialInstrument === null && selectedInstrument) {
      // Clear selection if initialInstrument is explicitly set to null
      setSelectedInstrument(null);
      setQuoteData(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialInstrument]);

  // Helper function to get instrument type from exchange segment
  const getInstrumentType = (exchangeSegment, instrument = null) => {
    if (exchangeSegment === "IDX_I") {
      return "INDEX";
    }
    if (exchangeSegment?.includes("FNO") || exchangeSegment?.includes("F_O")) {
      return "FUTURES";
    }
    if (instrument?.instrumentType) {
      return instrument.instrumentType;
    }
    // Default to EQUITY for most cases
    return "EQUITY";
  };

  // Helper function to get exchange name from exchange segment or instrument data
  const getExchangeName = (exchangeSegment, instrument = null) => {
    // First try to get from instrument's exchange field (set by InstrumentSearch)
    if (instrument?.exchange) {
      return instrument.exchange;
    }

    // Try to get from instrument's original data
    if (instrument?.instrument) {
      const exchange = instrument.instrument.SEM_EXM_EXCH_ID ||
                      instrument.instrument.EXCH_ID ||
                      instrument.instrument.EXCHANGE_ID;
      if (exchange) {
        return exchange.toUpperCase();
      }
    }

    // Fallback: extract from exchange segment format
    if (exchangeSegment === "IDX_I") {
      // For indices, we need to determine NSE or BSE from the instrument
      // NIFTY 50 (ID: 13) is NSE, SENSEX (ID: 51) is BSE
      if (instrument?.securityId) {
        const secId = parseInt(instrument.securityId);
        if (secId === 13) return "NSE"; // NIFTY 50
        if (secId === 51) return "BSE"; // SENSEX
      }
      // Default for IDX_I if we can't determine
      return "NSE";
    }

    // Extract exchange from segment format (e.g., "NSE_EQ" -> "NSE")
    if (exchangeSegment && exchangeSegment.includes("_")) {
      return exchangeSegment.split("_")[0];
    }

    return exchangeSegment || "NSE";
  };

  const handleInstrumentSelect = (instrument) => {
    if (!instrument) {
      setSelectedInstrument(null);
      setQuoteData(null);
      if (onInstrumentCleared) {
        onInstrumentCleared();
      }
      return;
    }

    // Validate instrument has required fields
    if (!instrument.securityId || instrument.securityId.trim() === "") {
      setError(
        "Selected instrument has invalid Security ID. Please select another instrument."
      );
      setSelectedInstrument(null);
      setQuoteData(null);
      if (onInstrumentCleared) {
        onInstrumentCleared();
      }
      return;
    }

    setSelectedInstrument(instrument);
    fetchMarketQuote(instrument);
  };

  const fetchMarketQuote = async (instrument) => {
    if (!instrument || !instrument.securityId) {
      setError("Please select an instrument");
      return;
    }

    // Clear any pending fetch to prevent duplicate calls
    if (fetchTimeoutRef.current) {
      clearTimeout(fetchTimeoutRef.current);
      fetchTimeoutRef.current = null;
    }

    setLoading(true);
    setError("");
    try {
      const securityId = parseInt(instrument.securityId);
      if (isNaN(securityId)) {
        setError("Invalid security ID");
        setLoading(false);
        return;
      }

      // Map exchange segment to API format
      const exchangeSegmentMap = {
        NSE_EQ: "NSE_EQ",
        BSE_EQ: "BSE_EQ",
        NSE_FNO: "NSE_FNO",
        BSE_FNO: "BSE_FNO",
        MCX_COM: "MCX_COM",
        IDX_I: "IDX_I", // Indices
      };
      const exchangeSegment =
        exchangeSegmentMap[instrument.exchangeSegment] || instrument.exchangeSegment || "NSE_EQ";

      const response = await api.getMarketQuote({
        access_token: accessToken,
        securities: { [exchangeSegment]: [securityId] },
      });

      // Check if response indicates failure
      if (response.data?.status === 'failure' || response.data?.status === 'failed') {
        let errorMsg = "Failed to get market quote";
        const responseData = response.data;
        const remarks = responseData?.remarks;
        let data = responseData?.data;

        // Handle nested data structure: data.data.805
        if (data?.data && typeof data.data === 'object') {
          data = data.data;
        }

        // First, check if error message is in data object (e.g., data.805 = "Too many requests...")
        if (data && typeof data === 'object') {
          const dataKeys = Object.keys(data);
          for (const key of dataKeys) {
            const value = data[key];
            if (typeof value === 'string' && value.length > 0) {
              errorMsg = value;
              break;
            }
          }
        }

        // If no message found in data, check remarks
        if (errorMsg === "Failed to get market quote" && remarks) {
          if (typeof remarks === 'string') {
            errorMsg = remarks;
          } else if (typeof remarks === 'object') {
            // Extract error message from object
            errorMsg = remarks.error_message ||
                      remarks.message ||
                      remarks.error ||
                      (remarks.error_code ? `Error ${remarks.error_code}` : null) ||
                      (remarks.error_type ? `Error: ${remarks.error_type}` : null) ||
                      errorMsg;
          }
        }

        // Fallback to response.error
        if (errorMsg === "Failed to get market quote" && response.error) {
          errorMsg = response.error;
        }

        setError(errorMsg);
        console.error("API returned failure:", responseData);
        return;
      }

      if (response.success) {
        // Parse the nested response structure
        // Response structure: data.data.data.{EXCHANGE_SEGMENT}.{securityId}
        const responseData = response.data;
        let quoteInfo = null;

        // Try to extract the actual quote data from nested structure
        // Handle both direct data.data and nested data.data.data structures
        let nestedData = null;
        if (responseData?.data?.data) {
          nestedData = responseData.data.data;
        } else if (responseData?.data) {
          nestedData = responseData.data;
        }

        if (nestedData) {
          // Find the matching exchange segment and security
          for (const seg in nestedData) {
            const securities = nestedData[seg];
            if (securities && typeof securities === 'object') {
              // Look for the security ID in this segment
              const secIdStr = securityId.toString();
              if (securities[secIdStr] || securities[securityId]) {
                const quote = securities[secIdStr] || securities[securityId];
                quoteInfo = {
                  securityId: secIdStr,
                  exchangeSegment: seg,
                  last_price: quote.last_price || quote.LTP || quote.lastPrice || quote.last_traded_price,
                  ohlc: quote.ohlc || quote.OHLC || {
                    open: quote.open || quote.OPEN,
                    high: quote.high || quote.HIGH,
                    low: quote.low || quote.LOW,
                    close: quote.close || quote.CLOSE,
                  },
                  ...quote,
                };
                break;
              }
            }
            if (quoteInfo) break;
          }
        }

        if (quoteInfo) {
          setQuoteData(quoteInfo);
          // Fetch intraday data after quote data is loaded
          fetchIntradayData(instrument);
        } else {
          console.error("Could not parse quote data. Response structure:", responseData);
          setError("Could not parse quote data from response");
        }
      } else {
        setError(response.error || "Failed to get market quote");
      }
    } catch (err) {
      setError(err.message || "Failed to get market quote");
    } finally {
      setLoading(false);
    }
  };

  // Fetch intraday historical data - tries today first, then goes back to find last trading day
  const fetchIntradayData = async (instrument) => {
    if (!accessToken || !instrument || !instrument.securityId) {
      return;
    }

    setLoadingIntraday(true);
    setIntradayError("");

    try {
      // Convert securityId to string as required by DhanHQ API
      const securityId = String(instrument.securityId || "");
      if (!securityId || securityId === "NaN") {
        setIntradayError("Invalid security ID");
        setLoadingIntraday(false);
        return;
      }

      const exchangeSegment = instrument.exchangeSegment || "NSE_EQ";
      const instrumentType = getInstrumentType(exchangeSegment, instrument);

      // Helper function to get date string N days ago
      const getDateString = (daysAgo = 0) => {
        const date = new Date();
        date.setDate(date.getDate() - daysAgo);
        return date.toISOString().split('T')[0];
      };

      // DhanHQ intraday_minute_data returns data for last 5 trading days
      // We need to provide valid dates - use a range that ensures we get data
      // The API automatically returns the last 5 trading days, so we just need valid dates
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      // Find the most recent weekday (skip weekends)
      let toDate = new Date(today);
      while (toDate.getDay() === 0 || toDate.getDay() === 6) {
        toDate.setDate(toDate.getDate() - 1);
      }

      // If it's still today and market might not have data yet, go back one more day
      // This ensures we request a date that definitely has historical data
      if (toDate.getTime() === today.getTime()) {
        toDate.setDate(toDate.getDate() - 1);
        // Skip weekends
        while (toDate.getDay() === 0 || toDate.getDay() === 6) {
          toDate.setDate(toDate.getDate() - 1);
        }
      }

      // Format dates as "YYYY-MM-DD HH:MM:SS" for REST API
      const toDateStr = toDate.toISOString().split('T')[0] + " 15:30:00"; // Market close time
      const fromDate = new Date(toDate);
      fromDate.setDate(fromDate.getDate() - 1); // Previous day (ensures from_date != to_date)
      // Skip weekends for from_date too
      while (fromDate.getDay() === 0 || fromDate.getDay() === 6) {
        fromDate.setDate(fromDate.getDate() - 1);
      }
      const fromDateStr = fromDate.toISOString().split('T')[0] + " 09:15:00"; // Market open time

      console.log(`[Intraday] Date range: from=${fromDateStr}, to=${toDateStr}`);

      try {
        console.log(`[Intraday] Fetching data:`, {
          security_id: securityId,
          exchange_segment: exchangeSegment,
          instrument_type: instrumentType,
          from_date: fromDateStr,
          to_date: toDateStr,
          interval: "5"
        });

        // Use numeric interval (5 minutes) - DhanHQ API expects numeric values: 1, 5, 10, 15, 60
        const response = await api.getHistoricalData({
          access_token: accessToken,
          security_id: securityId,
          exchange_segment: exchangeSegment,
          instrument_type: instrumentType.toUpperCase(), // Ensure uppercase (INDEX, EQUITY, etc.)
          from_date: fromDateStr,
          to_date: toDateStr,
          interval: "5", // Fetch intraday minute data with 5-minute interval (supported: 1, 5, 10, 15, 60)
        });

        console.log(`[Intraday] API Response:`, {
          success: response.success,
          hasData: !!response.data,
          dataType: typeof response.data,
          isArray: Array.isArray(response.data),
          dataKeys: response.data && typeof response.data === 'object' ? Object.keys(response.data) : null,
          error: response.error
        });

        if (response.success && response.data) {
          // Handle different response structures
          let allData = response.data;
          if (Array.isArray(allData)) {
            allData = allData;
          } else if (allData.data && Array.isArray(allData.data)) {
            allData = allData.data;
          } else if (allData.historical && Array.isArray(allData.historical)) {
            allData = allData.historical;
          } else if (typeof allData === 'object' && allData !== null) {
            // Try to find array in object values
            const values = Object.values(allData);
            const arrayValue = values.find(v => Array.isArray(v));
            if (arrayValue) {
              allData = arrayValue;
            } else {
              allData = [];
            }
          } else {
            allData = [];
          }

          console.log(`[Intraday] Parsed data:`, {
            length: allData.length,
            firstItem: allData.length > 0 ? allData[0] : null,
            sampleKeys: allData.length > 0 ? Object.keys(allData[0]) : null
          });

          if (allData && allData.length > 0) {
            // Group data by date to find the most recent trading day with data
            const dataByDate = {};
            let itemsWithoutDate = 0;

            allData.forEach((item, index) => {
              // Try multiple possible date field names (timestamp is most common for OHLC data)
              const itemDate = item.timestamp || item.TIMESTAMP || item.date || item.DATE ||
                              item.time || item.TIME || item.datetime || item.DATETIME ||
                              item.start_time || item.START_TIME || item.startTime || "";

              if (!itemDate) {
                itemsWithoutDate++;
                // If no date field, log for debugging
                console.warn(`[Intraday] Item ${index} has no date field. Available keys:`, Object.keys(item));
                return;
              }

              try {
                // Handle different date formats
                let itemDateStr;
                if (typeof itemDate === 'string') {
                  // Try parsing as ISO string or other formats
                  const dateObj = new Date(itemDate);
                  if (!isNaN(dateObj.getTime())) {
                    itemDateStr = dateObj.toISOString().split('T')[0];
                  } else {
                    // Try parsing as YYYY-MM-DD directly
                    if (/^\d{4}-\d{2}-\d{2}/.test(itemDate)) {
                      itemDateStr = itemDate.split('T')[0].split(' ')[0];
                    } else {
                      console.warn(`[Intraday] Could not parse date: ${itemDate}`);
                      return;
                    }
                  }
                } else if (itemDate instanceof Date) {
                  itemDateStr = itemDate.toISOString().split('T')[0];
                } else if (typeof itemDate === 'number') {
                  // Handle Unix timestamp (seconds or milliseconds)
                  const dateObj = new Date(itemDate * (itemDate < 10000000000 ? 1000 : 1));
                  itemDateStr = dateObj.toISOString().split('T')[0];
                } else {
                  console.warn(`[Intraday] Unexpected date type:`, typeof itemDate, itemDate);
                  return;
                }

                if (!dataByDate[itemDateStr]) {
                  dataByDate[itemDateStr] = [];
                }
                dataByDate[itemDateStr].push(item);
              } catch (e) {
                // Skip items with invalid dates
                console.warn(`[Intraday] Error parsing date for item ${index}:`, e, itemDate);
              }
            });

            console.log(`[Intraday] Grouped by date:`, {
              dates: Object.keys(dataByDate),
              counts: Object.keys(dataByDate).map(d => ({ date: d, count: dataByDate[d].length })),
              itemsWithoutDate
            });

            // Find the most recent date with data (checking from today backwards)
            let mostRecentDate = null;
            for (let daysBack = 0; daysBack <= 7; daysBack++) {
              const checkDate = getDateString(daysBack);
              if (dataByDate[checkDate] && dataByDate[checkDate].length > 0) {
                mostRecentDate = checkDate;
                break;
              }
            }

            // If no date match found but we have data, use the most recent date in the data
            if (!mostRecentDate && Object.keys(dataByDate).length > 0) {
              const sortedDates = Object.keys(dataByDate).sort().reverse();
              mostRecentDate = sortedDates[0];
              console.log(`[Intraday] Using most recent date from data: ${mostRecentDate}`);
            }

            if (mostRecentDate) {
              // Use data from the most recent trading day
              const dataToUse = dataByDate[mostRecentDate];
              setIntradayData(dataToUse);
              setIntradayDate(mostRecentDate);
              console.log(`[Intraday] Success: Found data for ${mostRecentDate}, ${dataToUse.length} entries`);
            } else {
              console.warn(`[Intraday] No matching date found. Available dates:`, Object.keys(dataByDate));
              setIntradayError("No intraday data available for recent trading days");
              setIntradayData(null);
              setIntradayDate(null);
            }
          } else {
            console.warn(`[Intraday] Response successful but no data array found`);
            setIntradayError("No intraday data available for recent trading days");
            setIntradayData(null);
            setIntradayDate(null);
          }
        } else {
          const errorMsg = response.error || "Failed to fetch intraday data";
          console.error(`[Intraday] API Error:`, errorMsg, response);
          setIntradayError(errorMsg);
          setIntradayData(null);
          setIntradayDate(null);
        }
      } catch (err) {
        console.error("[Intraday] Exception fetching intraday data:", err);
        setIntradayError(err.message || "Failed to fetch intraday data");
        setIntradayData(null);
        setIntradayDate(null);
      }
    } catch (err) {
      console.error("Error fetching intraday data:", err);
      setIntradayError(err.message || "Failed to fetch intraday data");
      setIntradayData(null);
    } finally {
      setLoadingIntraday(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <TrendingUp className="w-6 h-6 text-green-500" />
          <h2 className="text-2xl font-bold font-manrope">Market Data</h2>
        </div>
        {selectedInstrument && selectedInstrument.securityId && (
          <div className="text-sm text-zinc-400">
            Selected:{" "}
            <span className="text-white font-medium">
              {selectedInstrument.displayName ||
                selectedInstrument.symbolName}
            </span>{" "}
            (ID: {selectedInstrument.securityId},{" "}
            {selectedInstrument.exchangeSegment})
            {selectedInstrument.underlyingSymbol && (
              <span className="ml-2 text-zinc-500">
                | Underlying:{" "}
                <span className="text-zinc-300">
                  {selectedInstrument.underlyingSymbol}
                </span>
              </span>
            )}
          </div>
        )}
        {error && (
          <div className="mt-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        )}
      </div>

      {!selectedInstrument && (
        <div className="glass rounded-xl p-12 text-center">
          <TrendingUp className="w-16 h-16 text-zinc-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-zinc-400 mb-2">
            No Instrument Selected
          </h3>
          <p className="text-sm text-zinc-500">
            Use the search bar in the header to select an instrument and view its market data
          </p>
        </div>
      )}

      {quoteData && selectedInstrument && (
        <>
          {/* Top Row - LTP and Option Chain */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
            {/* Left Side - Last Traded Price with Real-Time Feed integrated */}
            <div className="glass rounded-lg p-3">
              <div className="flex items-center justify-between mb-1">
                <div className="text-xs text-zinc-400">Last Traded Price</div>
                <div className="flex items-center gap-1.5">
                  {isFeedConnected && realTimeData ? (
                    <>
                      <Activity className="w-3 h-3 text-green-500 animate-pulse" />
                      <Wifi className="w-3 h-3 text-green-500" />
                      <span className="text-xs text-green-500">Live</span>
                    </>
                  ) : (
                    <>
                      <WifiOff className="w-3 h-3 text-zinc-500" />
                      <span className="text-xs text-zinc-500">LTP</span>
                    </>
                  )}
                </div>
              </div>

              {/* Show real-time data if connected and available, otherwise show LTP from quote */}
              <div className="text-3xl font-bold text-green-500 mb-1">
                ₹{isFeedConnected && realTimeData?.lastPrice !== undefined && realTimeData?.lastPrice !== null
                  ? (typeof realTimeData.lastPrice === 'number'
                      ? realTimeData.lastPrice.toFixed(2)
                      : parseFloat(realTimeData.lastPrice)?.toFixed(2) || quoteData.last_price?.toFixed(2) || "0.00")
                  : quoteData.last_price?.toFixed(2) || "0.00"}
              </div>

              <div className="text-xs text-zinc-500 mb-1.5 leading-tight">
                Security ID: {quoteData.securityId} | Exchange:{" "}
                {getExchangeName(quoteData.exchangeSegment, selectedInstrument)}
                {selectedInstrument?.underlyingSymbol && (
                  <> | Underlying: <span className="text-zinc-400">{selectedInstrument.underlyingSymbol}</span></>
                )}
              </div>

              {/* Show real-time change if available */}
              {isFeedConnected && realTimeData?.change !== undefined && (
                <div className={`text-sm font-semibold mb-1.5 ${
                  (realTimeData.change || 0) >= 0 ? "text-green-400" : "text-red-400"
                }`}>
                  {realTimeData.change >= 0 ? "+" : ""}
                  {realTimeData.change.toFixed(2)}
                  {realTimeData.changePercent !== undefined && (
                    <span className="text-xs ml-1">
                      ({realTimeData.changePercent >= 0 ? "+" : ""}
                      {realTimeData.changePercent.toFixed(2)}%)
                    </span>
                  )}
                </div>
              )}

              {/* Show feed error if any */}
              {feedError && (
                <div className="mb-1.5 p-1.5 bg-red-500/20 border border-red-500/50 rounded text-red-400 text-xs">
                  {feedError}
                </div>
              )}

              {/* OHLC Data - Compact grid layout */}
              {quoteData.ohlc && (
                <div className="mt-2.5 pt-2.5 border-t border-zinc-800">
                  <h4 className="text-xs font-medium text-zinc-400 mb-1.5">
                    OHLC (Open, High, Low, Close)
                  </h4>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-zinc-500">Open</span>
                      <span className="text-sm font-semibold text-white">
                        ₹{quoteData.ohlc.open?.toFixed(2) || "0.00"}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-zinc-500">High</span>
                      <span className="text-sm font-semibold text-green-400">
                        ₹{quoteData.ohlc.high?.toFixed(2) || "0.00"}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-zinc-500">Low</span>
                      <span className="text-sm font-semibold text-red-400">
                        ₹{quoteData.ohlc.low?.toFixed(2) || "0.00"}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-zinc-500">Close</span>
                      <span className="text-sm font-semibold text-white">
                        ₹{quoteData.ohlc.close?.toFixed(2) || "0.00"}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Intraday Historical Data - Below OHLC */}
              <div className="mt-2.5 pt-2.5 border-t border-zinc-800">
                <div className="flex items-center justify-between mb-1.5">
                  <h4 className="text-xs font-medium text-zinc-400">
                    Intraday Data
                  </h4>
                  {intradayDate && (
                    <span className="text-[10px] text-zinc-500">
                      {(() => {
                        const today = new Date().toISOString().split('T')[0];
                        const dateObj = new Date(intradayDate);
                        if (intradayDate === today) {
                          return "Today";
                        } else {
                          return dateObj.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
                        }
                      })()}
                    </span>
                  )}
                </div>
                {loadingIntraday ? (
                  <div className="text-xs text-zinc-500 py-2">Loading intraday data...</div>
                ) : intradayError ? (
                  <div className="text-xs text-red-400 py-1">{intradayError}</div>
                ) : intradayData && intradayData.length > 0 ? (
                  <div className="space-y-0.5 max-h-32 overflow-y-auto">
                    {(() => {
                      // Get last 10 items and reverse to show most recent first
                      const recentData = intradayData.slice(-10).reverse();
                      return recentData.map((item, index) => {
                        // Handle different data structures
                        const time = item.time || item.TIME || item.timestamp || item.date || item.datetime || "";
                        const price = item.close || item.CLOSE || item.price || item.last_price || item.ltp || 0;
                        const priceNum = typeof price === 'number' ? price : parseFloat(price || 0);

                        // Calculate change from previous item (next in reversed array)
                        const prevItem = recentData[index + 1];
                        const prevPrice = prevItem
                          ? (prevItem.close || prevItem.CLOSE || prevItem.price || prevItem.last_price || prevItem.ltp || priceNum)
                          : priceNum;
                        const prevPriceNum = typeof prevPrice === 'number' ? prevPrice : parseFloat(prevPrice || priceNum);
                        const change = priceNum - prevPriceNum;

                        // Format time
                        let timeStr = 'N/A';
                        if (time) {
                          try {
                            const timeDate = new Date(time);
                            if (!isNaN(timeDate.getTime())) {
                              timeStr = timeDate.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
                            } else if (typeof time === 'string' && time.includes(':')) {
                              // Handle time string format like "09:30:00"
                              timeStr = time.substring(0, 5);
                            }
                          } catch (e) {
                            timeStr = String(time).substring(0, 5);
                          }
                        }

                        return (
                          <div key={index} className="flex justify-between items-center text-xs py-0.5">
                            <span className="text-zinc-500 text-[10px]">{timeStr}</span>
                            <span className={`font-medium text-xs ${change > 0 ? 'text-green-400' : change < 0 ? 'text-red-400' : 'text-white'}`}>
                              ₹{priceNum.toFixed(2)}
                            </span>
                          </div>
                        );
                      });
                    })()}
                  </div>
                ) : (
                  <div className="text-xs text-zinc-500 py-2">No intraday data available</div>
                )}
              </div>
            </div>

            {/* Right Side - Option Chain */}
            <div>
              <OptionChain
                accessToken={accessToken}
                selectedInstrument={selectedInstrument}
              />
            </div>
          </div>
        </>
      )}

      {/* Additional Info Section */}
      {selectedInstrument && !quoteData && !loading && (
        <div className="glass rounded-xl p-8 text-center">
          <div className="text-zinc-400">Loading market data...</div>
        </div>
      )}
    </div>
  );
}

export default MarketData;
