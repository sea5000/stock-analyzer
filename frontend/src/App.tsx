import React, { useState, useEffect } from 'react';
import { MessageSquare, Briefcase, Activity, Cpu } from 'lucide-react';
import { ChatView } from './components/ChatView';
import { PortfolioView } from './components/PortfolioView';
import './App.css';

export function App() {
  const [activeTab, setActiveTab] = useState<'chat' | 'portfolio'>('chat');
  const [serverStatus, setServerStatus] = useState<{
    status: string;
    model: string;
    ollama_online: boolean;
  }>({
    status: 'checking',
    model: 'qwen3.8:27b',
    ollama_online: false
  });

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch('/health');
        if (res.ok) {
          const data = await res.json();
          setServerStatus({
            status: data.status,
            model: data.configured_model || 'qwen3.8:27b',
            ollama_online: data.ollama_online
          });
        }
      } catch (err) {
        setServerStatus(prev => ({ ...prev, status: 'offline', ollama_online: false }));
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app-shell">
      {/* Top Navbar */}
      <header className="navbar">
        <div className="navbar-brand">
          <div className="brand-logo">📈</div>
          <div>
            <h1 className="brand-title">AI Stock & Portfolio Analyst</h1>
            <p className="brand-subtitle">Local AI Intelligence • Yahoo Finance Real-Time • Forward-Looking Diversification</p>
          </div>
        </div>

        <div className="navbar-right">
          {/* Status Badge */}
          <div className={`status-pill ${serverStatus.ollama_online ? 'online' : 'checking'}`}>
            <Cpu size={14} />
            <span>Ollama: <strong>{serverStatus.model}</strong></span>
            <span className="dot"></span>
          </div>

          {/* Tab Navigation */}
          <nav className="tab-nav">
            <button
              className={`tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
              onClick={() => setActiveTab('chat')}
            >
              <MessageSquare size={16} /> AI Financial Chat
            </button>
            <button
              className={`tab-btn ${activeTab === 'portfolio' ? 'active' : ''}`}
              onClick={() => setActiveTab('portfolio')}
            >
              <Briefcase size={16} /> Portfolio & Lots
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="main-viewport">
        <div
          style={{
            display: activeTab === 'chat' ? 'flex' : 'none',
            height: '100%',
            width: '100%',
            flexDirection: 'column',
          }}
        >
          <ChatView />
        </div>
        <div
          style={{
            display: activeTab === 'portfolio' ? 'block' : 'none',
            height: '100%',
            width: '100%',
          }}
        >
          <PortfolioView />
        </div>
      </main>
    </div>
  );
}

export default App;
