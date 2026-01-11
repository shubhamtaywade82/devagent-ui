import { useState } from 'react'
import { ShoppingCart, CheckCircle, XCircle, Calculator } from 'lucide-react'
import api from '../../services/api'
import InstrumentSearch from './InstrumentSearch'

function OrderPlacement({ accessToken }) {
  const [orderData, setOrderData] = useState({
    security_id: '',
    exchange_segment: 'NSE_EQ',
    transaction_type: 'BUY',
    quantity: '',
    order_type: 'MARKET',
    product_type: 'INTRADAY',
    price: '',
    trigger_price: '',
    validity: 'DAY'
  })
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [marginData, setMarginData] = useState(null)
  const [calculatingMargin, setCalculatingMargin] = useState(false)
  const [selectedInstrument, setSelectedInstrument] = useState(null)

  const handleInstrumentSelect = (instrument) => {
    setSelectedInstrument(instrument)
    if (instrument) {
      setOrderData({
        ...orderData,
        security_id: instrument.securityId,
        exchange_segment: instrument.exchangeSegment
      })
    } else {
      setOrderData({
        ...orderData,
        security_id: '',
        exchange_segment: 'NSE_EQ'
      })
    }
  }

  const handleCalculateMargin = async () => {
    if (!orderData.security_id || !orderData.quantity || !orderData.price) {
      setError('Please fill Security ID, Quantity, and Price to calculate margin')
      return
    }

    setCalculatingMargin(true)
    setError('')
    setMarginData(null)

    try {
      const payload = {
        access_token: accessToken,
        security_id: orderData.security_id,
        exchange_segment: orderData.exchange_segment,
        transaction_type: orderData.transaction_type,
        quantity: parseInt(orderData.quantity),
        product_type: orderData.product_type,
        price: parseFloat(orderData.price) || 0,
        trigger_price: parseFloat(orderData.trigger_price) || 0
      }

      const response = await api.calculateMargin(payload)
      if (response.success) {
        setMarginData(response.data)
      } else {
        setError(response.error || 'Failed to calculate margin')
      }
    } catch (err) {
      setError(err.message || 'Failed to calculate margin')
    } finally {
      setCalculatingMargin(false)
    }
  }

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
          exchange_segment: 'NSE_EQ',
          transaction_type: 'BUY',
          quantity: '',
          order_type: 'MARKET',
          product_type: 'INTRADAY',
          price: '',
          trigger_price: '',
          validity: 'DAY'
        })
        setMarginData(null)
        setSelectedInstrument(null)
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

          {marginData && (
            <div className="mb-4 p-4 bg-blue-500/20 border border-blue-500/50 rounded-lg">
              <div className="flex items-center gap-2 text-blue-400 mb-2">
                <Calculator className="w-5 h-5" />
                <span className="font-semibold">Margin Calculation</span>
              </div>
              <div className="text-sm text-zinc-300 space-y-1">
                {marginData.totalMargin && (
                  <p>Total Margin Required: <span className="font-mono text-white font-semibold">₹{typeof marginData.totalMargin === 'number' ? marginData.totalMargin.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : marginData.totalMargin}</span></p>
                )}
                {marginData.span && (
                  <p>Span: <span className="font-mono text-white">₹{typeof marginData.span === 'number' ? marginData.span.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : marginData.span}</span></p>
                )}
                {marginData.exposure && (
                  <p>Exposure: <span className="font-mono text-white">₹{typeof marginData.exposure === 'number' ? marginData.exposure.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : marginData.exposure}</span></p>
                )}
                {marginData.adHocMargin && (
                  <p>Ad-hoc Margin: <span className="font-mono text-white">₹{typeof marginData.adHocMargin === 'number' ? marginData.adHocMargin.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : marginData.adHocMargin}</span></p>
                )}
                {!marginData.totalMargin && !marginData.span && (
                  <pre className="text-xs overflow-x-auto">{JSON.stringify(marginData, null, 2)}</pre>
                )}
              </div>
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
            <div>
              <label className="block text-sm font-medium mb-2 text-zinc-300">
                Search Instrument
              </label>
              <InstrumentSearch
                onSelect={handleInstrumentSelect}
                placeholder="Search by symbol name (e.g., HDFC BANK, RELIANCE) or Security ID..."
                accessToken={accessToken}
              />
              {selectedInstrument && (
                <div className="mt-2 text-sm text-zinc-400">
                  Selected: <span className="text-white font-medium">{selectedInstrument.displayName || selectedInstrument.symbolName}</span>
                  {' '}(ID: {selectedInstrument.securityId}, {selectedInstrument.exchangeSegment})
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2 text-zinc-300">
                  Security ID
                </label>
                <input
                  type="text"
                  value={orderData.security_id}
                  onChange={(e) => setOrderData({...orderData, security_id: e.target.value})}
                  placeholder="Auto-filled from search or enter manually"
                  className="w-full px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-white placeholder-zinc-500"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-zinc-300">
                  Exchange Segment
                </label>
                <select
                  value={orderData.exchange_segment}
                  onChange={(e) => setOrderData({...orderData, exchange_segment: e.target.value})}
                  className="w-full px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-white"
                >
                  <option value="NSE_EQ">NSE Equity</option>
                  <option value="BSE_EQ">BSE Equity</option>
                  <option value="NSE_FNO">NSE F&O</option>
                  <option value="BSE_FNO">BSE F&O</option>
                  <option value="MCX_COM">MCX Commodity</option>
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
                  <option value="INTRADAY">Intraday</option>
                  <option value="MARGIN">Margin</option>
                  <option value="CNC">CNC</option>
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

            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleCalculateMargin}
                disabled={calculatingMargin || !orderData.security_id || !orderData.quantity || !orderData.price}
                className="flex-1 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                <Calculator className="w-4 h-4" />
                {calculatingMargin ? 'Calculating...' : 'Calculate Margin'}
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex-1 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Placing Order...' : 'Place Order'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

export default OrderPlacement

