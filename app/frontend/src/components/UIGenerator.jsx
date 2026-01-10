import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Sparkles, Palette, Copy, Check, Loader } from 'lucide-react'
import api from '../services/api'

function UIGenerator({ onClose }) {
  const [activeTab, setActiveTab] = useState('component')
  const [componentDescription, setComponentDescription] = useState('')
  const [designDescription, setDesignDescription] = useState('')
  const [generatedComponent, setGeneratedComponent] = useState('')
  const [generatedDesign, setGeneratedDesign] = useState(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleGenerateComponent = async () => {
    if (!componentDescription.trim()) return

    setLoading(true)
    setGeneratedComponent('')
    try {
      const response = await api.generateComponent(componentDescription)
      setGeneratedComponent(response.component)
    } catch (error) {
      console.error('Failed to generate component:', error)
      setGeneratedComponent('❌ Failed to generate component. Make sure Ollama is running.')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateDesign = async () => {
    if (!designDescription.trim()) return

    setLoading(true)
    setGeneratedDesign(null)
    try {
      const response = await api.generateDesignSystem(designDescription)
      setGeneratedDesign(response.design_system)
    } catch (error) {
      console.error('Failed to generate design system:', error)
      setGeneratedDesign({ error: 'Failed to generate design system. Make sure Ollama is running.' })
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = (text) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
          className="w-full max-w-4xl h-[80vh] bg-zinc-900 rounded-xl border border-zinc-800 flex flex-col overflow-hidden"
        >
          {/* Header */}
          <div className="h-14 border-b border-zinc-800 flex items-center justify-between px-6">
            <div className="flex items-center gap-3">
              <Sparkles className="w-5 h-5 text-violet-500" />
              <h2 className="text-lg font-semibold font-manrope">UI Generator</h2>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-zinc-800 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-zinc-400" />
            </button>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-zinc-800">
            <button
              onClick={() => setActiveTab('component')}
              className={`flex-1 px-6 py-3 text-sm font-medium transition-colors ${
                activeTab === 'component'
                  ? 'border-b-2 border-violet-500 text-violet-400'
                  : 'text-zinc-400 hover:text-zinc-300'
              }`}
            >
              <div className="flex items-center justify-center gap-2">
                <Sparkles className="w-4 h-4" />
                Component Generator
              </div>
            </button>
            <button
              onClick={() => setActiveTab('design')}
              className={`flex-1 px-6 py-3 text-sm font-medium transition-colors ${
                activeTab === 'design'
                  ? 'border-b-2 border-violet-500 text-violet-400'
                  : 'text-zinc-400 hover:text-zinc-300'
              }`}
            >
              <div className="flex items-center justify-center gap-2">
                <Palette className="w-4 h-4" />
                Design System
              </div>
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-hidden flex">
            {/* Component Tab */}
            {activeTab === 'component' && (
              <div className="flex-1 flex flex-col">
                <div className="p-6 border-b border-zinc-800">
                  <label className="block text-sm font-medium mb-2 text-zinc-300">
                    Describe the component you want to generate
                  </label>
                  <textarea
                    value={componentDescription}
                    onChange={(e) => setComponentDescription(e.target.value)}
                    placeholder="e.g., A button component with hover effects and loading state"
                    rows="3"
                    className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500 text-white placeholder-zinc-500 resize-none"
                  />
                  <button
                    onClick={handleGenerateComponent}
                    disabled={loading || !componentDescription.trim()}
                    className="mt-4 px-6 py-2 bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? (
                      <span className="flex items-center gap-2">
                        <Loader className="w-4 h-4 animate-spin" />
                        Generating...
                      </span>
                    ) : (
                      'Generate Component'
                    )}
                  </button>
                </div>

                {generatedComponent && (
                  <div className="flex-1 overflow-y-auto p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-sm font-semibold text-zinc-300">Generated Component</h3>
                      <button
                        onClick={() => handleCopy(generatedComponent)}
                        className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 rounded text-sm transition-colors"
                      >
                        {copied ? (
                          <>
                            <Check className="w-4 h-4" />
                            Copied!
                          </>
                        ) : (
                          <>
                            <Copy className="w-4 h-4" />
                            Copy
                          </>
                        )}
                      </button>
                    </div>
                    <pre className="bg-zinc-950 p-4 rounded-lg border border-zinc-800 overflow-x-auto">
                      <code className="text-sm text-zinc-300 font-mono whitespace-pre-wrap">
                        {generatedComponent}
                      </code>
                    </pre>
                  </div>
                )}
              </div>
            )}

            {/* Design System Tab */}
            {activeTab === 'design' && (
              <div className="flex-1 flex flex-col">
                <div className="p-6 border-b border-zinc-800">
                  <label className="block text-sm font-medium mb-2 text-zinc-300">
                    Describe the design system you want
                  </label>
                  <textarea
                    value={designDescription}
                    onChange={(e) => setDesignDescription(e.target.value)}
                    placeholder="e.g., A modern dark theme with purple and blue accents, clean typography"
                    rows="3"
                    className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500 text-white placeholder-zinc-500 resize-none"
                  />
                  <button
                    onClick={handleGenerateDesign}
                    disabled={loading || !designDescription.trim()}
                    className="mt-4 px-6 py-2 bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? (
                      <span className="flex items-center gap-2">
                        <Loader className="w-4 h-4 animate-spin" />
                        Generating...
                      </span>
                    ) : (
                      'Generate Design System'
                    )}
                  </button>
                </div>

                {generatedDesign && (
                  <div className="flex-1 overflow-y-auto p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-sm font-semibold text-zinc-300">Generated Design System</h3>
                      {typeof generatedDesign === 'object' && !generatedDesign.error && (
                        <button
                          onClick={() => handleCopy(JSON.stringify(generatedDesign, null, 2))}
                          className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 rounded text-sm transition-colors"
                        >
                          {copied ? (
                            <>
                              <Check className="w-4 h-4" />
                              Copied!
                            </>
                          ) : (
                            <>
                              <Copy className="w-4 h-4" />
                              Copy JSON
                            </>
                          )}
                        </button>
                      )}
                    </div>
                    <pre className="bg-zinc-950 p-4 rounded-lg border border-zinc-800 overflow-x-auto">
                      <code className="text-sm text-zinc-300 font-mono whitespace-pre-wrap">
                        {typeof generatedDesign === 'object'
                          ? JSON.stringify(generatedDesign, null, 2)
                          : generatedDesign}
                      </code>
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

export default UIGenerator

