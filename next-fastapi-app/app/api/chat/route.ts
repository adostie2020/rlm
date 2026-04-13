import { NextRequest } from "next/server";

const BACKEND_URL =
  process.env.NODE_ENV === "development"
    ? "http://127.0.0.1:8000"
    : process.env.RLM_BACKEND_URL || "https://your-render-backend-url.onrender.com";

export async function POST(req: NextRequest) {
  const body = await req.text();
  const protocol = req.nextUrl.searchParams.get("protocol") || "data";

  // Explicitly forward Jira headers that Vercel rewrites may strip
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  const jiraToken = req.headers.get("X-Jira-Token");
  const jiraResourceId = req.headers.get("X-Jira-Resource-Id");
  const jiraRefreshToken = req.headers.get("X-Jira-Refresh-Token");

  if (jiraToken) headers["X-Jira-Token"] = jiraToken;
  if (jiraResourceId) headers["X-Jira-Resource-Id"] = jiraResourceId;
  if (jiraRefreshToken) headers["X-Jira-Refresh-Token"] = jiraRefreshToken;

  const backendUrl = `${BACKEND_URL}/api/chat?protocol=${protocol}`;

  const backendRes = await fetch(backendUrl, {
    method: "POST",
    headers,
    body,
  });

  // Stream the response back to the client
  const responseHeaders: Record<string, string> = {
    "Content-Type": backendRes.headers.get("Content-Type") || "text/plain",
    "Cache-Control": "no-cache, no-transform",
    "X-Accel-Buffering": "no",
    Connection: "keep-alive",
  };

  // Forward the Vercel AI data stream header if present
  const aiStreamHeader = backendRes.headers.get("x-vercel-ai-data-stream");
  if (aiStreamHeader) responseHeaders["x-vercel-ai-data-stream"] = aiStreamHeader;

  // Forward refreshed Jira tokens so the frontend can update its session
  const newJiraToken = backendRes.headers.get("X-New-Jira-Token");
  const newJiraRefreshToken = backendRes.headers.get("X-New-Jira-Refresh-Token");
  if (newJiraToken) responseHeaders["X-New-Jira-Token"] = newJiraToken;
  if (newJiraRefreshToken) responseHeaders["X-New-Jira-Refresh-Token"] = newJiraRefreshToken;

  return new Response(backendRes.body, {
    status: backendRes.status,
    headers: responseHeaders,
  });
}
