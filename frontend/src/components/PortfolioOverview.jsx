import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { fetchQuestions, fetchStats } from '../lib/api'
import { TrendingUp, TrendingDown, AlertTriangle, Activity } from 'lucide-react'

function QuestionCard({ question }) {
  const currentProb = question.current_probability
  const marketPrice = question.polymarket_price
  const divergence = question.divergence
  
  // Determine badge color based on delta (change from prior)
  // We don't have prior in this view, so we'll just show the probability
  
  return (
    <Link 
      to={`/question/${question.id}`}
      className="card card-hover block"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-semibold text-white truncate pr-4">
            {question.title}
          </h3>
          <div className="flex items-center gap-2 mt-2">
            <span className="text-xs text-gray-500 bg-gray-900 px-2 py-1 rounded">
              {question.category || 'Uncategorized'}
            </span>
            <span className={`text-xs px-2 py-1 rounded ${
              question.status === 'active' 
                ? 'bg-emerald-500/20 text-emerald-400' 
                : 'bg-gray-700 text-gray-400'
            }`}>
              {question.status}
            </span>
          </div>
        </div>
        
        <div className="text-right">
          <div className="text-2xl font-bold text-white">
            {currentProb !== null && currentProb !== undefined
              ? `${(currentProb * 100).toFixed(0)}%`
              : 'N/A'}
          </div>
          <div className="text-sm text-gray-500">
            Agent probability
          </div>
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-4 mt-4 pt-4 border-t border-gray-700">
        <div>
          <div className="text-xs text-gray-500 mb-1">Market Price</div>
          <div className="text-sm font-medium text-gray-300">
            {marketPrice !== null && marketPrice !== undefined
              ? `${(marketPrice * 100).toFixed(0)}%`
              : 'N/A'}
          </div>
        </div>
        
        <div>
          <div className="text-xs text-gray-500 mb-1">Divergence</div>
          <div className={`text-sm font-medium ${
            divergence !== null && divergence !== undefined
              ? divergence > 0
                ? 'text-emerald-400'
                : 'text-red-400'
              : 'text-gray-500'
          }`}>
            {divergence !== null && divergence !== undefined
              ? `${divergence > 0 ? '+' : ''}${(divergence * 100).toFixed(1)}%`
              : 'N/A'}
          </div>
        </div>
      </div>
      
      {/* Warnings */}
      {(Math.abs(divergence || 0) > 0.15) && (
        <div className="mt-3 flex items-center gap-2 text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded px-3 py-2">
          <AlertTriangle size={14} />
          Market knows more? Divergence &gt; 15%
        </div>
      )}
      
      {question.last_updated && (
        <div className="mt-3 text-xs text-gray-600">
          Last updated: {new Date(question.last_updated).toLocaleDateString()}
        </div>
      )}
    </Link>
  )
}

function LoadingCard() {
  return (
    <div className="card">
      <div className="animate-pulse">
        <div className="h-6 bg-gray-700 rounded w-3/4 mb-2"></div>
        <div className="h-4 bg-gray-700 rounded w-1/4 mb-4"></div>
        <div className="grid grid-cols-2 gap-4">
          <div className="h-10 bg-gray-700 rounded"></div>
          <div className="h-10 bg-gray-700 rounded"></div>
        </div>
      </div>
    </div>
  )
}

function StatsSummary({ stats }) {
  if (!stats) return null
  
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
      <div className="card">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-emerald-500/20 rounded-lg">
            <Activity className="text-emerald-400" size={24} />
          </div>
          <div>
            <div className="text-2xl font-bold text-white">
              {stats.questions?.active || 0}
            </div>
            <div className="text-sm text-gray-500">Active Questions</div>
          </div>
        </div>
      </div>
      
      <div className="card">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-blue-500/20 rounded-lg">
            <TrendingUp className="text-blue-400" size={24} />
          </div>
          <div>
            <div className="text-2xl font-bold text-white">
              {stats.questions?.total || 0}
            </div>
            <div className="text-sm text-gray-500">Total Questions</div>
          </div>
        </div>
      </div>
      
      <div className="card">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-purple-500/20 rounded-lg">
            <TrendingDown className="text-purple-400" size={24} />
          </div>
          <div>
            <div className="text-2xl font-bold text-white">
              {stats.questions?.resolved || 0}
            </div>
            <div className="text-sm text-gray-500">Resolved</div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function PortfolioOverview() {
  const [questions, setQuestions] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    loadData()
  }, [filter])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const status = filter === 'all' ? null : filter
      const [questionsData, statsData] = await Promise.all([
        fetchQuestions(status),
        fetchStats()
      ])
      
      setQuestions(questionsData)
      setStats(statsData)
    } catch (err) {
      console.error('Error loading data:', err)
      const errorMessage = err.response?.data?.detail || err.message || 'Unknown error'
      setError(`Failed to load data: ${errorMessage}. Is the API running?`)
    } finally {
      setLoading(false)
    }
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-400 text-lg mb-4">{error}</div>
        <button 
          onClick={loadData}
          className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-white transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-white mb-2">Portfolio Overview</h2>
        <p className="text-gray-500">
          Active geopolitical and macro questions tracked by the reasoning agent
        </p>
      </div>

      <StatsSummary stats={stats} />

      {/* Filters */}
      <div className="flex gap-2 mb-6">
        {['all', 'active', 'resolved'].map((status) => (
          <button
            key={status}
            onClick={() => setFilter(status)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === status
                ? 'bg-gray-700 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white'
            }`}
          >
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </button>
        ))}
      </div>

      {/* Questions Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <LoadingCard key={i} />
          ))}
        </div>
      ) : questions.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg">No questions found</p>
          <p className="text-sm mt-2">
            Use the CLI to intake questions:{' '}
            <code className="bg-gray-800 px-2 py-1 rounded">
              python cli.py intake &lt;condition_id&gt;
            </code>
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {questions.map((question) => (
            <QuestionCard key={question.id} question={question} />
          ))}
        </div>
      )}
    </div>
  )
}
