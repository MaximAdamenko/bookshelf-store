import { useEffect, useState } from "react";
import { Link, Navigate, useLocation } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { login, verifyLogin } from "../api/auth";
import { ApiError } from "../api/client";
import { AuthCard, Field, FormError, FormNotice, SubmitButton } from "../components/form";
import { useAuth } from "../context/AuthContext";

const RESEND_COOLDOWN_SECONDS = 30;

interface Challenge {
  token: string;
  expiresAt: number;
}

function useTicker(active: boolean) {
  const [, setTick] = useState(0);
  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, [active]);
}

function formatSeconds(total: number) {
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

export default function LoginPage() {
  const { status, completeLogin } = useAuth();
  const location = useLocation();
  const state = (location.state ?? {}) as { from?: { pathname?: string }; registeredEmail?: string };
  const from = state.from?.pathname ?? "/";

  const [email, setEmail] = useState(state.registeredEmail ?? "");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [sentAt, setSentAt] = useState(0);

  useTicker(challenge !== null);

  const sendCode = useMutation({
    mutationFn: () => login(email, password),
    onSuccess: (res) => {
      setChallenge({ token: res.challenge_token, expiresAt: Date.now() + res.expires_in * 1000 });
      setSentAt(Date.now());
      setCode("");
      verify.reset();
    },
  });

  const verify = useMutation({
    mutationFn: () => verifyLogin(challenge!.token, code),
    onSuccess: (res) => completeLogin(res.access_token),
  });

  // Renders on mount for an already-authed visitor, and again after completeLogin
  // flips status — the same line is the post-login redirect to `from`.
  if (status === "authenticated") return <Navigate to={from} replace />;

  const now = Date.now();
  const expiresIn = challenge ? Math.max(0, Math.ceil((challenge.expiresAt - now) / 1000)) : 0;
  const resendIn = Math.max(0, RESEND_COOLDOWN_SECONDS - Math.floor((now - sentAt) / 1000));

  if (challenge) {
    const verifyError =
      verify.error instanceof ApiError && verify.error.status === 401
        ? "That code didn't work — it may be wrong or expired."
        : (verify.error?.message ?? null);

    return (
      <AuthCard title="Enter your code">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            verify.mutate();
          }}
          className="space-y-4"
        >
          <p className="text-sm text-stone-600">
            We emailed a 6-digit code to <span className="font-medium">{email}</span>.{" "}
            {expiresIn > 0
              ? `It expires in ${formatSeconds(expiresIn)}.`
              : "It has expired — send a new one."}
          </p>
          <Field
            label="Code"
            name="code"
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="[0-9]{6}"
            maxLength={6}
            required
            autoFocus
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
          />
          <FormError message={verifyError ?? sendCode.error?.message ?? null} />
          <SubmitButton pending={verify.isPending}>
            {verify.isPending ? "Checking…" : "Sign in"}
          </SubmitButton>
          <div className="flex items-center justify-between text-sm">
            <button
              type="button"
              onClick={() => sendCode.mutate()}
              disabled={resendIn > 0 || sendCode.isPending}
              className="font-medium text-amber-700 hover:text-amber-800 disabled:text-stone-400"
            >
              {sendCode.isPending
                ? "Sending…"
                : resendIn > 0
                  ? `Resend code (${resendIn}s)`
                  : "Resend code"}
            </button>
            <button
              type="button"
              onClick={() => {
                setChallenge(null);
                setPassword("");
                setCode("");
                sendCode.reset();
                verify.reset();
              }}
              className="text-stone-500 hover:text-stone-700"
            >
              Use a different account
            </button>
          </div>
        </form>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Log in">
      <div className="space-y-4">
        {state.registeredEmail && <FormNotice>Account created. Log in to continue.</FormNotice>}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            sendCode.mutate();
          }}
          className="space-y-4"
        >
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
          <Field
            label="Password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            maxLength={128}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <FormError message={sendCode.error?.message ?? null} />
          <SubmitButton pending={sendCode.isPending}>
            {sendCode.isPending ? "Checking…" : "Continue"}
          </SubmitButton>
        </form>
        <div className="flex items-center justify-between text-sm">
          <Link to="/forgot" className="font-medium text-amber-700 hover:text-amber-800">
            Forgot password?
          </Link>
          <span className="text-stone-600">
            New here?{" "}
            <Link to="/register" className="font-medium text-amber-700 hover:text-amber-800">
              Create an account
            </Link>
          </span>
        </div>
      </div>
    </AuthCard>
  );
}
