import { NextResponse } from "next/server";
import { buildLiveSessionConfig } from "@/server/agents/live-session";

export function GET() {
  return NextResponse.json({
    ok: true,
    session: buildLiveSessionConfig(),
  });
}
