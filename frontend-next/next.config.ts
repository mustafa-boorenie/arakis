import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Set turbopack root to avoid workspace detection issues
  turbopack: {
    root: __dirname,
  },

  output: 'export',

  // Disable image optimization for static export
  images: {
    unoptimized: true,
  },

  // Trailing slashes for cleaner URLs on Cloudflare
  trailingSlash: true,
};

export default nextConfig;
