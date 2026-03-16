import React, { useState, useEffect, useRef } from 'react';
import ChatFeed from './ChatFeed';
import InputBox from './InputBox';
import { RefreshCw, Download } from 'lucide-react';
import './ChatMain.css';

const API_BASE_URL = "http://localhost:8000/api";

/**
 * ChatMain — Core chat interface with SSE streaming.
 *
 * KEY DESIGN DECISIONS:
 *
 * 1. streamingRef — We use a ref (not state) to track whether we are currently
 *    streaming. This prevents the useEffect[activeSessionId] from calling
 *    fetchSessionMessages during a live stream, which would erase the in-flight
 *    SSE messages and cause the "blank page" bug on new chats.
 *
 * 2. streamDoneRef — Tracks whether the server has sent the 'done' event.
 *    We use a ref because the EventSource.onerror handler closes over the
 *    initial value of any state variable. A ref gives us the live value.
 *
 * 3. Single token event — The backend sends the complete answer as ONE SSE
 *    event (not chunked), so we avoid WSGI buffering issues. The content
 *    arrives instantly and renders with complete markdown.
 */
const ChatMain = ({ activeSessionId, setActiveSessionId }) => {
  const [messages, setMessages] = useState([]);
  const [isThinking, setIsThinking] = useState(false);
  const [sessionTitle, setSessionTitle] = useState('Financial Query Analysis');

  // Refs for SSE lifecycle — must be refs (not state) so closures see live values
  const streamingRef = useRef(false);
  const streamDoneRef = useRef(false);

  /**
   * Load chat history from the backend when switching sessions.
   * CRITICAL: Skip this if we're in the middle of streaming (streamingRef),
   * otherwise it overwrites the in-flight messages with the DB snapshot.
   */
  useEffect(() => {
    if (streamingRef.current) return; // Don't overwrite mid-stream

    if (activeSessionId) {
      fetchSessionMessages(activeSessionId);
    } else {
      setMessages([]);
      setSessionTitle('Financial Query Analysis');
    }
  }, [activeSessionId]);

  const getHeaders = () => ({
    'Authorization': `Bearer ${localStorage.getItem('fq-token')}`,
    'Content-Type': 'application/json'
  });

  const fetchSessionMessages = async (id) => {
    try {
      const res = await fetch(`${API_BASE_URL}/sessions/${id}/`, {
        headers: getHeaders()
      });
      if (res.status === 401) return; // Silent failure or handle in App
      const data = await res.json();
      setMessages(data.messages || []);
      if (data.title) setSessionTitle(data.title);
    } catch (err) {
      console.error('Failed to load session', err);
    }
  };

  /** Export current conversation as .txt */
  const handleExportChat = () => {
    if (messages.length === 0) return;
    const content = messages
      .map((m) => `[${m.role.toUpperCase()}]\n${m.content}\n`)
      .join('\n---\n\n');
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `finquery-${sessionTitle.slice(0, 20)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  /** Reload current session messages from DB */
  const handleRefresh = () => {
    if (activeSessionId && !streamingRef.current) {
      fetchSessionMessages(activeSessionId);
    }
  };

  const handleSendMessage = async (text) => {
    if (!text.trim() || streamingRef.current) return;

    // ── Create new session if none exists ──
    let currentSessionId = activeSessionId;
    if (!currentSessionId) {
      try {
        const res = await fetch(`${API_BASE_URL}/sessions/`, {
          method: 'POST',
          headers: getHeaders(),
          body: JSON.stringify({ title: text.substring(0, 40) }),
        });
        const data = await res.json();
        currentSessionId = data.id;
        setActiveSessionId(currentSessionId);
        setSessionTitle(text.substring(0, 40));
      } catch (err) {
        console.error('Failed to create session', err);
        return;
      }
    }

    // ── Add user message to UI immediately ──
    const userMsgId = Date.now().toString();
    setMessages((prev) => [...prev, { id: userMsgId, role: 'user', content: text }]);

    // ── Add assistant placeholder ──
    const assistantMsgId = (Date.now() + 1).toString();
    setMessages((prev) => [
      ...prev,
      {
        id: assistantMsgId,
        role: 'assistant',
        content: '',
        reasoning: '',
        reasoningDone: false,
        code: '',
        raw_data_json: null,
      },
    ]);

    // ── Lock streaming state ──
    setIsThinking(true);
    streamingRef.current = true;
    streamDoneRef.current = false;

    // ── SSE Connection with Token ──
    try {
      const token = localStorage.getItem('fq-token');
      // SimpleJWT often doesn't like tokens in query params but we've updated views 
      // to handle standard fetch. For EventSource, we need to pass token in query if backend supports it
      // OR use a polyfill that supports headers. 
      // Since we updated DRF views but EventSource is natively limited, 
      // let's ensure the backend can accept token in query string OR just use what we have.
      // ACTUALLY: Let's use fetch for SSE if we want headers, or just append token.
      const streamUrl = `${API_BASE_URL}/query/stream/?query=${encodeURIComponent(text)}&session_id=${currentSessionId}&token=${token}`;
      const eventSource = new EventSource(streamUrl);

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          switch (data.type) {
            case 'status':
              // Optional: could show a toast. Currently silent.
              break;

            case 'reasoning_token':
              // Accumulate CoT tokens into the reasoning field
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMsgId
                    ? { ...msg, reasoning: (msg.reasoning || '') + data.content }
                    : msg
                )
              );
              break;

            case 'reasoning_done':
              // Seal the CoT box — replace reasoning with clean version if provided
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMsgId
                    ? {
                        ...msg,
                        reasoning: data.content || msg.reasoning,
                        reasoningDone: true,
                      }
                    : msg
                )
              );
              break;

            case 'token':
              // Main answer — append to content
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMsgId
                    ? { ...msg, content: (msg.content || '') + data.content }
                    : msg
                )
              );
              break;

            case 'sql':
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMsgId ? { ...msg, code: data.content } : msg
                )
              );
              break;

            case 'raw_data':
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMsgId
                    ? { ...msg, raw_data_json: data.content }
                    : msg
                )
              );
              break;

            case 'done':
              // Mark complete BEFORE closing — onerror may fire synchronously
              streamDoneRef.current = true;
              streamingRef.current = false;
              setIsThinking(false);
              eventSource.close();
              break;

            default:
              break;
          }
        } catch (err) {
          console.error('Error parsing SSE event:', err, event.data);
        }
      };

      eventSource.onerror = () => {
        // Browser fires onerror on BOTH real errors AND the normal close
        // after the server ends the stream. We check the ref to distinguish.
        if (streamDoneRef.current) {
          // Expected close after 'done' — do nothing
          eventSource.close();
          return;
        }

        // Real error — server crashed or timed out before sending 'done'
        console.error('SSE connection error (server did not send done event)');
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgId
              ? {
                  ...msg,
                  content:
                    (msg.content || '') +
                    '\n\n⚠️ **Stream error.** The backend disconnected before finishing. ' +
                    'Please try again or refresh the page.',
                }
              : msg
          )
        );
        streamingRef.current = false;
        setIsThinking(false);
        eventSource.close();
      };
    } catch (error) {
      console.error('Failed to open SSE stream:', error);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsgId
            ? {
                ...msg,
                content:
                  '❌ Could not reach the backend API. Is the server running on port 8000?',
              }
            : msg
        )
      );
      streamingRef.current = false;
      setIsThinking(false);
    }
  };

  return (
    <div className="chat-main-container">
      {/* ── Header ── */}
      <header className="chat-header">
        <div className="header-title">
          <div className="icon">📊</div>
          <h2 className="session-title">{sessionTitle}</h2>
        </div>
        <div className="header-actions">
          {messages.length > 0 && (
            <>
              <button
                className="icon-btn"
                onClick={handleRefresh}
                title="Reload session from database"
                disabled={isThinking}
              >
                <RefreshCw size={16} className={isThinking ? 'spin' : ''} />
              </button>
              <button
                className="pill-btn"
                onClick={handleExportChat}
                title="Export this conversation as a .txt file"
              >
                <Download size={15} />
                <span>Export</span>
              </button>
            </>
          )}
        </div>
      </header>

      {/* ── Chat Feed / Hero State ── */}
      <div className="chat-scroll-area">
        {messages.length === 0 ? (
          <div className="hero-state">
            <div className="hero-icon">🤖</div>
            <h2 className="hero-title">FinQuery AI</h2>
            <p className="hero-subtitle">
              Your intelligent financial analyst. Ask me about your database, run SQL queries, or
              get portfolio insights.
            </p>
            <div className="hero-chips">
              <button className="hero-chip" onClick={() => handleSendMessage('How many active loans do we have and what is the total outstanding balance?')}>
                💰 Loan Overview
              </button>
              <button className="hero-chip" onClick={() => handleSendMessage('Who are the top 5 customers by total investment balance?')}>
                📈 Top Customers
              </button>
              <button className="hero-chip" onClick={() => handleSendMessage('What is the average credit score across all customers?')}>
                🎯 Credit Analysis
              </button>
              <button className="hero-chip" onClick={() => handleSendMessage('Show me a risk breakdown: how many customers have low, medium, and high credit scores?')}>
                ⚠️ Risk Report
              </button>
            </div>
          </div>
        ) : (
          <ChatFeed messages={messages} isThinking={isThinking} onRetry={handleSendMessage} />
        )}
      </div>

      {/* ── Input Box ── */}
      <div className="input-container-wrapper">
        <InputBox onSend={handleSendMessage} isProcessing={isThinking} />
      </div>
    </div>
  );
};

export default ChatMain;
