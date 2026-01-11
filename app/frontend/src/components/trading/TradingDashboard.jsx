import { useState, useEffect } from "react";
import {
  TrendingUp,
  TrendingDown,
  Wallet,
  DollarSign,
  Activity,
  RefreshCw,
} from "lucide-react";
import api from "../../services/api";

function TradingDashboard({ accessToken }) {
  const [funds, setFunds] = useState(null);
  const [positions, setPositions] = useState([]);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState({
    funds: null,
    positions: null,
    orders: null,
  });

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [accessToken]);

  const loadDashboardData = async () => {
    if (!accessToken) {
      setLoading(false);
      return;
    }

    setErrors({ funds: null, positions: null, orders: null });

    try {
      const [fundsData, positionsData, ordersData] = await Promise.all([
        api
          .getFunds(accessToken)
          .catch((err) => ({ success: false, error: err.message })),
        api
          .getPositions(accessToken)
          .catch((err) => ({ success: false, error: err.message })),
        api
          .getOrders(accessToken)
          .catch((err) => ({ success: false, error: err.message })),
      ]);

      // Handle funds data
      if (fundsData.success) {
        // DhanHQ API returns data nested under 'data' key
        const fundsDataValue = fundsData.data?.data || fundsData.data;
        setFunds(fundsDataValue);
        setErrors((prev) => ({ ...prev, funds: null }));
        // Log for debugging
        console.log("Funds data:", fundsDataValue);
      } else {
        setErrors((prev) => ({
          ...prev,
          funds: fundsData.error || "Failed to load funds",
        }));
        console.error("Funds error:", fundsData.error);
      }

      // Handle positions data
      if (positionsData.success) {
        const positionsArray = Array.isArray(positionsData.data)
          ? positionsData.data
          : positionsData.data?.data ||
            positionsData.data?.positions ||
            positionsData.data?.position ||
            [];
        setPositions(positionsArray);
        setErrors((prev) => ({ ...prev, positions: null }));
        console.log("Positions data:", positionsArray);
      } else {
        setErrors((prev) => ({
          ...prev,
          positions: positionsData.error || "Failed to load positions",
        }));
        console.error("Positions error:", positionsData.error);
      }

      // Handle orders data
      if (ordersData.success) {
        const ordersArray = Array.isArray(ordersData.data)
          ? ordersData.data
          : ordersData.data?.data ||
            ordersData.data?.orders ||
            ordersData.data?.order ||
            [];
        setOrders(ordersArray);
        setErrors((prev) => ({ ...prev, orders: null }));
        console.log("Orders data:", ordersArray);
      } else {
        setErrors((prev) => ({
          ...prev,
          orders: ordersData.error || "Failed to load orders",
        }));
        console.error("Orders error:", ordersData.error);
      }
    } catch (error) {
      console.error("Failed to load dashboard data:", error);
      setErrors({
        funds: error.message,
        positions: error.message,
        orders: error.message,
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-zinc-950">
        <div className="text-zinc-400 text-lg">Loading dashboard...</div>
      </div>
    );
  }

  if (!accessToken) {
    return (
      <div className="h-full flex items-center justify-center bg-zinc-950">
        <div className="text-red-400 text-lg">No access token available</div>
      </div>
    );
  }

  // Helper function to safely extract fund values with fallbacks
  const getFundValue = (funds, ...keys) => {
    if (!funds) return 0;
    for (const key of keys) {
      const value = funds[key];
      if (value !== undefined && value !== null) {
        return typeof value === "number" ? value : parseFloat(value) || 0;
      }
    }
    return 0;
  };

  const totalPnL = Array.isArray(positions)
    ? positions.reduce(
        (sum, pos) =>
          sum + (pos.unrealizedPnL || pos.unrealisedPnL || pos.pnl || 0),
        0
      )
    : 0;
  const activeOrders = Array.isArray(orders)
    ? orders.filter(
        (o) => o.orderStatus !== "COMPLETE" && o.orderStatus !== "CANCELLED"
      ).length
    : 0;

  // DhanHQ API returns 'availabelBalance' (note the typo in their API)
  const availableBalance = getFundValue(
    funds,
    "availabelBalance",
    "availableBalance",
    "availableFunds",
    "availableMargin",
    "available",
    "availableCash",
    "cashAvailable"
  );
  const withdrawableBalance = getFundValue(
    funds,
    "withdrawableBalance",
    "withdrawable",
    "withdrawableAmount"
  );
  const marginUsed = getFundValue(
    funds,
    "utilizedAmount",
    "marginUsed",
    "marginUtilized",
    "usedMargin",
    "margin",
    "marginUtilised"
  );
  const totalBalance = getFundValue(
    funds,
    "sodLimit",
    "totalBalance",
    "totalFunds",
    "totalMargin",
    "balance",
    "totalCash",
    "openingBalance"
  );
  const collateral = getFundValue(
    funds,
    "collateralAmount",
    "collateral",
    "collateralValue"
  );
  const receivableAmount = getFundValue(
    funds,
    "receiveableAmount",
    "receivableAmount",
    "receivable"
  );

  // Check if there are any errors
  const hasErrors = errors.funds || errors.positions || errors.orders;

  return (
    <div className="h-full overflow-y-auto p-6 bg-zinc-950">
      {/* Header with Refresh Button */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold">Dashboard</h2>
        <button
          onClick={loadDashboardData}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Error Messages */}
      {hasErrors && (
        <div className="mb-4 space-y-2">
          {errors.funds && (
            <div className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
              <strong>Funds Error:</strong> {errors.funds}
              <div className="text-xs text-red-300 mt-1">
                This might indicate an authentication issue or API connectivity
                problem.
              </div>
            </div>
          )}
          {errors.positions && (
            <div className="p-3 bg-yellow-500/20 border border-yellow-500/50 rounded-lg text-yellow-400 text-sm">
              <strong>Positions Error:</strong> {errors.positions}
            </div>
          )}
          {errors.orders && (
            <div className="p-3 bg-orange-500/20 border border-orange-500/50 rounded-lg text-orange-400 text-sm">
              <strong>Orders Error:</strong> {errors.orders}
            </div>
          )}
        </div>
      )}

      {/* Info Message for Empty Account */}
      {!hasErrors &&
        !loading &&
        funds &&
        availableBalance === 0 &&
        marginUsed === 0 &&
        positions.length === 0 &&
        orders.length === 0 && (
          <div className="mb-4 p-4 bg-blue-500/20 border border-blue-500/50 rounded-lg text-blue-400 text-sm">
            <strong>New Account Detected:</strong> Your account appears to be
            new or empty. This is normal for demo accounts or newly created
            trading accounts. Start by placing an order or check your account
            balance in the DhanHQ portal.
          </div>
        )}

      {/* Debug Info (only in development) */}
      {process.env.NODE_ENV === "development" && funds && (
        <div className="mb-4 p-3 bg-zinc-900/50 border border-zinc-800 rounded-lg text-xs text-zinc-500">
          <details>
            <summary className="cursor-pointer text-zinc-400">
              Debug: Funds Data Structure
            </summary>
            <pre className="mt-2 overflow-auto max-h-40">
              {JSON.stringify(funds, null, 2)}
            </pre>
          </details>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* Available Balance */}
        <div className="glass rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-zinc-400">Available Balance</span>
            <Wallet className="w-5 h-5 text-green-500" />
          </div>
          <div className="text-2xl font-bold text-white">
            ₹
            {availableBalance.toLocaleString("en-IN", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </div>
          {funds &&
            withdrawableBalance > 0 &&
            withdrawableBalance !== availableBalance && (
              <div className="text-xs text-zinc-500 mt-1">
                Withdrawable: ₹
                {withdrawableBalance.toLocaleString("en-IN", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </div>
            )}
          {!funds && !errors.funds && (
            <div className="text-xs text-zinc-500 mt-1">Loading...</div>
          )}
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
          <div
            className={`text-2xl font-bold ${
              totalPnL >= 0 ? "text-green-500" : "text-red-500"
            }`}
          >
            ₹
            {totalPnL.toLocaleString("en-IN", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </div>
        </div>

        {/* Margin Used */}
        <div className="glass rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-zinc-400">Margin Used</span>
            <DollarSign className="w-5 h-5 text-orange-500" />
          </div>
          <div className="text-2xl font-bold text-white">
            ₹
            {marginUsed.toLocaleString("en-IN", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </div>
          {collateral > 0 && (
            <div className="text-xs text-zinc-500 mt-1">
              Collateral: ₹
              {collateral.toLocaleString("en-IN", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </div>
          )}
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
        {errors.positions ? (
          <div className="text-center text-red-400 py-8">
            {errors.positions}
            <div className="text-sm text-zinc-500 mt-2">
              Check console for details
            </div>
          </div>
        ) : !Array.isArray(positions) || positions.length === 0 ? (
          <div className="text-center text-zinc-500 py-8">
            <div className="mb-2">No open positions</div>
            <div className="text-xs text-zinc-600">
              Open positions will appear here when you have active trades
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-zinc-800">
                  <th className="text-left py-2 px-4 text-sm font-medium text-zinc-400">
                    Symbol
                  </th>
                  <th className="text-left py-2 px-4 text-sm font-medium text-zinc-400">
                    Qty
                  </th>
                  <th className="text-left py-2 px-4 text-sm font-medium text-zinc-400">
                    Avg Price
                  </th>
                  <th className="text-left py-2 px-4 text-sm font-medium text-zinc-400">
                    LTP
                  </th>
                  <th className="text-right py-2 px-4 text-sm font-medium text-zinc-400">
                    P&L
                  </th>
                </tr>
              </thead>
              <tbody>
                {positions.map((pos, idx) => (
                  <tr
                    key={idx}
                    className="border-b border-zinc-800/50 hover:bg-zinc-800/30"
                  >
                    <td className="py-3 px-4 text-white">
                      {pos.tradingSymbol || pos.securityId}
                    </td>
                    <td className="py-3 px-4 text-white">{pos.quantity}</td>
                    <td className="py-3 px-4 text-white">
                      ₹{pos.averagePrice?.toFixed(2) || "0.00"}
                    </td>
                    <td className="py-3 px-4 text-white">
                      ₹{pos.lastPrice?.toFixed(2) || "0.00"}
                    </td>
                    <td
                      className={`py-3 px-4 text-right font-medium ${
                        (pos.unrealizedPnL || 0) >= 0
                          ? "text-green-500"
                          : "text-red-500"
                      }`}
                    >
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
        {errors.orders ? (
          <div className="text-center text-red-400 py-8">
            {errors.orders}
            <div className="text-sm text-zinc-500 mt-2">
              Check console for details
            </div>
          </div>
        ) : !Array.isArray(orders) || orders.length === 0 ? (
          <div className="text-center text-zinc-500 py-8">
            <div className="mb-2">No orders yet</div>
            <div className="text-xs text-zinc-600">
              Your order history will appear here after placing orders
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-zinc-800">
                  <th className="text-left py-2 px-4 text-sm font-medium text-zinc-400">
                    Order ID
                  </th>
                  <th className="text-left py-2 px-4 text-sm font-medium text-zinc-400">
                    Symbol
                  </th>
                  <th className="text-left py-2 px-4 text-sm font-medium text-zinc-400">
                    Type
                  </th>
                  <th className="text-left py-2 px-4 text-sm font-medium text-zinc-400">
                    Qty
                  </th>
                  <th className="text-left py-2 px-4 text-sm font-medium text-zinc-400">
                    Price
                  </th>
                  <th className="text-left py-2 px-4 text-sm font-medium text-zinc-400">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody>
                {orders.slice(0, 10).map((order, idx) => (
                  <tr
                    key={idx}
                    className="border-b border-zinc-800/50 hover:bg-zinc-800/30"
                  >
                    <td className="py-3 px-4 text-white font-mono text-sm">
                      {order.orderId}
                    </td>
                    <td className="py-3 px-4 text-white">
                      {order.tradingSymbol || order.securityId}
                    </td>
                    <td className="py-3 px-4 text-white">
                      {order.transactionType}
                    </td>
                    <td className="py-3 px-4 text-white">{order.quantity}</td>
                    <td className="py-3 px-4 text-white">
                      ₹{order.price?.toFixed(2) || "0.00"}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          order.orderStatus === "COMPLETE"
                            ? "bg-green-500/20 text-green-400"
                            : order.orderStatus === "CANCELLED"
                            ? "bg-red-500/20 text-red-400"
                            : "bg-yellow-500/20 text-yellow-400"
                        }`}
                      >
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
  );
}

export default TradingDashboard;
