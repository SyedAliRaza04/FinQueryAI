import React, { useState, useEffect } from 'react';
import { Plus, LayoutDashboard, Settings, Trash2, MessageSquare, LogOut } from 'lucide-react';
import SettingsModal from '../Settings/SettingsModal';
import './Sidebar.css';

import logo from '../../assets/logo.png';
import chatIcon from '../../assets/chat-icon.png';

const API_BASE_URL = "http://localhost:8000/api";

/**
 * Sidebar - Main navigation panel with Auth support.
 */
const Sidebar = ({ activeView, setActiveView, activeSessionId, setActiveSessionId, onLogout }) => {
  const [sessions, setSessions] = useState([]);
  const [showSettings, setShowSettings] = useState(false);
  const [hoveredSession, setHoveredSession] = useState(null);
  const username = localStorage.getItem('fq-user') || 'User';

  useEffect(() => {
    fetchSessions();
  }, [activeSessionId]);

  const getHeaders = () => ({
    'Authorization': `Bearer ${localStorage.getItem('fq-token')}`,
    'Content-Type': 'application/json'
  });

  const fetchSessions = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/sessions/`, {
        headers: getHeaders()
      });
      if (res.status === 401) return onLogout();
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
    e.stopPropagation();
    try {
      await fetch(`${API_BASE_URL}/sessions/${id}/`, { 
        method: 'DELETE',
        headers: getHeaders()
      });
      if (activeSessionId === id) {
        setActiveSessionId(null);
        setActiveView('chat');
      }
      fetchSessions();
    } catch (err) {
      console.error("Failed to delete session", err);
    }
  };

  // Group sessions by date
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
        <div className="sidebar-header">
          <div className="logo-container">
            <img src={chatIcon} alt="Icon" className="sidebar-icon-img" />
            <img src={logo} alt="FinQuery AI" className="sidebar-logo-img" />
          </div>
        </div>

        <div className="sidebar-action">
          <button className="new-chat-btn" onClick={handleNewChat}>
            <Plus size={18} />
            <span>New Chat</span>
          </button>
        </div>

        <nav className="sidebar-nav">
          <button
            className={`nav-item ${activeView === 'analytics' ? 'active' : ''}`}
            onClick={() => setActiveView('analytics')}
          >
            <LayoutDashboard size={18} />
            <span>Analytics</span>
          </button>
        </nav>

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

        <div className="sidebar-footer">
          <div className="user-profile">
            <div className="avatar">👤</div>
            <span className="user-name">{username}</span>
          </div>
          <div className="footer-actions">
            <button
              className="icon-btn"
              onClick={() => setShowSettings(true)}
              title="Settings"
            >
              <Settings size={18} />
            </button>
            <button
              className="icon-btn logout-btn"
              onClick={onLogout}
              title="Log Out"
              style={{ color: '#ef4444' }}
            >
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </aside>

      {showSettings && <SettingsModal onClose={() => setShowSettings(false)} />}
    </>
  );
};
export default Sidebar;
