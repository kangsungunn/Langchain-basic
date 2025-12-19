import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'LangChain RAG Chatbot',
  description: '지식 베이스 기반 AI 챗봇 - RAG 및 일반 대화 모드',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  )
}

