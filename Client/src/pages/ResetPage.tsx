import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { resetPassword } from "../api/auth";
import { AuthCard, Field, FormError, FormNotice, SubmitButton } from "../components/form";

export default function ResetPage() {
  const [params] = useSearchParams();
  const [token, setToken] = useState(params.get("token") ?? "");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [mismatch, setMismatch] = useState(false);

  const submit = useMutation({ mutationFn: () => resetPassword(token.trim(), password) });

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    const bad = password !== confirm;
    setMismatch(bad);
    if (!bad) submit.mutate();
  };

  if (submit.isSuccess) {
    return (
      <AuthCard title="Password updated">
        <div className="space-y-4">
          <FormNotice>{submit.data.detail}</FormNotice>
          <Link
            to="/login"
            className="inline-block rounded-md bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700"
          >
            Log in
          </Link>
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Reset password">
      <form onSubmit={onSubmit} className="space-y-4">
        <Field
          label="Reset token"
          name="token"
          required
          minLength={20}
          maxLength={128}
          hint="Paste the token from the reset email."
          value={token}
          onChange={(e) => setToken(e.target.value)}
        />
        <Field
          label="New password"
          name="password"
          type="password"
          autoComplete="new-password"
          required
          minLength={12}
          maxLength={128}
          hint="At least 12 characters."
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Field
          label="Confirm new password"
          name="confirm"
          type="password"
          autoComplete="new-password"
          required
          maxLength={128}
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
        />
        <FormError
          message={mismatch ? "Passwords do not match." : (submit.error?.message ?? null)}
        />
        <SubmitButton pending={submit.isPending}>
          {submit.isPending ? "Updating…" : "Update password"}
        </SubmitButton>
      </form>
    </AuthCard>
  );
}
