import { NextResponse } from "next/server";
import manifest from "@/generated/manifest.json";

export function GET() {
  return NextResponse.json(manifest);
}
