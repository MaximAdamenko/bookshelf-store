import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { forgotPassword } from "../api/auth";
import { AuthCard, Field, FormError, FormNotice, SubmitButton } from "../components/form";

export default function ForgotPage() {
  const [email, setEmail] = useState("");
  const submit = useMutation({ mutationFn: () => forgotPassword(email) });

  return (
    <AuthCard title="Forgot password">
      {submit.isSuccess ? (
        <div className="space-y-4">
          <FormNotice>{submit.data.detail}</FormNotice>
          <p className="text-sm text-stone-600">
            Got the email?{" "}
            <Link to="/reset" className="font-medium text-amber-700 hover:text-amber-800">
              Enter your reset token
            </Link>
          </p>
        </div>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submit.mutate();
          }}
          className="space-y-4"
        >
          <p className="text-sm text-stone-600">
            Enter your account email and we&rsquo;ll send a reset token.
          </p>
          <Field
            label="Email"
            name="email"
            type="email"
            autoComplete="email"
            required
            maxLength={254}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <FormError message={submit.error?.message ?? null} />
          <SubmitButton pending={submit.isPending}>
            {submit.isPending ? "Sending…" : "Send reset email"}
          </SubmitButton>
        </form>
      )}
      <p className="mt-4 text-sm">
        <Link to="/login" className="font-medium text-amber-700 hover:text-amber-800">
          Back to log in
        </Link>
      </p>
    </AuthCard>
  );
}
