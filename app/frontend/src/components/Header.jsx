import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Home, Sparkles } from 'lucide-react'
import UIGenerator from './UIGenerator'

function Header({ project }) {
  const [showUIGenerator, setShowUIGenerator] = useState(false)
  const navigate = useNavigate()

  return (
    <>
      <div className="h-14 border-b border-zinc-800 bg-zinc-900/80 backdrop-blur-sm flex items-center justify-between px-6">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="p-2 hover:bg-zinc-800 rounded-lg transition-colors"
            title="Home"
          >
            <Home className="w-5 h-5 text-zinc-400" />
          </button>
          <div className="h-6 w-px bg-zinc-800" />
          <h1 className="text-lg font-semibold font-manrope text-white">
            {project?.name || 'Untitled Project'}
          </h1>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowUIGenerator(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 rounded-lg font-medium transition-all"
          >
            <Sparkles className="w-4 h-4" />
            UI Generator
          </button>
        </div>
      </div>

      {showUIGenerator && (
        <UIGenerator
          onClose={() => setShowUIGenerator(false)}
        />
      )}
    </>
  )
}

export default Header

