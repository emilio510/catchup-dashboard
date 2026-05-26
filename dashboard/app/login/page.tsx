"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { GlassCard } from "@/components/ui/glass-card";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setPending(true);
    setError("");

    const formData = new FormData(e.currentTarget);
    const password = formData.get("password") as string;

    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });

    const data = await res.json();

    if (data.success) {
      router.push("/");
      router.refresh();
    } else {
      setError(data.error || "Wrong password");
      setPending(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <GlassCard className="w-full max-w-[400px] p-6">
      <form onSubmit={handleSubmit}>
        <h1 className="font-sans text-[18px] font-semibold text-[var(--color-text)]">Sign in</h1>
        <p className="mt-1 font-sans text-[12px] text-[var(--color-text-dim)]">Enter the dashboard password.</p>
        <input
          type="password"
          name="password"
          autoComplete="current-password"
          autoFocus
          placeholder="Password"
          className="mt-4 w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg-elev)] px-3 py-2 font-sans text-[13px] text-[var(--color-text)] placeholder:text-[var(--color-text-ghost)] focus:border-[var(--color-border-strong)] focus:outline-none"
        />
        {error && (
          <p className="mt-3 font-mono text-[11px] text-[var(--color-risk)]">{error}</p>
        )}
        <button
          type="submit"
          disabled={pending}
          className="mt-4 w-full rounded-md bg-[var(--color-ok-soft)] py-2 font-mono text-[12px] font-medium text-[var(--color-ok)] transition-colors hover:bg-[color:rgba(48,209,88,0.18)] disabled:opacity-50"
        >
          {pending ? "..." : "Sign in"}
        </button>
      </form>
      </GlassCard>
    </main>
  );
}
