import type { InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from "react";

export function AuthCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="mx-auto max-w-md py-10">
      <h1 className="text-2xl font-bold text-stone-900">{title}</h1>
      <div className="mt-6 rounded-lg border border-stone-200 bg-white p-6 shadow-sm">{children}</div>
    </div>
  );
}

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
}

export function Field({ label, hint, id, ...rest }: FieldProps) {
  const inputId = id ?? rest.name;
  return (
    <div>
      <label htmlFor={inputId} className="block text-sm font-medium text-stone-700">
        {label}
      </label>
      <input
        id={inputId}
        {...rest}
        className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2 text-sm focus:border-amber-500 focus:outline-none disabled:bg-stone-100"
      />
      {hint && <p className="mt-1 text-xs text-stone-500">{hint}</p>}
    </div>
  );
}

interface TextAreaFieldProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  hint?: string;
}

export function TextAreaField({ label, hint, id, ...rest }: TextAreaFieldProps) {
  const inputId = id ?? rest.name;
  return (
    <div>
      <label htmlFor={inputId} className="block text-sm font-medium text-stone-700">
        {label}
      </label>
      <textarea
        id={inputId}
        {...rest}
        className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2 text-sm focus:border-amber-500 focus:outline-none disabled:bg-stone-100"
      />
      {hint && <p className="mt-1 text-xs text-stone-500">{hint}</p>}
    </div>
  );
}

export function FormError({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{message}</div>
  );
}

export function FormNotice({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">
      {children}
    </div>
  );
}

export function SubmitButton({ pending, children }: { pending: boolean; children: ReactNode }) {
  return (
    <button
      type="submit"
      disabled={pending}
      className="w-full rounded-md bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-50"
    >
      {children}
    </button>
  );
}
