// tailwind yang dipakai berulang, supaya tampilan konsisten.
export const inputClass =
  "block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-slate-100";

const buttonBase =
  "inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-60";

export const buttonPrimary = `${buttonBase} bg-blue-600 text-white hover:bg-blue-700`;
export const buttonSecondary = `${buttonBase} border border-slate-300 bg-white text-slate-700 hover:bg-slate-50`;
export const buttonDanger = `${buttonBase} border border-red-300 bg-white text-red-700 hover:bg-red-50`;