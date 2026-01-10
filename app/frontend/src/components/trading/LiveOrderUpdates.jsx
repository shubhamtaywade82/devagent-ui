import { useState, useEffect, useRef } from 'react'
import { Bell, Wifi, WifiOff, CheckCircle, XCircle, Clock } from 'lucide-react'
import TradingWebSocket from '../../services/websocket'

function LiveOrderUpdates({ accessToken }) {
  const [orderUpdates, setOrderUpdates] = useState([])
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState('')
  const wsRef = useRef(null)

  useEffect(() => {
    if (!accessToken) return

    const ws = new TradingWebSocket(
      '/ws/trading/order-updates/{access_token}',
      accessToken,
      (data) => {
        if (data.type === 'order_update') {
          setOrderUpdates(prev => [data.data, ...prev].slice(0, 20)) // Keep last 20 updates
          setError('')
        } else if (data.type === 'error') {
          setError(data.message)
        }
      },
      (err) => {
        setError('WebSocket connection error')
        setIsConnected(false)
      },
      () => {
        setIsConnected(false)
      }
    )

    ws.connect()
    wsRef.current = ws

    setTimeout(() => {
      if (ws.ws && ws.ws.readyState === WebSocket.OPEN) {
        setIsConnected(true)
      }
    }, 1000)

    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect()
      }
    }
  }, [accessToken])

  const getStatusIcon = (status) => {
    switch (status) {
      case 'TRADED':
      case 'COMPLETE':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'REJECTED':
      case 'CANCELLED':
        return <XCircle className="w-4 h-4 text-red-500" />
      default:
        return <Clock className="w-4 h-4 text-yellow-500" />
    }
  }

  return (
    <div className="glass rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Bell className="w-5 h-5 text-green-500" />
          <h3 className="text-lg font-semibold">Live Order Updates</h3>
        </div>
        <div className="flex items-center gap-2">
          {isConnected ? (
            <>
              <Wifi className="w-4 h-4 text-green-500" />
              <span className="text-xs text-green-500">Connected</span>
            </>
          ) : (
            <>
              <WifiOff className="w-4 h-4 text-red-500" />
              <span className="text-xs text-red-500">Disconnected</span>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      <div className="space-y-2 max-h-96 overflow-y-auto">
        {orderUpdates.length === 0 ? (
          <div className="text-center text-zinc-500 py-8">
            No order updates yet. Orders will appear here in real-time.
          </div>
        ) : (
          orderUpdates.map((update, idx) => (
            <div key={idx} className="bg-zinc-900 rounded-lg p-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                {getStatusIcon(update.orderStatus || update.status)}
                <div>
                  <div className="text-sm font-medium text-white">
                    Order ID: {update.orderId || update.order_id}
                  </div>
                  <div className="text-xs text-zinc-400">
                    {update.tradingSymbol || update.symbol} • {update.orderStatus || update.status}
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm text-white">
                  Qty: {update.quantity || update.qty}
                </div>
                <div className="text-xs text-zinc-400">
                  ₹{update.price?.toFixed(2) || '0.00'}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default LiveOrderUpdates

