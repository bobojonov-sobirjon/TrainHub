import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import type { ReactNode } from "react";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return <p className="muted" style={{ padding: 24 }}>Загрузка...</p>;
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return children;
}
