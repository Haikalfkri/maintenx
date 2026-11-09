import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="py-16 text-center">
      <p className="text-4xl font-bold text-slate-300">404</p>
      <p className="mt-2 text-slate-600">This page does not exist.</p>
      <Link to="/" className="mt-4 inline-block text-sm font-medium text-blue-600 hover:underline">
        Back to dashboard
      </Link>
    </div>
  );
}