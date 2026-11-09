import { ROLE_LABELS } from "../constants";
import { useAuth } from "../hooks/auth-context";
import { fullName } from "../utils";

export default function Dashboard() {
  const { user } = useAuth();
  if (!user) return null;

  return (
    <div>
      <h1 className="text-2xl font-bold">Welcome, {fullName(user)}</h1>
      <p className="mt-1 text-slate-600">
        {user.organization.name} · {ROLE_LABELS[user.role]}
      </p>
      <div className="mt-6 rounded-lg border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-500">
        KPI cards and charts will appear here once downtime and analytics are built.
      </div>
    </div>
  );
}