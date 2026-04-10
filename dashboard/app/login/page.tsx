"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

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
    <main className="min-h-screen flex items-center justify-center bg-[#0d1117]">
      <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-8 w-80">
        <h1 className="text-lg font-bold text-[#e6edf3] mb-6 text-center">
          Catch-up Dashboard
        </h1>
        <form onSubmit={handleSubmit}>
          <input
            type="password"
            name="password"
            placeholder="Password"
            autoFocus
            className="w-full bg-[#0d1117] border border-[#30363d] rounded px-3 py-2 text-sm text-[#e6edf3] placeholder-[#8b949e] outline-none focus:border-[#388bfd] mb-4"
          />
          <button
            type="submit"
            disabled={pending}
            className="w-full bg-[#238636] hover:bg-[#2ea043] text-white text-sm font-medium py-2 rounded disabled:opacity-50"
          >
            {pending ? "..." : "Sign in"}
          </button>
          {error && (
            <p className="text-[#f85149] text-xs mt-3 text-center">{error}</p>
          )}
        </form>
      </div>
    </main>
  );
}
