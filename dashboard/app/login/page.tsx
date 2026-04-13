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
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#0c0f1a",
      }}
    >
      <div
        style={{
          background: "#141b33",
          border: "1px solid #1e2a4a",
          borderRadius: 12,
          padding: 32,
          width: 320,
        }}
      >
        <h1
          style={{
            fontSize: 16,
            fontWeight: 600,
            color: "#e2e8f0",
            marginBottom: 24,
            textAlign: "center",
          }}
        >
          Catch-up Dashboard
        </h1>
        <form onSubmit={handleSubmit}>
          <input
            type="password"
            name="password"
            placeholder="Password"
            autoFocus
            style={{
              width: "100%",
              background: "#0c0f1a",
              border: "1px solid #1e2a4a",
              borderRadius: 8,
              padding: "8px 12px",
              fontSize: 13,
              color: "#e2e8f0",
              outline: "none",
              marginBottom: 16,
            }}
          />
          <button
            type="submit"
            disabled={pending}
            style={{
              width: "100%",
              background: "#238636",
              color: "white",
              fontSize: 13,
              fontWeight: 500,
              padding: "8px 0",
              borderRadius: 8,
              border: "none",
              cursor: "pointer",
              opacity: pending ? 0.5 : 1,
            }}
          >
            {pending ? "..." : "Sign in"}
          </button>
          {error && (
            <p style={{ color: "#f87171", fontSize: 11, marginTop: 12, textAlign: "center" }}>
              {error}
            </p>
          )}
        </form>
      </div>
    </main>
  );
}
