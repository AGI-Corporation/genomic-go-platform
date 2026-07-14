import { NextResponse } from "next/server";
import openapi from "@/generated/openapi.json";

export function GET() {
  return NextResponse.json(openapi);
}
