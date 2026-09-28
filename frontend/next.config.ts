import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-contained server bundle for a small production Docker image.
  output: "standalone",
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "DENY" },
        ],
      },
      {
        // The lead page embeds the resume PDF, so this one route may be framed by our own
        // pages (and only ours). Listed last so it overrides the DENY above.
        source: "/api/leads/:id/resume",
        headers: [
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
          { key: "Content-Security-Policy", value: "frame-ancestors 'self'" },
        ],
      },
    ];
  },
};

export default nextConfig;
