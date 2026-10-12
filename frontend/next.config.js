/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  async rewrites() {
    const backendHost = process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000';
    return [
      {
        source: '/api/v1/:path*',
        destination: `${backendHost}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
