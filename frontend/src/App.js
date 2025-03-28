import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import MainLayout from './components/layout/MainLayout';

// Lazy load components
const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const PatientData = React.lazy(() => import('./pages/PatientData'));
const Jobs = React.lazy(() => import('./pages/Jobs'));
const Adapters = React.lazy(() => import('./pages/Adapters'));
const LiveInspection = React.lazy(() => import('./pages/LiveInspection'));

function App() {
  return (
    <Router>
      <React.Suspense fallback={
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin rounded-full h-32 w-32 border-t-2 border-b-2 border-blue-500"></div>
        </div>
      }>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="patients" element={<PatientData />} />
            <Route path="jobs" element={<Jobs />} />
            <Route path="adapters" element={<Adapters />} />
            <Route path="live-inspection" element={<LiveInspection />} />
          </Route>
        </Routes>

        {/* Toast notifications */}
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#363636',
              color: '#fff',
              borderRadius: '12px',
              padding: '16px',
              boxShadow: '0 10px 25px rgba(0, 0, 0, 0.1)',
            },
            success: {
              iconTheme: {
                primary: '#10B981',
                secondary: '#fff',
              },
            },
            error: {
              iconTheme: {
                primary: '#EF4444',
                secondary: '#fff',
              },
            },
          }}
        />
      </React.Suspense>
    </Router>
  );
}

export default App;
