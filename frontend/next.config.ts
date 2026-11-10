import type { NextConfig } from "next";
const config: NextConfig = {
  distDir: process.env.VOICEBRIDGE_DIST_DIR || ".next",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.VOICEBRIDGE_API_URL || "http://127.0.0.1:8000"}/api/:path*`,
      },
    ];
  },
};
export default config;
