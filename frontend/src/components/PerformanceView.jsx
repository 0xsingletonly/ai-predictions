import { useState, useEffect } from 'react'
import { fetchQuestions, fetchQuestionPerformance } from '../lib/api'
import { Trophy, TrendingUp, TrendingDown, AlertCircle } from 'lucide-react'

function PerformanceCard({ question, onClick }) {
  return (
    <div 
      className="card card-hover cursor-pointer"
      onClick={onClick}
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
            {question.status === 'resolved' && (
              <span className={`text-xs px-2 py-1 rounded ${
                question.outcome === 'yes' 
                  ? 'bg-emerald-500/20 text-emerald-400'
                  : 'bg-red-500/20 text-red-400'
              }`}>
                Resolved: {question.outcome?.toUpperCase()}
              </span>
            )}
          </div>
        </div>
      </div>

      {question.brier_score !== null && (
        <div className="grid grid-cols-2 gap-4 mt-4 pt-4 border-t border-gray-700">
          <div>
            <div className="text-xs text-gray-500 mb-1">Agent Brier Score</div>
            <div className={`text-lg font-bold ${
              question.brier_score < 0.25 ? 'text-emerald-400' : 
              question.brier_score < 0.5 ? 'text-amber-400' : 'text-red-400'
            }`}>
              {question.brier_score.toFixed(3)}
            </div>
            <div className="text-xs text-gray-600">
              {question.brier_score < 0.25 ? 'Good' : 
               question.brier_score < 0.5 ? 'Fair' : 'Poor'}
            </div>
          </div>
          
          <div>
            <div className="text-xs text-gray-500 mb-1">vs Market</div>
            <div className={`text-lg font-bold ${
              question.agent_vs_market < 0 ? 'text-emerald-400' : 'text-red-400'
            }`}>
              {question.agent_vs_market !== null 
                ? `${question.agent_vs_market > 0 ? '+' : ''}${question.agent_vs_market.toFixed(3)}`
                : 'N/A'}
            </div>
            <div className="text-xs text-gray-600">
              {question.agent_vs_market < 0 ? 'Agent better' : 
               question.agent_vs_market > 0 ? 'Market better' : 'Tie'}
            </div>
          </div>
        </div>
      )}

      <div className="mt-4 flex items-center gap-4 text-xs text-gray-500">
        <div>
          Updates: {question.num_updates}
        </div>
        <div>
          Warnings: {question.anchoring_warnings + question.overreaction_warnings}
        </div>
      </div>
    </div>
  )
}

function PerformanceDetail({ questionId, onClose }) {
  const [performance, setPerformance] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadPerformance()
  }, [questionId])

  const loadPerformance = async () => {
    try {
      setLoading(true)
      const data = await fetchQuestionPerformance(questionId)
      setPerformance(data)
    } catch (err) {
      console.error('Error loading performance:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="card">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-700 rounded w-1/3"></div>
          <div className="h-20 bg-gray-700 rounded"></div>
        </div>
      </div>
    )
  }

  if (!performance) return null

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-bold text-white">Performance Details</h3>
        <button 
          onClick={onClose}
          className="text-gray-500 hover:text-white transition-colors"
        >
          Close
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="p-4 bg-gray-900 rounded-lg">
          <div className="text-xs text-gray-500 mb-1">Total Updates</div>
          <div className="text-2xl font-bold text-white">{performance.num_updates}</div>
        </div>
        
        {performance.brier_score !== null && (
          <>
            <div className="p-4 bg-gray-900 rounded-lg">
              <div className="text-xs text-gray-500 mb-1">Agent Brier</div>
              <div className={`text-2xl font-bold ${
                performance.brier_score < 0.25 ? 'text-emerald-400' : 
                performance.brier_score < 0.5 ? 'text-amber-400' : 'text-red-400'
              }`}>
                {performance.brier_score.toFixed(3)}
              </div>
            </div>
            
            <div className="p-4 bg-gray-900 rounded-lg">
              <div className="text-xs text-gray-500 mb-1">Market Brier</div>
              <div className="text-2xl font-bold text-blue-400">
                {performance.market_brier_score?.toFixed(3) || 'N/A'}
              </div>
            </div>
            
            <div className="p-4 bg-gray-900 rounded-lg">
              <div className="text-xs text-gray-500 mb-1">Advantage</div>
              <div className={`text-2xl font-bold ${
                performance.agent_vs_market < 0 ? 'text-emerald-400' : 'text-red-400'
              }`}>
                {performance.agent_vs_market !== null 
                  ? `${performance.agent_vs_market > 0 ? '+' : ''}${performance.agent_vs_market.toFixed(3)}`
                  : 'N/A'}
              </div>
            </div>
          </>
        )}
      </div>

      {/* Probability Range */}
      {performance.probability_range && (
        <div className="mb-6">
          <h4 className="text-sm font-medium text-gray-300 mb-3">Probability Range</h4>
          <div className="p-4 bg-gray-900 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs text-gray-500">Min</div>
                <div className="text-lg font-semibold text-white">
                  {performance.probability_range.min !== null 
                    ? `${(performance.probability_range.min * 100).toFixed(0)}%`
                    : 'N/A'}
                </div>
              </div>
              <div className="flex-1 mx-8 h-2 bg-gray-700 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-red-500 via-yellow-500 to-emerald-500"
                  style={{ width: '100%' }}
                ></div>
              </div>
              <div className="text-right">
                <div className="text-xs text-gray-500">Max</div>
                <div className="text-lg font-semibold text-white">
                  {performance.probability_range.max !== null 
                    ? `${(performance.probability_range.max * 100).toFixed(0)}%`
                    : 'N/A'}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Divergence */}
      {performance.avg_divergence_from_market !== null && (
        <div className="mb-6">
          <h4 className="text-sm font-medium text-gray-300 mb-3">Market Divergence</h4>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-gray-900 rounded-lg">
              <div className="text-xs text-gray-500 mb-1">Average</div>
              <div className={`text-lg font-semibold ${
                performance.avg_divergence_from_market > 0 ? 'text-emerald-400' : 'text-red-400'
              }`}>
                {`${performance.avg_divergence_from_market > 0 ? '+' : ''}${(performance.avg_divergence_from_market * 100).toFixed(1)}%`}
              </div>
            </div>
            <div className="p-4 bg-gray-900 rounded-lg">
              <div className="text-xs text-gray-500 mb-1">Max Absolute</div>
              <div className="text-lg font-semibold text-white">
                {performance.max_divergence !== null 
                  ? `${(performance.max_divergence * 100).toFixed(1)}%`
                  : 'N/A'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Warnings */}
      <div className="flex gap-4">
        {performance.anchoring_warnings > 0 && (
          <div className="flex items-center gap-2 text-amber-400 text-sm">
            <AlertCircle size={16} />
            {performance.anchoring_warnings} anchoring warning(s)
          </div>
        )}
        {performance.overreaction_warnings > 0 && (
          <div className="flex items-center gap-2 text-red-400 text-sm">
            <AlertCircle size={16} />
            {performance.overreaction_warnings} overreaction warning(s)
          </div>
        )}
      </div>
    </div>
  )
}

export default function PerformanceView() {
  const [questions, setQuestions] = useState([])
  const [selectedQuestion, setSelectedQuestion] = useState(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    loadData()
  }, [filter])

  const loadData = async () => {
    try {
      setLoading(true)
      const status = filter === 'all' ? null : filter
      const questionsData = await fetchQuestions(status)
      
      // Load performance data for each question
      const questionsWithPerformance = await Promise.all(
        questionsData.map(async (q) => {
          try {
            const perf = await fetchQuestionPerformance(q.id)
            return { ...q, ...perf }
          } catch (err) {
            return q
          }
        })
      )
      
      setQuestions(questionsWithPerformance)
    } catch (err) {
      console.error('Error loading performance data:', err)
    } finally {
      setLoading(false)
    }
  }

  // Calculate summary stats
  const resolvedQuestions = questions.filter(q => q.status === 'resolved')
  const agentBetterCount = resolvedQuestions.filter(q => q.agent_vs_market < 0).length
  const avgBrierScore = resolvedQuestions.length > 0
    ? resolvedQuestions.reduce((sum, q) => sum + (q.brier_score || 0), 0) / resolvedQuestions.length
    : null

  return (
    <div>
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-white mb-2">Performance</h2>
        <p className="text-gray-500">
          Brier scores and calibration metrics for resolved and active questions
        </p>
      </div>

      {/* Summary Stats */}
      {resolvedQuestions.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="card">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-emerald-500/20 rounded-lg">
                <Trophy className="text-emerald-400" size={24} />
              </div>
              <div>
                <div className="text-2xl font-bold text-white">
                  {agentBetterCount}/{resolvedQuestions.length}
                </div>
                <div className="text-sm text-gray-500">Agent Beat Market</div>
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
                  {avgBrierScore !== null ? avgBrierScore.toFixed(3) : 'N/A'}
                </div>
                <div className="text-sm text-gray-500">Avg Agent Brier</div>
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
                  {resolvedQuestions.length}
                </div>
                <div className="text-sm text-gray-500">Resolved Questions</div>
              </div>
            </div>
          </div>
        </div>
      )}

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

      {/* Selected Question Detail */}
      {selectedQuestion && (
        <div className="mb-6">
          <PerformanceDetail 
            questionId={selectedQuestion.id}
            onClose={() => setSelectedQuestion(null)}
          />
        </div>
      )}

      {/* Questions Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="card">
              <div className="animate-pulse space-y-4">
                <div className="h-6 bg-gray-700 rounded w-3/4"></div>
                <div className="h-16 bg-gray-700 rounded"></div>
              </div>
            </div>
          ))}
        </div>
      ) : questions.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg">No questions found</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {questions.map((question) => (
            <PerformanceCard 
              key={question.id} 
              question={question}
              onClick={() => setSelectedQuestion(question)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
