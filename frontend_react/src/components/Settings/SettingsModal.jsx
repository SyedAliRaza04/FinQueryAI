import React from 'react';
import { X, Moon, Sun, Palette, Type, Server, CheckCircle } from 'lucide-react';
import { useTheme, THEMES, ACCENTS } from '../../context/ThemeContext';
import './SettingsModal.css';

/**
 * SettingsModal - A full-featured settings panel with:
 *  - Theme selection (Dark / Light / Midnight)
 *  - Accent color picker
 *  - Font size control
 *  - Backend model info display
 */
const SettingsModal = ({ onClose }) => {
  const { theme, setTheme, accent, setAccent, fontSize, setFontSize } = useTheme();

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-panel" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="settings-header">
          <h2>Settings</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Close settings">
            <X size={20} />
          </button>
        </div>

        <div className="settings-body">
          {/* ── Appearance ── */}
          <section className="settings-section">
            <h3 className="settings-section-title">
              <Palette size={16} /> Appearance
            </h3>

            <label className="settings-label">Theme</label>
            <div className="theme-options">
              <button
                className={`theme-option ${theme === THEMES.dark ? 'active' : ''}`}
                onClick={() => setTheme(THEMES.dark)}
              >
                <Moon size={18} />
                <span>Dark</span>
                {theme === THEMES.dark && <CheckCircle size={14} className="check" />}
              </button>
              <button
                className={`theme-option ${theme === THEMES.light ? 'active' : ''}`}
                onClick={() => setTheme(THEMES.light)}
              >
                <Sun size={18} />
                <span>Light</span>
                {theme === THEMES.light && <CheckCircle size={14} className="check" />}
              </button>
              <button
                className={`theme-option ${theme === THEMES.midnight ? 'active' : ''}`}
                onClick={() => setTheme(THEMES.midnight)}
              >
                <span style={{ fontSize: '1rem' }}>🌌</span>
                <span>Midnight</span>
                {theme === THEMES.midnight && <CheckCircle size={14} className="check" />}
              </button>
            </div>

            <label className="settings-label" style={{ marginTop: '1.25rem' }}>Accent Color</label>
            <div className="accent-options">
              {Object.entries(ACCENTS).map(([key, val]) => (
                <button
                  key={key}
                  className={`accent-swatch ${accent === key ? 'active' : ''}`}
                  style={{ backgroundColor: val.color }}
                  onClick={() => setAccent(key)}
                  title={val.name}
                >
                  {accent === key && <CheckCircle size={14} style={{ color: '#000' }} />}
                </button>
              ))}
            </div>
          </section>

          {/* ── Typography ── */}
          <section className="settings-section">
            <h3 className="settings-section-title">
              <Type size={16} /> Typography
            </h3>
            <label className="settings-label">Font Size</label>
            <div className="font-options">
              {['small', 'medium', 'large'].map((size) => (
                <button
                  key={size}
                  className={`font-option ${fontSize === size ? 'active' : ''}`}
                  onClick={() => setFontSize(size)}
                >
                  {size === 'small' && <span style={{ fontSize: '0.75rem' }}>Aa</span>}
                  {size === 'medium' && <span style={{ fontSize: '1rem' }}>Aa</span>}
                  {size === 'large' && <span style={{ fontSize: '1.25rem' }}>Aa</span>}
                  <span>{size.charAt(0).toUpperCase() + size.slice(1)}</span>
                </button>
              ))}
            </div>
          </section>

          {/* ── Backend Info ── */}
          <section className="settings-section">
            <h3 className="settings-section-title">
              <Server size={16} /> Backend
            </h3>
            <div className="info-row">
              <span className="info-key">Model</span>
              <span className="info-value info-badge">Llama 3.1 (Ollama)</span>
            </div>
            <div className="info-row">
              <span className="info-key">Backend URL</span>
              <span className="info-value">http://localhost:8000</span>
            </div>
            <div className="info-row">
              <span className="info-key">Status</span>
              <span className="info-value" style={{ color: '#34d399', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#34d399', display: 'inline-block' }} />
                Connected
              </span>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};

export default SettingsModal;
