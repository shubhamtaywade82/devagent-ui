import { useState } from "react";
import { motion } from "framer-motion";
import { LogIn, Key, Lock } from "lucide-react";
import api from "../../services/api";

function TradingAuth({ onAuthSuccess }) {
  const [method, setMethod] = useState("token"); // 'token', 'pin', or 'oauth'
  const [accessToken, setAccessToken] = useState("");
  const [pin, setPin] = useState("");
  const [totp, setTotp] = useState("");
  const [tokenId, setTokenId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [oauthUrl, setOauthUrl] = useState("");

  const handleTokenAuth = async (e) => {
    e.preventDefault();
    if (!accessToken) {
      setError("Access token is required");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const response = await api.tradingAuthToken({ token_id: accessToken });
      if (response.success && response.access_token) {
        onAuthSuccess(response.access_token);
      } else {
        setError(response.error || "Token validation failed");
      }
    } catch (err) {
      setError(err.message || "Token validation failed");
    } finally {
      setLoading(false);
    }
  };

  const handlePinAuth = async (e) => {
    e.preventDefault();
    if (!pin || !totp) {
      setError("PIN and TOTP are required");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const response = await api.tradingAuthPin({ pin, totp });
      if (response.success && response.access_token) {
        onAuthSuccess(response.access_token);
      } else {
        setError(response.error || "Authentication failed");
      }
    } catch (err) {
      setError(err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  const handleOAuthInit = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.tradingAuthOAuth();
      if (response.success && response.login_url) {
        setOauthUrl(response.login_url);
        window.open(response.login_url, "_blank");
      } else {
        setError(response.error || "OAuth initialization failed");
      }
    } catch (err) {
      setError(err.message || "OAuth initialization failed");
    } finally {
      setLoading(false);
    }
  };

  const handleOAuthConsume = async (e) => {
    e.preventDefault();
    if (!tokenId) {
      setError("Token ID is required");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const response = await api.tradingAuthConsume({ token_id: tokenId });
      if (response.success && response.access_token) {
        onAuthSuccess(response.access_token);
      } else {
        setError(response.error || "Token consumption failed");
      }
    } catch (err) {
      setError(err.message || "Token consumption failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-md glass rounded-xl p-8"
    >
      <div className="text-center mb-6">
        <LogIn className="w-12 h-12 text-green-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold font-manrope mb-2">
          Dhan Trading Login
        </h2>
        <p className="text-zinc-400 text-sm">Connect to your Dhan account</p>
      </div>

      {/* Method Toggle */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setMethod("token")}
          className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            method === "token"
              ? "bg-green-600 text-white"
              : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
          }`}
        >
          Access Token
        </button>
        <button
          onClick={() => setMethod("pin")}
          className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            method === "pin"
              ? "bg-green-600 text-white"
              : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
          }`}
        >
          PIN & TOTP
        </button>
        <button
          onClick={() => setMethod("oauth")}
          className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            method === "oauth"
              ? "bg-green-600 text-white"
              : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
          }`}
        >
          OAuth
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Access Token Method */}
      {method === "token" && (
        <form onSubmit={handleTokenAuth} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2 text-zinc-300 flex items-center gap-2">
              <Key className="w-4 h-4" />
              Access Token
            </label>
            <input
              type="password"
              value={accessToken}
              onChange={(e) => setAccessToken(e.target.value)}
              placeholder="Paste your DhanHQ access token"
              className="w-full px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-white placeholder-zinc-500"
              required
            />
            <p className="text-xs text-zinc-500 mt-2">
              Enter your DhanHQ access token directly. You can get this from
              DhanHQ API or generate it using PIN/TOTP.
            </p>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Validating..." : "Login with Token"}
          </button>
        </form>
      )}

      {/* PIN & TOTP Method */}
      {method === "pin" && (
        <form onSubmit={handlePinAuth} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2 text-zinc-300 flex items-center gap-2">
              <Key className="w-4 h-4" />
              PIN
            </label>
            <input
              type="password"
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              placeholder="Enter your PIN"
              className="w-full px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-white placeholder-zinc-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2 text-zinc-300 flex items-center gap-2">
              <Lock className="w-4 h-4" />
              TOTP
            </label>
            <input
              type="text"
              value={totp}
              onChange={(e) => setTotp(e.target.value)}
              placeholder="Enter TOTP from authenticator"
              className="w-full px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-white placeholder-zinc-500"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Authenticating..." : "Login"}
          </button>
        </form>
      )}

      {/* OAuth Method */}
      {method === "oauth" && (
        <div className="space-y-4">
          {!oauthUrl ? (
            <button
              onClick={handleOAuthInit}
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Initializing..." : "Open Login Page"}
            </button>
          ) : (
            <form onSubmit={handleOAuthConsume} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2 text-zinc-300">
                  Token ID (from redirect URL)
                </label>
                <input
                  type="text"
                  value={tokenId}
                  onChange={(e) => setTokenId(e.target.value)}
                  placeholder="Paste token_id from redirect URL"
                  className="w-full px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-white placeholder-zinc-500"
                  required
                />
                <p className="text-xs text-zinc-500 mt-2">
                  After logging in, copy the token_id from the redirect URL
                </p>
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? "Processing..." : "Complete Login"}
              </button>
            </form>
          )}
        </div>
      )}
    </motion.div>
  );
}

export default TradingAuth;
