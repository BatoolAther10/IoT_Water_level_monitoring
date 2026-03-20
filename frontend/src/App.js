import React, { Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import ProtectedRoute from './components/ProtectedRoute';

// Pages
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import NodeCreation from './pages/NodeCreation';

// Components
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';

// Styles
import './App.css';
import './styles/responsive.css';
import './styles/darkMode.css';

// ============================================================================
// ERROR BOUNDARY
// ============================================================================

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('❌ ERROR BOUNDARY CAUGHT:', error);
    console.error('ERROR INFO:', errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={styles.errorContainer}>
          <h1>⚠️ Something went wrong</h1>
          <p><strong>Error:</strong> {this.state.error?.message}</p>
          <button 
            onClick={() => {
              this.setState({ hasError: false });
              window.location.href = '/';
            }}
            style={styles.button}
          >
            Go to Home
          </button>
          <button 
            onClick={() => window.location.reload()}
            style={styles.button}
          >
            Reload Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

const styles = {
  errorContainer: {
    padding: '40px',
    textAlign: 'center',
    background: '#fee',
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    color: '#c00',
    fontFamily: 'monospace'
  },
  button: {
    padding: '10px 20px',
    margin: '10px',
    background: '#c00',
    color: 'white',
    border: 'none',
    borderRadius: '5px',
    cursor: 'pointer',
    fontSize: '16px'
  }
};

// ============================================================================
// LOADING FALLBACK
// ============================================================================

function LoadingFallback() {
  return (
    <div style={{ padding: '40px', textAlign: 'center' }}>
      <h2>Loading...</h2>
    </div>
  );
}

// ============================================================================
// APP COMPONENT
// ============================================================================

function AppContent() {
  return (
    <Router>
      <Routes>
        {/* ========== PUBLIC ROUTES ========== */}
        
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* ========== PROTECTED ROUTES ========== */}
        
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <div className="app-layout">
                <Navbar />
                
                <div className="app-container">
                  <Sidebar />
                  
                  <main className="main-content">
                    <Suspense fallback={<LoadingFallback />}>
                      <Routes>
                        <Route path="/" element={<Home />} />
                        <Route path="/node-creation" element={<NodeCreation />} />
                        
                        {/* Placeholder for future routes */}
                        <Route path="/realtime" element={<Home />} />
                        <Route path="/model-comparison" element={<Home />} />
                        <Route path="/batch-prediction" element={<Home />} />
                        
                        <Route path="*" element={<Navigate to="/" replace />} />
                      </Routes>
                    </Suspense>
                  </main>
                </div>
              </div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </Router>
  );
}

// ============================================================================
// MAIN APP
// ============================================================================

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <AppContent />
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;