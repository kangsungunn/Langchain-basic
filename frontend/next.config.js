/** @type {import('next').NextConfig} */
const nextConfig = {
    output: 'standalone',
    // API_URL은 서버 사이드에서만 사용 (프록시용)
    // 클라이언트는 상대 경로(/api/chat/rag) 사용
}

module.exports = nextConfig

