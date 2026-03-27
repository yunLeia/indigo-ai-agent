import { NextRequest, NextResponse } from "next/server";
import { runListenPipeline } from "@/server/agents/pipeline";
import type { LiveIngestRequest } from "@/types/live-agent";

export async function POST(request: NextRequest) {
  const body = (await request.json()) as Partial<LiveIngestRequest>;

  if (!body.listenInput || !body.rawContext) {
    return NextResponse.json(
      {
        ok: false,
        error: "listenInput and rawContext are required.",
      },
      { status: 400 },
    );
  }

  return NextResponse.json({
    ok: true,
    result: runListenPipeline(body.listenInput, body.rawContext),
  });
}
