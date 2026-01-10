import { useState, useEffect } from 'react'
import { Wallet, TrendingUp, TrendingDown } from 'lucide-react'
import api from '../../services/api'

function PortfolioView({ accessToken }) {
  const [holdings, setHoldings] = useState([])
  const [positions, setPositions] = useState([])
  const [funds, setFunds] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('holdings')

  useEffect(() => {
    loadPortfolioData()
    const interval = setInterval(loadPortfolioData, 30000)
    return () => clearInterval(interval)
  }, [accessToken])

  const loadPortfolioData = async () => {
    try {
      const [holdingsData, positionsData, fundsData] = await Promise.all([
        api.getHoldings(accessToken),
        api.getPositions(accessToken),
        api.getFunds(accessToken)
      ])

      if (holdingsData.success) setHoldings(holdingsData.data || [])
      if (positionsData.success) setPositions(positionsData.data || [])
      if (fundsData.success) setFunds(fundsData.data)
    } catch (error) {
      console.error('Failed to load portfolio:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-zinc-400">Loading portfolio...</div>
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      {/* Summary Cards */}
      {funds && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="glass rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-zinc-400">Total Balance</span>
              <Wallet className="w-5 h-5 text-blue-500" />
            </div>
            <div className="text-2xl font-bold text-white">
              ₹{funds.totalBalance?.toLocaleString('en-IN') || '0.00'}
            </div>
          </div>
          <div className="glass rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-zinc-400">Available Balance</span>
              <TrendingUp className="w-5 h-5 text-green-500" />
            </div>
            <div className="text-2xl font-bold text-white">
              ₹{funds.availableBalance?.toLocaleString('en-IN') || '0.00'}
            </div>
          </div>
          <div className="glass rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-zinc-400">Margin Used</span>
              <TrendingDown className="w-5 h-5 text-orange-500" />
            </div>
            <div className="text-2xl font-bold text-white">
              ₹{funds.marginUsed?.toLocaleString('en-IN') || '0.00'}
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-zinc-800">
        <button
          onClick={() => setActiveTab('holdings')}
          className={`px-6 py-3 text-sm font-medium transition-colors ${
            activeTab === 'holdings'
              ? 'border-b-2 border-green-500 text-green-400'
              : 'text-zinc-400 hover:text-zinc-300'
          }`}
        >
          Holdings
        </button>
        <button
          onClick={() => setActiveTab('positions')}
          className={`px-6 py-3 text-sm font-medium transition-colors ${
            activeTab === 'positions'
              ? 'border-b-2 border-green-500 text-green-400'
              : 'text-zinc-400 hover:text-zinc-300'
          }`}
        >
          Positions
        </button>
      </div>

      {/* Holdings */}
      {activeTab === 'holdings' && (
        <div className="glass rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Holdings</h2>
          {holdings.length === 0 ? (
            <div className="text-center text-zinc-500 py-8">No holdings</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-zinc-800">
                    <th className="text-left py-2 px-4 text-sm font-medium text-zinc-400">Symbol</th>
                    <th className="text-left py-2 px-4 text-sm font-medium text-zinc-400">Quantity</th>
                    <th className="text-left py-2 px-4 text-sm font-medium text-zinc-400">Avg Price</th>
                    <th className="text-left py-2 px-4 text-sm font-medium text-zinc-400">LTP</th>
                    <th className="text-right py-2 px-4 text-sm font-medium text-zinc-400">P&L</th>
                    <th className="text-right py-2 px-4 text-sm font-medium text-zinc-400">Value</th>
                  </tr>
                </thead>
                <tbody>
                  {holdings.map((holding, idx) => {
                    const pnl = (holding.lastPrice - holding.averagePrice) * holding.quantity
                    const value = holding.lastPrice * holding.quantity
                    return (
                      <tr key={idx} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                        <td className="py-3 px-4 text-white">{holding.tradingSymbol || holding.securityId}</td>
                        <td className="py-3 px-4 text-white">{holding.quantity}</td>
                        <td className="py-3 px-4 text-white">₹{holding.averagePrice?.toFixed(2) || '0.00'}</td>
                        <td className="py-3 px-4 text-white">₹{holding.lastPrice?.toFixed(2) || '0.00'}</td>
                        <td className={`py-3 px-4 text-right font-medium ${
                          pnl >= 0 ? 'text-green-500' : 'text-red-500'
                        }`}>
                          ₹{pnl.toFixed(2)}
                        </td>
                        <td className="py-3 px-4 text-right text-white">₹{value.toFixed(2)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Positions */}
      {activeTab === 'positions' && (
        <div className="glass rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Open Positions</h2>
          {positions.length === 0 ? (
            <div className="text-center text-zinc-500 py-8">No open positions</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-zinc-800">
                    <th className="text-left py-2 px-4 text-sm font-medium text-zinc-400">Symbol</th>
                    <th className="text-left py-2 px-4 text-sm font-medium text-zinc-400">Qty</th>
                    <th className="text-left py-2 px-4 text-sm font-medium text-zinc-400">Avg Price</th>
                    <th className="text-left py-2 px-4 text-sm font-medium text-zinc-400">LTP</th>
                    <th className="text-right py-2 px-4 text-sm font-medium text-zinc-400">P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((pos, idx) => (
                    <tr key={idx} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                      <td className="py-3 px-4 text-white">{pos.tradingSymbol || pos.securityId}</td>
                      <td className="py-3 px-4 text-white">{pos.quantity}</td>
                      <td className="py-3 px-4 text-white">₹{pos.averagePrice?.toFixed(2) || '0.00'}</td>
                      <td className="py-3 px-4 text-white">₹{pos.lastPrice?.toFixed(2) || '0.00'}</td>
                      <td className={`py-3 px-4 text-right font-medium ${
                        (pos.unrealizedPnL || 0) >= 0 ? 'text-green-500' : 'text-red-500'
                      }`}>
                        ₹{(pos.unrealizedPnL || 0).toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default PortfolioView

