import { motion } from "framer-motion";
import {
  Activity,
  CheckCircle,
  XCircle,
  Clock,
  ChevronRight,
  Loader,
} from "lucide-react";

function ExecutionFlowSidebar({ executionSteps, showSidebar, onToggle }) {
  if (!showSidebar) {
    return (
      <div className="w-12 border-r border-zinc-800 bg-zinc-900/80 flex flex-col items-center py-3">
        <button
          onClick={onToggle}
          className="text-zinc-500 hover:text-zinc-300 transition-colors"
          title="Show execution flow"
        >
          <Activity className="w-5 h-5" />
        </button>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ width: 0, opacity: 0 }}
      animate={{ width: 280, opacity: 1 }}
      exit={{ width: 0, opacity: 0 }}
      className="w-[280px] border-r border-zinc-800 bg-zinc-900/90 flex flex-col"
    >
      <div className="p-3 border-b border-zinc-800 bg-zinc-900">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold text-zinc-300 flex items-center gap-2">
            <Activity className="w-4 h-4 text-green-500" />
            Execution Flow
          </h3>
          <button
            onClick={onToggle}
            className="text-zinc-500 hover:text-zinc-300 transition-colors"
            title="Hide execution flow"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-3">
        {executionSteps.length === 0 ? (
          <div className="text-center text-zinc-500 text-xs mt-8">
            <Activity className="w-8 h-8 mx-auto mb-2 text-zinc-600" />
            <p>Waiting for execution...</p>
            <p className="text-[10px] text-zinc-600 mt-2">
              Steps will appear here as the agent processes your request
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {executionSteps.map((step, index) => (
              <motion.div
                key={step.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className={`p-3 rounded-lg border text-xs ${
                  step.status === "completed"
                    ? "bg-green-500/10 border-green-500/30"
                    : step.status === "error"
                    ? "bg-red-500/10 border-red-500/30"
                    : step.status === "active"
                    ? "bg-yellow-500/10 border-yellow-500/30 animate-pulse"
                    : "bg-zinc-800/50 border-zinc-700"
                }`}
              >
                <div className="flex items-start gap-2">
                  <div className="mt-0.5 flex-shrink-0">
                    {step.status === "completed" && (
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    )}
                    {step.status === "error" && (
                      <XCircle className="w-4 h-4 text-red-500" />
                    )}
                    {step.status === "active" && (
                      <Loader className="w-4 h-4 text-yellow-500 animate-spin" />
                    )}
                    {step.status === "pending" && (
                      <Clock className="w-4 h-4 text-zinc-500" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-zinc-200 mb-1 text-[11px]">
                      {step.title}
                    </div>
                    <div className="text-zinc-400 text-[10px] mb-2 leading-relaxed">
                      {step.description}
                    </div>
                    {step.type === "tool" && step.args && Object.keys(step.args).length > 0 && (
                      <details className="mt-2">
                        <summary className="text-zinc-500 hover:text-zinc-300 cursor-pointer text-[10px] font-medium">
                          View Parameters
                        </summary>
                        <pre className="mt-2 text-[9px] text-zinc-400 overflow-x-auto bg-zinc-950/50 p-2 rounded border border-zinc-700">
                          {JSON.stringify(step.args, null, 2)}
                        </pre>
                      </details>
                    )}
                    {step.result && step.status !== "active" && (
                      <div className={`mt-2 text-[10px] p-2 rounded ${
                        step.status === "error"
                          ? "text-red-300 bg-red-500/10"
                          : "text-green-300 bg-green-500/10"
                      }`}>
                        <div className="font-medium mb-1">
                          {step.status === "error" ? "Error:" : "Result:"}
                        </div>
                        {step.result}
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}

export default ExecutionFlowSidebar;

