import { useState, useEffect, useRef } from "react";
import { Search, X } from "lucide-react";
import api from "../../services/api";

function InstrumentSearch({
  onSelect,
  placeholder = "Search by symbol name or Security ID...",
  accessToken = null,
  exchangeSegment = null,
}) {
  const [instruments, setInstruments] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [filteredInstruments, setFilteredInstruments] = useState({
    indices: [],
    equity: [],
    options: [],
    other: [],
  });
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showPreSuggestions, setShowPreSuggestions] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  const searchRef = useRef(null);
  const suggestionsRef = useRef(null);
  const instrumentsCacheRef = useRef(null); // Cache instruments to avoid reloading
  const justSelectedRef = useRef(false); // Track if we just selected an instrument

  // Popular pre-suggestions with expected exchange segments
  const popularSuggestions = {
    indices: [
      {
        name: "NIFTY 50",
        searchTerms: ["NIFTY", "NIFTY 50", "NIFTY50"],
        exchangeSegment: "IDX_I",
        expectedSymbol: "NIFTY",
      },
      {
        name: "SENSEX",
        searchTerms: ["SENSEX", "BSE SENSEX"],
        exchangeSegment: "IDX_I",
        expectedSymbol: "SENSEX",
      },
      {
        name: "NIFTY BANK",
        searchTerms: ["NIFTY BANK", "BANKNIFTY", "NIFTYBANK"],
        exchangeSegment: "IDX_I",
        expectedSymbol: "NIFTY BANK",
      },
      {
        name: "NIFTY IT",
        searchTerms: ["NIFTY IT", "NIFTYIT"],
        exchangeSegment: "IDX_I",
        expectedSymbol: "NIFTY IT",
      },
      {
        name: "NIFTY NEXT 50",
        searchTerms: ["NIFTY NEXT 50", "NIFTYNEXT50"],
        exchangeSegment: "IDX_I",
        expectedSymbol: "NIFTY NEXT 50",
      },
    ],
    equity: [
      {
        name: "HDFC BANK",
        searchTerms: ["HDFC BANK", "HDFCBANK"],
        exchangeSegment: "NSE_EQ",
        expectedSymbol: "HDFCBANK",
      },
      {
        name: "RELIANCE",
        searchTerms: ["RELIANCE", "RELIANCE IND"],
        exchangeSegment: "NSE_EQ",
        expectedSymbol: "RELIANCE",
      },
      {
        name: "TCS",
        searchTerms: ["TCS", "TATA CONSULTANCY"],
        exchangeSegment: "NSE_EQ",
        expectedSymbol: "TCS",
      },
      {
        name: "INFY",
        searchTerms: ["INFY", "INFOSYS"],
        exchangeSegment: "NSE_EQ",
        expectedSymbol: "INFY",
      },
      {
        name: "ICICI BANK",
        searchTerms: ["ICICI BANK", "ICICIBANK"],
        exchangeSegment: "NSE_EQ",
        expectedSymbol: "ICICIBANK",
      },
      {
        name: "SBIN",
        searchTerms: ["SBIN", "STATE BANK"],
        exchangeSegment: "NSE_EQ",
        expectedSymbol: "SBIN",
      },
      {
        name: "BHARTI AIRTEL",
        searchTerms: ["BHARTI AIRTEL", "BHARTIARTL"],
        exchangeSegment: "NSE_EQ",
        expectedSymbol: "BHARTIARTL",
      },
      {
        name: "HINDUNILVR",
        searchTerms: ["HINDUNILVR", "HINDUSTAN UNILEVER"],
        exchangeSegment: "NSE_EQ",
        expectedSymbol: "HINDUNILVR",
      },
    ],
  };

  // Load instruments on mount - with caching
  useEffect(() => {
    // Use cached instruments if available and no exchangeSegment change
    if (instrumentsCacheRef.current && !exchangeSegment) {
      setInstruments(instrumentsCacheRef.current);
      setLoading(false);
      return;
    }
    // Always load instruments (segmentwise API doesn't require auth)
    loadInstruments();
  }, [accessToken, exchangeSegment]);

  // Categorize instrument by type
  const categorizeInstrument = (instrument) => {
    const segment = instrument.SEM_SEGMENT || instrument.SEGMENT || "";
    const instrumentType = (
      instrument.INSTRUMENT ||
      instrument.INSTRUMENT_TYPE ||
      ""
    ).toUpperCase();
    const exchangeSegment =
      instrument.SEM_EXM_EXCH_ID || instrument.EXCH_ID || "";

    // Check for indices
    if (
      segment === "I" ||
      instrumentType === "INDEX" ||
      exchangeSegment === "IDX_I"
    ) {
      return "indices";
    }

    // Check for options (F&O segment with OPT in instrument type or name)
    if (segment === "D") {
      const symbolName = (
        instrument.SYMBOL_NAME ||
        instrument.SEM_SYMBOL_NAME ||
        ""
      ).toUpperCase();
      if (instrumentType.includes("OPT") || symbolName.includes("OPT")) {
        return "options";
      }
    }

    // Check for equity/stocks (segment E)
    if (segment === "E") {
      return "equity";
    }

    // Default to equity if segment is E, otherwise unknown
    return segment === "E" ? "equity" : "other";
  };

  // Filter instruments based on search query - optimized with debouncing
  useEffect(() => {
    // Don't show suggestions if we just selected an instrument
    if (justSelectedRef.current) {
      justSelectedRef.current = false;
      return;
    }

    if (searchQuery.trim().length < 2) {
      setFilteredInstruments({
        indices: [],
        equity: [],
        options: [],
        other: [],
      });
      setShowSuggestions(false);
      // Show pre-suggestions only when input is focused AND query is empty
      setShowPreSuggestions(isFocused && searchQuery.trim().length === 0);
      return;
    }

    // Hide pre-suggestions when user starts typing
    setShowPreSuggestions(false);

    // Debounce search to avoid excessive filtering
    const timeoutId = setTimeout(() => {
      const query = searchQuery.toLowerCase().trim();

      if (query.length < 2) {
        setFilteredInstruments({
          indices: [],
          equity: [],
          options: [],
          other: [],
        });
        setShowSuggestions(false);
        return;
      }

      // Optimized filtering - limit search to first 10000 instruments for performance
      // Most common instruments are usually at the top
      const searchLimit = Math.min(instruments.length, 10000);
      const filtered = instruments.slice(0, searchLimit).filter((inst) => {
        const symbolName = (
          inst.SYMBOL_NAME ||
          inst.SEM_SYMBOL_NAME ||
          inst.SM_SYMBOL_NAME ||
          ""
        ).toLowerCase();
        const tradingSymbol = (
          inst.SEM_TRADING_SYMBOL ||
          inst.TRADING_SYMBOL ||
          ""
        ).toLowerCase();
        const displayName = (
          inst.DISPLAY_NAME ||
          inst.SEM_CUSTOM_SYMBOL ||
          ""
        ).toLowerCase();
        const underlyingSymbol = (
          inst.UNDERLYING_SYMBOL ||
          inst.underlying_symbol ||
          ""
        ).toLowerCase();
        const securityId = (
          inst.SEM_SECURITY_ID ||
          inst.SECURITY_ID ||
          inst.SM_SECURITY_ID ||
          ""
        ).toString();
        const isin = (inst.ISIN || "").toLowerCase();

        return (
          symbolName.includes(query) ||
          tradingSymbol.includes(query) ||
          displayName.includes(query) ||
          underlyingSymbol.includes(query) ||
          securityId.includes(query) ||
          isin.includes(query)
        );
      });

      // Group by category
      const grouped = {
        indices: [],
        equity: [],
        options: [],
        other: [],
      };

      filtered.forEach((inst) => {
        const category = categorizeInstrument(inst);
        grouped[category].push(inst);
      });

      // Limit each category to prevent too many results
      const maxPerCategory = 10;
      grouped.indices = grouped.indices.slice(0, maxPerCategory);
      grouped.equity = grouped.equity.slice(0, maxPerCategory);
      grouped.options = grouped.options.slice(0, maxPerCategory);
      grouped.other = grouped.other.slice(0, maxPerCategory);

      // Store grouped results
      setFilteredInstruments(grouped);
      setShowSuggestions(
        grouped.indices.length > 0 ||
          grouped.equity.length > 0 ||
          grouped.options.length > 0 ||
          grouped.other.length > 0
      );
    }, 200); // 200ms debounce

    return () => clearTimeout(timeoutId);
  }, [searchQuery, instruments, isFocused]);

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(event.target) &&
        searchRef.current &&
        !searchRef.current.contains(event.target)
      ) {
        setShowSuggestions(false);
        setShowPreSuggestions(false);
        setIsFocused(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const loadInstruments = async () => {
    setLoading(true);
    setError("");
    try {
      // Strategy: Use segmentwise API by default (no auth needed, better data quality, faster)
      // Load NSE_EQ by default, can add BSE_EQ if needed
      let response;

      if (exchangeSegment) {
        // Use specified segment
        try {
          console.log(`Loading instruments for segment: ${exchangeSegment}`);
          response = await api.getInstrumentListSegmentwise(exchangeSegment);
          if (!response || !response.success) {
            console.log("Segmentwise API failed, trying CSV fallback");
            response = await api.getInstrumentListCSV("detailed");
          }
        } catch (err) {
          console.warn("Segmentwise API error, using CSV:", err);
          try {
            response = await api.getInstrumentListCSV("detailed");
          } catch (csvErr) {
            console.error("CSV API also failed:", csvErr);
            throw csvErr;
          }
        }
      } else {
        // Default: Load NSE_EQ (most common, fastest)
        // Optionally load BSE_EQ in parallel for better coverage
        try {
          console.log("Loading instruments from NSE_EQ and BSE_EQ");
          const [nseResponse, bseResponse] = await Promise.allSettled([
            api.getInstrumentListSegmentwise("NSE_EQ"),
            api.getInstrumentListSegmentwise("BSE_EQ"),
          ]);

          let loadedInstruments = [];

          if (
            nseResponse.status === "fulfilled" &&
            nseResponse.value &&
            nseResponse.value.success
          ) {
            const nseList =
              nseResponse.value.data?.instruments ||
              nseResponse.value.data?.data ||
              [];
            if (Array.isArray(nseList)) {
              loadedInstruments = [...loadedInstruments, ...nseList];
              console.log(`Loaded ${nseList.length} instruments from NSE_EQ`);
            }
          } else {
            console.warn(
              "NSE_EQ API failed:",
              nseResponse.reason || nseResponse.value
            );
          }

          if (
            bseResponse.status === "fulfilled" &&
            bseResponse.value &&
            bseResponse.value.success
          ) {
            const bseList =
              bseResponse.value.data?.instruments ||
              bseResponse.value.data?.data ||
              [];
            if (Array.isArray(bseList)) {
              loadedInstruments = [...loadedInstruments, ...bseList];
              console.log(`Loaded ${bseList.length} instruments from BSE_EQ`);
            }
          } else {
            console.warn(
              "BSE_EQ API failed:",
              bseResponse.reason || bseResponse.value
            );
          }

          if (loadedInstruments.length > 0) {
            response = {
              success: true,
              data: {
                instruments: loadedInstruments,
                count: loadedInstruments.length,
              },
            };
            console.log(
              `Successfully loaded ${loadedInstruments.length} instruments from segmentwise API (NSE_EQ + BSE_EQ)`
            );
          } else {
            // Fallback to CSV if both fail
            console.log(
              "No instruments from segmentwise API, trying CSV fallback"
            );
            response = await api.getInstrumentListCSV("detailed");
          }
        } catch (err) {
          console.warn("Segmentwise API error, using CSV:", err);
          try {
            response = await api.getInstrumentListCSV("detailed");
          } catch (csvErr) {
            console.error("CSV API also failed:", csvErr);
            throw csvErr;
          }
        }
      }

      if (response && response.success) {
        // Handle both CSV format (array of objects) and segmentwise format
        const instList =
          response.data?.instruments || response.data?.data || [];
        let finalList = [];

        if (Array.isArray(instList)) {
          finalList = instList;
        } else if (typeof instList === "object") {
          // If it's an object, convert to array
          finalList = Object.values(instList);
        }

        if (finalList.length === 0) {
          console.warn("No instruments found in response:", response);
          setError(
            "No instruments found. Please try syncing instruments first."
          );
        } else {
          setInstruments(finalList);
          // Cache instruments if no specific exchangeSegment (for reuse)
          if (!exchangeSegment) {
            instrumentsCacheRef.current = finalList;
          }
          console.log(`Successfully loaded ${finalList.length} instruments`);
        }
      } else {
        const errorMsg = response?.error || "Failed to load instruments";
        console.error("API returned error:", errorMsg);
        setError(errorMsg);
      }
    } catch (err) {
      const errorMsg =
        err.message || err.toString() || "Failed to load instruments";
      setError(errorMsg);
      console.error("Error loading instruments:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (instrument) => {
    // Extract relevant data from instrument - try multiple field names
    const securityId =
      instrument.SEM_SECURITY_ID ||
      instrument.SECURITY_ID ||
      instrument.SM_SECURITY_ID ||
      instrument.SEC_ID ||
      instrument.securityId ||
      instrument.security_id ||
      instrument.id;

    const exchangeSegment =
      instrument.SEM_EXM_EXCH_ID ||
      instrument.EXCH_ID ||
      instrument.EXCHANGE_ID ||
      instrument.exchange;

    const segment =
      instrument.SEM_SEGMENT || instrument.SEGMENT || instrument.segment;

    // Map exchange and segment to DhanHQ format
    let exchangeSegmentFormatted = "NSE_EQ";
    const exchange = (exchangeSegment || "").toString().toUpperCase();
    const seg = (segment || "").toString().toUpperCase();

    // Check instrument type for indices
    const instrumentType = (
      instrument.INSTRUMENT ||
      instrument.INSTRUMENT_TYPE ||
      ""
    ).toUpperCase();

    // Handle indices first - segment "I" or "INDEX", or instrument type "INDEX" should use IDX_I
    if (seg === "I" || seg === "INDEX" || instrumentType === "INDEX") {
      exchangeSegmentFormatted = "IDX_I";
    } else if (exchange === "NSE" && seg === "E") {
      exchangeSegmentFormatted = "NSE_EQ";
    } else if (exchange === "BSE" && seg === "E") {
      exchangeSegmentFormatted = "BSE_EQ";
    } else if (exchange === "NSE" && seg === "D") {
      exchangeSegmentFormatted = "NSE_FNO";
    } else if (exchange === "BSE" && seg === "D") {
      exchangeSegmentFormatted = "BSE_FNO";
    } else if (exchange === "MCX") {
      exchangeSegmentFormatted = "MCX_COM";
    } else if (exchange === "BSE") {
      // Default BSE to equity if segment not specified
      exchangeSegmentFormatted = "BSE_EQ";
    } else {
      // Default to NSE_EQ if unknown
      exchangeSegmentFormatted = "NSE_EQ";
    }

    // Validate security ID
    if (
      !securityId ||
      securityId === "" ||
      securityId === "undefined" ||
      securityId === "null"
    ) {
      console.error("Invalid security ID for instrument:", instrument);
      setError(
        `Invalid Security ID for ${
          instrument.DISPLAY_NAME ||
          instrument.SYMBOL_NAME ||
          "selected instrument"
        }. Please try another instrument.`
      );
      return;
    }

    const instrumentData = {
      securityId: securityId.toString().trim(),
      exchangeSegment: exchangeSegmentFormatted,
      exchange: exchange, // Store the original exchange (NSE, BSE, etc.)
      symbolName:
        instrument.SYMBOL_NAME ||
        instrument.SEM_SYMBOL_NAME ||
        instrument.SM_SYMBOL_NAME ||
        "",
      tradingSymbol:
        instrument.SEM_TRADING_SYMBOL || instrument.TRADING_SYMBOL || "",
      displayName:
        instrument.DISPLAY_NAME || instrument.SEM_CUSTOM_SYMBOL || "",
      underlyingSymbol:
        instrument.UNDERLYING_SYMBOL || instrument.underlying_symbol || "",
      lotSize: instrument.LOT_SIZE || instrument.SEM_LOT_UNITS || 1,
      tickSize: instrument.TICK_SIZE || instrument.SEM_TICK_SIZE || 0.01,
      instrument: instrument,
    };

    // Mark that we just selected an instrument to prevent suggestions from showing
    justSelectedRef.current = true;

    setSearchQuery(
      instrumentData.displayName ||
        instrumentData.symbolName ||
        instrumentData.tradingSymbol
    );
    setShowSuggestions(false);
    setError(""); // Clear any previous errors

    if (onSelect) {
      onSelect(instrumentData);
    }
  };

  const handleClear = () => {
    setSearchQuery("");
    setShowSuggestions(false);
    setShowPreSuggestions(false);
    if (onSelect) {
      onSelect(null);
    }
  };

  const handlePreSuggestionClick = async (suggestion) => {
    setSearchQuery(suggestion.name);
    setShowPreSuggestions(false);
    setLoading(true);
    setError("");

    try {
      const exchangeSegment = suggestion.exchangeSegment || "NSE_EQ";
      const expectedSymbol = suggestion.expectedSymbol || suggestion.name;

      // Load instruments from the correct segment
      const response = await api.getInstrumentListSegmentwise(exchangeSegment);

      if (!response || !response.success) {
        // Fallback: try searching in loaded instruments
        const found = searchInLoadedInstruments(suggestion, expectedSymbol);
        if (found) {
          handleSelect(found);
          setLoading(false);
          return;
        }
        throw new Error(`Failed to load instruments for ${exchangeSegment}`);
      }

      const segmentInstruments =
        response.data?.instruments || response.data?.data || [];

      // Search for the exact instrument
      const found = findExactInstrument(
        segmentInstruments,
        suggestion,
        expectedSymbol,
        exchangeSegment
      );

      if (found) {
        handleSelect(found);
      } else {
        // If exact match not found, try searching in loaded instruments as fallback
        const fallbackFound = searchInLoadedInstruments(
          suggestion,
          expectedSymbol
        );
        if (fallbackFound) {
          handleSelect(fallbackFound);
        } else {
          setError(
            `Could not find ${suggestion.name}. Please try searching manually.`
          );
          // Set query so user can see search results
          setShowSuggestions(true);
        }
      }
    } catch (err) {
      console.error("Error finding pre-suggestion instrument:", err);
      // Fallback: try searching in loaded instruments
      const found = searchInLoadedInstruments(
        suggestion,
        suggestion.expectedSymbol || suggestion.name
      );
      if (found) {
        handleSelect(found);
      } else {
        setError(
          `Could not find ${suggestion.name}. Please try searching manually.`
        );
        setShowSuggestions(true);
      }
    } finally {
      setLoading(false);
    }
  };

  // Helper function to search in loaded instruments
  const searchInLoadedInstruments = (suggestion, expectedSymbol) => {
    const searchTerms = suggestion.searchTerms.map((term) =>
      term.toLowerCase()
    );
    const expectedSymbolLower = expectedSymbol.toLowerCase();

    return instruments.find((inst) => {
      const symbolName = (
        inst.SYMBOL_NAME ||
        inst.SEM_SYMBOL_NAME ||
        inst.SM_SYMBOL_NAME ||
        ""
      ).toUpperCase();
      const tradingSymbol = (
        inst.SEM_TRADING_SYMBOL ||
        inst.TRADING_SYMBOL ||
        ""
      ).toUpperCase();
      const displayName = (
        inst.DISPLAY_NAME ||
        inst.SEM_CUSTOM_SYMBOL ||
        ""
      ).toUpperCase();

      // For indices, check segment and instrument type
      if (suggestion.exchangeSegment === "IDX_I") {
        const segment = (inst.SEM_SEGMENT || inst.SEGMENT || "").toUpperCase();
        const instrumentType = (
          inst.INSTRUMENT ||
          inst.INSTRUMENT_TYPE ||
          ""
        ).toUpperCase();
        if (segment !== "I" && instrumentType !== "INDEX") {
          return false;
        }
      } else {
        // For equity, check segment is E
        const segment = (inst.SEM_SEGMENT || inst.SEGMENT || "").toUpperCase();
        if (segment !== "E") {
          return false;
        }
      }

      // Exact match on symbol name (preferred)
      if (symbolName === expectedSymbol.toUpperCase()) {
        return true;
      }

      // Exact match on trading symbol
      if (tradingSymbol === expectedSymbol.toUpperCase()) {
        return true;
      }

      // Check if any search term matches exactly
      return searchTerms.some(
        (term) =>
          symbolName === term.toUpperCase() ||
          tradingSymbol === term.toUpperCase()
      );
    });
  };

  // Helper function to find exact instrument in segment instruments
  const findExactInstrument = (
    segmentInstruments,
    suggestion,
    expectedSymbol,
    exchangeSegment
  ) => {
    const expectedSymbolUpper = expectedSymbol.toUpperCase();
    const searchTerms = suggestion.searchTerms.map((term) =>
      term.toUpperCase()
    );

    // First pass: exact matches
    for (const inst of segmentInstruments) {
      const symbolName = (inst.SYMBOL_NAME || "").toUpperCase();
      const tradingSymbol = (
        inst.TRADING_SYMBOL ||
        inst.SEM_TRADING_SYMBOL ||
        ""
      ).toUpperCase();
      const displayName = (inst.DISPLAY_NAME || "").toUpperCase();

      // Check segment and instrument type
      const segment = (inst.SEM_SEGMENT || inst.SEGMENT || "").toUpperCase();
      const instrumentType = (
        inst.INSTRUMENT ||
        inst.INSTRUMENT_TYPE ||
        ""
      ).toUpperCase();

      if (exchangeSegment === "IDX_I") {
        if (segment !== "I" && instrumentType !== "INDEX") {
          continue;
        }
      } else {
        if (segment !== "E") {
          continue;
        }
      }

      // Exact match on symbol name (highest priority)
      if (symbolName === expectedSymbolUpper) {
        return inst;
      }

      // Exact match on trading symbol
      if (tradingSymbol === expectedSymbolUpper) {
        return inst;
      }

      // Exact match on any search term
      if (
        searchTerms.some(
          (term) =>
            symbolName === term ||
            tradingSymbol === term ||
            displayName === term
        )
      ) {
        return inst;
      }
    }

    return null;
  };

  const getExchangeSegmentDisplay = (instrument) => {
    const exchange = instrument.SEM_EXM_EXCH_ID || instrument.EXCH_ID || "NSE";
    const segment = instrument.SEM_SEGMENT || instrument.SEGMENT || "E";
    if (segment === "E") return `${exchange} Equity`;
    if (segment === "D") return `${exchange} F&O`;
    if (segment === "C") return `${exchange} Currency`;
    if (segment === "M") return `${exchange} Commodity`;
    return exchange;
  };

  // Render a single instrument item
  const renderInstrument = (instrument, idx) => {
    const securityId =
      instrument.SEM_SECURITY_ID ||
      instrument.SECURITY_ID ||
      instrument.SM_SECURITY_ID ||
      instrument.SEC_ID ||
      instrument.securityId ||
      "N/A";
    const symbolName =
      instrument.SYMBOL_NAME ||
      instrument.SEM_SYMBOL_NAME ||
      instrument.SM_SYMBOL_NAME ||
      "";
    const tradingSymbol =
      instrument.SEM_TRADING_SYMBOL || instrument.TRADING_SYMBOL || "";
    const displayName =
      instrument.DISPLAY_NAME || instrument.SEM_CUSTOM_SYMBOL || symbolName;
    const hasValidId =
      securityId &&
      securityId !== "N/A" &&
      securityId !== "undefined" &&
      securityId !== "null";

    return (
      <button
        key={`${securityId}-${idx}`}
        onClick={() => handleSelect(instrument)}
        disabled={!hasValidId}
        className={`w-full text-left px-4 py-3 hover:bg-zinc-800 border-b border-zinc-800/50 last:border-b-0 transition-colors ${
          !hasValidId ? "opacity-50 cursor-not-allowed" : ""
        }`}
      >
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <div className="text-white font-medium truncate">
              {displayName || symbolName || tradingSymbol}
            </div>
            <div className="text-sm text-zinc-400 mt-1">
              {tradingSymbol && tradingSymbol !== symbolName && (
                <span className="mr-2">{tradingSymbol}</span>
              )}
              <span className={hasValidId ? "text-zinc-500" : "text-red-400"}>
                ID: {securityId} | {getExchangeSegmentDisplay(instrument)}
                {!hasValidId && " (Invalid - Missing Security ID)"}
              </span>
            </div>
          </div>
        </div>
      </button>
    );
  };

  // Render a section with title and instruments
  const renderSection = (title, instruments, category) => {
    if (!instruments || instruments.length === 0) return null;

    return (
      <div
        key={category}
        className="border-b border-zinc-800/50 last:border-b-0"
      >
        <div className="px-4 py-2 bg-zinc-800/30 text-zinc-300 text-xs font-semibold uppercase tracking-wider">
          {title}
        </div>
        {instruments.map((instrument, idx) =>
          renderInstrument(instrument, idx)
        )}
      </div>
    );
  };

  return (
    <div className="relative w-full z-50">
      <div className="relative" ref={searchRef}>
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Search className="h-5 w-5 text-zinc-400" />
        </div>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => {
            // Reset the selection flag when user types
            justSelectedRef.current = false;
            setSearchQuery(e.target.value);
          }}
          onFocus={() => {
            // Set focused state
            setIsFocused(true);
            // Reset the selection flag when user focuses
            justSelectedRef.current = false;
            if (searchQuery.trim().length === 0) {
              // Show pre-suggestions when input is empty and focused
              setShowPreSuggestions(true);
            } else if (
              (filteredInstruments.indices &&
                filteredInstruments.indices.length > 0) ||
              (filteredInstruments.equity &&
                filteredInstruments.equity.length > 0) ||
              (filteredInstruments.options &&
                filteredInstruments.options.length > 0) ||
              (filteredInstruments.other &&
                filteredInstruments.other.length > 0)
            ) {
              setShowSuggestions(true);
            }
          }}
          onBlur={() => {
            // Delay blur to allow clicking on suggestions
            setTimeout(() => {
              setIsFocused(false);
              // Hide pre-suggestions when input loses focus
              // (The click-outside handler will also handle this, but this is a backup)
            }, 200);
          }}
          placeholder={loading ? "Loading instruments..." : placeholder}
          className="w-full pl-10 pr-10 py-3 bg-zinc-900 border border-zinc-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-white placeholder-zinc-500"
          disabled={loading}
        />
        {searchQuery && (
          <button
            onClick={handleClear}
            className="absolute inset-y-0 right-0 pr-3 flex items-center"
          >
            <X className="h-5 w-5 text-zinc-400 hover:text-zinc-300" />
          </button>
        )}
      </div>

      {error && <div className="mt-2 text-sm text-red-400">{error}</div>}

      {/* Pre-suggestions - shown when input is empty or focused */}
      {showPreSuggestions && (
        <div
          ref={suggestionsRef}
          className="absolute w-full mt-1 bg-zinc-900 border border-zinc-800 rounded-lg shadow-2xl max-h-80 overflow-y-auto"
          style={{ zIndex: 1001 }}
        >
          <div className="px-4 py-2 bg-zinc-800/30 text-zinc-300 text-xs font-semibold uppercase tracking-wider">
            Popular Indices
          </div>
          {popularSuggestions.indices.map((suggestion, idx) => (
            <button
              key={`pre-index-${idx}`}
              onClick={() => handlePreSuggestionClick(suggestion)}
              className="w-full text-left px-4 py-3 hover:bg-zinc-800 border-b border-zinc-800/50 last:border-b-0 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="text-white font-medium">
                    {suggestion.name}
                  </div>
                  <div className="text-sm text-zinc-400 mt-1">Index</div>
                </div>
              </div>
            </button>
          ))}
          <div className="px-4 py-2 bg-zinc-800/30 text-zinc-300 text-xs font-semibold uppercase tracking-wider">
            Popular Stocks
          </div>
          {popularSuggestions.equity.map((suggestion, idx) => (
            <button
              key={`pre-equity-${idx}`}
              onClick={() => handlePreSuggestionClick(suggestion)}
              className="w-full text-left px-4 py-3 hover:bg-zinc-800 border-b border-zinc-800/50 last:border-b-0 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="text-white font-medium">
                    {suggestion.name}
                  </div>
                  <div className="text-sm text-zinc-400 mt-1">Equity</div>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {showSuggestions &&
        (filteredInstruments.indices?.length > 0 ||
          filteredInstruments.equity?.length > 0 ||
          filteredInstruments.options?.length > 0 ||
          filteredInstruments.other?.length > 0) && (
          <div
            ref={suggestionsRef}
            className="absolute w-full mt-1 bg-zinc-900 border border-zinc-800 rounded-lg shadow-2xl max-h-80 overflow-y-auto"
            style={{ zIndex: 1001 }}
          >
            {renderSection("Indices", filteredInstruments.indices, "indices")}
            {renderSection(
              "Stocks / Equity",
              filteredInstruments.equity,
              "equity"
            )}
            {renderSection("Options", filteredInstruments.options, "options")}
            {filteredInstruments.other &&
              filteredInstruments.other.length > 0 &&
              renderSection("Other", filteredInstruments.other, "other")}
          </div>
        )}

      {showSuggestions &&
        searchQuery.length >= 2 &&
        (!filteredInstruments.indices ||
          filteredInstruments.indices.length === 0) &&
        (!filteredInstruments.equity ||
          filteredInstruments.equity.length === 0) &&
        (!filteredInstruments.options ||
          filteredInstruments.options.length === 0) &&
        (!filteredInstruments.other ||
          filteredInstruments.other.length === 0) && (
          <div
            className="absolute w-full mt-1 bg-zinc-900 border border-zinc-800 rounded-lg shadow-2xl p-4 text-center text-zinc-400 text-sm"
            style={{ zIndex: 1001 }}
          >
            No instruments found
          </div>
        )}
    </div>
  );
}

export default InstrumentSearch;
