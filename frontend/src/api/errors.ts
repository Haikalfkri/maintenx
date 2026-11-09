import { isAxiosError } from "axios";

export interface ParsedApiError {
  message: string;
  fieldErrors: Record<string, string>;
}

export function parseApiError(error: unknown): ParsedApiError {
  if (!isAxiosError(error)) {
    return { message: "Something went wrong.", fieldErrors: {} };
  }
  if (!error.response) {
    return { message: "Cannot reach the server. Check your connection.", fieldErrors: {} };
  }

  const data: unknown = error.response.data;
  if (data && typeof data === "object") {
    const fieldErrors: Record<string, string> = {};
    let message = "";
    for (const [key, value] of Object.entries(data)) {
      const text = Array.isArray(value) ? value.join(" ") : typeof value === "string" ? value : "";
      if (!text) continue;
      if (key === "detail" || key === "non_field_errors") message = text;
      else fieldErrors[key] = text;
    }
    if (message || Object.keys(fieldErrors).length > 0) {
      return { message: message || "Please fix the highlighted fields.", fieldErrors };
    }
  }
  return { message: `Request failed (${error.response.status}).`, fieldErrors: {} };
}

export function isNotFound(error: unknown): boolean {
  return isAxiosError(error) && error.response?.status === 404;
}