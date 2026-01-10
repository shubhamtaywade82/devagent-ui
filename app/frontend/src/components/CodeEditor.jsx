import { useEffect } from 'react'
import Editor from '@monaco-editor/react'
import { Save } from 'lucide-react'
import { motion } from 'framer-motion'

function CodeEditor({ file, content, onChange, onSave }) {
  const getLanguageFromPath = (path) => {
    if (!path) return 'plaintext'
    const ext = path.split('.').pop().toLowerCase()
    const languageMap = {
      'js': 'javascript',
      'jsx': 'javascript',
      'ts': 'typescript',
      'tsx': 'typescript',
      'py': 'python',
      'java': 'java',
      'cpp': 'cpp',
      'c': 'c',
      'cs': 'csharp',
      'go': 'go',
      'rs': 'rust',
      'php': 'php',
      'rb': 'ruby',
      'swift': 'swift',
      'kt': 'kotlin',
      'scala': 'scala',
      'sh': 'shell',
      'bash': 'shell',
      'zsh': 'shell',
      'yaml': 'yaml',
      'yml': 'yaml',
      'json': 'json',
      'xml': 'xml',
      'html': 'html',
      'css': 'css',
      'scss': 'scss',
      'sass': 'sass',
      'less': 'less',
      'md': 'markdown',
      'sql': 'sql',
      'dockerfile': 'dockerfile',
      'makefile': 'makefile',
    }
    return languageMap[ext] || 'plaintext'
  }

  if (!file) {
    return (
      <div className="h-full flex items-center justify-center bg-zinc-950">
        <div className="text-center text-zinc-500">
          <p className="text-lg mb-2">No file selected</p>
          <p className="text-sm">Select a file from the file tree to start editing</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-zinc-950">
      {/* Editor Header */}
      <div className="h-10 border-b border-zinc-800 bg-zinc-900/80 flex items-center justify-between px-4">
        <div className="flex items-center gap-2">
          <span className="text-sm text-zinc-400 font-mono">{file.path}</span>
        </div>
        <button
          onClick={onSave}
          className="flex items-center gap-2 px-3 py-1.5 bg-violet-600 hover:bg-violet-500 rounded text-sm font-medium transition-colors"
        >
          <Save className="w-4 h-4" />
          Save
        </button>
      </div>

      {/* Monaco Editor */}
      <div className="flex-1">
        <Editor
          height="100%"
          language={getLanguageFromPath(file.path)}
          value={content}
          onChange={onChange}
          theme="vs-dark"
          options={{
            fontSize: 14,
            minimap: { enabled: true },
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            automaticLayout: true,
            tabSize: 2,
            insertSpaces: true,
            formatOnPaste: true,
            formatOnType: true,
            lineNumbers: 'on',
            renderLineHighlight: 'all',
            cursorBlinking: 'smooth',
            cursorSmoothCaretAnimation: 'on',
          }}
        />
      </div>
    </div>
  )
}

export default CodeEditor

