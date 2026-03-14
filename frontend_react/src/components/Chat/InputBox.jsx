import React, { useState, useRef, useEffect } from 'react';
import { Lightbulb, Database, TrendingUp, FileText, ArrowUp } from 'lucide-react';

/**
 * InputBox - Smart query input with:
 *  - Auto-resizing textarea
 *  - Functional action chips that inject & submit real queries
 *  - Arrow send button (active state when text present)
 *  - Keyboard shortcut: Enter to send, Shift+Enter for newline
 */
const InputBox = ({ onSend, isProcessing }) => {
  const [text, setText] = useState('');
  const textareaRef = useRef(null);

  // Auto-resize textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [text]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    if (text.trim() && !isProcessing) {
      onSend(text.trim());
      setText('');
    }
  };

  /**
   * handleChipClick - Injects and immediately submits a predefined query.
   * Each chip has a distinct purpose for the financial analyst use case.
   */
  const handleChipClick = (query) => {
    if (!isProcessing) {
      onSend(query);
      setText('');
    }
  };

  const ACTION_CHIPS = [
    {
      id: 'brainstorm',
      label: 'Brainstorm',
      icon: <Lightbulb size={13} />,
      colorClass: 'text-yellow',
      // Triggers a full customer table exploration + visualization
      query: 'Give me a complete overview of all customers in the database. Show their loan status, balances, and geographic distribution. Visualize the results.',
    },
    {
      id: 'query-db',
      label: 'Query DB',
      icon: <Database size={13} />,
      colorClass: 'text-blue',
      // Fetches top 10 from all major tables
      query: 'Show me the top 10 records from each major table in the database including customers, loans, and transactions.',
    },
    {
      id: 'risk-report',
      label: 'Risk Report',
      icon: <TrendingUp size={13} />,
      colorClass: 'text-red',
      // Financial risk analysis query
      query: 'Generate a financial risk report. Show all customers with delinquent or defaulted loans, their outstanding balances, and risk exposure summary.',
    },
    {
      id: 'summary',
      label: 'Summarize',
      icon: <FileText size={13} />,
      colorClass: 'text-purple',
      // High-level portfolio summary
      query: 'Provide an executive summary of the entire financial portfolio: total assets under management, number of active customers, total loans outstanding, and key performance metrics.',
    },
  ];

  return (
    <div className="input-box-container">
      <div className={`input-wrapper ${isProcessing ? 'processing' : ''}`}>
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your financial data..."
          rows={1}
          disabled={isProcessing}
          className="chat-textarea"
        />

        <div className="input-footer">
          {/* Smart Action Chips */}
          <div className="action-chips">
            {ACTION_CHIPS.map((chip) => (
              <button
                key={chip.id}
                className={`chip ${isProcessing ? 'chip-disabled' : ''}`}
                onClick={() => handleChipClick(chip.query)}
                disabled={isProcessing}
                title={chip.query}
              >
                <span className={`chip-icon ${chip.colorClass}`}>{chip.icon}</span>
                {chip.label}
              </button>
            ))}
          </div>

          {/* Send Button */}
          <div className="submit-actions">
            <button
              className={`circle-btn ${text.trim() && !isProcessing ? 'active' : ''}`}
              onClick={handleSubmit}
              disabled={isProcessing || !text.trim()}
              aria-label="Send message"
              title="Send (Enter)"
            >
              <ArrowUp size={18} />
            </button>
          </div>
        </div>
      </div>
      <p className="input-hint">Press <kbd>Enter</kbd> to send · <kbd>Shift+Enter</kbd> for new line</p>
    </div>
  );
};

export default InputBox;
