import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar/Sidebar';
import ChatMain from './components/Chat/ChatMain';
import AnalyticsMain from './components/Analytics/AnalyticsMain';
import LandingPage from './components/Landing/LandingPage';
import { ThemeProvider } from './context/ThemeContext';
import './App.css';

/**
 * App - Root component.
 * Handles authentication state and conditional rendering (Landing vs Dashboard).
 */
function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(!!localStorage.getItem('fq-token'));
  const [activeView, setActiveView] = useState('chat'); // 'chat' | 'analytics'
  const [activeSessionId, setActiveSessionId] = useState(null);

  const handleLoginSuccess = () => {
    setIsLoggedIn(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('fq-token');
    localStorage.removeItem('fq-refresh');
    localStorage.removeItem('fq-user');
    setIsLoggedIn(false);
    setActiveSessionId(null);
  };

  if (!isLoggedIn) {
    return (
      <ThemeProvider>
        <LandingPage onEnterApp={handleLoginSuccess} />
      </ThemeProvider>
    );
  }

  return (
    <ThemeProvider>
      <div className="app-container">
        <Sidebar
          activeView={activeView}
          setActiveView={setActiveView}
          activeSessionId={activeSessionId}
          setActiveSessionId={setActiveSessionId}
          onLogout={handleLogout}
        />

        <main className="main-content">
          {activeView === 'chat' ? (
            <ChatMain
              activeSessionId={activeSessionId}
              setActiveSessionId={setActiveSessionId}
            />
          ) : (
            <AnalyticsMain />
          )}
        </main>
      </div>
    </ThemeProvider>
  );
}

export default App;
