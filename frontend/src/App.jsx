import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import './App.css'

const API_BASE = 'http://localhost:8000'

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isComplete, setIsComplete] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    // Start conversation on load
    startConversation()
  }, [])

  const startConversation = async () => {
    try {
      const response = await axios.post(`${API_BASE}/api/start-conversation`)
      setSessionId(response.data.session_id)
      setMessages([{
        role: 'assistant',
        content: response.data.message
      }])
    } catch (error) {
      console.error('Error starting conversation:', error)
    }
  }

  const sendMessage = async (e) => {
    e.preventDefault()
    if (!input.trim() || !sessionId || isLoading) return

    const userMessage = input.trim()
    setInput('')
    
    // Add user message to UI immediately
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsLoading(true)

    try {
      const response = await axios.post(`${API_BASE}/api/chat`, {
        session_id: sessionId,
        message: userMessage
      })

      // Add assistant response
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response.data.message
      }])

      setIsComplete(response.data.is_complete)
    } catch (error) {
      console.error('Error sending message:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, something went wrong. Please try again.'
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const restartConversation = () => {
    setMessages([])
    setSessionId(null)
    setIsComplete(false)
    startConversation()
  }

  return (
    <div className="app">
      <div className="chat-container">
        <div className="chat-header">
          <div className="header-content">
            <div>
              <h1>Coverix Insurance</h1>
              {sessionId && <p style={{fontSize: '12px', opacity: 0.7}}>Session: {sessionId}</p>}
            </div>
            <button onClick={restartConversation} className="restart-header-btn" title="Start over">
              Restart Chat
            </button>
          </div>
        </div>

        <div className="messages-container">
          {messages.map((msg, index) => (
            <div key={index} className={`message ${msg.role}`}>
              <div className="message-content">
                {msg.content}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="message assistant">
              <div className="message-content typing">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {isComplete ? (
          <div className="completion-section">
            <button onClick={restartConversation} className="restart-btn">
              Start New Quote
            </button>
          </div>
        ) : (
          <form onSubmit={sendMessage} className="input-form">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your message..."
              disabled={isLoading}
              autoFocus
            />
            <button type="submit" disabled={isLoading || !input.trim()}>
              Send
            </button>
          </form>
        )}
      </div>
      <div className="sidebar">
        <h3>Resources</h3>
        <a href="https://coverix.ai" target="_blank" rel="noopener noreferrer">
          🏠 Home
        </a>
        <a href="https://coverix.ai/team" target="_blank" rel="noopener noreferrer">
          📧 The Team
        </a>
        <a href="https://www.linkedin.com/company/coverixai/" target="_blank" rel="noopener noreferrer">
          ℹ️ LinkedIn
        </a>
      </div>
    </div>
  )
}

export default App