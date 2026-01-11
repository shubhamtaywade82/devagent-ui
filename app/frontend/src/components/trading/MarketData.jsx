import { useState, useEffect } from "react";
import { Search, TrendingUp } from "lucide-react";
import api from "../../services/api";
import RealTimeMarketFeed from "./RealTimeMarketFeed";
import InstrumentSearch from "./InstrumentSearch";

function MarketData({ accessToken, initialInstrument = null, onInstrumentCleared }) {
  const [selectedInstrument, setSelectedInstrument] = useState(null);
  const [quoteData, setQuoteData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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
          fetchMarketQuote(initialInstrument);
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

      if (response.success) {
        // Parse the nested response structure
        // Response structure: data.data.data.NSE_EQ.{securityId}
        const responseData = response.data;
        let quoteInfo = null;

        // Try to extract the actual quote data from nested structure
        if (responseData?.data?.data) {
          const nestedData = responseData.data.data;
          // Find the first exchange segment and security
          for (const seg in nestedData) {
            const securities = nestedData[seg];
            for (const secId in securities) {
              quoteInfo = {
                securityId: secId,
                exchangeSegment: seg,
                ...securities[secId],
              };
              break;
            }
            if (quoteInfo) break;
          }
        }

        if (quoteInfo) {
          setQuoteData(quoteInfo);
        } else {
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
    <div
      className="h-full overflow-y-auto p-6"
      style={{ position: "relative" }}
    >
      <div className="max-w-4xl mx-auto relative" style={{ zIndex: 1 }}>
        <div
          className="glass rounded-xl p-8 mb-6 relative"
          style={{ zIndex: 1 }}
        >
          <div className="flex items-center gap-3 mb-6">
            <TrendingUp className="w-6 h-6 text-green-500" />
            <h2 className="text-2xl font-bold font-manrope">Market Data</h2>
          </div>

          <div className="space-y-4 relative" style={{ zIndex: 1000 }}>
            <InstrumentSearch
              onSelect={handleInstrumentSelect}
              placeholder="Search by symbol name (e.g., HDFC BANK, RELIANCE) or Security ID..."
              accessToken={accessToken}
            />
            {selectedInstrument && (
              <div className="text-sm">
                {selectedInstrument.securityId ? (
                  <div className="text-zinc-400">
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
                ) : (
                  <div className="text-red-400 bg-red-500/20 border border-red-500/50 rounded-lg p-3">
                    ⚠️ Selected instrument "
                    {selectedInstrument.displayName ||
                      selectedInstrument.symbolName}
                    " is missing Security ID. This instrument may not be
                    tradable or may require a different identifier. Please
                    select a different instrument.
                  </div>
                )}
              </div>
            )}
          </div>

          {error && (
            <div className="mt-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}
        </div>

        {quoteData && (
          <>
            <div className="glass rounded-xl p-8 mb-6">
              <h3 className="text-lg font-semibold mb-4">Quote Data</h3>

              {/* Last Price */}
              <div className="mb-6">
                <div className="bg-zinc-900 rounded-lg p-6">
                  <div className="text-sm text-zinc-400 mb-2">
                    Last Traded Price
                  </div>
                  <div className="text-4xl font-bold text-green-500">
                    ₹{quoteData.last_price?.toFixed(2) || "0.00"}
                  </div>
                  <div className="text-xs text-zinc-500 mt-2">
                    Security ID: {quoteData.securityId} | Exchange:{" "}
                    {getExchangeName(quoteData.exchangeSegment, selectedInstrument)}
                    {selectedInstrument?.underlyingSymbol && (
                      <> | Underlying: <span className="text-zinc-400">{selectedInstrument.underlyingSymbol}</span></>
                    )}
                  </div>
                </div>
              </div>

              {/* OHLC Data */}
              {quoteData.ohlc && (
                <div>
                  <h4 className="text-sm font-medium text-zinc-400 mb-3">
                    OHLC (Open, High, Low, Close)
                  </h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-zinc-900 rounded-lg p-4">
                      <div className="text-sm text-zinc-400 mb-1">Open</div>
                      <div className="text-lg font-semibold text-white">
                        ₹{quoteData.ohlc.open?.toFixed(2) || "0.00"}
                      </div>
                    </div>
                    <div className="bg-zinc-900 rounded-lg p-4">
                      <div className="text-sm text-zinc-400 mb-1">High</div>
                      <div className="text-lg font-semibold text-green-400">
                        ₹{quoteData.ohlc.high?.toFixed(2) || "0.00"}
                      </div>
                    </div>
                    <div className="bg-zinc-900 rounded-lg p-4">
                      <div className="text-sm text-zinc-400 mb-1">Low</div>
                      <div className="text-lg font-semibold text-red-400">
                        ₹{quoteData.ohlc.low?.toFixed(2) || "0.00"}
                      </div>
                    </div>
                    <div className="bg-zinc-900 rounded-lg p-4">
                      <div className="text-sm text-zinc-400 mb-1">Close</div>
                      <div className="text-lg font-semibold text-white">
                        ₹{quoteData.ohlc.close?.toFixed(2) || "0.00"}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Real-Time Market Feed */}
            {selectedInstrument && (
              <RealTimeMarketFeed
                accessToken={accessToken}
                securityId={parseInt(selectedInstrument.securityId)}
                exchangeSegment={selectedInstrument.exchangeSegment || "NSE_EQ"}
              />
            )}
          </>
        )}

        <div className="mt-6 glass rounded-xl p-8">
          <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-zinc-900 rounded-lg p-4">
              <h4 className="text-sm font-medium text-zinc-400 mb-2">
                Option Chain
              </h4>
              <p className="text-sm text-zinc-500">
                View option chain for Nifty, Bank Nifty, etc.
              </p>
              <p className="text-xs text-zinc-600 mt-2">Coming soon...</p>
            </div>
            <div className="bg-zinc-900 rounded-lg p-4">
              <h4 className="text-sm font-medium text-zinc-400 mb-2">
                Historical Data
              </h4>
              <p className="text-sm text-zinc-500">
                Get historical OHLC data for analysis
              </p>
              <p className="text-xs text-zinc-600 mt-2">Coming soon...</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default MarketData;
