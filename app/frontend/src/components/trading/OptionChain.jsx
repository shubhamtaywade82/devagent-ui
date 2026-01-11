import { useState, useEffect, useRef } from "react";
import { Calendar, ChevronDown, Loader2, Target } from "lucide-react";
import api from "../../services/api";

function OptionChain({ accessToken, selectedInstrument }) {
  const [expiryList, setExpiryList] = useState([]);
  const [selectedExpiry, setSelectedExpiry] = useState("");
  const [optionChain, setOptionChain] = useState(null);
  const [underlyingLTP, setUnderlyingLTP] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingExpiry, setLoadingExpiry] = useState(false);
  const [error, setError] = useState("");
  const [showExpiryDropdown, setShowExpiryDropdown] = useState(false);
  const expiryDropdownRef = useRef(null);
  const tableBodyRef = useRef(null);
  const scrollableContainerRef = useRef(null);
  const [atmStrike, setAtmStrike] = useState(null);
  const fetchingRef = useRef(false); // Prevent duplicate fetches
  const autoLoadRef = useRef(false); // Track if auto-load has been triggered

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
      autoLoadRef.current = false; // Reset auto-load flag
      return;
    }

    // Reset auto-load flag when instrument changes
    autoLoadRef.current = false;

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
          // Only do this once per instrument change
          if (!autoLoadRef.current) {
            const firstExpiry = expiries[0];
            console.log("Auto-selecting first expiry:", firstExpiry);
            console.log("Underlying ID:", underlyingIdValue, "Exchange Segment:", exchangeSegment);
            setSelectedExpiry(firstExpiry);
            autoLoadRef.current = true;

            // Always fetch option chain for the first expiry with 1 second delay
            setTimeout(() => {
              if (!fetchingRef.current) {
                console.log("Auto-loading option chain for expiry:", firstExpiry);
                fetchOptionChain(underlyingIdValue, exchangeSegment, firstExpiry);
              } else {
                console.log("Skipping auto-load, fetch already in progress");
              }
            }, 1000); // 1 second delay
          }
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

  // Note: Removed the backup useEffect that watched selectedExpiry to prevent duplicate fetches
  // Option chain is now only fetched from:
  // 1. Auto-load when expiry list is fetched (in fetchExpiryList)
  // 2. Manual selection via handleExpirySelect

  // Fetch option chain
  const fetchOptionChain = async (underlyingId, exchangeSegment, expiry) => {
    if (!accessToken || !underlyingId || !exchangeSegment || !expiry) {
      return;
    }

    // Prevent duplicate fetches
    if (fetchingRef.current) {
      console.log("Option chain fetch already in progress, skipping duplicate call");
      return;
    }

    fetchingRef.current = true;
    setLoading(true);
    setError("");
    try {
      const response = await api.getOptionChain({
        access_token: accessToken,
        under_security_id: underlyingId,
        under_exchange_segment: exchangeSegment,
        expiry: expiry,
      });

      console.log("Option chain response:", response);
      console.log("Response keys:", Object.keys(response));
      if (response.data) {
        console.log("Response.data keys:", Object.keys(response.data));
        if (response.data.data) {
          console.log("Response.data.data keys:", Object.keys(response.data.data));
        }
      }

      // Handle response structure - DhanHQ can return various formats
      // Check for both response.success and response.status === "success"
      const isSuccess = response.success === true || response.status === "success";

      // Handle different response structures:
      // 1. { success: true, data: {...} }
      // 2. { status: "success", data: {...} }
      // 3. { status: "success", remarks: "...", data: {...} }
      // 4. { data: {...}, status: "..." } - This is the case we're seeing
      let workingData = response.data || response;

      if (isSuccess || response.status === "success" || workingData) {
        // Extract the option chain object (oc) from nested data structure
        let ocData = null;
        let ltp = null;
        let data = workingData;

        // Handle case where response.data has { data: {...}, status: "..." } structure
        // This happens when DhanHQ API returns { data: {...}, status: "..." } and backend wraps it
        // So we have: { success: true, data: { data: {...}, status: "..." } }
        // The actual option chain is in response.data.data
        if (response.data && typeof response.data === 'object' && response.data.data && (response.data.status !== undefined || response.data.remarks !== undefined)) {
          // Check if response.data.data itself has the option chain structure
          const unwrappedData = response.data.data;
          console.log("Unwrapped response.data.data (handling data/status structure)");
          console.log("Unwrapped data keys:", Object.keys(unwrappedData));

          // If unwrappedData has data/status again, unwrap one more level
          if (unwrappedData && typeof unwrappedData === 'object' && unwrappedData.data && (unwrappedData.status !== undefined || unwrappedData.remarks !== undefined)) {
            data = unwrappedData.data;
            console.log("Double unwrapped: response.data.data.data");
          } else {
            data = unwrappedData;
          }
        }
        // Handle structure: { data: {...}, status: "..." } or { data: {...}, remarks: "..." }
        // If data has status/remarks, the actual data is nested in data.data
        else if (data && typeof data === 'object' && (data.status !== undefined || data.remarks !== undefined) && data.data) {
          data = data.data;
          console.log("Unwrapped nested data structure (status/remarks/data)");
        }

        // Try multiple possible response structures
        // Structure 0: Check if data itself is the option chain (has numeric keys)
        if (data && typeof data === 'object' && !Array.isArray(data)) {
          const keys = Object.keys(data);
          const numericKeys = keys.filter(k => !isNaN(parseFloat(k)) && isFinite(parseFloat(k)));

          // If we have a single numeric key (like "805"), it might be an error code
          // Check if the value is a string (error message) or an object (might be data)
          if (numericKeys.length === 1 && keys.length === 1) {
            const singleKey = numericKeys[0];
            const value = data[singleKey];
            if (typeof value === 'string') {
              // This is likely an error message
              console.error("Error code in response:", singleKey, value);
              let errorMessage = value;

              // Handle rate limiting errors specifically
              if (value.toLowerCase().includes("too many requests") ||
                  value.toLowerCase().includes("rate limit") ||
                  singleKey === "805" ||
                  value.toLowerCase().includes("blocked")) {
                errorMessage = "⚠️ Rate limit exceeded. Too many requests to DhanHQ API. Please wait a few minutes before trying again.";
              }

              setError(errorMessage);
              setOptionChain(null);
              setUnderlyingLTP(null);
              return;
            } else if (typeof value === 'object' && value !== null) {
              // The value might be the actual data
              console.log("Single numeric key found, checking if value is option chain");
              const valueKeys = Object.keys(value);
              const valueNumericKeys = valueKeys.filter(k => !isNaN(parseFloat(k)) && isFinite(parseFloat(k)));
              if (valueNumericKeys.length > 5) {
                // This looks like an option chain
                ocData = value;
                ltp = data.last_price || data.lastPrice || data.LTP || data.ltp;
                console.log("Found option chain in single numeric key value");
              }
            }
          } else if (numericKeys.length > 5) {
            // This looks like an option chain object directly
            ocData = data;
            ltp = data.last_price || data.lastPrice || data.LTP || data.ltp;
            console.log("Found option chain as direct data object (numeric keys)");
          }
        }

        // Structure 1: { data: { oc: {...}, last_price: ... } }
        if (!ocData && data.oc) {
          ocData = data.oc;
          ltp = data.last_price || data.lastPrice || data.LTP || data.ltp;
          console.log("Found option chain in data.oc");
        }
        // Structure 2: { data: { data: { oc: {...}, last_price: ... } } }
        if (!ocData && data.data?.oc) {
          ocData = data.data.oc;
          ltp = data.data.last_price || data.data.lastPrice || data.data.LTP || data.data.ltp;
          console.log("Found option chain in data.data.oc");
        }
        // Structure 3: { data: { data: { data: { oc: {...}, last_price: ... } } } }
        if (!ocData && data.data?.data?.oc) {
          ocData = data.data.data.oc;
          ltp = data.data.data.last_price || data.data.data.lastPrice || data.data.data.LTP || data.data.data.ltp;
          console.log("Found option chain in data.data.data.oc");
        }
        // Structure 4: Check for nested option chain structures
        if (!ocData && data.option_chain) {
          ocData = data.option_chain;
          ltp = data.last_price || data.lastPrice || data.LTP || data.ltp;
          console.log("Found option chain in data.option_chain");
        }

        if (!ocData && data.optionChain) {
          ocData = data.optionChain;
          ltp = data.last_price || data.lastPrice || data.LTP || data.ltp;
          console.log("Found option chain in data.optionChain");
        }

        // Structure 5: Try to find any nested object that looks like option chain
        if (!ocData && typeof data === 'object' && !Array.isArray(data)) {
          for (const key in data) {
            const value = data[key];
            if (value && typeof value === 'object' && !Array.isArray(value)) {
              const valueKeys = Object.keys(value);
              const valueNumericKeys = valueKeys.filter(k => !isNaN(parseFloat(k)) && isFinite(parseFloat(k)));
              if (valueNumericKeys.length > 5) { // Likely an option chain if has many numeric keys
                ocData = value;
                ltp = data.last_price || data.lastPrice || data.LTP || data.ltp;
                console.log(`Found option chain in data.${key}`);
                break;
              }
            }
          }
        }

        if (ocData && typeof ocData === 'object') {
          console.log("Option chain data found, setting state");
          console.log("Option chain keys (first 10):", Object.keys(ocData).slice(0, 10));
          setOptionChain(ocData);
          setUnderlyingLTP(ltp);
          setError(""); // Clear any previous errors
        } else {
          console.error("Could not find option chain data in response. Full response:", response);
          console.error("Working data keys:", data ? Object.keys(data) : "no data");
          console.error("Working data type:", typeof data);
          if (data && typeof data === 'object') {
            console.error("Data structure:", Object.keys(data));
            // Log all keys and their types to help debug
            for (const key in data) {
              const value = data[key];
              const valueType = typeof value;
              const valueInfo = Array.isArray(value)
                ? `(array[${value.length}])`
                : (valueType === 'object' && value !== null ? `(object with keys: ${Object.keys(value).slice(0, 5).join(', ')})` : '');
              console.error(`  ${key}:`, valueType, valueInfo);
            }
            if (data.data) {
              console.error("Data.data structure:", Object.keys(data.data));
              // Check if data.data itself might be the option chain
              if (typeof data.data === 'object' && !Array.isArray(data.data)) {
                const dataDataKeys = Object.keys(data.data);
                const numericKeys = dataDataKeys.filter(k => !isNaN(parseFloat(k)) && isFinite(parseFloat(k)));
                console.error("Data.data numeric keys count:", numericKeys.length);
                if (numericKeys.length > 5) {
                  console.log("Data.data looks like option chain! Using it directly.");
                  ocData = data.data;
                  ltp = data.last_price || data.lastPrice || data.LTP || data.ltp;
                  setOptionChain(ocData);
                  setUnderlyingLTP(ltp);
                  setError("");
                  return; // Exit early since we found it
                }
              }
            }
          }
          // Only set error if we don't already have option chain data (don't overwrite successful load)
          if (!optionChain) {
            const errorKeys = data ? Object.keys(data) : (response.data ? Object.keys(response.data) : []);
            setError(`Option chain data format not recognized. Response structure: ${JSON.stringify(errorKeys)}`);
            setOptionChain(null);
            setUnderlyingLTP(null);
          } else {
            console.warn("Failed to parse new option chain data, but keeping existing data");
          }
        }
      } else {
        let errorMsg = response.error || response.message || response.remarks || "Failed to fetch option chain";

        // Check for rate limiting in error message
        if (typeof errorMsg === 'string' && (
          errorMsg.toLowerCase().includes("too many requests") ||
          errorMsg.toLowerCase().includes("rate limit") ||
          errorMsg.toLowerCase().includes("429") ||
          errorMsg.toLowerCase().includes("blocked")
        )) {
          errorMsg = "⚠️ Rate limit exceeded. Too many requests to DhanHQ API. Please wait a few minutes before trying again.";
        }

        console.error("Option chain fetch failed:", errorMsg);
        setError(errorMsg);
        setOptionChain(null);
        setUnderlyingLTP(null);
      }
    } catch (err) {
      console.error("Error fetching option chain:", err);
      setError(err.message || "Failed to fetch option chain");
      setOptionChain(null);
    } finally {
      setLoading(false);
      fetchingRef.current = false;
    }
  };

  const handleExpirySelect = (expiry) => {
    // Don't fetch if we're already fetching or if there's a rate limit error
    if (fetchingRef.current || (error && error.includes("Rate limit"))) {
      console.log("Skipping expiry select - fetch in progress or rate limited");
      setSelectedExpiry(expiry);
      setShowExpiryDropdown(false);
      return;
    }

    setSelectedExpiry(expiry);
    setShowExpiryDropdown(false);

    const underlyingIdValue = getOptionUnderlyingId();
    const exchangeSegment = getOptionExchangeSegment(selectedInstrument);

    if (underlyingIdValue && exchangeSegment) {
      // Add 1 second delay before fetching option chain
      setTimeout(() => {
        if (!fetchingRef.current) {
          fetchOptionChain(underlyingIdValue, exchangeSegment, expiry);
        }
      }, 1000);
    }
  };

  // Scroll to strike closest to LTP (ATM) when option chain loads
  useEffect(() => {
    if (!optionChain || !underlyingLTP || !scrollableContainerRef.current) {
      return;
    }

    // Calculate closest strike to LTP (ATM strike)
    const strikes = Object.keys(optionChain)
      .map(Number)
      .filter(strike => !isNaN(strike))
      .filter((strike) => {
        // Filter out strikes where both call and put have LTP of 0 or no LTP
        const strikeKey = strike.toFixed(6);
        const strikeData = optionChain[strikeKey] || optionChain[strike.toString()] || optionChain[strike];
        const call = strikeData?.ce || strikeData?.CE || strikeData?.call || null;
        const put = strikeData?.pe || strikeData?.PE || strikeData?.put || null;
        const callLTP = call?.last_price || call?.LTP || call?.ltp || 0;
        const putLTP = put?.last_price || put?.LTP || put?.ltp || 0;
        return callLTP > 0 || putLTP > 0;
      })
      .sort((a, b) => a - b);

    if (strikes.length === 0) return;

    // Find the closest strike to LTP (ATM)
    const closestStrike = strikes.reduce((prev, curr) => {
      return Math.abs(curr - underlyingLTP) < Math.abs(prev - underlyingLTP) ? curr : prev;
    });

    setAtmStrike(closestStrike);

    // Wait for DOM to render, then scroll to the ATM strike
    const scrollToATM = () => {
      const container = scrollableContainerRef.current;
      if (!container) return;

      // Find the row with the ATM strike
      const rows = container.querySelectorAll('tbody tr');
      let targetRow = null;

      rows.forEach((row) => {
        const strikeCell = row.querySelector('td:first-child');
        if (strikeCell) {
          const strikeValue = parseFloat(strikeCell.textContent.trim());
          if (Math.abs(strikeValue - closestStrike) < 0.01) { // Use small tolerance for float comparison
            targetRow = row;
          }
        }
      });

      if (targetRow) {
        // Use scrollIntoView for smooth scrolling to center
        targetRow.scrollIntoView({
          behavior: 'smooth',
          block: 'center',
          inline: 'nearest'
        });
      }
    };

    // Try multiple times with increasing delays to ensure DOM is ready
    setTimeout(scrollToATM, 150);
    setTimeout(scrollToATM, 300);
    setTimeout(scrollToATM, 500);
  }, [optionChain, underlyingLTP]);

  // Don't render if not an index
  if (!selectedInstrument || !isIndex(selectedInstrument)) {
    return null;
  }

  return (
    <div className="glass rounded-xl p-8">
      {/* Header and Expiry Selection on Single Line */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <h3 className="text-lg font-semibold">Option Chain</h3>

        {loadingExpiry ? (
          <div className="flex items-center gap-2 text-sm text-zinc-400">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading expiries...
          </div>
        ) : expiryList.length > 0 ? (
          <div className="flex items-center gap-3">
            <span className="text-sm text-zinc-400 whitespace-nowrap">
              Select Expiry ({expiryList.length} available)
            </span>
            <div className="relative" ref={expiryDropdownRef}>
              <button
                onClick={() => setShowExpiryDropdown(!showExpiryDropdown)}
                className="px-4 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-white text-left flex items-center justify-between hover:border-zinc-700 transition-colors min-w-[200px]"
              >
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-zinc-400" />
                  <span>{selectedExpiry || expiryList[0] || "Select expiry"}</span>
                </div>
                <ChevronDown className={`w-4 h-4 text-zinc-400 transition-transform ${showExpiryDropdown ? "rotate-180" : ""}`} />
              </button>
              {showExpiryDropdown && (
                <div className="absolute z-50 right-0 mt-1 w-full min-w-[200px] bg-zinc-900 border border-zinc-800 rounded-lg shadow-2xl max-h-60 overflow-y-auto">
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
          <div className="text-sm text-zinc-500">
            No expiry dates available
          </div>
        ) : null}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Option Chain Table */}
      {loading && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-green-500" />
          <span className="ml-2 text-zinc-400">Loading option chain...</span>
        </div>
      )}

      {optionChain && !loading && (
        <div className="overflow-x-auto">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm text-zinc-400">
              Showing option chain for expiry: <span className="text-white font-medium">{selectedExpiry}</span>
            </div>
            {atmStrike !== null && underlyingLTP && (
              <button
                onClick={() => {
                  const container = scrollableContainerRef.current;
                  if (!container) return;
                  const rows = container.querySelectorAll('tbody tr');
                  rows.forEach((row) => {
                    const strikeCell = row.querySelector('td:first-child');
                    if (strikeCell) {
                      const strikeValue = parseFloat(strikeCell.textContent.trim());
                      if (Math.abs(strikeValue - atmStrike) < 0.01) {
                        row.scrollIntoView({
                          behavior: 'smooth',
                          block: 'center',
                          inline: 'nearest'
                        });
                      }
                    }
                  });
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-green-500/20 hover:bg-green-500/30 border border-green-500/30 rounded-lg text-green-400 transition-colors"
                title="Scroll to ATM (At The Money) strike"
              >
                <Target className="w-3.5 h-3.5" />
                Scroll to ATM
              </button>
            )}
          </div>
          <div className="bg-zinc-900 rounded-lg overflow-hidden">
            <div ref={scrollableContainerRef} className="max-h-[600px] overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-zinc-900 z-10">
                  <tr className="border-b border-zinc-800">
                    <th className="px-4 py-3 text-left text-zinc-400 font-medium">Strike</th>
                    <th className="px-4 py-3 text-right text-zinc-400 font-medium">Call OI</th>
                    <th className="px-4 py-3 text-right text-zinc-400 font-medium">Call LTP</th>
                    <th className="px-4 py-3 text-right text-zinc-400 font-medium">Put LTP</th>
                    <th className="px-4 py-3 text-right text-zinc-400 font-medium">Put OI</th>
                  </tr>
                </thead>
                <tbody ref={tableBodyRef}>
                  {(() => {
                    // Handle object-based option chain structure: { "20450.000000": { ce: {...}, pe: {...} }, ... }
                    if (!optionChain || typeof optionChain !== 'object') {
                      return (
                        <tr>
                          <td colSpan="5" className="px-4 py-8 text-center text-zinc-400">
                            No option chain data available
                          </td>
                        </tr>
                      );
                    }

                    // Convert object structure to array of strikes and filter out strikes with no LTP data
                    const strikes = Object.keys(optionChain)
                      .map(Number)
                      .filter(strike => !isNaN(strike))
                      .filter((strike) => {
                        // Filter out strikes where both call and put have LTP of 0 or no LTP
                        const strikeKey = strike.toFixed(6); // Match the format "20450.000000"
                        const strikeData = optionChain[strikeKey] || optionChain[strike.toString()] || optionChain[strike];
                        const call = strikeData?.ce || strikeData?.CE || strikeData?.call || null;
                        const put = strikeData?.pe || strikeData?.PE || strikeData?.put || null;

                        const callLTP = call?.last_price || call?.LTP || call?.ltp || 0;
                        const putLTP = put?.last_price || put?.LTP || put?.ltp || 0;

                        // Keep strike if at least one option (call or put) has a non-zero LTP
                        return callLTP > 0 || putLTP > 0;
                      })
                      .sort((a, b) => a - b);

                    if (strikes.length === 0) {
                      return (
                        <tr>
                          <td colSpan="5" className="px-4 py-8 text-center text-zinc-400">
                            No option chain data available (all strikes filtered out)
                          </td>
                        </tr>
                      );
                    }

                    return strikes.map((strike) => {
                      const strikeKey = strike.toFixed(6); // Match the format "20450.000000"
                      const strikeData = optionChain[strikeKey] || optionChain[strike.toString()] || optionChain[strike];
                      const call = strikeData?.ce || strikeData?.CE || strikeData?.call || null;
                      const put = strikeData?.pe || strikeData?.PE || strikeData?.put || null;

                      const isATM = atmStrike !== null && Math.abs(strike - atmStrike) < 0.01;
                      return (
                        <tr
                          key={strike}
                          className={`border-b border-zinc-800/50 hover:bg-zinc-800/50 transition-colors ${
                            isATM ? "bg-green-500/10 border-green-500/30" : ""
                          }`}
                        >
                          <td className={`px-4 py-3 font-medium ${
                            isATM ? "text-green-400 font-bold" : "text-white"
                          }`}>
                            {strike}
                            {isATM && <span className="ml-2 text-xs text-green-500">ATM</span>}
                          </td>
                          <td className="px-4 py-3 text-right text-zinc-300">
                            {call?.oi || call?.OI || call?.open_interest || call?.OPEN_INTEREST || "—"}
                          </td>
                          <td className="px-4 py-3 text-right text-green-400 font-medium">
                            {call?.last_price || call?.LTP || call?.ltp ? `₹${parseFloat(call.last_price || call.LTP || call.ltp).toFixed(2)}` : "—"}
                          </td>
                          <td className="px-4 py-3 text-right text-red-400 font-medium">
                            {put?.last_price || put?.LTP || put?.ltp ? `₹${parseFloat(put.last_price || put.LTP || put.ltp).toFixed(2)}` : "—"}
                          </td>
                          <td className="px-4 py-3 text-right text-zinc-300">
                            {put?.oi || put?.OI || put?.open_interest || put?.OPEN_INTEREST || "—"}
                          </td>
                        </tr>
                      );
                    });
                  })()}
                </tbody>
            </table>
            </div>
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

