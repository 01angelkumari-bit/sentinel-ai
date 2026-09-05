"use client";
import { ArrowLeft, ArrowRight, CheckCircle2, Eye, EyeOff, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import { Auth3DShell } from "@/components/auth/auth-3d-shell";
import { apiFetch, authenticationError, fetchWithTimeout, warmAuthenticationApi } from "@/lib/auth";

export default function RegisterPage() {
  const submissionInFlight = useRef(false);
  const otpForm = useRef<HTMLFormElement>(null);
  const lastSubmittedOtp = useRef("");
  const router = useRouter();
  const [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [loading, setLoading] = useState(false),
    [step, setStep] = useState<"details" | "otp">("details"),
    [email, setEmail] = useState(""),
    [challengeId, setChallengeId] = useState(""),
    [otp, setOtp] = useState(""),
    [resendIn, setResendIn] = useState(0),
    [showPasswords, setShowPasswords] = useState(false);
  useEffect(() => {
    router.prefetch("/onboarding");
    warmAuthenticationApi();
  }, [router]);
  useEffect(() => {
    if (step !== "otp" || resendIn <= 0) return;
    const timer = window.setInterval(
      () => setResendIn((seconds) => Math.max(0, seconds - 1)),
      1_000,
    );
    return () => window.clearInterval(timer);
  }, [step, resendIn]);
  useEffect(() => {
    if (
      step === "otp" &&
      otp.length === 6 &&
      otp !== lastSubmittedOtp.current &&
      !loading
    ) {
      lastSubmittedOtp.current = otp;
      otpForm.current?.requestSubmit();
    }
  }, [loading, otp, step]);
  async function requestOtp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submissionInFlight.current) return;
    submissionInFlight.current = true;
    setError("");
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password") ?? ""),
      confirmPassword = String(form.get("confirmPassword") ?? "");
    if (password !== confirmPassword) {
      setError("Passwords do not match. Please confirm your password.");
      submissionInFlight.current = false;
      return;
    }
    const payload = {
      email: String(form.get("email") ?? "").trim(),
      full_name: String(form.get("fullName") ?? "").trim(),
      organization_name: String(form.get("organizationName") ?? "").trim(),
      password,
    };
    setLoading(true);
    try {
      const response = await apiFetch("/auth/register", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      const result = (await response.json()) as {
        challenge_id?: string;
        detail?: string;
        expires_in_seconds?: number;
        message?: string;
        resend_after_seconds?: number;
      };
      if (!response.ok || !result.challenge_id)
        throw new Error(authenticationError(response.status, result.detail));
      setEmail(payload.email);
      setChallengeId(result.challenge_id);
      setOtp("");
      setResendIn(result.resend_after_seconds ?? 60);
      setMessage(
        result.message ?? "Verification code sent. Check your inbox.",
      );
      setStep("otp");
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Unable to reach the registration service.",
      );
    } finally {
      setLoading(false);
      submissionInFlight.current = false;
    }
  }
  async function verifyOtp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submissionInFlight.current) return;
    submissionInFlight.current = true;
    setLoading(true);
    setError("");
    if (otp.length !== 6) {
      setError("Enter the complete six-character verification code.");
      setLoading(false);
      submissionInFlight.current = false;
      return;
    }
    try {
      const response = await apiFetch("/auth/register/verify-otp", {
        method: "POST",
        body: JSON.stringify({ challenge_id: challengeId, otp }),
      });
      const result = (await response.json()) as {
        access_token?: string;
        detail?: string;
      };
      if (!response.ok || !result.access_token)
        throw new Error(authenticationError(response.status, result.detail));
      const session = await fetchWithTimeout("/api/auth/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          accessToken: result.access_token,
          remember: false,
        }),
      });
      if (!session.ok)
        throw new Error("Your secure session could not be created.");
      window.location.replace("/onboarding");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Verification failed.");
      setLoading(false);
      submissionInFlight.current = false;
    }
  }
  async function resend() {
    if (loading || submissionInFlight.current || resendIn > 0) return;
    submissionInFlight.current = true;
    setLoading(true);
    setError("");
    try {
      const response = await apiFetch("/auth/register/resend", {
        method: "POST",
        body: JSON.stringify({ challenge_id: challengeId }),
      });
      const result = (await response.json()) as {
        detail?: string;
        message?: string;
        resend_after_seconds?: number;
      };
      if (!response.ok)
        throw new Error(authenticationError(response.status, result.detail));
      setOtp("");
      lastSubmittedOtp.current = "";
      setResendIn(result.resend_after_seconds ?? 60);
      setMessage(result.message ?? "A new verification code was sent.");
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Code could not be resent.",
      );
    } finally {
      setLoading(false);
      submissionInFlight.current = false;
    }
  }
  function updateOtp(event: ChangeEvent<HTMLInputElement>) {
    const value = event.currentTarget.value
      .toUpperCase()
      .replace(/[^A-Z0-9]/g, "")
      .slice(0, 6);
    setOtp(value);
    setError("");
  }
  function changeEmail() {
    setStep("details");
    setChallengeId("");
    setOtp("");
    setMessage("");
    setError("");
    lastSubmittedOtp.current = "";
  }
  return (
    <Auth3DShell mode="register">
      {step === "details" ? (
        <form onSubmit={requestOtp} className="auth-form-enter">
          <div className="auth-panel-badge">
            <ShieldCheck size={14} /> CREATE IDENTITY
          </div>
          <h2>Create workspace</h2>
          <p className="auth-panel-copy">
            Verify your real email before your isolated workspace is created.
          </p>
          <div className="auth-register-grid">
            <label>
              Organization name
              <input
                required
                name="organizationName"
                autoComplete="organization"
                placeholder="Acme Corporation"
                className="auth-3d-input"
              />
            </label>
            <label>
              Full name
              <input
                required
                name="fullName"
                autoComplete="name"
                placeholder="Your name"
                className="auth-3d-input"
              />
            </label>
            <label className="auth-span-two">
              Work email
              <input
                required
                name="email"
                type="email"
                autoComplete="email"
                placeholder="you@company.com"
                className="auth-3d-input"
              />
            </label>
            <label>
              Password
              <span className="auth-password-field">
                <input
                  required
                  name="password"
                  type={showPasswords ? "text" : "password"}
                  autoComplete="new-password"
                  minLength={8}
                  placeholder="Minimum 8 characters"
                  className="auth-3d-input"
                />
                <button type="button" className="auth-password-toggle" aria-label={showPasswords ? "Hide passwords" : "Show passwords"} onClick={() => setShowPasswords(value => !value)}>{showPasswords ? <EyeOff size={17}/> : <Eye size={17}/>}</button>
              </span>
            </label>
            <label>
              Confirm password
              <input
                required
                name="confirmPassword"
                type={showPasswords ? "text" : "password"}
                autoComplete="new-password"
                minLength={8}
                placeholder="Repeat password"
                className="auth-3d-input"
              />
            </label>
          </div>
          <div className="auth-password-hint">
            <CheckCircle2 size={14} />A letter-and-number OTP will be delivered
            through configured SMTP
          </div>
          {error && (
            <p role="alert" className="auth-notice auth-notice-error">
              {error}
            </p>
          )}
          <button disabled={loading} className="auth-primary-button">
            {loading ? "SENDING SECURE CODE…" : "VERIFY EMAIL"}
            <ArrowRight size={17} />
          </button>
          <p className="auth-switch-copy">
            Already registered? <Link href="/login">Return to login</Link>
          </p>
        </form>
      ) : (
        <form ref={otpForm} onSubmit={verifyOtp} className="auth-form-enter">
          <button
            type="button"
            onClick={changeEmail}
            className="auth-panel-badge"
          >
            <ArrowLeft size={14} /> CHANGE EMAIL
          </button>
          <h2>Verify email</h2>
          <p className="auth-panel-copy">
            Enter the six-character code sent to{" "}
            <strong className="text-white">{email}</strong>. The code contains
            letters and numbers and expires in 10 minutes.
          </p>
          {message && (
            <p role="status" className="auth-notice auth-notice-success">
              {message}
            </p>
          )}
          <div className="auth-field-stack">
            <label>
              Verification code
              <input
                required
                name="otp"
                inputMode="text"
                autoComplete="one-time-code"
                autoFocus
                minLength={6}
                maxLength={6}
                pattern="[A-Za-z0-9]{6}"
                value={otp}
                onChange={updateOtp}
                className="auth-3d-input uppercase tracking-[.35em]"
                placeholder="A7K29P"
              />
            </label>
          </div>
          {error && (
            <p role="alert" className="auth-notice auth-notice-error">
              {error}
            </p>
          )}
          <button disabled={loading} className="auth-primary-button">
            {loading ? "VERIFYING CODE…" : "VERIFY & CREATE ACCOUNT"}
            <ArrowRight size={17} />
          </button>
          <button
            type="button"
            disabled={loading || resendIn > 0}
            onClick={() => void resend()}
            className="mt-4 w-full text-center text-xs text-cyan-300 disabled:opacity-50"
          >
            {resendIn > 0
              ? `Resend available in ${resendIn}s`
              : "Resend verification code"}
          </button>
        </form>
      )}
    </Auth3DShell>
  );
}
