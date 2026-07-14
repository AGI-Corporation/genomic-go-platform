import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
const NO_STORE = { "Cache-Control": "no-store" };

const CONTACT_TO = process.env.CONTACT_TO || "agi@science.delivery";
const CONTACT_FROM = process.env.CONTACT_FROM || "Science.Delivery <onboarding@resend.dev>";

function env(keys: string[]) {
  for (const k of keys) if (process.env[k]) return process.env[k] as string;
  return undefined;
}
function trim(v: string) { return v.replace(/\/+$/, ""); }
function esc(v: string) {
  return String(v).replace(/[<>&]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" }[c] as string));
}

type Body = {
  name?: string; email?: string; organization?: string;
  interest?: string; message?: string; kind?: string;
};

export async function POST(request: Request) {
  let body: Body;
  try { body = await request.json(); } catch { return NextResponse.json({ detail: "Invalid request" }, { status: 400, headers: NO_STORE }); }

  const name = (body.name || "").trim();
  const email = (body.email || "").trim();
  const message = (body.message || "").trim();
  if (!name || !email || !message) return NextResponse.json({ detail: "Name, email, and message are required." }, { status: 422, headers: NO_STORE });
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return NextResponse.json({ detail: "Invalid email address." }, { status: 422, headers: NO_STORE });

  const investor = body.kind === "investor";
  const subject = investor
    ? `[Science.Delivery] Investor inquiry from ${name}`
    : `[Science.Delivery] New inquiry from ${name}`;
  const label = investor ? "Intended investment" : "Area of interest";
  const text =
    `New ${investor ? "investor" : "contact"} form submission\n\n` +
    `Name:         ${name}\n` +
    `Email:        ${email}\n` +
    `Organization: ${body.organization || "—"}\n` +
    `${label}: ${body.interest || "—"}\n\n` +
    `Message:\n${message}\n`;
  const html =
    `<h2>New ${investor ? "investor" : "contact"} inquiry</h2>` +
    `<p><strong>Name:</strong> ${esc(name)}<br/>` +
    `<strong>Email:</strong> ${esc(email)}<br/>` +
    `<strong>Organization:</strong> ${esc(body.organization || "—")}<br/>` +
    `<strong>${label}:</strong> ${esc(body.interest || "—")}</p>` +
    `<p><strong>Message:</strong><br/>${esc(message).replace(/\n/g, "<br/>")}</p>`;

  const apiBase = env(["KYLON_API_BASE", "P2_API_BASE"]);
  const appId = env(["KYLON_APP_ID", "NEXT_PUBLIC_KYLON_APP_ID"]);
  const apiToken = env(["KYLON_API_TOKEN", "PURECLAW_API_TOKEN"]);
  const connectionId = env(["RESEND_CONNECTION_ID"]);

  // If email isn't wired yet, accept gracefully so the site never appears broken.
  if (!apiBase || !appId || !apiToken || !connectionId) {
    console.warn("Contact received but email delivery not configured", { hasBase: !!apiBase, hasApp: !!appId, hasToken: !!apiToken, hasConn: !!connectionId });
    return NextResponse.json({ status: "accepted", delivered: false, detail: "Received. Email delivery is pending configuration." }, { headers: NO_STORE });
  }

  const execUrl = `${trim(apiBase)}/api/build-apps/${encodeURIComponent(appId)}/connections/${encodeURIComponent(connectionId)}/tools/execute`;
  try {
    const res = await fetch(execUrl, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: `Bearer ${apiToken}`,
        cookie: request.headers.get("cookie") || "",
      },
      cache: "no-store",
      body: JSON.stringify({
        tool: "RESEND_SEND_EMAIL",
        arguments: { from: CONTACT_FROM, to: CONTACT_TO, reply_to: email, subject, text, html },
      }),
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      console.error("Resend send failed", res.status, detail);
      return NextResponse.json({ status: "error", delivered: false, detail: "Email delivery failed." }, { status: 502, headers: NO_STORE });
    }
    return NextResponse.json({ status: "sent", delivered: true, to: CONTACT_TO }, { headers: NO_STORE });
  } catch (e) {
    console.error("Resend send exception", e);
    return NextResponse.json({ status: "error", delivered: false, detail: "Email delivery failed." }, { status: 502, headers: NO_STORE });
  }
}
