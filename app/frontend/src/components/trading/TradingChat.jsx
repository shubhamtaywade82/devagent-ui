import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send,
  Bot,
  User,
  Loader,
  TrendingUp,
  MessageSquare,
  Activity,
} from "lucide-react";
import ExecutionFlowSidebar from "./ExecutionFlowSidebar";

function TradingChat({ accessToken }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [currentToolCalls, setCurrentToolCalls] = useState([]);
  const [currentReasoning, setCurrentReasoning] = useState("");
  const [executionSteps, setExecutionSteps] = useState([]);
  const [showSidebar, setShowSidebar] = useState(true);
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
      let isFirstContentChunk = true;

      // Reset tool calls, reasoning, and execution steps for new message
      setCurrentToolCalls([]);
      setCurrentReasoning("");
      setExecutionSteps([]);

      setMessages((prev) => [...prev, { role: "assistant", content: "", toolCalls: [], reasoning: "" }]);

      // Add initial planning step
      setExecutionSteps([{
        id: Date.now(),
        type: "planning",
        status: "active",
        title: "Analyzing request",
        description: "Understanding your query and planning the approach...",
        timestamp: new Date().toISOString()
      }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.substring(6));

              // Handle different message types
              if (data.type === "tool_calls" && data.tool_calls) {
                setCurrentToolCalls(data.tool_calls);
                setMessages((prev) => {
                  const newMessages = [...prev];
                  newMessages[newMessages.length - 1].toolCalls = data.tool_calls;
                  return newMessages;
                });

                // Update execution steps with tool calls
                setExecutionSteps((prev) => {
                  const newSteps = [...prev];
                  // Mark planning as complete
                  const planningStep = newSteps.find(s => s.type === "planning");
                  if (planningStep) {
                    planningStep.status = "completed";
                  }

                  // Add tool execution steps
                  data.tool_calls.forEach((toolCall, index) => {
                    newSteps.push({
                      id: Date.now() + index,
                      type: "tool",
                      status: toolCall.status === "success" ? "completed" : toolCall.status === "error" ? "error" : "active",
                      title: `Executing: ${toolCall.tool}`,
                      description: toolCall.status === "success" ? "Tool executed successfully" : toolCall.status === "error" ? toolCall.result : "Running tool...",
                      tool: toolCall.tool,
                      args: toolCall.args,
                      result: toolCall.result,
                      timestamp: toolCall.timestamp || new Date().toISOString()
                    });
                  });

                  return newSteps;
                });
                continue;
              }

              if (data.type === "reasoning" && data.content) {
                setCurrentReasoning(data.content);
                setMessages((prev) => {
                  const newMessages = [...prev];
                  newMessages[newMessages.length - 1].reasoning = data.content;
                  return newMessages;
                });

                // Update execution steps with reasoning
                setExecutionSteps((prev) => {
                  const newSteps = [...prev];
                  newSteps.push({
                    id: Date.now(),
                    type: "reasoning",
                    status: "completed",
                    title: "Reasoning",
                    description: data.content,
                    timestamp: new Date().toISOString()
                  });
                  return newSteps;
                });
                continue;
              }

              // Handle content (either with type: "content" or just data.content)
              const content = (data.type === "content" || !data.type) ? (data.content || "") : "";

              // Skip if this is not a content message
              if (data.type && data.type !== "content" && data.type !== "tool_calls" && data.type !== "reasoning") {
                continue;
              }

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
                // Mark planning as completed even on error
                setExecutionSteps((prev) => {
                  return prev.map(step =>
                    step.type === "planning" && step.status === "active"
                      ? { ...step, status: "completed", description: "Analysis completed" }
                      : step
                  );
                });
                break;
              }

              // If we have content, mark planning as completed and add response step
              if (content.length > 0) {
                // Mark planning step as completed when first content arrives
                if (isFirstContentChunk) {
                  setExecutionSteps((prev) => {
                    const newSteps = prev.map(step =>
                      step.type === "planning" && step.status === "active"
                        ? { ...step, status: "completed", description: "Analysis completed" }
                        : step
                    );

                    // Add response generation step if it doesn't exist
                    const hasResponseStep = newSteps.some(s => s.type === "response");
                    if (!hasResponseStep) {
                      newSteps.push({
                        id: Date.now(),
                        type: "response",
                        status: "active",
                        title: "Generating response",
                        description: "Formulating the final answer...",
                        timestamp: new Date().toISOString()
                      });
                    }

                    return newSteps;
                  });
                  isFirstContentChunk = false;
                }
              }

              assistantMessage += content;
              setMessages((prev) => {
                const newMessages = [...prev];
                newMessages[newMessages.length - 1].content = assistantMessage;
                return newMessages;
              });

              // Stop if we get a done flag
              if (data.done) {
                // Mark all active steps as completed
                setExecutionSteps((prev) => {
                  return prev.map(step => {
                    if (step.status === "active") {
                      if (step.type === "response") {
                        return { ...step, status: "completed", description: "Response generated successfully" };
                      } else if (step.type === "planning") {
                        return { ...step, status: "completed", description: "Analysis completed" };
                      }
                    }
                    return step;
                  });
                });
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
        // Mark planning as completed even if no content
        setExecutionSteps((prev) => {
          return prev.map(step =>
            step.type === "planning" && step.status === "active"
              ? { ...step, status: "completed", description: "Analysis completed" }
              : step
          );
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
    <div className="h-full flex bg-zinc-900/50">
      {/* Left Sidebar - Execution Flow (Separate Component) */}
      <ExecutionFlowSidebar
        executionSteps={executionSteps}
        showSidebar={showSidebar}
        onToggle={() => setShowSidebar(!showSidebar)}
      />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-zinc-900/50">
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
            <div key={index} className="flex flex-col gap-2">
              <motion.div
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
                  {/* Show reasoning if available */}
                  {message.reasoning && (
                    <div className="mb-2 pb-2 border-b border-zinc-700">
                      <div className="text-xs text-zinc-400 flex items-center gap-1 mb-1">
                        <TrendingUp className="w-3 h-3" />
                        <span className="font-medium">Reasoning</span>
                      </div>
                      <div className="text-xs text-zinc-300">{message.reasoning}</div>
                    </div>
                  )}

                  {/* Show tool calls if available */}
                  {message.toolCalls && message.toolCalls.length > 0 && (
                    <div className="mb-2 pb-2 border-b border-zinc-700">
                      <div className="text-xs text-zinc-400 flex items-center gap-1 mb-2">
                        <MessageSquare className="w-3 h-3" />
                        <span className="font-medium">Tools Used ({message.toolCalls.length})</span>
                      </div>
                      <div className="space-y-2">
                        {message.toolCalls.map((toolCall, toolIndex) => (
                          <div
                            key={toolIndex}
                            className={`text-xs p-2 rounded border ${
                              toolCall.status === "success"
                                ? "bg-green-500/10 border-green-500/30 text-green-300"
                                : toolCall.status === "error"
                                ? "bg-red-500/10 border-red-500/30 text-red-300"
                                : "bg-yellow-500/10 border-yellow-500/30 text-yellow-300"
                            }`}
                          >
                            <div className="font-medium mb-1">
                              {toolCall.status === "success" && "✅ "}
                              {toolCall.status === "error" && "❌ "}
                              {toolCall.status === "executing" && "⏳ "}
                              {toolCall.tool}
                            </div>
                            {Object.keys(toolCall.args || {}).length > 0 && (
                              <div className="text-zinc-400 mt-1">
                                <details className="cursor-pointer">
                                  <summary className="text-zinc-500 hover:text-zinc-300">
                                    Parameters
                                  </summary>
                                  <pre className="mt-1 text-[10px] overflow-x-auto">
                                    {JSON.stringify(toolCall.args, null, 2)}
                                  </pre>
                                </details>
                              </div>
                            )}
                            {toolCall.result && (
                              <div className="text-zinc-400 mt-1 text-[10px]">
                                {toolCall.result}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Message content */}
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
            </div>
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
    </div>
  );
}

export default TradingChat;
