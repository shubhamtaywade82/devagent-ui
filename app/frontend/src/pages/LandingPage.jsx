import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Code2, Sparkles, FileCode, Zap } from 'lucide-react'
import api from '../services/api'

function LandingPage() {
  const [projectName, setProjectName] = useState('')
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleCreateProject = async (e) => {
    e.preventDefault()
    if (!projectName.trim()) return

    setLoading(true)
    try {
      const response = await api.createProject({
        name: projectName,
        description: description
      })
      navigate(`/editor/${response.id}`)
    } catch (error) {
      console.error('Failed to create project:', error)
      alert('Failed to create project. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-8">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-2xl"
      >
        {/* Header */}
        <div className="text-center mb-12">
          <motion.div
            initial={{ scale: 0.9 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2 }}
            className="inline-flex items-center gap-3 mb-6"
          >
            <Code2 className="w-12 h-12 text-violet-500" />
            <h1 className="text-5xl font-bold font-manrope bg-gradient-to-r from-violet-400 to-blue-400 bg-clip-text text-transparent">
              DevAgent
            </h1>
          </motion.div>
          <p className="text-zinc-400 text-lg">
            AI-Powered Development Editor
          </p>
        </div>

        {/* Features */}
        <div className="grid grid-cols-2 gap-4 mb-12">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
            className="glass rounded-lg p-4"
          >
            <Sparkles className="w-6 h-6 text-violet-500 mb-2" />
            <h3 className="font-semibold mb-1">AI Code Assistant</h3>
            <p className="text-sm text-zinc-400">Intelligent code suggestions</p>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4 }}
            className="glass rounded-lg p-4"
          >
            <FileCode className="w-6 h-6 text-blue-500 mb-2" />
            <h3 className="font-semibold mb-1">Component Generator</h3>
            <p className="text-sm text-zinc-400">Generate React components</p>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.5 }}
            className="glass rounded-lg p-4"
          >
            <Zap className="w-6 h-6 text-violet-500 mb-2" />
            <h3 className="font-semibold mb-1">Design System</h3>
            <p className="text-sm text-zinc-400">AI-powered design tools</p>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.6 }}
            className="glass rounded-lg p-4"
          >
            <Code2 className="w-6 h-6 text-blue-500 mb-2" />
            <h3 className="font-semibold mb-1">Smart Editor</h3>
            <p className="text-sm text-zinc-400">Monaco-powered editing</p>
          </motion.div>
        </div>

        {/* Create Project Form */}
        <motion.form
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          onSubmit={handleCreateProject}
          className="glass rounded-xl p-8"
        >
          <h2 className="text-2xl font-bold font-manrope mb-6">
            Create New Project
          </h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2 text-zinc-300">
                Project Name
              </label>
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="My Awesome Project"
                className="w-full px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500 text-white placeholder-zinc-500"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2 text-zinc-300">
                Description (Optional)
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe your project..."
                rows="3"
                className="w-full px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500 text-white placeholder-zinc-500 resize-none"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Creating...' : 'Create Project'}
            </button>
          </div>
        </motion.form>
      </motion.div>
    </div>
  )
}

export default LandingPage

