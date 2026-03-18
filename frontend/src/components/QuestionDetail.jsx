import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  ReferenceLine
} from 'recharts'
import { fetchQuestion, fetchQuestionLogs, fetchReasoningForDate } from '../lib/api'
import { ArrowLeft, Calendar, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'

function ProbabilityChart({ logs }) {
  const data = [...logs].reverse().map(log => ({
    date: new Date(log.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    fullDate: log.date,
    agent: log.posterior_probability !== null ? log.posterior_probability * 100 : null,
    market: log.polymarket_price !== null ? log.polymarket_price * 100 : null,
  }))

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
          <XAxis 
            dataKey="date" 
            stroke="#8b949e"
            fontSize={12}
          />
          <YAxis 
            domain={[0, 100]} 
            stroke="#8b949e"
            fontSize={12}
            tickFormatter={(value) => `${value}%`}
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: '#161b22', 
              border: '1px solid #30363d',
              borderRadius: '8px'
            }}
            labelStyle={{ color: '#f0f6fc' }}
            formatter={(value, name) => [`${value?.toFixed(1)}%`, name]}
          />
          <Legend />
          <ReferenceLine y={50} stroke="#484f58" strokeDasharray="3 3" />
          <Line 
            type="monotone" 
            dataKey="agent" 
            name="Agent Probability" 
            stroke="#10b981" 
            strokeWidth={2}
            dot={{ fill: '#10b981', strokeWidth: 0, r: 4 }}
            activeDot={{ r: 6 }}
          />
          <Line 
            type="monotone" 
            dataKey="market" 
            name="Market Price" 
            stroke="#3b82f6" 
            strokeWidth={2}
            dot={{ fill: '#3b82f6', strokeWidth: 0, r: 4 }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

function ReasoningPanel({ log, onClose }) {
  if (!log) return null

  const evidence = log.evidence_classification || {}
  const yesEvidence = evidence.supports_yes || []
  const noEvidence = evidence.supports_no || []
  const neutralEvidence = evidence.neutral || []

  return (
    <div className="card mt-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">
          Reasoning for {new Date(log.date).toLocaleDateString()}
        </h3>
        <button 
          onClick={onClose}
          className="text-gray-500 hover:text-white transition-colors"
        >
          Close
        </button>
      </div>

      {/* Probability Change */}
      <div className="grid grid-cols-3 gap-4 mb-6 p-4 bg-gray-900 rounded-lg">
        <div>
          <div className="text-xs text-gray-500 mb-1">Prior</div>
          <div className="text-lg font-semibold text-white">
            {log.prior_probability !== null 
              ? `${(log.prior_probability * 100).toFixed(0)}%`
              : 'N/A'}
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-500 mb-1">Posterior</div>
          <div className="text-lg font-semibold text-white">
            {log.posterior_probability !== null 
              ? `${(log.posterior_probability * 100).toFixed(0)}%`
              : 'N/A'}
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-500 mb-1">Delta</div>
          <div className={`text-lg font-semibold ${
            log.delta > 0 ? 'text-emerald-400' : log.delta < 0 ? 'text-red-400' : 'text-gray-400'
          }`}>
            {log.delta !== null 
              ? `${log.delta > 0 ? '+' : ''}${(log.delta * 100).toFixed(1)}%`
              : 'N/A'}
          </div>
        </div>
      </div>

      {/* Bull Case */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-emerald-400 mb-2 flex items-center gap-2">
          <CheckCircle size={16} />
          Bull Case (Higher Probability)
        </h4>
        <div className="p-4 bg-emerald-500/5 border border-emerald-500/20 rounded-lg">
          <p className="text-sm text-gray-300 whitespace-pre-wrap">
            {log.bull_case || 'No bull case recorded'}
          </p>
        </div>
      </div>

      {/* Bear Case */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-red-400 mb-2 flex items-center gap-2">
          <XCircle size={16} />
          Bear Case (Lower Probability)
        </h4>
        <div className="p-4 bg-red-500/5 border border-red-500/20 rounded-lg">
          <p className="text-sm text-gray-300 whitespace-pre-wrap">
            {log.bear_case || 'No bear case recorded'}
          </p>
        </div>
      </div>

      {/* WTCMM */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-amber-400 mb-2">
          What Would Change My Mind?
        </h4>
        <div className="p-4 bg-amber-500/5 border border-amber-500/20 rounded-lg">
          <p className="text-sm text-gray-300">
            {log.what_would_change_my_mind || 'Not recorded'}
          </p>
        </div>
      </div>

      {/* Evidence Classification */}
      <div className="mb-4">
        <h4 className="text-sm font-medium text-gray-300 mb-3">Evidence Classification</h4>
        
        {yesEvidence.length > 0 && (
          <div className="mb-3">
            <div className="text-xs text-emerald-400 mb-1">Supports YES ({yesEvidence.length})</div>
            <ul className="text-sm text-gray-400 space-y-1">
              {yesEvidence.map((item, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-emerald-500 mt-1">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        
        {noEvidence.length > 0 && (
          <div className="mb-3">
            <div className="text-xs text-red-400 mb-1">Supports NO ({noEvidence.length})</div>
            <ul className="text-sm text-gray-400 space-y-1">
              {noEvidence.map((item, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-red-500 mt-1">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        
        {neutralEvidence.length > 0 && (
          <div>
            <div className="text-xs text-gray-500 mb-1">Neutral ({neutralEvidence.length})</div>
            <ul className="text-sm text-gray-400 space-y-1">
              {neutralEvidence.map((item, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-gray-500 mt-1">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Confidence & Warnings */}
      <div className="flex items-center gap-4 pt-4 border-t border-gray-700">
        <div>
          <span className="text-xs text-gray-500">Confidence: </span>
          <span className={`text-sm font-medium ${
            log.update_confidence === 'high' ? 'text-emerald-400' :
            log.update_confidence === 'medium' ? 'text-amber-400' : 'text-gray-400'
          }`}>
            {log.update_confidence?.toUpperCase() || 'N/A'}
          </span>
        </div>
        
        {log.anchoring_warning && (
          <div className="flex items-center gap-1 text-xs text-amber-400">
            <AlertTriangle size={12} />
            Anchoring Warning
          </div>
        )}
        
        {log.overreaction_warning && (
          <div className="flex items-center gap-1 text-xs text-red-400">
            <AlertTriangle size={12} />
            Overreaction Warning
          </div>
        )}
      </div>
    </div>
  )
}

export default function QuestionDetail() {
  const { id } = useParams()
  const [question, setQuestion] = useState(null)
  const [logs, setLogs] = useState([])
  const [selectedLog, setSelectedLog] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadData()
  }, [id])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const [questionData, logsData] = await Promise.all([
        fetchQuestion(id),
        fetchQuestionLogs(id)
      ])
      
      setQuestion(questionData)
      setLogs(logsData)
      
      // Select the most recent log by default
      if (logsData.length > 0) {
        setSelectedLog(logsData[0])
      }
    } catch (err) {
      console.error('Error loading question:', err)
      setError('Failed to load question data')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="animate-pulse h-8 bg-gray-800 rounded w-1/3"></div>
        <div className="animate-pulse h-96 bg-gray-800 rounded"></div>
      </div>
    )
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

  if (!question) {
    return (
      <div className="text-center py-12 text-gray-500">
        Question not found
      </div>
    )
  }

  return (
    <div>
      {/* Back Button */}
      <Link 
        to="/" 
        className="inline-flex items-center gap-2 text-gray-400 hover:text-white transition-colors mb-6"
      >
        <ArrowLeft size={20} />
        Back to Portfolio
      </Link>

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-2">{question.title}</h1>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500 bg-gray-800 px-2 py-1 rounded">
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
        {question.description && (
          <p className="text-gray-500 mt-4">{question.description}</p>
        )}
      </div>

      {/* Probability Chart */}
      <div className="card mb-6">
        <h2 className="text-lg font-semibold text-white mb-4">Probability Evolution</h2>
        {logs.length > 0 ? (
          <ProbabilityChart logs={logs} />
        ) : (
          <div className="h-80 flex items-center justify-center text-gray-500">
            No data available yet
          </div>
        )}
      </div>

      {/* Daily Log History */}
      <div className="card mb-6">
        <h2 className="text-lg font-semibold text-white mb-4">Daily Log History</h2>
        
        {logs.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No updates yet
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-gray-700">
                  <th className="pb-2 font-medium">Date</th>
                  <th className="pb-2 font-medium">Agent</th>
                  <th className="pb-2 font-medium">Market</th>
                  <th className="pb-2 font-medium">Delta</th>
                  <th className="pb-2 font-medium">Confidence</th>
                  <th className="pb-2 font-medium"></th>
                </tr>
              </thead>
              <tbody className="text-sm">
                {logs.map((log) => (
                  <tr 
                    key={log.id} 
                    className={`border-b border-gray-800 hover:bg-gray-800/50 cursor-pointer ${
                      selectedLog?.id === log.id ? 'bg-gray-800' : ''
                    }`}
                    onClick={() => setSelectedLog(log)}
                  >
                    <td className="py-3">
                      {new Date(log.date).toLocaleDateString()}
                    </td>
                    <td className="py-3">
                      {log.posterior_probability !== null 
                        ? `${(log.posterior_probability * 100).toFixed(0)}%`
                        : 'N/A'}
                    </td>
                    <td className="py-3 text-gray-400">
                      {log.polymarket_price !== null 
                        ? `${(log.polymarket_price * 100).toFixed(2)}%`
                        : 'N/A'}
                    </td>
                    <td className={`py-3 ${
                      log.delta > 0 ? 'text-emerald-400' : log.delta < 0 ? 'text-red-400' : 'text-gray-400'
                    }`}>
                      {log.delta !== null 
                        ? `${log.delta > 0 ? '+' : ''}${(log.delta * 100).toFixed(1)}%`
                        : 'N/A'}
                    </td>
                    <td className="py-3">
                      <span className={`text-xs ${
                        log.update_confidence === 'high' ? 'text-emerald-400' :
                        log.update_confidence === 'medium' ? 'text-amber-400' : 'text-gray-400'
                      }`}>
                        {log.update_confidence?.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-3">
                      {(log.anchoring_warning || log.overreaction_warning) && (
                        <AlertTriangle size={14} className="text-amber-400" />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Reasoning Panel */}
      {selectedLog && (
        <ReasoningPanel 
          log={selectedLog} 
          onClose={() => setSelectedLog(null)} 
        />
      )}
    </div>
  )
}
