import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { TrendingUp, ArrowLeft, LogOut, Bot } from "lucide-react";
import TradingChat from "../components/trading/TradingChat";
import TradingAuth from "../components/trading/TradingAuth";
import api from "../services/api";

function TradingAIPage() {
  const navigate = useNavigate();
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
      <div className="h-16 border-b border-zinc-800 bg-zinc-900/80 backdrop-blur-sm flex items-center justify-between px-6 z-10">
        <div className="flex items-center gap-6 flex-1">
          <button
            onClick={() => navigate("/trading")}
            className="p-2 hover:bg-zinc-800 rounded-lg transition-colors"
            title="Back to Trading Dashboard"
          >
            <ArrowLeft className="w-5 h-5 text-zinc-400" />
          </button>
          <div className="h-6 w-px bg-zinc-800" />
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
              <Bot className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <h1 className="text-lg font-semibold font-manrope text-white">
                Trading AI Assistant
              </h1>
              <p className="text-xs text-zinc-500">
                Your intelligent trading companion
              </p>
            </div>
          </div>
          {userProfile && (
            <span className="text-sm text-zinc-400 hidden md:block ml-auto">
              {userProfile.name || userProfile.clientId}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate("/trading")}
            className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm font-medium transition-colors text-zinc-300"
          >
            Dashboard
          </button>
          <button
            onClick={handleLogout}
            className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm font-medium transition-colors text-zinc-300"
          >
            <LogOut className="w-4 h-4 inline mr-2" />
            Logout
          </button>
        </div>
      </div>

      {/* Chat Content - Full Page */}
      <div className="flex-1 overflow-hidden bg-zinc-950 p-4">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="h-full max-w-6xl mx-auto bg-zinc-900/50 border border-zinc-800 rounded-lg overflow-hidden"
        >
          <TradingChat accessToken={accessToken} />
        </motion.div>
      </div>
    </div>
  );
}

export default TradingAIPage;

