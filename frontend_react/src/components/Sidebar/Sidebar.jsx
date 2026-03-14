import React, { useState, useEffect } from 'react';
import { Plus, LayoutDashboard, Settings, Trash2, MessageSquare } from 'lucide-react';
import SettingsModal from '../Settings/SettingsModal';
import './Sidebar.css';

const API_BASE_URL = "http://localhost:8000/api";

/**
 * Sidebar - Main navigation panel with:
 * - New Chat button
 * - Analytics navigation
 * - Chat history with session delete
 * - Settings modal trigger in footer
 */
const Sidebar = ({ activeView, setActiveView, activeSessionId, setActiveSessionId }) => {
  const [sessions, setSessions] = useState([]);
  const [showSettings, setShowSettings] = useState(false);
  const [hoveredSession, setHoveredSession] = useState(null);

  useEffect(() => {
    fetchSessions();
  }, [activeSessionId]);

  const fetchSessions = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/sessions/`);
      const data = await res.json();
      setSessions(data);
    } catch (err) {
      console.error("Failed to fetch sessions", err);
    }
  };

  const handleNewChat = () => {
    setActiveSessionId(null);
    setActiveView('chat');
  };

  const handleSelectSession = (id) => {
    setActiveSessionId(id);
    setActiveView('chat');
  };

  const handleDeleteSession = async (e, id) => {
    e.stopPropagation(); // Don't trigger session select
    try {
      await fetch(`${API_BASE_URL}/sessions/${id}/`, { method: 'DELETE' });
      // If we deleted the active session, clear it
      if (activeSessionId === id) {
        setActiveSessionId(null);
        setActiveView('chat');
      }
      fetchSessions();
    } catch (err) {
      console.error("Failed to delete session", err);
    }
  };

  // Group sessions by date (today, this week, older)
  const groupedSessions = sessions.reduce((groups, session) => {
    const created = new Date(session.created_at || Date.now());
    const now = new Date();
    const diffDays = Math.floor((now - created) / (1000 * 60 * 60 * 24));
    const group = diffDays === 0 ? 'Today' : diffDays <= 7 ? 'This Week' : 'Older';
    if (!groups[group]) groups[group] = [];
    groups[group].push(session);
    return groups;
  }, {});

  return (
    <>
      <aside className="sidebar">
        {/* Header */}
        <div className="sidebar-header">
          <div className="logo-container">
            <div className="logo-icon">🤖</div>
            <h1 className="logo-text">FinQuery AI</h1>
          </div>
        </div>

        {/* New Chat */}
        <div className="sidebar-action">
          <button className="new-chat-btn" onClick={handleNewChat}>
            <Plus size={18} />
            <span>New Chat</span>
          </button>
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav">
          <button
            className={`nav-item ${activeView === 'analytics' ? 'active' : ''}`}
            onClick={() => setActiveView('analytics')}
          >
            <LayoutDashboard size={18} />
            <span>Analytics</span>
          </button>
        </nav>

        {/* Chat History */}
        <div className="sidebar-history-section">
          {Object.keys(groupedSessions).length === 0 ? (
            <div className="empty-history">
              <MessageSquare size={22} style={{ opacity: 0.4 }} />
              <span>No chats yet</span>
            </div>
          ) : (
            Object.entries(groupedSessions).map(([group, groupSessions]) => (
              <div key={group} className="history-group">
                <h3 className="section-title">{group}</h3>
                <div className="history-list">
                  {groupSessions.map((session) => (
                    <div
                      key={session.id}
                      className={`history-item-wrapper ${activeSessionId === session.id ? 'active' : ''}`}
                      onMouseEnter={() => setHoveredSession(session.id)}
                      onMouseLeave={() => setHoveredSession(null)}
                    >
                      <button
                        className="history-item"
                        onClick={() => handleSelectSession(session.id)}
                      >
                        <span className="truncate">{session.title}</span>
                      </button>
                      {hoveredSession === session.id && (
                        <button
                          className="delete-session-btn"
                          onClick={(e) => handleDeleteSession(e, session.id)}
                          title="Delete chat"
                        >
                          <Trash2 size={12} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer - Settings */}
        <div className="sidebar-footer">
          <div className="user-profile">
            <div className="avatar">👤</div>
            <span className="user-name">User</span>
          </div>
          <button
            className="icon-btn settings-btn"
            onClick={() => setShowSettings(true)}
            title="Open Settings"
          >
            <Settings size={18} />
          </button>
        </div>
      </aside>

      {/* Settings Modal */}
      {showSettings && <SettingsModal onClose={() => setShowSettings(false)} />}
    </>
  );
};

export default Sidebar;
