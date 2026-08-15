import { useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { register } from "../api/auth";
import { AuthCard, Field, FormError, SubmitButton } from "../components/form";
import { useAuth } from "../context/AuthContext";

export default function RegisterPage() {
  const { status } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    email: "",
    password: "",
    confirm: "",
    first_name: "",
    last_name: "",
    birth_date: "",
    phone: "",
  });
  const [mismatch, setMismatch] = useState(false);

  const submit = useMutation({
    // Empty optionals are omitted: the server forbids unknown/empty values.
    mutationFn: () =>
      register({
        email: form.email,
        password: form.password,
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        ...(form.birth_date ? { birth_date: form.birth_date } : {}),
        ...(form.phone.trim() ? { phone: form.phone.trim() } : {}),
      }),
    onSuccess: () => navigate("/login", { state: { registeredEmail: form.email } }),
  });

  if (status === "authenticated") return <Navigate to="/" replace />;

  const set = (key: keyof typeof form) => (e: ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    const bad = form.password !== form.confirm;
    setMismatch(bad);
    if (!bad) submit.mutate();
  };

  return (
    <AuthCard title="Create an account">
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <Field
            label="First name"
            name="first_name"
            autoComplete="given-name"
            required
            maxLength={60}
            value={form.first_name}
            onChange={set("first_name")}
          />
          <Field
            label="Last name"
            name="last_name"
            autoComplete="family-name"
            required
            maxLength={60}
            value={form.last_name}
            onChange={set("last_name")}
          />
        </div>
        <Field
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          required
          maxLength={254}
          value={form.email}
          onChange={set("email")}
        />
        <Field
          label="Password"
          name="password"
          type="password"
          autoComplete="new-password"
          required
          minLength={12}
          maxLength={128}
          hint="At least 12 characters."
          value={form.password}
          onChange={set("password")}
        />
        <Field
          label="Confirm password"
          name="confirm"
          type="password"
          autoComplete="new-password"
          required
          maxLength={128}
          value={form.confirm}
          onChange={set("confirm")}
        />
        <div className="grid grid-cols-2 gap-3">
          <Field
            label="Birth date (optional)"
            name="birth_date"
            type="date"
            value={form.birth_date}
            onChange={set("birth_date")}
          />
          <Field
            label="Phone (optional)"
            name="phone"
            type="tel"
            autoComplete="tel"
            value={form.phone}
            onChange={set("phone")}
          />
        </div>
        <FormError
          message={mismatch ? "Passwords do not match." : (submit.error?.message ?? null)}
        />
        <SubmitButton pending={submit.isPending}>
          {submit.isPending ? "Creating…" : "Create account"}
        </SubmitButton>
      </form>
      <p className="mt-4 text-sm text-stone-600">
        Already have an account?{" "}
        <Link to="/login" className="font-medium text-amber-700 hover:text-amber-800">
          Log in
        </Link>
      </p>
    </AuthCard>
  );
}
