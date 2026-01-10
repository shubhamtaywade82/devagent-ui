import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, Wallet, DollarSign, Activity } from 'lucide-react'
import api from '../../services/api'

function TradingDashboard({ accessToken }) {
  const [funds, setFunds] = useState(null)
  const [positions, setPositions] = useState([])
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboardData()
    const interval = setInterval(loadDashboardData, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [accessToken])

  const loadDashboardData = async () => {
    if (!accessToken) {
      setLoading(false)
      return
    }

    try {
      const [fundsData, positionsData, ordersData] = await Promise.all([
        api.getFunds(accessToken),
        api.getPositions(accessToken),
        api.getOrders(accessToken)
      ])

      if (fundsData.success) setFunds(fundsData.data)
      if (positionsData.success) {
        const positionsArray = Array.isArray(positionsData.data)
          ? positionsData.data
          : (positionsData.data?.data || positionsData.data?.positions || [])
        setPositions(positionsArray)
      }
      if (ordersData.success) {
        const ordersArray = Array.isArray(ordersData.data)
          ? ordersData.data
          : (ordersData.data?.data || ordersData.data?.orders || [])
        setOrders(ordersArray)
      }
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-zinc-950">
        <div className="text-zinc-400 text-lg">Loading dashboard...</div>
      </div>
    )
  }

  if (!accessToken) {
    return (
      <div className="h-full flex items-center justify-center bg-zinc-950">
        <div className="text-red-400 text-lg">No access token available</div>
      </div>
    )
  }

  // Helper function to safely extract fund values with fallbacks
  const getFundValue = (funds, ...keys) => {
    if (!funds) return 0
    for (const key of keys) {
      const value = funds[key]
      if (value !== undefined && value !== null) {
        return typeof value === 'number' ? value : parseFloat(value) || 0
      }
    }
    return 0
  }

  const totalPnL = Array.isArray(positions)
    ? positions.reduce((sum, pos) => sum + (pos.unrealizedPnL || pos.unrealisedPnL || pos.pnl || 0), 0)
    : 0
  const activeOrders = Array.isArray(orders)
    ? orders.filter(o => o.orderStatus !== 'COMPLETE' && o.orderStatus !== 'CANCELLED').length
    : 0

  const availableBalance = getFundValue(funds, 'availableBalance', 'availableFunds', 'availableMargin', 'available')
  const marginUsed = getFundValue(funds, 'marginUsed', 'marginUtilized', 'usedMargin', 'margin')
  const totalBalance = getFundValue(funds, 'totalBalance', 'totalFunds', 'totalMargin', 'balance')
  const collateral = getFundValue(funds, 'collateral', 'collateralValue', 'collateralAmount')

  return (
    <div className="h-full overflow-y-auto p-6 bg-zinc-950">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* Available Balance */}
        <div className="glass rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-zinc-400">Available Balance</span>
            <Wallet className="w-5 h-5 text-green-500" />
          </div>
          <div className="text-2xl font-bold text-white">
            ₹{availableBalance.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>

        {/* Total P&L */}
        <div className="glass rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-zinc-400">Total P&L</span>
            {totalPnL >= 0 ? (
              <TrendingUp className="w-5 h-5 text-green-500" />
            ) : (
              <TrendingDown className="w-5 h-5 text-red-500" />
            )}
          </div>
          <div className={`text-2xl font-bold ${totalPnL >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            ₹{totalPnL.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>

        {/* Margin Used */}
        <div className="glass rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-zinc-400">Margin Used</span>
            <DollarSign className="w-5 h-5 text-blue-500" />
          </div>
          <div className="text-2xl font-bold text-white">
            ₹{marginUsed.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>

        {/* Active Orders */}
        <div className="glass rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-zinc-400">Active Orders</span>
            <Activity className="w-5 h-5 text-violet-500" />
          </div>
          <div className="text-2xl font-bold text-white">{activeOrders}</div>
        </div>
      </div>

      {/* Positions */}
      <div className="glass rounded-lg p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Open Positions</h2>
        {!Array.isArray(positions) || positions.length === 0 ? (
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

      {/* Recent Orders */}
      <div className="glass rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Recent Orders</h2>
        {!Array.isArray(orders) || orders.length === 0 ? (
          <div className="text-center text-zinc-500 py-8">No orders yet</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-zinc-800">
                  <th className="text-left py-2 px-4 text-sm font-medium text-zinc-400">Order ID</th>
                  <th className="text-left py-2 px-4 text-sm font-medium text-zinc-400">Symbol</th>
                  <th className="text-left py-2 px-4 text-sm font-medium text-zinc-400">Type</th>
                  <th className="text-left py-2 px-4 text-sm font-medium text-zinc-400">Qty</th>
                  <th className="text-left py-2 px-4 text-sm font-medium text-zinc-400">Price</th>
                  <th className="text-left py-2 px-4 text-sm font-medium text-zinc-400">Status</th>
                </tr>
              </thead>
              <tbody>
                {orders.slice(0, 10).map((order, idx) => (
                  <tr key={idx} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                    <td className="py-3 px-4 text-white font-mono text-sm">{order.orderId}</td>
                    <td className="py-3 px-4 text-white">{order.tradingSymbol || order.securityId}</td>
                    <td className="py-3 px-4 text-white">{order.transactionType}</td>
                    <td className="py-3 px-4 text-white">{order.quantity}</td>
                    <td className="py-3 px-4 text-white">₹{order.price?.toFixed(2) || '0.00'}</td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        order.orderStatus === 'COMPLETE' ? 'bg-green-500/20 text-green-400' :
                        order.orderStatus === 'CANCELLED' ? 'bg-red-500/20 text-red-400' :
                        'bg-yellow-500/20 text-yellow-400'
                      }`}>
                        {order.orderStatus}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default TradingDashboard

