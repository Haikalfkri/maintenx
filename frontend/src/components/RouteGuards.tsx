import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "../hooks/auth-context";
import type { Role } from "../types";
import { Spinner } from "./ui";

export function ProtectedRoute() {
    const { user, isLoading } = useAuth();
    const location = useLocation();

    if (isLoading) return <Spinner label="Checking session..." />;
    if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
    return <Outlet />;
}

export function RoleRoute({ allow }: { allow: Role[] }) {
  const { user } = useAuth();
  if (!user || !allow.includes(user.role)) return <Navigate to="/equipment" replace />;
  return <Outlet />;
}