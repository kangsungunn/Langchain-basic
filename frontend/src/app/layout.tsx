import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: '변리사 민사소송법 답안지 첨삭 서비스',
  description: 'AI 기반 자동 첨삭으로 답안의 쟁점, 논리, 표현을 종합적으로 분석합니다',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ko">
      <body className="antialiased">{children}</body>
    </html>
  )
}
