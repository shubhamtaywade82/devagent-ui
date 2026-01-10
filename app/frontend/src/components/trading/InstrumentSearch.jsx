import { useState, useEffect, useRef } from 'react'
import { Search, X } from 'lucide-react'
import api from '../../services/api'

function InstrumentSearch({
  onSelect,
  placeholder = "Search by symbol name or Security ID...",
  accessToken = null,
  exchangeSegment = null
}) {
  const [instruments, setInstruments] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [filteredInstruments, setFilteredInstruments] = useState([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const searchRef = useRef(null)
  const suggestionsRef = useRef(null)

  // Load instruments on mount
  useEffect(() => {
    loadInstruments()
  }, [accessToken, exchangeSegment])

  // Filter instruments based on search query
  useEffect(() => {
    if (searchQuery.trim().length >= 2) {
      const query = searchQuery.toLowerCase().trim()
      const filtered = instruments.filter(inst => {
        const symbolName = (inst.SYMBOL_NAME || inst.SEM_SYMBOL_NAME || '').toLowerCase()
        const tradingSymbol = (inst.SEM_TRADING_SYMBOL || inst.TRADING_SYMBOL || '').toLowerCase()
        const displayName = (inst.DISPLAY_NAME || inst.SEM_CUSTOM_SYMBOL || '').toLowerCase()
        const securityId = (inst.SEM_SECURITY_ID || inst.SECURITY_ID || '').toString()
        const isin = (inst.ISIN || '').toLowerCase()

        return symbolName.includes(query) ||
               tradingSymbol.includes(query) ||
               displayName.includes(query) ||
               securityId.includes(query) ||
               isin.includes(query)
      }).slice(0, 10) // Limit to 10 results
      setFilteredInstruments(filtered)
      setShowSuggestions(filtered.length > 0)
    } else {
      setFilteredInstruments([])
      setShowSuggestions(false)
    }
  }, [searchQuery, instruments])

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(event.target) &&
        searchRef.current &&
        !searchRef.current.contains(event.target)
      ) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const loadInstruments = async () => {
    setLoading(true)
    setError('')
    try {
      let response

      if (accessToken && exchangeSegment) {
        // Use segmentwise API if access token and exchange segment are provided
        response = await api.getInstrumentListSegmentwise(accessToken, exchangeSegment)
      } else {
        // Use CSV API (no auth needed) - use compact format for faster loading
        response = await api.getInstrumentListCSV('compact')
      }

      if (response.success) {
        // Handle both CSV format (array of objects) and segmentwise format
        const instList = response.data?.instruments || response.data?.data || []
        if (Array.isArray(instList)) {
          setInstruments(instList)
        } else if (typeof instList === 'object') {
          // If it's an object, convert to array
          setInstruments(Object.values(instList))
        } else {
          setInstruments([])
        }
      } else {
        setError(response.error || 'Failed to load instruments')
      }
    } catch (err) {
      setError(err.message || 'Failed to load instruments')
      console.error('Error loading instruments:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSelect = (instrument) => {
    // Extract relevant data from instrument
    const securityId = instrument.SEM_SECURITY_ID || instrument.SECURITY_ID || instrument.SM_SECURITY_ID
    const exchangeSegment = instrument.SEM_EXM_EXCH_ID || instrument.EXCH_ID
    const segment = instrument.SEM_SEGMENT || instrument.SEGMENT

    // Map exchange and segment to DhanHQ format
    let exchangeSegmentFormatted = 'NSE_EQ'
    if (exchangeSegment === 'NSE' && segment === 'E') {
      exchangeSegmentFormatted = 'NSE_EQ'
    } else if (exchangeSegment === 'BSE' && segment === 'E') {
      exchangeSegmentFormatted = 'BSE_EQ'
    } else if (exchangeSegment === 'NSE' && segment === 'D') {
      exchangeSegmentFormatted = 'NSE_FNO'
    } else if (exchangeSegment === 'BSE' && segment === 'D') {
      exchangeSegmentFormatted = 'BSE_FNO'
    } else if (exchangeSegment === 'MCX') {
      exchangeSegmentFormatted = 'MCX_COM'
    }

    const instrumentData = {
      securityId: securityId?.toString() || '',
      exchangeSegment: exchangeSegmentFormatted,
      symbolName: instrument.SYMBOL_NAME || instrument.SEM_SYMBOL_NAME || instrument.SM_SYMBOL_NAME || '',
      tradingSymbol: instrument.SEM_TRADING_SYMBOL || instrument.TRADING_SYMBOL || '',
      displayName: instrument.DISPLAY_NAME || instrument.SEM_CUSTOM_SYMBOL || '',
      lotSize: instrument.LOT_SIZE || instrument.SEM_LOT_UNITS || 1,
      tickSize: instrument.TICK_SIZE || instrument.SEM_TICK_SIZE || 0.01,
      instrument: instrument
    }

    setSearchQuery(instrumentData.displayName || instrumentData.symbolName || instrumentData.tradingSymbol)
    setShowSuggestions(false)

    if (onSelect) {
      onSelect(instrumentData)
    }
  }

  const handleClear = () => {
    setSearchQuery('')
    setShowSuggestions(false)
    if (onSelect) {
      onSelect(null)
    }
  }

  const getExchangeSegmentDisplay = (instrument) => {
    const exchange = instrument.SEM_EXM_EXCH_ID || instrument.EXCH_ID || 'NSE'
    const segment = instrument.SEM_SEGMENT || instrument.SEGMENT || 'E'
    if (segment === 'E') return `${exchange} Equity`
    if (segment === 'D') return `${exchange} F&O`
    if (segment === 'C') return `${exchange} Currency`
    if (segment === 'M') return `${exchange} Commodity`
    return exchange
  }

  return (
    <div className="relative w-full z-50">
      <div className="relative" ref={searchRef}>
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Search className="h-5 w-5 text-zinc-400" />
        </div>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onFocus={() => {
            if (filteredInstruments.length > 0) {
              setShowSuggestions(true)
            }
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

      {error && (
        <div className="mt-2 text-sm text-red-400">{error}</div>
      )}

      {showSuggestions && filteredInstruments.length > 0 && (
        <div
          ref={suggestionsRef}
          className="absolute w-full mt-1 bg-zinc-900 border border-zinc-800 rounded-lg shadow-2xl max-h-80 overflow-y-auto"
          style={{ zIndex: 1001 }}
        >
          {filteredInstruments.map((instrument, idx) => {
            const securityId = instrument.SEM_SECURITY_ID || instrument.SECURITY_ID || instrument.SM_SECURITY_ID
            const symbolName = instrument.SYMBOL_NAME || instrument.SEM_SYMBOL_NAME || instrument.SM_SYMBOL_NAME || ''
            const tradingSymbol = instrument.SEM_TRADING_SYMBOL || instrument.TRADING_SYMBOL || ''
            const displayName = instrument.DISPLAY_NAME || instrument.SEM_CUSTOM_SYMBOL || symbolName

            return (
              <button
                key={idx}
                onClick={() => handleSelect(instrument)}
                className="w-full text-left px-4 py-3 hover:bg-zinc-800 border-b border-zinc-800/50 last:border-b-0 transition-colors"
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
                      <span className="text-zinc-500">
                        ID: {securityId} | {getExchangeSegmentDisplay(instrument)}
                      </span>
                    </div>
                  </div>
                </div>
              </button>
            )
          })}
        </div>
      )}

      {showSuggestions && searchQuery.length >= 2 && filteredInstruments.length === 0 && (
        <div
          className="absolute w-full mt-1 bg-zinc-900 border border-zinc-800 rounded-lg shadow-2xl p-4 text-center text-zinc-400 text-sm"
          style={{ zIndex: 1001 }}
        >
          No instruments found
        </div>
      )}
    </div>
  )
}

export default InstrumentSearch

