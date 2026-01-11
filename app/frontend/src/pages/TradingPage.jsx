import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  TrendingUp,
  Wallet,
  BarChart3,
  ShoppingCart,
  LogIn,
  MessageSquare,
  X,
  ExternalLink,
} from "lucide-react";
import TradingDashboard from "../components/trading/TradingDashboard";
import OrderPlacement from "../components/trading/OrderPlacement";
import PortfolioView from "../components/trading/PortfolioView";
import MarketData from "../components/trading/MarketData";
import TradingAuth from "../components/trading/TradingAuth";
import LiveOrderUpdates from "../components/trading/LiveOrderUpdates";
import TradingChat from "../components/trading/TradingChat";
import IndexIndicators from "../components/trading/IndexIndicators";
import api from "../services/api";

function TradingPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("dashboard");
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [accessToken, setAccessToken] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [showChat, setShowChat] = useState(false);

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
      <div className="h-16 border-b border-zinc-800 bg-zinc-900/80 backdrop-blur-sm flex items-center justify-between px-6 z-10">
        <div className="flex items-center gap-6 flex-1">
          <div className="flex items-center gap-3">
            <TrendingUp className="w-6 h-6 text-green-500" />
            <h1 className="text-lg font-semibold font-manrope text-white">
              Trading Dashboard
            </h1>
          </div>
          {userProfile && (
            <span className="text-sm text-zinc-400 hidden md:block">
              {userProfile.name || userProfile.clientId}
            </span>
          )}
          {/* Market Indices - Compact */}
          {isAuthenticated && (
            <div className="flex-1 flex justify-center">
              <IndexIndicators accessToken={accessToken} />
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => window.open("/trading/ai", "_blank")}
            className="px-4 py-2 rounded-lg text-sm font-medium transition-colors bg-green-600 hover:bg-green-500 text-white"
            title="Open Trading AI Assistant in full page"
          >
            <MessageSquare className="w-4 h-4 inline mr-2" />
            AI Assistant
            <ExternalLink className="w-3 h-3 inline ml-2" />
          </button>
          <button
            onClick={() => setShowChat(!showChat)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              showChat
                ? "bg-zinc-700 hover:bg-zinc-600 text-white"
                : "bg-zinc-800 hover:bg-zinc-700 text-zinc-300"
            }`}
            title="Toggle AI Trading Assistant Sidebar"
          >
            <MessageSquare className="w-4 h-4 inline mr-2" />
            {showChat ? "Hide Sidebar" : "Chat Sidebar"}
          </button>
          <button
            onClick={handleLogout}
            className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm font-medium transition-colors"
          >
            Logout
          </button>
        </div>
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

        {/* Sidebars */}
        {isAuthenticated && (
          <>
            {/* Live Order Updates Sidebar */}
            <div className="w-80 border-l border-zinc-800 overflow-hidden flex flex-col">
              <LiveOrderUpdates accessToken={accessToken} />
            </div>

            {/* Trading Chat Sidebar - Collapsible */}
            {showChat && (
              <motion.div
                initial={{ width: 0, opacity: 0 }}
                animate={{ width: 400, opacity: 1 }}
                exit={{ width: 0, opacity: 0 }}
                className="border-l border-zinc-800 overflow-hidden flex flex-col"
                style={{ width: showChat ? "400px" : "0" }}
              >
                <TradingChat accessToken={accessToken} />
              </motion.div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default TradingPage;
