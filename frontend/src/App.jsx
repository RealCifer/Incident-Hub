import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import IncidentDetail from './pages/IncidentDetail';
import RcaForm from './pages/RcaForm';
import { Layout } from './components/Layout';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/incident/:id" element={<IncidentDetail />} />
          <Route path="/rca/:id" element={<RcaForm />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
