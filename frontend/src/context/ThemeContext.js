import React, { createContext, useState, useEffect } from 'react';

export const ThemeContext = createContext();

export const ThemeProvider = ({ children }) => {
  const [isDarkMode, setIsDarkMode] = useState(() => {
    try {
      const saved = localStorage.getItem('darkMode');
      console.log('[THEME] Initial darkMode from localStorage:', saved);
      return saved === 'true';
    } catch (error) {
      console.error('[THEME] Error reading darkMode from localStorage:', error);
      return false;
    }
  });

  // Apply theme on change
  useEffect(() => {
    try {
      console.log('[THEME] Applying theme. isDarkMode:', isDarkMode);
      
      // Save preference
      localStorage.setItem('darkMode', isDarkMode.toString());
      
      // Apply to document
      if (isDarkMode) {
        document.body.classList.add('dark-mode');
        console.log('[THEME] Dark mode enabled');
      } else {
        document.body.classList.remove('dark-mode');
        console.log('[THEME] Light mode enabled');
      }
    } catch (error) {
      console.error('[THEME] Error applying theme:', error);
    }
  }, [isDarkMode]);

  const toggleDarkMode = () => {
    try {
      console.log('[THEME] Toggle called. Current:', isDarkMode);
      setIsDarkMode(!isDarkMode);
    } catch (error) {
      console.error('[THEME] Error toggling theme:', error);
    }
  };

  const value = {
    isDarkMode,
    toggleDarkMode
  };

  console.log('[THEME] Provider state:', value);

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
};