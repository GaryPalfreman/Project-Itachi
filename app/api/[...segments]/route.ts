const API_PATHS = new Set([
  "/api/status",
  "/api/health",
  "/api/unlock",
  "/api/chat",
]);

async function forwardToFastAPI(request: Request): Promise<Response> {
  const incomingUrl = new URL(request.url);
  const originalPath = incomingUrl.pathname;

  if (!API_PATHS.has(originalPath)) {
    return Response.json({ detail: "Not found" }, { status: 404 });
  }

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("content-length");
  headers.set("x-itachi-original-path", originalPath);

  try {
    return await fetch(new URL(`/api${incomingUrl.search}`, incomingUrl.origin), {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD"
        ? undefined
        : await request.arrayBuffer(),
      cache: "no-store",
      redirect: "manual",
    });
  } catch {
    return Response.json(
      { detail: "Itachi could not reach its API. Please try again shortly." },
      { status: 502 },
    );
  }
}

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export const GET = forwardToFastAPI;
export const HEAD = forwardToFastAPI;
export const POST = forwardToFastAPI;
export const PUT = forwardToFastAPI;
export const PATCH = forwardToFastAPI;
export const DELETE = forwardToFastAPI;
