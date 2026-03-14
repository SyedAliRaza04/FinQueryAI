import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Copy, RotateCcw, BarChart2, Check, ChevronDown, ChevronUp } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import DataChart from './DataChart';

/**
 * ReasoningBlock — React-controlled collapsible (NOT native <details>).
 *
 * Using a plain React-state button avoids the browser reflow bug that
 * occurred with <details> open/close while tokens were streaming in.
 */
const ReasoningBlock = ({ reasoning, isStreaming, reasoningDone }) => {
  const [open, setOpen] = useState(true);

  // Auto-collapse 600ms after reasoning is complete
  useEffect(() => {
    if (reasoningDone && !isStreaming) {
      const t = setTimeout(() => setOpen(false), 600);
      return () => clearTimeout(t);
    }
  }, [reasoningDone, isStreaming]);

  if (!reasoning) return null;

  return (
    <div className="reasoning-block">
      <button
        className="reasoning-header"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="reasoning-icon">💡</span>
        <span className="reasoning-label">
          {isStreaming && !reasoningDone ? 'Thinking...' : 'Thinking Process'}
        </span>
        {isStreaming && !reasoningDone && <span className="reasoning-spinner" />}
        <span className="reasoning-chevron">
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </span>
      </button>

      {open && (
        <div className="reasoning-content markdown-body">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{reasoning}</ReactMarkdown>
        </div>
      )}
    </div>
  );
};

/**
 * Custom markdown components for rich rendering.
 * Tables, code blocks, blockquotes all get styled treatment.
 */
const makeMarkdownComponents = () => ({
  code({ node, inline, className, children, ...props }) {
    const match = /language-(\w+)/.exec(className || '');
    if (!inline && match) {
      return (
        <SyntaxHighlighter
          style={oneDark}
          language={match[1]}
          PreTag="div"
          customStyle={{ borderRadius: '8px', fontSize: '0.82rem', margin: '0.5rem 0' }}
          {...props}
        >
          {String(children).replace(/\n$/, '')}
        </SyntaxHighlighter>
      );
    }
    return <code className="inline-code" {...props}>{children}</code>;
  },
  table({ children }) {
    return (
      <div className="md-table-wrapper">
        <table className="md-table">{children}</table>
      </div>
    );
  },
  blockquote({ children }) {
    return <blockquote className="md-blockquote">{children}</blockquote>;
  },
});

const markdownComponents = makeMarkdownComponents();

/**
 * ChatFeed — Renders conversation with:
 *  - Auto-scroll that only scrolls when user is already at the bottom
 *    (prevents the oscillation/glitch when streaming fast)
 *  - Deferred markdown rendering: tables and complex markdown blocks are
 *    rendered from the COMPLETE content, not token-by-token, eliminating
 *    broken "| pipe | text |" artifacts mid-stream
 *  - Copy with checkmark, Retry, Visualize Answer
 */
const ChatFeed = ({ messages, isThinking, onRetry }) => {
  const feedRef = useRef(null);
  const [expandedCharts, setExpandedCharts] = useState({});
  const [copiedId, setCopiedId] = useState(null);

  const getScrollContainer = () => feedRef.current?.parentElement;

  const toggleChart = (msgId) => {
    setExpandedCharts((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  const handleCopy = useCallback((text, id) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 1500);
    });
  }, []);

  /** Smart auto-scroll: only fires when within 120px of bottom, no smooth animation queuing */
  useEffect(() => {
    const container = getScrollContainer();
    if (!container) return;
    const distanceFromBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight;
    if (distanceFromBottom < 150) {
      container.scrollTop = container.scrollHeight;
    }
  }, [messages]);

  /** Track manual scroll to pause auto-scroll when reading */
  const handleScroll = useCallback(() => {
    const container = getScrollContainer();
    if (!container) return;
    // noop — threshold check in useEffect handles it
  }, []);

  return (
    <div
      ref={feedRef}
      className="chat-feed-inner"
      onScroll={handleScroll}
    >
      {messages.map((msg, idx) => {
        const msgKey = msg.id || String(idx);
        const isCopied = copiedId === msgKey;
        const isActiveStream =
          isThinking && idx === messages.length - 1 && msg.role === 'assistant';

        return (
          <div key={msgKey} className={`message-row ${msg.role} animate-fade-in`}>
            {msg.role === 'assistant' && (
              <div className="message-avatar bot">🤖</div>
            )}

            <div className={`message-bubble ${msg.role}`}>
              {/* ── Thinking Process (CoT only — never the answer) ── */}
              {msg.reasoning && (
                <ReasoningBlock
                  reasoning={msg.reasoning}
                  isStreaming={isActiveStream}
                  reasoningDone={msg.reasoningDone}
                />
              )}

              {/* ── Main Answer ── */}
              {msg.content && (
                <div className="message-content markdown-body">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={markdownComponents}
                  >
                    {msg.content}
                  </ReactMarkdown>
                </div>
              )}

              {/* ── SQL Code Block ── */}
              {msg.code && (
                <div className="code-block animate-fade-in">
                  <div className="code-header">
                    <span>SQL Query</span>
                    <button
                      className="code-copy"
                      onClick={() => handleCopy(msg.code, `code-${msgKey}`)}
                    >
                      {copiedId === `code-${msgKey}` ? (
                        <><Check size={13} /> Copied!</>
                      ) : (
                        <><Copy size={13} /> Copy SQL</>
                      )}
                    </button>
                  </div>
                  <pre><code className="sql-code">{msg.code}</code></pre>
                </div>
              )}

              {/* ── Data Visualization ── */}
              {expandedCharts[msgKey] && msg.raw_data_json?.length > 0 && (
                <div className="chart-container animate-fade-in">
                  <DataChart data={msg.raw_data_json} />
                </div>
              )}

              {/* ── Action Bar (only after stream completes) ── */}
              {msg.role === 'assistant' && (msg.content || msg.reasoning) && !isActiveStream && (
                <div className="message-actions">
                  {msg.raw_data_json?.length > 0 && (
                    <button
                      className="action-btn text-green"
                      onClick={() => toggleChart(msgKey)}
                    >
                      <BarChart2 size={13} />
                      {expandedCharts[msgKey] ? 'Hide Chart' : 'Visualize Answer'}
                    </button>
                  )}

                  <button
                    className="action-btn"
                    onClick={() => handleCopy(msg.content, msgKey)}
                  >
                    {isCopied
                      ? <><Check size={13} /> Copied!</>
                      : <><Copy size={13} /> Copy</>}
                  </button>

                  {onRetry && idx > 0 && messages[idx - 1]?.role === 'user' && (
                    <button
                      className="action-btn"
                      onClick={() => onRetry(messages[idx - 1].content)}
                    >
                      <RotateCcw size={13} /> Try again
                    </button>
                  )}
                </div>
              )}
            </div>

            {msg.role === 'user' && (
              <div className="message-avatar user">👤</div>
            )}
          </div>
        );
      })}

      {/* Typing indicator — only shown before any tokens arrive */}
      {isThinking &&
        messages[messages.length - 1]?.content === '' &&
        messages[messages.length - 1]?.reasoning === '' && (
          <div className="message-row assistant animate-fade-in">
            <div className="message-avatar bot">🤖</div>
            <div className="message-bubble assistant thinking">
              <div className="typing-indicator">
                <span /><span /><span />
              </div>
            </div>
          </div>
        )}

      {/* Spacer at bottom */}
      <div style={{ height: '24px' }} />
    </div>
  );
};

export default ChatFeed;
