import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import './Sidebar.css';

const Sidebar = () => {
  const location = useLocation();

  /**
   * Menu items for sidebar navigation
   * Each item has: path, label, and icon
   */
  const menuItems = [
    {
      path: '/',
      label: 'Dashboard',
      icon: '📊'
    },
    {
      path: '/realtime',
      label: 'Real-time',
      icon: '⚡'
    },
    {
      path: '/model-comparison',
      label: 'Model Comparison',
      icon: '🔄'
    },
    {
      path: '/batch-prediction',
      label: 'Batch Upload',
      icon: '📤'
    },
    {
      path: '/node-creation',
      label: 'Add Node',
      icon: '➕'
    }
  ];

  return (
    <aside className="sidebar">
      {/* Sidebar Navigation Items */}
      {menuItems.map((item) => (
        <Link
          key={item.path}
          to={item.path}
          className={`sidebar-item ${
            location.pathname === item.path ? 'active' : ''
          }`}
          title={item.label}
        >
          {/* Icon */}
          <span className="icon">{item.icon}</span>

          {/* Label */}
          <span>{item.label}</span>
        </Link>
      ))}
    </aside>
  );
};

export default Sidebar;