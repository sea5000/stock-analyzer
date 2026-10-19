import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Bot,
  User,
  Sparkles,
  RefreshCw,
  RotateCcw,
  Copy,
  Check,
  Database,
  ExternalLink
} from 'lucide-react';
import { MarkdownRenderer } from './MarkdownRenderer';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

interface SourcingInfo {
  sources: string[];
  links: { title: string; url: string }[];
}

function extractSourcing(text: string): SourcingInfo {
  const sources: string[] = [];
  const links: { title: string; url: string }[] = [];
  
  // Extract markdown links [title](url) as citation links
  const mdLinkRegex = /\[([^\]]+)\]\((https?:\/\/[^\s\)]+)\)/g;
  let match;
  const seenUrls = new Set<string>();
  while ((match = mdLinkRegex.exec(text)) !== null) {
    if (!seenUrls.has(match[2])) {
      seenUrls.add(match[2]);
      links.push({ title: match[1], url: match[2] });
    }
  }

  const lower = text.toLowerCase();
  
  if (
    lower.includes('portfolio') ||
    lower.includes('lots') ||
    lower.includes('bought lot') ||
    lower.includes('unrealized p&l') ||
    lower.includes('cost basis') ||
    lower.includes('sector breakdown')
  ) {
    sources.push('User Portfolio Engine');
  }

  if (
    lower.includes('stock price') ||
    lower.includes('p/e') ||
    lower.includes('market cap') ||
    lower.includes('52-week') ||
    lower.includes('dividend yield') ||
    lower.includes('analyst') ||
    lower.includes('target price') ||
    lower.includes('yfinance') ||
    lower.includes('yahoo finance')
  ) {
    sources.push('Yahoo Finance Live API');
  }

  if (
    lower.includes('balance sheet') ||
    lower.includes('cash flow') ||
    lower.includes('debt-to-equity') ||
    lower.includes('sec') ||
    lower.includes('10-k') ||
    lower.includes('10-q') ||
    lower.includes('quarterly earnings')
  ) {
    sources.push('Corporate Filings / SEC');
  }

  if (
    lower.includes('s&p 500') ||
    lower.includes('sp500') ||
    lower.includes('benchmark') ||
    lower.includes('vanguard') ||
    lower.includes('index')
  ) {
    sources.push('S&P 500 Benchmark Data');
  }

  if (
    lower.includes('reuters') ||
    lower.includes('bloomberg') ||
    lower.includes('financial news') ||
    lower.includes('press release') ||
    links.length > 0
  ) {
    sources.push('Financial News Wire');
  }

  return { sources, links };
}

const MessageSourcingBar: React.FC<{ content: string }> = ({ content }) => {
  const { sources, links } = extractSourcing(content);
  if (sources.length === 0 && links.length === 0) return null;

  return (
    <div className="message-sources-bar">
      <div className="sources-header">
        <Database size={12} /> Data Sourced From:
      </div>
      <div className="sources-badges">
        {sources.map((src, idx) => (
          <span key={idx} className="source-badge">
            {src}
          </span>
        ))}
        {links.map((link, idx) => (
          <a
            key={idx}
            href={link.url}
            target="_blank"
            rel="noopener noreferrer"
            className="source-link-badge"
            title={link.url}
          >
            <span>{link.title.length > 28 ? link.title.slice(0, 28) + '...' : link.title}</span>
            <ExternalLink size={10} />
          </a>
        ))}
      </div>
    </div>
  );
};

const STORAGE_KEY_MESSAGES = 'stock_analyzer_chat_messages';
const STORAGE_KEY_THREAD = 'stock_analyzer_chat_thread_id';

const INITIAL_WELCOME_MESSAGE: Message = {
  id: 'welcome_1',
  role: 'assistant',
  content: "Hello! I'm your local AI Stock & Portfolio Analysis Assistant, powered by Qwen 2.5 / 3.8 and Yahoo Finance.\n\nI can analyze your **bought stock lots**, evaluate your **live portfolio P&L**, audit **sector diversification**, and provide **forward-looking recommendations** on what to buy next to rebalance. What would you like to explore today?"
};

const QUICK_PROMPTS = [
  "Analyze my portfolio diversification and highlight any risks.",
  "I have $2,000 to invest. What should I buy next to diversify?",
  "What is the current stock price and key valuation ratios for NVDA?",
  "Compare AMD and Nvidia using fundamentals and analyst targets.",
  "Show the latest financial news and balance sheet for Apple."
];

export const ChatView: React.FC = () => {
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopyMessage = async (id: string, text: string) => {
    try {
      // Strip any internal reasoning <think> tags before copying to clipboard
      const cleaned = text.replace(/<think>[\s\S]*?<\/think>/g, '').trim() || text;
      await navigator.clipboard.writeText(cleaned);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (e) {
      console.warn("Clipboard copy failed, using fallback:", e);
      try {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        setCopiedId(id);
        setTimeout(() => setCopiedId(null), 2000);
      } catch (err) {}
    }
  };

  const [messages, setMessages] = useState<Message[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY_MESSAGES);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed;
        }
      }
    } catch (e) {
      console.warn("Could not load saved chat history:", e);
    }
    return [INITIAL_WELCOME_MESSAGE];
  });

  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [threadId, setThreadId] = useState<string>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY_THREAD);
      if (saved) return saved;
    } catch (e) {}
    const newId = `thread_${Date.now()}`;
    try {
      localStorage.setItem(STORAGE_KEY_THREAD, newId);
    } catch (e) {}
    return newId;
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming]);

  // Persist messages to localStorage whenever they update
  useEffect(() => {
    try {
      const completeMessages = messages.filter(m => m.content && m.content.trim().length > 0);
      if (completeMessages.length > 0) {
        localStorage.setItem(STORAGE_KEY_MESSAGES, JSON.stringify(completeMessages));
      }
    } catch (e) {
      console.warn("Could not save messages to localStorage:", e);
    }
  }, [messages]);

  const handleResetChat = () => {
    if (messages.length > 1 && !confirm("Start a new chat session? This will clear your current conversation history.")) {
      return;
    }
    const newId = `thread_${Date.now()}`;
    setThreadId(newId);
    setMessages([INITIAL_WELCOME_MESSAGE]);
    try {
      localStorage.setItem(STORAGE_KEY_THREAD, newId);
      localStorage.setItem(STORAGE_KEY_MESSAGES, JSON.stringify([INITIAL_WELCOME_MESSAGE]));
    } catch (e) {}
  };

  const sendMessage = async (textToSend?: string) => {
    const promptText = (textToSend || input).trim();
    if (!promptText || isStreaming) return;

    const userMessage: Message = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: promptText
    };

    const assistantId = `assistant_${Date.now()}`;
    const assistantMessagePlaceholder: Message = {
      id: assistantId,
      role: 'assistant',
      content: ''
    };

    setMessages(prev => [...prev, userMessage, assistantMessagePlaceholder]);
    setInput('');
    setIsStreaming(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: {
            content: promptText,
            id: userMessage.id,
            role: 'user'
          },
          threadId: threadId
        })
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      if (!response.body) {
        throw new Error("No response body received from server");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let accumulated = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        accumulated += chunk;

        setMessages(prev =>
          prev.map(msg =>
            msg.id === assistantId ? { ...msg, content: accumulated } : msg
          )
        );
      }
    } catch (err: any) {
      console.error("Streaming error:", err);
      setMessages(prev =>
        prev.map(msg =>
          msg.id === assistantId
            ? { ...msg, content: `⚠️ Error communicating with AI server: ${err.message}. Please verify the backend and Ollama are running.` }
            : msg
        )
      );
    } finally {
      setIsStreaming(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="chat-container">
      {/* Quick Prompt Pills & Actions */}
      <div className="quick-prompts-bar">
        <span className="quick-prompts-label">
          <Sparkles size={14} className="sparkle-icon" /> Quick Inquiries:
        </span>
        <div className="quick-prompts-list">
          {QUICK_PROMPTS.map((prompt, idx) => (
            <button
              key={idx}
              className="quick-prompt-btn"
              onClick={() => sendMessage(prompt)}
              disabled={isStreaming}
            >
              {prompt}
            </button>
          ))}
        </div>
        <button
          className="btn-new-chat"
          onClick={handleResetChat}
          title="Start fresh conversation"
          disabled={isStreaming}
        >
          <RotateCcw size={13} /> New Chat
        </button>
      </div>

      {/* Messages Thread */}
      <div className="messages-thread">
        {messages.map((msg) => (
          <div key={msg.id} className={`message-row ${msg.role}`}>
            <div className={`message-avatar ${msg.role}`}>
              {msg.role === 'assistant' ? <Bot size={18} /> : <User size={18} />}
            </div>
            <div className="message-bubble-wrapper">
              <div className="message-bubble-header">
                <span className="message-role-title">
                  {msg.role === 'assistant' ? 'AI Market Analyst' : 'You'}
                </span>
                {msg.content && (
                  <button
                    className="btn-copy-msg"
                    onClick={() => handleCopyMessage(msg.id, msg.content)}
                    title="Copy message content"
                  >
                    {copiedId === msg.id ? (
                      <>
                        <Check size={12} className="copied-text" />
                        <span className="copied-text">Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy size={12} />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                )}
              </div>
              <div className="message-content">
                {msg.content ? (
                  <>
                    <MarkdownRenderer content={msg.content} />
                    {msg.role === 'assistant' && (
                      <MessageSourcingBar content={msg.content} />
                    )}
                  </>
                ) : isStreaming ? (
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                ) : (
                  <span className="empty-msg">No response.</span>
                )}
              </div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Composer */}
      <div className="chat-composer">
        <textarea
          className="chat-input"
          placeholder="Ask about a stock, your portfolio, or how to diversify (Press Enter to send)..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
          disabled={isStreaming}
        />
        <button
          className="send-btn"
          onClick={() => sendMessage()}
          disabled={!input.trim() || isStreaming}
        >
          {isStreaming ? <RefreshCw size={18} className="spin-icon" /> : <Send size={18} />}
        </button>
      </div>
    </div>
  );
};
