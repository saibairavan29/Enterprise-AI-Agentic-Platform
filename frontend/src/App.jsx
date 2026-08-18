import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';

import 'bootstrap/dist/css/bootstrap.min.css';

// Route guard component
const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center min-vh-100" style={{ backgroundColor: '#0a0c16', color: '#ffffff' }}>
        <div className="spinner-border text-cyan" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    );
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
};

// Simple NotFound Component
const NotFound = () => {
  return (
    <div className="d-flex flex-column justify-content-center align-items-center min-vh-100" style={{ backgroundColor: '#0a0c16', color: '#ffffff' }}>
      <h1 className="text-gradient-glowing fw-bold display-1">404</h1>
      <p className="text-secondary mb-4">The requested interface does not exist or has not been deployed.</p>
      <a href="/" className="btn btn-premium-primary">Return Home</a>
    </div>
  );
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Public Auth Routes */}
          <Route path="/login" element={<Login />} />
          
          {/* Protected Enterprise Interfaces */}
          <Route 
            path="/" 
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            } 
          />
          
          {/* Fallbacks */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
