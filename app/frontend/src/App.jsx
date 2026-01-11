import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import EditorPage from './pages/EditorPage'
import TradingPage from './pages/TradingPage'
import TradingAIPage from './pages/TradingAIPage'

function App() {
  return (
    <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/editor/:projectId" element={<EditorPage />} />
        <Route path="/trading" element={<TradingPage />} />
        <Route path="/trading/ai" element={<TradingAIPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  )
}

export default App

