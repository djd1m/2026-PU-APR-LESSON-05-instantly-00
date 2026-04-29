import { useState, useEffect } from 'react';
import { Outlet, Navigate } from 'react-router-dom';
import { useAuthStore } from '../store/auth';

export default function ProtectedRoute() {
  const token = useAuthStore((state) => state.token);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (token) {
      useAuthStore.getState().checkAuth().finally(() => setChecked(true));
    } else {
      setChecked(true);
    }
  }, [token]);

  if (!checked) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-gray-400">Loading...</div>
      </div>
    );
  }

  if (!useAuthStore.getState().token) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
