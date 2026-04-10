import { NextResponse } from "next/server";

export async function GET() {
  const pw = process.env.DASHBOARD_PASSWORD;
  return NextResponse.json({
    has_password: !!pw,
    password_length: pw?.length ?? 0,
    password_preview: pw ? pw.substring(0, 3) + "..." : "NOT SET",
  });
}
