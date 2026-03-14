import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom'
import PortfolioOverview from './components/PortfolioOverview'
import QuestionDetail from './components/QuestionDetail'
import PerformanceView from './components/PerformanceView'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-900 text-gray-100">
        {/* Header */}
        <header className="bg-gray-800 border-b border-gray-700">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center">
                <h1 className="text-xl font-bold text-white">
                  Macro Reasoning Agent
                </h1>
                <span className="ml-2 text-xs text-gray-500 bg-gray-900 px-2 py-1 rounded">
                  v0.2
                </span>
              </div>
              <nav className="flex space-x-4">
                <NavLink 
                  to="/" 
                  className={({ isActive }) => 
                    isActive ? 'nav-link active' : 'nav-link'
                  }
                  end
                >
                  Portfolio
                </NavLink>
                <NavLink 
                  to="/performance" 
                  className={({ isActive }) => 
                    isActive ? 'nav-link active' : 'nav-link'
                  }
                >
                  Performance
                </NavLink>
              </nav>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            <Route path="/" element={<PortfolioOverview />} />
            <Route path="/question/:id" element={<QuestionDetail />} />
            <Route path="/performance" element={<PerformanceView />} />
          </Routes>
        </main>

        {/* Footer */}
        <footer className="bg-gray-800 border-t border-gray-700 mt-auto">
          <div className="max-w-7xl mx-auto px-4 py-4 text-center text-sm text-gray-500">
            Macro Reasoning Agent v0.2 • Polymarket-Integrated Geopolitical Forecasting
          </div>
        </footer>
      </div>
    </Router>
  )
}

export default App
