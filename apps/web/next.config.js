/** @type {import('next').NextConfig} */
const nextConfig = {
  // 代理 API 请求到后端
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};

module.exports = nextConfig;
