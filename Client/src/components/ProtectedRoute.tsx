import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import NotFoundPage from "../pages/NotFoundPage";

function PageSpinner() {
  return (
    <div className="flex justify-center py-24">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-stone-300 border-t-amber-600" />
    </div>
  );
}

export function ProtectedRoute() {
  const { status } = useAuth();
  const location = useLocation();
  if (status === "loading") return <PageSpinner />;
  if (status === "anonymous") return <Navigate to="/login" state={{ from: location }} replace />;
  return <Outlet />;
}

// Non-admins see the 404 page, not a "forbidden" screen: same stance as the
// server — existence of admin surfaces is never confirmed.
export function AdminRoute() {
  const { status, isAdmin } = useAuth();
  const location = useLocation();
  if (status === "loading") return <PageSpinner />;
  if (status === "anonymous") return <Navigate to="/login" state={{ from: location }} replace />;
  if (!isAdmin) return <NotFoundPage />;
  return <Outlet />;
}
