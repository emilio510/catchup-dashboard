"use client";

import { useActionState } from "react";
import { loginAction } from "./action";

export default function LoginPage() {
  const [state, formAction, isPending] = useActionState(
    async (_prev: { error?: string }, formData: FormData) => {
      return await loginAction(formData);
    },
    {}
  );

  return (
    <main className="min-h-screen flex items-center justify-center bg-[#0d1117]">
      <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-8 w-80">
        <h1 className="text-lg font-bold text-[#e6edf3] mb-6 text-center">
          Catch-up Dashboard
        </h1>
        <form action={formAction}>
          <input
            type="password"
            name="password"
            placeholder="Password"
            autoFocus
            className="w-full bg-[#0d1117] border border-[#30363d] rounded px-3 py-2 text-sm text-[#e6edf3] placeholder-[#8b949e] outline-none focus:border-[#388bfd] mb-4"
          />
          <button
            type="submit"
            disabled={isPending}
            className="w-full bg-[#238636] hover:bg-[#2ea043] text-white text-sm font-medium py-2 rounded disabled:opacity-50"
          >
            {isPending ? "..." : "Sign in"}
          </button>
          {state.error && (
            <p className="text-[#f85149] text-xs mt-3 text-center">{state.error}</p>
          )}
        </form>
      </div>
    </main>
  );
}
