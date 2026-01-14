/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  
  // 避免 Server Action 快取問題
  experimental: {
    serverActions: {
      bodySizeLimit: '2mb',
    },
  },
  
  // 生產環境優化
  poweredByHeader: false,
  compress: true,
  
  // 清除構建 ID 快取
  generateBuildId: async () => {
    // 使用時間戳避免快取問題
    return `build-${Date.now()}`
  },
  
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.API_URL || 'http://localhost:8082'}/api/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
