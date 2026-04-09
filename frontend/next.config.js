/** @type {import('next').NextConfig} */
const nextConfig = {
    output: 'standalone',
    // BACKEND_URL은 서버 사이드에서만 사용 (프록시용)
    // 클라이언트는 상대 경로(/api/v1/...) 사용
}

module.exports = nextConfig

