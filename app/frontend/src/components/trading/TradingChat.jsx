import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send,
  Bot,
  User,
  Loader,
  TrendingUp,
  MessageSquare,
} from "lucide-react";

function TradingChat({ accessToken }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const messagesEndRef = useRef(null);
  const abortControllerRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    if (!accessToken) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "⚠️ Please authenticate first to use the trading assistant.",
        },
      ]);
      return;
    }

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);
    setStreaming(true);

    try {
      // Use streaming endpoint with access_token for trading tools
      const response = await fetch(
        `${
          import.meta.env.VITE_BACKEND_URL || "http://localhost:8001"
        }/api/chat/stream`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: userMessage,
            access_token: accessToken, // Pass access token for trading tools
            task: "trading", // Optional: route to trading-specialized model if using Ollama Router
          }),
        }
      );

      if (!response.ok) {
        // Try to get error message from response
        let errorMessage = "Failed to get response";
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch (e) {
          errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantMessage = "";
      let hasError = false;

      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.substring(6));
              const content = data.content || "";

              // If it's an error, replace the message content
              if (data.error) {
                hasError = true;
                const errorMsg =
                  content ||
                  "An error occurred. Please check if Ollama is running or if the API is configured correctly.";
                setMessages((prev) => {
                  const newMessages = [...prev];
                  newMessages[newMessages.length - 1].content = errorMsg;
                  return newMessages;
                });
                break;
              }

              assistantMessage += content;
              setMessages((prev) => {
                const newMessages = [...prev];
                newMessages[newMessages.length - 1].content = assistantMessage;
                return newMessages;
              });
              // Stop if we get a done flag
              if (data.done) {
                break;
              }
            } catch (e) {
              // Ignore parse errors
              console.warn("Failed to parse chat response line:", line, e);
            }
          }
        }
      }

      // If we got an empty response and no error was set, show a helpful message
      if (!hasError && !assistantMessage.trim()) {
        setMessages((prev) => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1].content =
            "⚠️ No response received. Please check if Ollama is running or if the API is configured correctly.";
          return newMessages;
        });
      }
    } catch (error) {
      console.error("Chat error:", error);
      let errorMessage = "❌ Failed to get response. Please try again.";

      if (error.message) {
        if (
          error.message.includes("Ollama") ||
          error.message.includes("ollama")
        ) {
          errorMessage =
            "⚠️ Ollama is not running. Please start Ollama: `ollama serve`";
        } else if (error.message.includes("HTTP")) {
          errorMessage = `⚠️ ${error.message}. Please check your backend configuration.`;
        } else if (
          error.message.includes("Failed to fetch") ||
          error.message.includes("NetworkError")
        ) {
          errorMessage =
            "⚠️ Cannot connect to backend. Please check if the backend server is running.";
        } else {
          errorMessage = `⚠️ Error: ${error.message}`;
        }
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: errorMessage,
        },
      ]);
    } finally {
      setLoading(false);
      setStreaming(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleQuickQuestion = (question) => {
    setInput(question);
    // Auto-send after a brief delay
    setTimeout(() => {
      handleSend();
    }, 100);
  };

  const quickQuestions = [
    "What are my current positions?",
    "Show me my portfolio P&L",
    "What's the current price of NIFTY?",
    "Analyze HDFC Bank stock",
  ];

  return (
    <div className="h-full flex flex-col bg-zinc-900/50">
      <div className="p-4 border-b border-zinc-800">
        <h2 className="text-sm font-semibold text-zinc-300 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-green-500" />
          Trading Assistant
        </h2>
        <p className="text-xs text-zinc-500 mt-1">
          Ask about markets, positions, or get trading insights
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-zinc-500 text-sm mt-8">
            <Bot className="w-12 h-12 mx-auto mb-4 text-zinc-600" />
            <p className="font-medium mb-2">Trading AI Assistant</p>
            <p className="text-xs mb-4">
              I can help you with market analysis, portfolio insights, and
              trading strategies.
            </p>

            {/* Quick Questions */}
            <div className="mt-6 space-y-2">
              <p className="text-xs text-zinc-600 mb-2">Try asking:</p>
              {quickQuestions.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => handleQuickQuestion(q)}
                  className="block w-full text-left px-3 py-2 text-xs bg-zinc-800 hover:bg-zinc-700 rounded-lg text-zinc-400 hover:text-zinc-300 transition-colors"
                >
                  <MessageSquare className="w-3 h-3 inline mr-2" />
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        <AnimatePresence>
          {messages.map((message, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex gap-3 ${
                message.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              {message.role === "assistant" && (
                <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-4 h-4 text-green-500" />
                </div>
              )}
              <div
                className={`max-w-[85%] rounded-lg px-4 py-2 ${
                  message.role === "user"
                    ? "bg-green-600 text-white"
                    : "bg-zinc-800 text-zinc-200"
                }`}
              >
                <div className="text-sm whitespace-pre-wrap break-words">
                  {message.content ||
                    (loading && index === messages.length - 1 ? (
                      <div className="flex items-center gap-2">
                        <Loader className="w-4 h-4 animate-spin" />
                        <span>Analyzing...</span>
                      </div>
                    ) : (
                      ""
                    ))}
                </div>
              </div>
              {message.role === "user" && (
                <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0">
                  <User className="w-4 h-4 text-blue-500" />
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 border-t border-zinc-800">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={
              accessToken
                ? "Ask about markets, positions, or analysis..."
                : "Please authenticate first..."
            }
            rows="2"
            className="flex-1 px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-white placeholder-zinc-500 resize-none text-sm"
            disabled={loading || !accessToken}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim() || !accessToken}
            className="px-4 py-2 bg-green-600 hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
          >
            {loading ? (
              <Loader className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
        {!accessToken && (
          <p className="text-xs text-zinc-500 mt-2">
            ⚠️ Authentication required to use trading features
          </p>
        )}
      </div>
    </div>
  );
}

export default TradingChat;
