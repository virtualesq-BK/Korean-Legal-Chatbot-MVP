import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [country, setCountry] = useState('USA');
  const [userType, setUserType] = useState('individual');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  useEffect(() => {
    setMessages([]);
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = {
      id: messages.length + 1,
      text: input,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString()
    };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await axios.post(
        `${API_URL}/chat`,
        {
          message: input,
          country: country,
          user_type: userType
        },
        { timeout: 60000 }
      );

      const replyText = response.data?.reply ?? "No response from the server.";
      const botPayload = {
        text: replyText,
        sender: 'bot',
        timestamp: new Date().toLocaleTimeString(),
        confidence: response.data?.confidence,
        needsExpert: response.data?.needs_expert,
        suggestedActions: response.data?.suggested_actions || [],
        lawReferences: response.data?.law_references || []
      };
      const expertPayload = response.data?.needs_expert
        ? {
            text: `⚖️ It seems you need expert consultation. Would you like to connect with a ${response.data?.suggested_expert_type ?? 'legal'} specialist?`,
            sender: 'bot',
            timestamp: new Date().toLocaleTimeString(),
            isExpertSuggestion: true
          }
        : null;

      setMessages(prev => {
        const next = [...prev, { ...botPayload, id: prev.length + 1 }];
        if (expertPayload) next.push({ ...expertPayload, id: prev.length + 2 });
        return next;
      });

    } catch (error) {
      console.error('Error:', error);
      const isNetworkError = error?.code === 'ERR_NETWORK' || error?.message?.includes('Network Error');
      const isTimeout = error?.code === 'ECONNABORTED' || error?.message?.includes('timeout');
      const isLocalhost = typeof window !== 'undefined' && /localhost|127\.0\.0\.1/.test(window.location?.hostname || '');
      const serverDetail = error?.response?.data?.detail;
      let text = "⚠️ Sorry, an error occurred while processing your request. Please try again.";
      if (typeof serverDetail === 'string') {
        text = `⚠️ ${serverDetail}`;
      } else if (isTimeout) {
        text = "⚠️ Request timed out. On Render free tier the backend may be waking up (cold start). Please try again in a few seconds.";
      } else if (isNetworkError) {
        text = isLocalhost
          ? "⚠️ Could not reach the server. Start the backend (e.g. in backend/: uvicorn app:app --host 0.0.0.0 --port 8000)."
          : "⚠️ Could not reach the API. Check REACT_APP_API_URL in the frontend Environment and redeploy, or the backend may be starting up—try again shortly.";
      }
      setMessages(prev => [...prev, {
        id: prev.length + 1,
        text,
        sender: 'bot',
        timestamp: new Date().toLocaleTimeString()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickQuestion = (question) => {
    setInput(question);
  };

  const handleConnectExpert = () => {
    alert('Expert connection feature coming soon!');
  };

  const handleActionClick = (action) => {
    alert(`"${action}" feature coming soon!`);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-main">
          <h1>
            <img src="/상담 변호사.jpg" alt="" className="header-logo" />
            Korean Legal Assistant
          </h1>
          <p className="subtitle">Comprehensive Legal Guide for Foreign Businesses in Korea</p>
          
          <div className="controls">
            <div className="control-group">
              <label>Country:</label>
              <select value={country} onChange={(e) => setCountry(e.target.value)}>
                <option value="USA">USA</option>
                <option value="UAE">UAE</option>
                <option value="UK">UK</option>
                <option value="general">General</option>
              </select>
            </div>
            
            <div className="control-group">
              <label>User Type:</label>
              <select value={userType} onChange={(e) => setUserType(e.target.value)}>
                <option value="individual">Individual</option>
                <option value="sme">SME (Small & Medium Enterprise)</option>
                <option value="corporate">Corporate</option>
              </select>
            </div>
          </div>
        </div>
        <div className="header-disclaimer">
          ⚠️ <strong>Important Notice:</strong> This chatbot is for informational purposes only. It does not replace legal advice. Please consult with a qualified attorney before making any important decisions.
        </div>
      </header>

      <div className="welcome-section">
        👋 Hello! I'm your guide to the legal landscape for foreign businesses in Korea.
        <br />
        Select your country above and ask anything about Korean law.
      </div>

      <div className="quick-questions-section">
        <label htmlFor="quick-questions-select" className="quick-questions-label">Quick Questions:</label>
        <select
          id="quick-questions-select"
          className="quick-questions-select"
          value=""
          onChange={(e) => {
            const v = e.target.value;
            if (v) {
              handleQuickQuestion(v);
              e.target.value = "";
            }
          }}
        >
          <option value="">Select a quick question...</option>
          <option value="Foreign investment incentives and MOTIE reporting in Korea?">💼 Investment & Incentives</option>
          <option value="Digital platform and AI regulations in Korea 2025?">📱 Digital & AI Rules</option>
          <option value="Yellow Envelope Act and labor law changes in Korea?">👷 Labor & Yellow Envelope</option>
          <option value="IP protection and trademark act changes in Korea?">®️ IP & Trademark</option>
          <option value="ESG and supply chain due diligence in Korea?">🌱 ESG & Supply Chain</option>
          <option value="Company setup, tax, fair trade, and PIPA in Korea?">🏛️ Corporate, Tax & Compliance</option>
        </select>
      </div>

      <div className="chat-container">
        <div className="messages-wrapper">
          {messages.map((msg) => (
            <div key={msg.id} className={`message ${msg.sender}`}>
              {msg.sender === 'user' && (
                <img src="/상담 변호사.jpg" alt="" className="message-avatar" />
              )}
              <div className="message-bubble">
                <div className="message-text">{msg.text}</div>
                <div className="message-footer">
                  <span className="timestamp">{msg.timestamp}</span>
                  {msg.confidence && (
                    <span className={`confidence ${msg.confidence > 0.7 ? 'high' : msg.confidence > 0.4 ? 'medium' : 'low'}`}>
                      Confidence: {Math.round(msg.confidence * 100)}%
                    </span>
                  )}
                </div>
                {msg.lawReferences && msg.lawReferences.length > 0 && (
                  <div className="law-references">
                    <div className="law-refs-label">📚 Related English Laws (국가법령정보 영문법령)</div>
                    {msg.lawReferences.map((ref, index) => (
                      <a key={index} href={ref.url} target="_blank" rel="noopener noreferrer" className="law-ref-link">
                        {ref.name_en || ref.name} — {ref.name}
                      </a>
                    ))}
                  </div>
                )}
                {msg.suggestedActions && msg.suggestedActions.length > 0 && (
                  <div className="suggested-actions">
                    {msg.suggestedActions.map((action, index) => (
                      <button key={index} className="action-btn" onClick={() => handleActionClick(action)}>{action}</button>
                    ))}
                  </div>
                )}
                {msg.isExpertSuggestion && (
                  <button className="expert-btn" onClick={handleConnectExpert}>
                    👨‍⚖️ Connect with Expert
                  </button>
                )}
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div className="message bot">
              <div className="message-bubble">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                <div className="typing-hint">Waiting for response (up to 1 min on first request)…</div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="input-section">
          <div className="input-wrapper">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask anything about Korean law..."
              disabled={isLoading}
            />
            <button 
              onClick={handleSend} 
              disabled={isLoading || !input.trim()}
              className="send-btn"
            >
              {isLoading ? 'Processing...' : 'Send'}
            </button>
          </div>
          <div className="input-hint">
            e.g., "MOTIE reporting for foreign investment", "AI Basic Act obligations", "Yellow Envelope Act 2026"
          </div>
        </div>
      </div>

      <footer className="app-footer">
        <div className="footer-info">
          <span>Korean Legal Chatbot MVP v1.0</span>
          <span>•</span>
          <span>Contact: virtual.esq@gmail.com</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
