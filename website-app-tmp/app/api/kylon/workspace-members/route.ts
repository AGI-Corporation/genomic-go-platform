import { NextResponse } from "next/server";
import { normalizeWorkspaceMemberProfiles } from "@/lib/kylon/workspace-member-profiles";

export const dynamic = "force-dynamic";

const NO_STORE_HEADERS = { "Cache-Control": "no-store" };

function trimTrailingSlash(value: string) {
  return value.replace(/\/+$/, "");
}

function firstEnvValue(keys: string[]) {
  for (const key of keys) {
    const value = process.env[key];
    if (value) return value;
  }
  return undefined;
}

function memberResponse(payload: unknown) {
  return NextResponse.json(
    { members: normalizeWorkspaceMemberProfiles(payload) },
    { headers: NO_STORE_HEADERS },
  );
}

export async function GET() {
  const apiBase = firstEnvValue(["KYLON_API_BASE", "P2_API_BASE"]);
  const workspaceId = firstEnvValue(["KYLON_WORKSPACE_ID", "WORKSPACE_ID"]);
  const apiToken = firstEnvValue(["PURECLAW_API_TOKEN"]);

  if (!apiBase || !workspaceId || !apiToken) {
    return memberResponse({ members: [] });
  }

  const url = `${trimTrailingSlash(apiBase)}/workspaces/${encodeURIComponent(workspaceId)}/members`;

  try {
    const response = await fetch(url, {
      headers: {
        accept: "application/json",
        "x-api-key": apiToken,
      },
      cache: "no-store",
    });

    if (!response.ok) {
      console.warn("Failed to load Kylon workspace members", {
        status: response.status,
        workspaceId,
      });
      return memberResponse({ members: [] });
    }

    return memberResponse(await response.json());
  } catch (error) {
    console.warn("Failed to load Kylon workspace members", {
      workspaceId,
      error: error instanceof Error ? error.message : String(error),
    });
    return memberResponse({ members: [] });
  }
}
