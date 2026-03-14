import { useState } from 'react';
import Sidebar from './components/Sidebar/Sidebar';
import ChatMain from './components/Chat/ChatMain';
import AnalyticsMain from './components/Analytics/AnalyticsMain';
import { ThemeProvider } from './context/ThemeContext';
import './App.css';

/**
 * App - Root component.
 * Wrapped with ThemeProvider for global dark/light/midnight theme support.
 */
function App() {
  const [activeView, setActiveView] = useState('chat'); // 'chat' | 'analytics'
  const [activeSessionId, setActiveSessionId] = useState(null);

  return (
    <ThemeProvider>
      <div className="app-container">
        <Sidebar
          activeView={activeView}
          setActiveView={setActiveView}
          activeSessionId={activeSessionId}
          setActiveSessionId={setActiveSessionId}
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
