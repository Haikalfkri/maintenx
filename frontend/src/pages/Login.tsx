import { zodResolver } from "@hookform/resolvers/zod";
import { isAxiosError } from "axios";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { parseApiError } from "../api/errors";
import { buttonPrimary, inputClass } from "../components/styles";
import { FormField } from "../components/ui";
import { useAuth } from "../hooks/auth-context";

const schema = z.object({
  email: z.email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});
type LoginValues = z.infer<typeof schema>;

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [serverError, setServerError] = useState("");

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({ resolver: zodResolver(schema) });

  // Kembali ke halaman yang tadinya ingin dibuka
  const from = (location.state as { from?: string } | null)?.from ?? "/";

  if (user) return <Navigate to={from} replace />;

  async function onSubmit(values: LoginValues) {
    setServerError("");
    try {
      await login(values.email, values.password);
      navigate(from, { replace: true });
    } catch (error) {
      if (isAxiosError(error) && error.response?.status === 401) {
        setServerError("Invalid email or password.");
      } else {
        setServerError(parseApiError(error).message);
      }
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold text-blue-700">MaintenX</h1>
        <p className="mb-6 text-sm text-slate-500">Sign in to your organization</p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <FormField label="Email" htmlFor="email" error={errors.email?.message}>
            <input id="email" type="email" autoComplete="username" className={inputClass} {...register("email")} />
          </FormField>
          <FormField label="Password" htmlFor="password" error={errors.password?.message}>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              className={inputClass}
              {...register("password")}
            />
          </FormField>

          {serverError && (
            <p className="rounded-md bg-red-50 p-3 text-sm text-red-700" role="alert">
              {serverError}
            </p>
          )}

          <button type="submit" disabled={isSubmitting} className={`${buttonPrimary} w-full`}>
            {isSubmitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}