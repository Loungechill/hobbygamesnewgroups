const FEED_URL = "https://raw.githubusercontent.com/Loungechill/hobbygamesnewgroups/main/hobbygames-sale.yml";

export default {
  async fetch(request) {
    const { pathname } = new URL(request.url);
    if (pathname !== "/" && pathname !== "/feed.yml") {
      return new Response("Not found", { status: 404 });
    }
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method not allowed", {
        status: 405,
        headers: { Allow: "GET, HEAD" },
      });
    }

    try {
      const upstream = await fetch(FEED_URL, {
        method: request.method,
        cf: { cacheEverything: true, cacheTtlByStatus: { "200-299": 300, "400-599": -1 } },
        signal: AbortSignal.timeout(30000),
      });
      if (!upstream.ok) throw new Error("GitHub returned " + upstream.status);
      return new Response(upstream.body, {
        headers: {
          "Content-Type": "application/xml; charset=utf-8",
          "Cache-Control": "public, max-age=300",
        },
      });
    } catch (error) {
      console.error(error.message);
      return new Response("Feed temporarily unavailable", { status: 502 });
    }
  },
};
