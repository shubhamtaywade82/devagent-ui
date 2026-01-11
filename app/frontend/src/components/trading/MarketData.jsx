import { useState, useEffect, useRef } from "react";
import { TrendingUp } from "lucide-react";
import api from "../../services/api";
import RealTimeMarketFeed from "./RealTimeMarketFeed";
import OptionChain from "./OptionChain";

function MarketData({ accessToken, initialInstrument = null, onInstrumentCleared }) {
  const [selectedInstrument, setSelectedInstrument] = useState(null);
  const [quoteData, setQuoteData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const fetchTimeoutRef = useRef(null);

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
          {/* Quote Data - Combined LTP and OHLC */}
          <div className="glass rounded-xl p-6 mb-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Left Side - Last Traded Price */}
              <div>
                <div className="text-sm text-zinc-400 mb-2">Last Traded Price</div>
                <div className="text-5xl font-bold text-green-500 mb-4">
                  ₹{quoteData.last_price?.toFixed(2) || "0.00"}
                </div>
                <div className="text-xs text-zinc-500">
                  Security ID: {quoteData.securityId} | Exchange:{" "}
                  {getExchangeName(quoteData.exchangeSegment, selectedInstrument)}
                  {selectedInstrument?.underlyingSymbol && (
                    <> | Underlying: <span className="text-zinc-400">{selectedInstrument.underlyingSymbol}</span></>
                  )}
                </div>
              </div>

              {/* Right Side - OHLC Data */}
              {quoteData.ohlc && (
                <div>
                  <h4 className="text-sm font-medium text-zinc-400 mb-4">
                    OHLC (Open, High, Low, Close)
                  </h4>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-zinc-500">Open</span>
                      <span className="text-lg font-semibold text-white">
                        ₹{quoteData.ohlc.open?.toFixed(2) || "0.00"}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-zinc-500">High</span>
                      <span className="text-lg font-semibold text-green-400">
                        ₹{quoteData.ohlc.high?.toFixed(2) || "0.00"}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-zinc-500">Low</span>
                      <span className="text-lg font-semibold text-red-400">
                        ₹{quoteData.ohlc.low?.toFixed(2) || "0.00"}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-zinc-500">Close</span>
                      <span className="text-lg font-semibold text-white">
                        ₹{quoteData.ohlc.close?.toFixed(2) || "0.00"}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Bottom Row - Real-Time Feed and Option Chain */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* Real-Time Market Feed */}
            <div>
              <RealTimeMarketFeed
                accessToken={accessToken}
                securityId={parseInt(selectedInstrument.securityId)}
                exchangeSegment={selectedInstrument.exchangeSegment || "NSE_EQ"}
              />
            </div>

            {/* Option Chain - Only for indices */}
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
