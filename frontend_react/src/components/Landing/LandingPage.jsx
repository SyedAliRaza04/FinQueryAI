import { useState } from 'react';
import './Landing.css';
import AuthOverlay from '../Auth/AuthOverlay';
import logo from '../../assets/logo.png';
import chatIcon from '../../assets/chat-icon.png';

/**
 * LandingPage - Premium entrance to FinQuery AI.
 */
function LandingPage({ onEnterApp }) {
  const [showAuth, setShowAuth] = useState(false);
  const [authMode, setAuthMode] = useState('login'); // 'login' | 'register'

  const handleStart = () => {
    setAuthMode('register');
    setShowAuth(true);
  };

  const handleLoginStatus = () => {
    setAuthMode('login');
    setShowAuth(true);
  };

  return (
    <div className="landing-container">
      <div className="animated-bg">
        <div className="glow-1"></div>
        <div className="glow-2"></div>
      </div>

      <div className="landing-content">
        <div className="landing-brand">
          <img src={logo} alt="FinQuery AI Logo" className="brand-logo" />
        </div>

        <div className="hero-visual">
          <div className="icon-wrapper">
            <img src={chatIcon} alt="AI Chatbot Icon" className="main-bot-icon" />
            <div className="icon-pulse"></div>
          </div>
        </div>

        <p className="landing-subtitle">
          The intelligent bridge between your natural language and complex financial databases. 
          Generate SQL, visualize trends, and gain deeper insights with local LLM precision.
        </p>
        
        <div className="landing-actions">
          <button className="btn-primary" onClick={handleStart}>
            Get Started
          </button>
          <button className="btn-secondary" onClick={handleLoginStatus}>
            Login to Account
          </button>
        </div>
      </div>

      {showAuth && (
        <AuthOverlay 
          mode={authMode} 
          setMode={setAuthMode}
          onClose={() => setShowAuth(false)} 
          onSuccess={onEnterApp}
        />
      )}
    </div>
  );
}

export default LandingPage;
