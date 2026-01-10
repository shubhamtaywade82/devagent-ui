import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  TrendingUp,
  Wallet,
  BarChart3,
  ShoppingCart,
  LogIn,
} from "lucide-react";
import TradingDashboard from "../components/trading/TradingDashboard";
import OrderPlacement from "../components/trading/OrderPlacement";
import PortfolioView from "../components/trading/PortfolioView";
import MarketData from "../components/trading/MarketData";
import TradingAuth from "../components/trading/TradingAuth";
import LiveOrderUpdates from "../components/trading/LiveOrderUpdates";
import IndexIndicators from "../components/trading/IndexIndicators";
import api from "../services/api";

function TradingPage() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [accessToken, setAccessToken] = useState(null);
  const [userProfile, setUserProfile] = useState(null);

  useEffect(() => {
    // Check if access token exists in localStorage
    const token = localStorage.getItem("dhan_access_token");
    if (token) {
      setAccessToken(token);
      setIsAuthenticated(true);
      loadUserProfile(token);
    }
  }, []);

  const loadUserProfile = async (token) => {
    try {
      const response = await api.getTradingProfile({ token_id: token });
      if (response.success) {
        setUserProfile(response.data);
      }
    } catch (error) {
      console.error("Failed to load profile:", error);
    }
  };

  const handleAuthSuccess = (token) => {
    localStorage.setItem("dhan_access_token", token);
    setAccessToken(token);
    setIsAuthenticated(true);
    loadUserProfile(token);
  };

  const handleLogout = () => {
    localStorage.removeItem("dhan_access_token");
    setAccessToken(null);
    setIsAuthenticated(false);
    setUserProfile(null);
  };

  if (!isAuthenticated) {
    return (
      <div className="h-screen bg-zinc-950 flex items-center justify-center">
        <TradingAuth onAuthSuccess={handleAuthSuccess} />
      </div>
    );
  }

  return (
    <div className="h-screen bg-zinc-950 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="h-14 border-b border-zinc-800 bg-zinc-900/80 backdrop-blur-sm flex items-center justify-between px-6 z-10">
        <div className="flex items-center gap-4">
          <TrendingUp className="w-6 h-6 text-green-500" />
          <h1 className="text-lg font-semibold font-manrope text-white">
            Trading Dashboard
          </h1>
          {userProfile && (
            <span className="text-sm text-zinc-400">
              {userProfile.name || userProfile.clientId}
            </span>
          )}
        </div>
        <button
          onClick={handleLogout}
          className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm font-medium transition-colors"
        >
          Logout
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-zinc-800 bg-zinc-900/50">
        <button
          onClick={() => setActiveTab("dashboard")}
          className={`px-6 py-3 text-sm font-medium transition-colors ${
            activeTab === "dashboard"
              ? "border-b-2 border-green-500 text-green-400"
              : "text-zinc-400 hover:text-zinc-300"
          }`}
        >
          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4" />
            Dashboard
          </div>
        </button>
        <button
          onClick={() => setActiveTab("orders")}
          className={`px-6 py-3 text-sm font-medium transition-colors ${
            activeTab === "orders"
              ? "border-b-2 border-green-500 text-green-400"
              : "text-zinc-400 hover:text-zinc-300"
          }`}
        >
          <div className="flex items-center gap-2">
            <ShoppingCart className="w-4 h-4" />
            Place Order
          </div>
        </button>
        <button
          onClick={() => setActiveTab("portfolio")}
          className={`px-6 py-3 text-sm font-medium transition-colors ${
            activeTab === "portfolio"
              ? "border-b-2 border-green-500 text-green-400"
              : "text-zinc-400 hover:text-zinc-300"
          }`}
        >
          <div className="flex items-center gap-2">
            <Wallet className="w-4 h-4" />
            Portfolio
          </div>
        </button>
        <button
          onClick={() => setActiveTab("market")}
          className={`px-6 py-3 text-sm font-medium transition-colors ${
            activeTab === "market"
              ? "border-b-2 border-green-500 text-green-400"
              : "text-zinc-400 hover:text-zinc-300"
          }`}
        >
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            Market Data
          </div>
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {/* NIFTY and SENSEX - Always visible at top */}
        {isAuthenticated && accessToken && (
          <div className="border-b border-zinc-800 bg-zinc-900/50 p-4">
            <IndexIndicators accessToken={accessToken} />
          </div>
        )}

        <div className="flex-1 overflow-hidden flex">
          <div className="flex-1 overflow-hidden">
            {activeTab === "dashboard" && (
              <TradingDashboard accessToken={accessToken} />
            )}
            {activeTab === "orders" && (
              <OrderPlacement accessToken={accessToken} />
            )}
            {activeTab === "portfolio" && (
              <PortfolioView accessToken={accessToken} />
            )}
            {activeTab === "market" && <MarketData accessToken={accessToken} />}
          </div>

          {/* Live Order Updates Sidebar */}
          {isAuthenticated && (
            <div className="w-80 border-l border-zinc-800 overflow-y-auto">
              <LiveOrderUpdates accessToken={accessToken} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default TradingPage;
