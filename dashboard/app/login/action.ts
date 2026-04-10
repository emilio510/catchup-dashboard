"use server";

import { cookies } from "next/headers";

export async function loginAction(formData: FormData): Promise<{ error?: string; success?: boolean }> {
  const password = formData.get("password") as string;
  const expected = process.env.DASHBOARD_PASSWORD;

  if (!expected) {
    return { error: "DASHBOARD_PASSWORD not configured" };
  }

  if (password !== expected) {
    return { error: "Wrong password" };
  }

  const cookieStore = await cookies();
  cookieStore.set("catchup-auth", "authenticated", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 30,
    path: "/",
  });

  return { success: true };
}
