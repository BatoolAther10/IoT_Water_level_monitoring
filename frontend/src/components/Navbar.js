import React, { useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { ThemeContext } from '../context/ThemeContext';
import './Navbar.css';

const Navbar = () => {
  const { user, logout } = useContext(AuthContext);
  const { isDarkMode, toggleDarkMode } = useContext(ThemeContext);
  const navigate = useNavigate();

  /**
   * Handle user logout
   * - Clear auth context
   * - Remove tokens from localStorage
   * - Redirect to login page
   */
  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  /**
   * Toggle between light and dark mode
   * - Updates theme context
   * - Saves preference to localStorage
   * - Updates document class for CSS theming
   */
  const handleThemeToggle = () => {
    toggleDarkMode();
  };

  return (
    <nav className="navbar">
      {/* Left Side - Logo and Title */}
      <div className="navbar-left">
        {/* College Logo */}
        <div className="navbar-logo-container">
          <img 
            src="https://bajraionline.com/wp-content/uploads/2022/08/Vasavi-College-of-Engineering-logo.gif" 
            alt="Vasavi College of Engineering Logo" 
            className="navbar-logo-img"
            title="Vasavi College of Engineering"
          />
        </div>

        {/* App Title */}
        <h1 className="navbar-title"> Water Tank Monitor</h1>
      </div>

      {/* Right Side Controls */}
      <div className="navbar-controls">
        {/* Dark Mode Toggle Button */}
        <button
          className="btn-theme"
          onClick={handleThemeToggle}
          title={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          aria-label="Toggle dark mode"
        >
          {isDarkMode ? '☀️' : '🌙'}
        </button>

        {/* User Email Display */}
        {user && (
          <span className="user-info">
            👤 {user.email}
          </span>
        )}

        {/* Logout Button */}
        <button
          className="btn-logout"
          onClick={handleLogout}
          title="Logout from your account"
        >
          Logout
        </button>
      </div>
    </nav>
  );
};

export default Navbar;