import React, { createContext, useContext, useState, useEffect } from 'react';

/**
 * ThemeContext - Provides dark/light mode + accent color theme management
 * across the whole FinQuery application.
 */
const ThemeContext = createContext();

export const THEMES = {
  dark: 'dark',
  light: 'light',
  midnight: 'midnight',
};

export const ACCENTS = {
  emerald: { name: 'Emerald', color: '#34d399', hover: '#10b981' },
  blue: { name: 'Electric Blue', color: '#3b82f6', hover: '#2563eb' },
  purple: { name: 'Violet', color: '#8b5cf6', hover: '#7c3aed' },
  gold: { name: 'Gold', color: '#f59e0b', hover: '#d97706' },
};

export const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(() => localStorage.getItem('fq-theme') || THEMES.dark);
  const [accent, setAccent] = useState(() => localStorage.getItem('fq-accent') || 'emerald');
  const [fontSize, setFontSize] = useState(() => localStorage.getItem('fq-fontsize') || 'medium');

  useEffect(() => {
    // Apply theme to root element
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('fq-theme', theme);
  }, [theme]);

  useEffect(() => {
    // Apply accent color CSS variables to root
    const accentConfig = ACCENTS[accent] || ACCENTS.emerald;
    document.documentElement.style.setProperty('--accent-green', accentConfig.color);
    document.documentElement.style.setProperty('--accent-green-hover', accentConfig.hover);
    localStorage.setItem('fq-accent', accent);
  }, [accent]);

  useEffect(() => {
    const sizeMap = { small: '14px', medium: '16px', large: '18px' };
    document.documentElement.style.setProperty('--base-font-size', sizeMap[fontSize] || '16px');
    localStorage.setItem('fq-fontsize', fontSize);
  }, [fontSize]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, accent, setAccent, fontSize, setFontSize }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => useContext(ThemeContext);
