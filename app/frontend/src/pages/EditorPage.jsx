import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import FileTree from '../components/FileTree'
import CodeEditor from '../components/CodeEditor'
import ChatSidebar from '../components/ChatSidebar'
import Header from '../components/Header'
import api from '../services/api'

function EditorPage() {
  const { projectId } = useParams()
  const [project, setProject] = useState(null)
  const [files, setFiles] = useState([])
  const [selectedFile, setSelectedFile] = useState(null)
  const [fileContent, setFileContent] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadProject()
    loadFiles()
  }, [projectId])

  const loadProject = async () => {
    try {
      const data = await api.getProject(projectId)
      setProject(data)
    } catch (error) {
      console.error('Failed to load project:', error)
    }
  }

  const loadFiles = async () => {
    try {
      const data = await api.getFiles(projectId)
      setFiles(data)
      setLoading(false)
    } catch (error) {
      console.error('Failed to load files:', error)
      setLoading(false)
    }
  }

  const handleFileSelect = async (file) => {
    setSelectedFile(file)
    setFileContent(file.content || '')
  }

  const handleSaveFile = async () => {
    if (!selectedFile) return

    try {
      await api.saveFile({
        project_id: projectId,
        path: selectedFile.path,
        content: fileContent
      })
      // Reload files to get updated content
      loadFiles()
      alert('File saved successfully!')
    } catch (error) {
      console.error('Failed to save file:', error)
      alert('Failed to save file. Please try again.')
    }
  }

  const handleCreateFile = async (path) => {
    try {
      await api.saveFile({
        project_id: projectId,
        path: path,
        content: ''
      })
      loadFiles()
      // Select the newly created file
      const newFile = { path, content: '' }
      handleFileSelect(newFile)
    } catch (error) {
      console.error('Failed to create file:', error)
      alert('Failed to create file. Please try again.')
    }
  }

  const handleDeleteFile = async (path) => {
    if (!confirm(`Delete ${path}?`)) return

    try {
      await api.deleteFile(projectId, path)
      if (selectedFile && selectedFile.path === path) {
        setSelectedFile(null)
        setFileContent('')
      }
      loadFiles()
    } catch (error) {
      console.error('Failed to delete file:', error)
      alert('Failed to delete file. Please try again.')
    }
  }

  if (loading) {
    return (
      <div className="h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-zinc-400">Loading project...</div>
      </div>
    )
  }

  return (
    <div className="h-screen bg-zinc-950 flex flex-col overflow-hidden">
      <Header project={project} />

      <div className="flex-1 flex overflow-hidden">
        {/* File Tree */}
        <motion.div
          initial={{ x: -300 }}
          animate={{ x: 0 }}
          className="w-64 border-r border-zinc-800 bg-zinc-900/50"
        >
          <FileTree
            files={files}
            selectedFile={selectedFile}
            onFileSelect={handleFileSelect}
            onCreateFile={handleCreateFile}
            onDeleteFile={handleDeleteFile}
            projectId={projectId}
          />
        </motion.div>

        {/* Code Editor */}
        <div className="flex-1 flex flex-col">
          <CodeEditor
            file={selectedFile}
            content={fileContent}
            onChange={setFileContent}
            onSave={handleSaveFile}
          />
        </div>

        {/* Chat Sidebar */}
        <motion.div
          initial={{ x: 400 }}
          animate={{ x: 0 }}
          className="w-80 border-l border-zinc-800 bg-zinc-900/50"
        >
          <ChatSidebar projectId={projectId} files={files} />
        </motion.div>
      </div>
    </div>
  )
}

export default EditorPage

