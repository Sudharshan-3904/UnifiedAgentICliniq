import { useState, useEffect, useRef } from 'react'
import { MCPClient } from './mcp-client'
import BMIWidget from './components/BMIWidget'
import { Send, Sparkles, Activity, AlertCircle, History, Info, Github } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string | any;
  type: 'text' | 'widget';
}

function App() {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: "Hello! I'm your premium **BMI Health Advisor**. Tell me your **height** (e.g., 1.75m or 175cm) and **weight** (e.g., 70kg) to get started.",
      type: 'text'
    }
  ])
  const [status, setStatus] = useState<'connecting' | 'connected' | 'error'>('connecting')
  const [logs, setLogs] = useState<string[]>(['Handshake initiated...'])

  const mcpClient = useRef<MCPClient | null>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const url = new URL('/sse', window.location.origin).href
    mcpClient.current = new MCPClient(url)

    addLog(`Connecting to ${url}...`)

    mcpClient.current.connect()
      .then(() => {
        setStatus('connected')
        addLog('Handshake complete. Client ready.')
      })
      .catch(err => {
        console.error(err)
        setStatus('error')
        addLog(`Protocol Error: ${err.message || 'Connection failed'}`)
      })

    return () => {
      // Potentially close ES if needed
    }
  }, [])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const addLog = (msg: string) => {
    setLogs(prev => [...prev.slice(-10), `> ${msg}`])
  }

  const handleSend = async () => {
    if (!input.trim() || status !== 'connected') return

    const userText = input.trim()
    setInput('')

    const userMsgId = Math.random().toString(36).substr(2, 9)
    setMessages(prev => [...prev, {
      id: userMsgId,
      role: 'user',
      content: userText,
      type: 'text'
    }])

    // Parsing height and weight
    const weightMatch = userText.match(/(\d+\.?\d*)\s*kg/i);
    const heightMatch = userText.match(/(\d+\.?\d*)\s*(m|cm)/i);

    if (weightMatch && heightMatch) {
      let weight = parseFloat(weightMatch[1]);
      let height = parseFloat(heightMatch[1]);
      if (heightMatch[2].toLowerCase() === 'cm') height /= 100;

      addLog(`Calling tool: calculate_bmi(height=${height}, weight=${weight})`)

      try {
        const result = await mcpClient.current?.callTool("calculate_bmi_tool", { height, weight })
        const data = JSON.parse(result.content[0].text)

        if (data.error) {
          setMessages(prev => [...prev, {
            id: Math.random().toString(36).substr(2, 9),
            role: 'assistant',
            content: `Error: ${data.error}`,
            type: 'text'
          }])
        } else {
          setMessages(prev => [...prev, {
            id: Math.random().toString(36).substr(2, 9),
            role: 'assistant',
            content: data,
            type: 'widget'
          }])
        }
      } catch (err: any) {
        setMessages(prev => [...prev, {
          id: Math.random().toString(36).substr(2, 9),
          role: 'assistant',
          content: `Protocol Error: ${err.message || 'Check logs'}`,
          type: 'text'
        }])
      }
    } else {
      setMessages(prev => [...prev, {
        id: Math.random().toString(36).substr(2, 9),
        role: 'assistant',
        content: "I need both your height (e.g. 1.75m) and weight (e.g. 70kg) to calculate your BMI.",
        type: 'text'
      }])
    }
  }

  return (
    <div className="min-h-screen bg-[#fafafa] text-gray-900 font-sans selection:bg-blue-100">
      {/* Background blobs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none -z-10">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-100/50 blur-[120px] rounded-full" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-indigo-100/50 blur-[120px] rounded-full" />
      </div>

      <div className="max-w-6xl mx-auto px-4 py-8 md:py-12 flex flex-col md:flex-row gap-8 min-h-[90vh]">
        {/* Main Content */}
        <div className="flex-1 flex flex-col bg-white rounded-[2.5rem] shadow-2xl border border-gray-100 overflow-hidden">
          {/* Header */}
          <header className="px-8 py-6 border-b border-gray-50 flex justify-between items-center bg-white/80 backdrop-blur-md sticky top-0 z-10">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-600 rounded-2xl flex items-center justify-center text-white shadow-lg shadow-blue-200">
                <Activity size={24} />
              </div>
              <div>
                <h1 className="text-xl font-black tracking-tight text-gray-800">Sujit <span className="text-blue-600">BMI</span></h1>
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${status === 'connected' ? 'bg-green-500 animate-pulse' : status === 'connecting' ? 'bg-amber-500' : 'bg-red-500'}`} />
                  <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
                    {status === 'connected' ? 'Protocol Online' : status === 'connecting' ? 'Connecting...' : 'Protocol Offline'}
                  </span>
                </div>
              </div>
            </div>
            <div className="hidden sm:flex gap-4">
              <button className="p-2 text-gray-400 hover:text-gray-600 transition-colors"><Info size={20} /></button>
              <button className="p-2 text-gray-400 hover:text-gray-600 transition-colors"><Github size={20} /></button>
            </div>
          </header>

          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto px-8 py-8 space-y-8">
            <AnimatePresence initial={false}>
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`flex gap-4 max-w-[85%] ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                    <div className={`w-10 h-10 rounded-2xl flex items-center justify-center shrink-0 shadow-lg ${msg.role === 'assistant'
                        ? 'bg-gradient-to-br from-gray-800 to-gray-900 text-white'
                        : 'bg-gradient-to-br from-blue-500 to-blue-600 text-white'
                      }`}>
                      {msg.role === 'assistant' ? <Sparkles size={20} /> : <div className="font-bold text-sm">You</div>}
                    </div>

                    <div className={`space-y-4 ${msg.role === 'user' ? 'text-right' : ''}`}>
                      {msg.type === 'text' ? (
                        <div className={`px-6 py-4 rounded-3xl shadow-sm text-sm leading-relaxed ${msg.role === 'assistant'
                            ? 'bg-gray-50 text-gray-800 border border-gray-100 rounded-tl-none'
                            : 'bg-blue-600 text-white rounded-tr-none'
                          }`}>
                          {msg.content.toString().split('**').map((part: string, i: number) =>
                            i % 2 === 1 ? <b key={i} className="font-bold">{part}</b> : part
                          )}
                        </div>
                      ) : (
                        <BMIWidget data={msg.content} />
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
            <div ref={chatEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-8 bg-white border-t border-gray-50">
            <div className="relative group">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Type your height (1.8m) and weight (75kg)..."
                className="w-full pl-6 pr-16 py-5 bg-gray-50 border border-gray-100 rounded-[2rem] text-sm focus:outline-none focus:ring-4 focus:ring-blue-100 focus:bg-white transition-all group-hover:bg-gray-100/50"
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || status !== 'connected'}
                className="absolute right-2 top-2 bottom-2 px-6 bg-blue-600 text-white rounded-2xl flex items-center justify-center hover:bg-blue-700 active:scale-95 transition-all disabled:opacity-50 disabled:active:scale-100 shadow-lg shadow-blue-200"
              >
                <Send size={18} />
              </button>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {['1.75m 70kg', '165cm 55kg', '1.9m 100kg'].map(ex => (
                <button
                  key={ex}
                  onClick={() => setInput(ex)}
                  className="px-4 py-2 bg-gray-50 hover:bg-gray-100 text-[10px] font-bold uppercase tracking-wider text-gray-400 rounded-full border border-gray-100 transition-colors"
                >
                  {ex}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <aside className="w-full md:w-80 flex flex-col gap-6">
          <div className="bg-white p-8 rounded-[2.5rem] shadow-xl border border-gray-100">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-8 h-8 bg-amber-100 text-amber-600 rounded-xl flex items-center justify-center"><Info size={16} /></div>
              <h3 className="text-sm font-black uppercase tracking-widest text-gray-400">Quick Guide</h3>
            </div>
            <ul className="space-y-4">
              {[
                { label: 'BMI', val: 'Measure of body fat based on height/weight.' },
                { label: 'Units', val: 'Supports meters (m) and centimeters (cm).' },
                { label: 'Insight', val: 'Get ideal weight range and health tips.' }
              ].map((item, i) => (
                <li key={i} className="group">
                  <div className="text-[10px] font-black text-blue-600 uppercase mb-1">{item.label}</div>
                  <div className="text-xs text-gray-500 leading-relaxed font-medium">{item.val}</div>
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-gray-900 p-8 rounded-[2.5rem] shadow-xl text-white flex-1 overflow-hidden flex flex-col border border-gray-800">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-8 h-8 bg-gray-800 text-gray-400 rounded-xl flex items-center justify-center"><History size={16} /></div>
              <h3 className="text-sm font-black uppercase tracking-widest text-gray-400">Protocol Logs</h3>
            </div>
            <div className="flex-1 font-mono text-[10px] space-y-2 opacity-60 overflow-y-auto custom-scrollbar">
              {logs.map((log, i) => <div key={i} className="break-all">{log}</div>)}
            </div>
            <div className="mt-6 pt-6 border-t border-gray-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertCircle size={14} className="text-gray-500" />
                <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">v3.0 Stable</span>
              </div>
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}

export default App
