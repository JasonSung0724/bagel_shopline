import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: '減醣市集 - 訂單報告生成器',
  description: '快速整合多平台訂單，一鍵生成出貨報告',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-TW">
      <body className="antialiased">{children}</body>
    </html>
  )
}
