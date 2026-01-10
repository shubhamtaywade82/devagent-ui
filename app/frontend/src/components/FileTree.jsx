import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { File, Folder, Plus, Trash2, ChevronRight, ChevronDown } from 'lucide-react'

function FileTree({ files, selectedFile, onFileSelect, onCreateFile, onDeleteFile, projectId }) {
  const [expandedFolders, setExpandedFolders] = useState({})
  const [showNewFileInput, setShowNewFileInput] = useState(false)
  const [newFilePath, setNewFilePath] = useState('')

  const organizeFiles = (files) => {
    const tree = {}
    files.forEach(file => {
      const parts = file.path.split('/')
      let current = tree

      for (let i = 0; i < parts.length - 1; i++) {
        const part = parts[i]
        if (!current[part]) {
          current[part] = { type: 'folder', children: {} }
        }
        current = current[part].children
      }

      const fileName = parts[parts.length - 1]
      current[fileName] = { type: 'file', ...file }
    })
    return tree
  }

  const handleCreateFile = () => {
    if (newFilePath.trim()) {
      onCreateFile(newFilePath.trim())
      setNewFilePath('')
      setShowNewFileInput(false)
    }
  }

  const renderTree = (tree, path = '', level = 0) => {
    const items = []

    Object.entries(tree).sort(([a], [b]) => {
      const aIsFolder = tree[a].type === 'folder'
      const bIsFolder = tree[b].type === 'folder'
      if (aIsFolder && !bIsFolder) return -1
      if (!aIsFolder && bIsFolder) return 1
      return a.localeCompare(b)
    }).forEach(([name, item]) => {
      const fullPath = path ? `${path}/${name}` : name
      const isExpanded = expandedFolders[fullPath]

      if (item.type === 'folder') {
        items.push(
          <div key={fullPath}>
            <div
              className="flex items-center gap-2 px-2 py-1.5 hover:bg-zinc-800 cursor-pointer rounded text-sm"
              style={{ paddingLeft: `${level * 12 + 8}px` }}
              onClick={() => setExpandedFolders({
                ...expandedFolders,
                [fullPath]: !isExpanded
              })}
            >
              {isExpanded ? (
                <ChevronDown className="w-4 h-4 text-zinc-400" />
              ) : (
                <ChevronRight className="w-4 h-4 text-zinc-400" />
              )}
              <Folder className="w-4 h-4 text-blue-500" />
              <span className="text-zinc-300">{name}</span>
            </div>
            {isExpanded && (
              <div>
                {renderTree(item.children, fullPath, level + 1)}
              </div>
            )}
          </div>
        )
      } else {
        items.push(
          <div
            key={fullPath}
            className={`flex items-center gap-2 px-2 py-1.5 hover:bg-zinc-800 cursor-pointer rounded text-sm group ${
              selectedFile?.path === fullPath ? 'bg-violet-500/20 border-l-2 border-violet-500' : ''
            }`}
            style={{ paddingLeft: `${level * 12 + 8}px` }}
            onClick={() => onFileSelect(item)}
          >
            <File className="w-4 h-4 text-zinc-400" />
            <span className="text-zinc-300 flex-1">{name}</span>
            <button
              onClick={(e) => {
                e.stopPropagation()
                onDeleteFile(fullPath)
              }}
              className="opacity-0 group-hover:opacity-100 p-1 hover:bg-zinc-700 rounded transition-opacity"
            >
              <Trash2 className="w-3 h-3 text-red-400" />
            </button>
          </div>
        )
      }
    })

    return items
  }

  const tree = organizeFiles(files)

  return (
    <div className="h-full flex flex-col bg-zinc-900/50">
      <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-zinc-300">Files</h2>
        <button
          onClick={() => setShowNewFileInput(true)}
          className="p-1.5 hover:bg-zinc-800 rounded transition-colors"
          title="New File"
        >
          <Plus className="w-4 h-4 text-zinc-400" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        <AnimatePresence>
          {showNewFileInput && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mb-2 p-2 bg-zinc-800 rounded"
            >
              <input
                type="text"
                value={newFilePath}
                onChange={(e) => setNewFilePath(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleCreateFile()
                  } else if (e.key === 'Escape') {
                    setShowNewFileInput(false)
                    setNewFilePath('')
                  }
                }}
                placeholder="path/to/file.js"
                className="w-full px-2 py-1 bg-zinc-900 border border-zinc-700 rounded text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
                autoFocus
              />
              <div className="flex gap-2 mt-2">
                <button
                  onClick={handleCreateFile}
                  className="px-2 py-1 bg-violet-600 hover:bg-violet-500 rounded text-xs font-medium"
                >
                  Create
                </button>
                <button
                  onClick={() => {
                    setShowNewFileInput(false)
                    setNewFilePath('')
                  }}
                  className="px-2 py-1 bg-zinc-700 hover:bg-zinc-600 rounded text-xs font-medium"
                >
                  Cancel
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {Object.keys(tree).length === 0 ? (
          <div className="text-center text-zinc-500 text-sm mt-8">
            No files yet. Click + to create one.
          </div>
        ) : (
          renderTree(tree)
        )}
      </div>
    </div>
  )
}

export default FileTree

