import { useState, useEffect, useRef } from "react";
import { Calendar, ChevronDown, Loader2 } from "lucide-react";
import api from "../../services/api";

function OptionChain({ accessToken, selectedInstrument }) {
  const [expiryList, setExpiryList] = useState([]);
  const [selectedExpiry, setSelectedExpiry] = useState("");
  const [optionChain, setOptionChain] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingExpiry, setLoadingExpiry] = useState(false);
  const [error, setError] = useState("");
  const [showExpiryDropdown, setShowExpiryDropdown] = useState(false);
  const expiryDropdownRef = useRef(null);

  // For option chain, use the instrument's security ID directly as the underlying security ID
  // According to DhanHQ API: option_chain(under_security_id, under_exchange_segment, expiry)
  // The under_security_id is the security ID of the underlying instrument
  const getOptionUnderlyingId = () => {
    if (!selectedInstrument || !selectedInstrument.securityId) {
      return null;
    }
    return parseInt(selectedInstrument.securityId);
  };

  // Get exchange segment for options
  // According to DhanHQ API: under_exchange_segment should be the exchange segment (e.g., IDX_I, NSE_FO, BSE_FO)
  // For indices, use IDX_I directly
  // For equity, use NSE_FO or BSE_FO
  const getOptionExchangeSegment = (instrument) => {
    if (!instrument) return "IDX_I";

    const exchangeSegment = instrument.exchangeSegment;

    // For indices (IDX_I), use IDX_I directly
    if (exchangeSegment === "IDX_I") {
      return "IDX_I";
    }

    // For equity segments, convert to F&O segment (NSE_EQ -> NSE_FO, BSE_EQ -> BSE_FO)
    if (exchangeSegment === "NSE_EQ") {
      return "NSE_FO";
    }
    if (exchangeSegment === "BSE_EQ") {
      return "BSE_FO";
    }

    // If already a F&O segment, use it as is
    if (exchangeSegment === "NSE_FO" || exchangeSegment === "BSE_FO") {
      return exchangeSegment;
    }

    // Fallback - try to construct from exchange segment
    if (exchangeSegment && exchangeSegment.includes("_")) {
      const [exchange] = exchangeSegment.split("_");
      return `${exchange}_FO`;
    }

    // Default fallback
    return "IDX_I";
  };

  // Check if instrument is an index
  const isIndex = (instrument) => {
    if (!instrument) return false;
    return instrument.exchangeSegment === "IDX_I" ||
           instrument.instrumentType === "INDEX" ||
           (instrument.instrument?.INSTRUMENT || "").toUpperCase() === "INDEX";
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        expiryDropdownRef.current &&
        !expiryDropdownRef.current.contains(event.target)
      ) {
        setShowExpiryDropdown(false);
      }
    };

    if (showExpiryDropdown) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [showExpiryDropdown]);

  // Fetch expiry list when instrument changes
  useEffect(() => {
    if (!accessToken || !selectedInstrument || !isIndex(selectedInstrument)) {
      setExpiryList([]);
      setSelectedExpiry("");
      setOptionChain(null);
      return;
    }

    const fetchExpiryList = async () => {
      setLoadingExpiry(true);
      setError("");
      try {
        const underlyingIdValue = getOptionUnderlyingId();
        const exchangeSegment = getOptionExchangeSegment(selectedInstrument);

        if (!underlyingIdValue) {
          setError("Could not determine underlying security ID for options");
          setLoadingExpiry(false);
          return;
        }

        const response = await api.getExpiryList({
          access_token: accessToken,
          under_security_id: underlyingIdValue,
          under_exchange_segment: exchangeSegment,
        });

        console.log("Expiry list response:", response);
        console.log("Response type check - success:", response.success, "status:", response.status);
        console.log("Response.data:", response.data);
        console.log("Response.data.data:", response.data?.data);
        console.log("Response.data.data.data:", response.data?.data?.data);

        // Handle both success: true and status: "success" formats
        const isSuccess = response.success === true || response.status === "success";

        // Try to extract expiries regardless of success flag (sometimes data is there even if status is different)
        let expiries = [];

        // Response structure from backend:
        // { success: true, data: { status: "success", data: { data: [...], status: "success" } } }
        // So we need to check response.data.data.data (three levels deep)
        if (response.data?.data?.data && Array.isArray(response.data.data.data)) {
          expiries = response.data.data.data;
          console.log("Found expiries in response.data.data.data:", expiries);
        } else if (response.data?.data && Array.isArray(response.data.data)) {
          // Fallback: two levels deep
          expiries = response.data.data;
          console.log("Found expiries in response.data.data:", expiries);
        } else if (Array.isArray(response.data)) {
          // Direct array format: { data: ["2026-01-13", ...], status: "success" }
          expiries = response.data;
          console.log("Found expiries in response.data (array):", expiries);
        } else if (response.data?.expiry_list && Array.isArray(response.data.expiry_list)) {
          // Alternative format with expiry_list key
          expiries = response.data.expiry_list;
          console.log("Found expiries in response.data.expiry_list:", expiries);
        } else if (isSuccess && response.data) {
          // Last resort: check if data itself might be the array (unlikely but possible)
          console.warn("Unexpected response format, attempting to extract expiries");
        }

        console.log("Final parsed expiry list:", expiries, "Length:", expiries.length);

        if (expiries.length > 0) {
          setExpiryList(expiries);
          setError(""); // Clear any previous errors

          // Auto-select the first (nearest) expiry and load option chain
          const firstExpiry = expiries[0];
          setSelectedExpiry(firstExpiry);
          console.log("Auto-loading option chain for expiry:", firstExpiry);
          // Always fetch option chain for the first expiry
          fetchOptionChain(underlyingIdValue, exchangeSegment, firstExpiry);
        } else if (isSuccess) {
          // Only show error if we expected success but found no expiries
          console.error("No expiries found in response. Full response:", JSON.stringify(response, null, 2));
          setError("No expiry dates found");
          setExpiryList([]);
        } else {
          // Handle error response
          let errorMsg = "Failed to fetch expiry list";
          if (response.data?.data && typeof response.data.data === 'object') {
            const dataKeys = Object.keys(response.data.data);
            for (const key of dataKeys) {
              const value = response.data.data[key];
              if (typeof value === 'string' && value.length > 0) {
                errorMsg = value;
                break;
              }
            }
          } else if (response.error) {
            errorMsg = response.error;
          }
          setError(errorMsg);
        }
      } catch (err) {
        setError(err.message || "Failed to fetch expiry list");
      } finally {
        setLoadingExpiry(false);
      }
    };

    fetchExpiryList();
  }, [accessToken, selectedInstrument]);

  // Fetch option chain
  const fetchOptionChain = async (underlyingId, exchangeSegment, expiry) => {
    if (!accessToken || !underlyingId || !exchangeSegment || !expiry) {
      return;
    }

    setLoading(true);
    setError("");
    try {
      const response = await api.getOptionChain({
        access_token: accessToken,
        under_security_id: underlyingId,
        under_exchange_segment: exchangeSegment,
        expiry: expiry,
      });

      if (response.success && response.data) {
        setOptionChain(response.data);
      } else {
        setError(response.error || "Failed to fetch option chain");
        setOptionChain(null);
      }
    } catch (err) {
      setError(err.message || "Failed to fetch option chain");
      setOptionChain(null);
    } finally {
      setLoading(false);
    }
  };

  const handleExpirySelect = (expiry) => {
    setSelectedExpiry(expiry);
    setShowExpiryDropdown(false);

    const underlyingIdValue = getOptionUnderlyingId();
    const exchangeSegment = getOptionExchangeSegment(selectedInstrument);

    if (underlyingIdValue && exchangeSegment) {
      fetchOptionChain(underlyingIdValue, exchangeSegment, expiry);
    }
  };

  // Don't render if not an index
  if (!selectedInstrument || !isIndex(selectedInstrument)) {
    return null;
  }

  return (
    <div className="glass rounded-xl p-8">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Option Chain</h3>
        {loadingExpiry && (
          <div className="flex items-center gap-2 text-sm text-zinc-400">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading expiries...
          </div>
        )}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Expiry Selection */}
      {loadingExpiry ? (
        <div className="mb-4 flex items-center gap-2 text-sm text-zinc-400">
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading expiry dates...
        </div>
      ) : expiryList.length > 0 ? (
        <div className="mb-4">
          <label className="text-sm font-medium text-zinc-400 mb-2 block">
            Select Expiry ({expiryList.length} available)
          </label>
          <div className="relative" ref={expiryDropdownRef}>
            <button
              onClick={() => setShowExpiryDropdown(!showExpiryDropdown)}
              className="w-full md:w-64 px-4 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-white text-left flex items-center justify-between hover:border-zinc-700 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-zinc-400" />
                <span>{selectedExpiry || expiryList[0] || "Select expiry"}</span>
              </div>
              <ChevronDown className={`w-4 h-4 text-zinc-400 transition-transform ${showExpiryDropdown ? "rotate-180" : ""}`} />
            </button>
            {showExpiryDropdown && (
              <div className="absolute z-50 w-full md:w-64 mt-1 bg-zinc-900 border border-zinc-800 rounded-lg shadow-2xl max-h-60 overflow-y-auto">
                {expiryList.map((expiry, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleExpirySelect(expiry)}
                    className={`w-full px-4 py-2 text-left hover:bg-zinc-800 transition-colors ${
                      selectedExpiry === expiry
                        ? "bg-green-500/20 text-green-400"
                        : "text-white"
                    }`}
                  >
                    {expiry}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : !error ? (
        <div className="mb-4 text-sm text-zinc-500">
          No expiry dates available
        </div>
      ) : null}

      {/* Option Chain Table */}
      {loading && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-green-500" />
          <span className="ml-2 text-zinc-400">Loading option chain...</span>
        </div>
      )}

      {optionChain && !loading && (
        <div className="overflow-x-auto">
          <div className="text-sm text-zinc-400 mb-2">
            Showing option chain for expiry: <span className="text-white font-medium">{selectedExpiry}</span>
          </div>
          <div className="bg-zinc-900 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800">
                  <th className="px-4 py-3 text-left text-zinc-400 font-medium">Strike</th>
                  <th className="px-4 py-3 text-right text-zinc-400 font-medium">Call OI</th>
                  <th className="px-4 py-3 text-right text-zinc-400 font-medium">Call LTP</th>
                  <th className="px-4 py-3 text-right text-zinc-400 font-medium">Put LTP</th>
                  <th className="px-4 py-3 text-right text-zinc-400 font-medium">Put OI</th>
                </tr>
              </thead>
              <tbody>
                {(() => {
                  // Handle different response formats
                  let chainData = [];

                  if (Array.isArray(optionChain)) {
                    chainData = optionChain;
                  } else if (optionChain.data && Array.isArray(optionChain.data)) {
                    chainData = optionChain.data;
                  } else if (optionChain.option_chain && Array.isArray(optionChain.option_chain)) {
                    chainData = optionChain.option_chain;
                  } else if (typeof optionChain === 'object') {
                    // Try to find any array in the response
                    const keys = Object.keys(optionChain);
                    for (const key of keys) {
                      if (Array.isArray(optionChain[key])) {
                        chainData = optionChain[key];
                        break;
                      }
                    }
                  }

                  if (chainData.length === 0) {
                    return (
                      <tr>
                        <td colSpan="5" className="px-4 py-8 text-center text-zinc-400">
                          No option chain data available
                        </td>
                      </tr>
                    );
                  }

                  // Group by strike price and separate calls/puts
                  const strikeMap = {};
                  chainData.forEach((option) => {
                    const strike = option.strike_price || option.STRIKE_PRICE || option.strike || 0;
                    const optionType = (option.option_type || option.OPTION_TYPE || "").toUpperCase();

                    if (!strikeMap[strike]) {
                      strikeMap[strike] = { strike, call: null, put: null };
                    }

                    if (optionType === "CE" || optionType === "CALL") {
                      strikeMap[strike].call = option;
                    } else if (optionType === "PE" || optionType === "PUT") {
                      strikeMap[strike].put = option;
                    }
                  });

                  const sortedStrikes = Object.keys(strikeMap)
                    .map(Number)
                    .sort((a, b) => a - b);

                  return sortedStrikes.map((strike) => {
                    const row = strikeMap[strike];
                    const call = row.call;
                    const put = row.put;

                    return (
                      <tr
                        key={strike}
                        className="border-b border-zinc-800/50 hover:bg-zinc-800/50 transition-colors"
                      >
                        <td className="px-4 py-3 text-white font-medium">
                          {strike}
                        </td>
                        <td className="px-4 py-3 text-right text-zinc-300">
                          {call?.open_interest || call?.OI || call?.OPEN_INTEREST || "—"}
                        </td>
                        <td className="px-4 py-3 text-right text-green-400 font-medium">
                          {call?.last_price || call?.LTP || call?.ltp ? `₹${parseFloat(call.last_price || call.LTP || call.ltp).toFixed(2)}` : "—"}
                        </td>
                        <td className="px-4 py-3 text-right text-red-400 font-medium">
                          {put?.last_price || put?.LTP || put?.ltp ? `₹${parseFloat(put.last_price || put.LTP || put.ltp).toFixed(2)}` : "—"}
                        </td>
                        <td className="px-4 py-3 text-right text-zinc-300">
                          {put?.open_interest || put?.OI || put?.OPEN_INTEREST || "—"}
                        </td>
                      </tr>
                    );
                  });
                })()}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!loading && !optionChain && selectedExpiry && (
        <div className="text-center py-8 text-zinc-400">
          Select an expiry to view option chain
        </div>
      )}
    </div>
  );
}

export default OptionChain;

