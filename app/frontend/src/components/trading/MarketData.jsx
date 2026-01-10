import { useState } from 'react'
import { Search, TrendingUp } from 'lucide-react'
import api from '../../services/api'
import RealTimeMarketFeed from './RealTimeMarketFeed'

function MarketData({ accessToken }) {
  const [searchSymbol, setSearchSymbol] = useState('')
  const [quoteData, setQuoteData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!searchSymbol) return

    setLoading(true)
    setError('')
    try {
      // Assuming security ID format - in real app, you'd search securities first
      const securityId = parseInt(searchSymbol)
      if (isNaN(securityId)) {
        setError('Please enter a valid security ID')
        setLoading(false)
        return
      }

      const response = await api.getMarketQuote({
        access_token: accessToken,
        securities: { "NSE_EQ": [securityId] }
      })

      if (response.success) {
        // Parse the nested response structure
        // Response structure: data.data.data.NSE_EQ.{securityId}
        const responseData = response.data
        let quoteInfo = null

        // Try to extract the actual quote data from nested structure
        if (responseData?.data?.data) {
          const nestedData = responseData.data.data
          // Find the first exchange segment and security
          for (const exchangeSegment in nestedData) {
            const securities = nestedData[exchangeSegment]
            for (const secId in securities) {
              quoteInfo = {
                securityId: secId,
                exchangeSegment: exchangeSegment,
                ...securities[secId]
              }
              break
            }
            if (quoteInfo) break
          }
        }

        if (quoteInfo) {
          setQuoteData(quoteInfo)
        } else {
          setError('Could not parse quote data from response')
        }
      } else {
        setError(response.error || 'Failed to get market quote')
      }
    } catch (err) {
      setError(err.message || 'Failed to get market quote')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-4xl mx-auto">
        <div className="glass rounded-xl p-8 mb-6">
          <div className="flex items-center gap-3 mb-6">
            <TrendingUp className="w-6 h-6 text-green-500" />
            <h2 className="text-2xl font-bold font-manrope">Market Data</h2>
          </div>

          <form onSubmit={handleSearch} className="flex gap-2">
            <input
              type="text"
              value={searchSymbol}
              onChange={(e) => setSearchSymbol(e.target.value)}
              placeholder="Enter Security ID (e.g., 1333 for HDFC Bank)"
              className="flex-1 px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-white placeholder-zinc-500"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <Search className="w-5 h-5" />
              {loading ? 'Loading...' : 'Search'}
            </button>
          </form>

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
                <div className="text-sm text-zinc-400 mb-2">Last Traded Price</div>
                <div className="text-4xl font-bold text-green-500">
                  ₹{quoteData.last_price?.toFixed(2) || '0.00'}
                </div>
                <div className="text-xs text-zinc-500 mt-2">
                  Security ID: {quoteData.securityId} | Exchange: {quoteData.exchangeSegment}
                </div>
              </div>
            </div>

            {/* OHLC Data */}
            {quoteData.ohlc && (
              <div>
                <h4 className="text-sm font-medium text-zinc-400 mb-3">OHLC (Open, High, Low, Close)</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-zinc-900 rounded-lg p-4">
                    <div className="text-sm text-zinc-400 mb-1">Open</div>
                    <div className="text-lg font-semibold text-white">
                      ₹{quoteData.ohlc.open?.toFixed(2) || '0.00'}
                    </div>
                  </div>
                  <div className="bg-zinc-900 rounded-lg p-4">
                    <div className="text-sm text-zinc-400 mb-1">High</div>
                    <div className="text-lg font-semibold text-green-400">
                      ₹{quoteData.ohlc.high?.toFixed(2) || '0.00'}
                    </div>
                  </div>
                  <div className="bg-zinc-900 rounded-lg p-4">
                    <div className="text-sm text-zinc-400 mb-1">Low</div>
                    <div className="text-lg font-semibold text-red-400">
                      ₹{quoteData.ohlc.low?.toFixed(2) || '0.00'}
                    </div>
                  </div>
                  <div className="bg-zinc-900 rounded-lg p-4">
                    <div className="text-sm text-zinc-400 mb-1">Close</div>
                    <div className="text-lg font-semibold text-white">
                      ₹{quoteData.ohlc.close?.toFixed(2) || '0.00'}
                    </div>
                  </div>
                </div>
              </div>
            )}
            </div>

            {/* Real-Time Market Feed */}
            <RealTimeMarketFeed
              accessToken={accessToken}
              securityId={parseInt(searchSymbol)}
            />
          </>
        )}

        <div className="mt-6 glass rounded-xl p-8">
          <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-zinc-900 rounded-lg p-4">
              <h4 className="text-sm font-medium text-zinc-400 mb-2">Option Chain</h4>
              <p className="text-sm text-zinc-500">View option chain for Nifty, Bank Nifty, etc.</p>
              <p className="text-xs text-zinc-600 mt-2">Coming soon...</p>
            </div>
            <div className="bg-zinc-900 rounded-lg p-4">
              <h4 className="text-sm font-medium text-zinc-400 mb-2">Historical Data</h4>
              <p className="text-sm text-zinc-500">Get historical OHLC data for analysis</p>
              <p className="text-xs text-zinc-600 mt-2">Coming soon...</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default MarketData

