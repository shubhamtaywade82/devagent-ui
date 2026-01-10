import { useState } from 'react'
import { ShoppingCart, CheckCircle, XCircle } from 'lucide-react'
import api from '../../services/api'

function OrderPlacement({ accessToken }) {
  const [orderData, setOrderData] = useState({
    security_id: '',
    exchange_segment: 'NSE',
    transaction_type: 'BUY',
    quantity: '',
    order_type: 'MARKET',
    product_type: 'INTRA',
    price: '',
    trigger_price: '',
    validity: 'DAY'
  })
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setResult(null)

    try {
      const payload = {
        access_token: accessToken,
        ...orderData,
        quantity: parseInt(orderData.quantity),
        price: parseFloat(orderData.price) || 0,
        trigger_price: parseFloat(orderData.trigger_price) || 0
      }

      const response = await api.placeOrder(payload)
      if (response.success) {
        setResult(response.data)
        // Reset form
        setOrderData({
          security_id: '',
          exchange_segment: 'NSE',
          transaction_type: 'BUY',
          quantity: '',
          order_type: 'MARKET',
          product_type: 'INTRA',
          price: '',
          trigger_price: '',
          validity: 'DAY'
        })
      } else {
        setError(response.error || 'Failed to place order')
      }
    } catch (err) {
      setError(err.message || 'Failed to place order')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto">
        <div className="glass rounded-xl p-8">
          <div className="flex items-center gap-3 mb-6">
            <ShoppingCart className="w-6 h-6 text-green-500" />
            <h2 className="text-2xl font-bold font-manrope">Place Order</h2>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          {result && (
            <div className="mb-4 p-4 bg-green-500/20 border border-green-500/50 rounded-lg">
              <div className="flex items-center gap-2 text-green-400 mb-2">
                <CheckCircle className="w-5 h-5" />
                <span className="font-semibold">Order Placed Successfully!</span>
              </div>
              <div className="text-sm text-zinc-300">
                <p>Order ID: <span className="font-mono">{result.orderId}</span></p>
                {result.correlationId && (
                  <p>Correlation ID: <span className="font-mono">{result.correlationId}</span></p>
                )}
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2 text-zinc-300">
                  Security ID
                </label>
                <input
                  type="text"
                  value={orderData.security_id}
                  onChange={(e) => setOrderData({...orderData, security_id: e.target.value})}
                  placeholder="e.g., 1333"
                  className="w-full px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-white placeholder-zinc-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-zinc-300">
                  Exchange
                </label>
                <select
                  value={orderData.exchange_segment}
                  onChange={(e) => setOrderData({...orderData, exchange_segment: e.target.value})}
                  className="w-full px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-white"
                >
                  <option value="NSE">NSE</option>
                  <option value="BSE">BSE</option>
                  <option value="NSE_FNO">NSE F&O</option>
                  <option value="BSE_FNO">BSE F&O</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2 text-zinc-300">
                  Transaction Type
                </label>
                <select
                  value={orderData.transaction_type}
                  onChange={(e) => setOrderData({...orderData, transaction_type: e.target.value})}
                  className="w-full px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-white"
                >
                  <option value="BUY">BUY</option>
                  <option value="SELL">SELL</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-zinc-300">
                  Quantity
                </label>
                <input
                  type="number"
                  value={orderData.quantity}
                  onChange={(e) => setOrderData({...orderData, quantity: e.target.value})}
                  placeholder="Enter quantity"
                  className="w-full px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-white placeholder-zinc-500"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2 text-zinc-300">
                  Order Type
                </label>
                <select
                  value={orderData.order_type}
                  onChange={(e) => setOrderData({...orderData, order_type: e.target.value})}
                  className="w-full px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-white"
                >
                  <option value="MARKET">MARKET</option>
                  <option value="LIMIT">LIMIT</option>
                  <option value="SL">Stop Loss</option>
                  <option value="SL-M">Stop Loss Market</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-zinc-300">
                  Product Type
                </label>
                <select
                  value={orderData.product_type}
                  onChange={(e) => setOrderData({...orderData, product_type: e.target.value})}
                  className="w-full px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-white"
                >
                  <option value="INTRA">Intraday</option>
                  <option value="CNC">CNC</option>
                  <option value="MARGIN">Margin</option>
                </select>
              </div>
            </div>

            {(orderData.order_type === 'LIMIT' || orderData.order_type === 'SL' || orderData.order_type === 'SL-M') && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2 text-zinc-300">
                    Price
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={orderData.price}
                    onChange={(e) => setOrderData({...orderData, price: e.target.value})}
                    placeholder="Enter price"
                    className="w-full px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-white placeholder-zinc-500"
                    required={orderData.order_type !== 'MARKET'}
                  />
                </div>

                {(orderData.order_type === 'SL' || orderData.order_type === 'SL-M') && (
                  <div>
                    <label className="block text-sm font-medium mb-2 text-zinc-300">
                      Trigger Price
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      value={orderData.trigger_price}
                      onChange={(e) => setOrderData({...orderData, trigger_price: e.target.value})}
                      placeholder="Enter trigger price"
                      className="w-full px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-white placeholder-zinc-500"
                      required
                    />
                  </div>
                )}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Placing Order...' : 'Place Order'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

export default OrderPlacement

