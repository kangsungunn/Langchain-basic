import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    // 환경 변수 확인
    if (!BACKEND_URL || BACKEND_URL === 'http://localhost:8000') {
      console.error('⚠️ API_URL 환경 변수가 설정되지 않았습니다.')
      return NextResponse.json(
        {
          error: 'Backend URL not configured',
          detail: 'API_URL environment variable is not set in Vercel'
        },
        { status: 500 }
      )
    }

    console.log(`🔄 Proxying to: ${BACKEND_URL}/api/chat/rag`)
    console.log(`📦 Request body:`, JSON.stringify(body).substring(0, 100))

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 60000) // 60초 타임아웃

    try {
      const response = await fetch(`${BACKEND_URL}/api/chat/rag`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Failed to read error response')
        console.error(`❌ Backend error ${response.status}:`, errorText)
        return NextResponse.json(
          {
            error: `Backend error: ${response.status}`,
            detail: errorText.substring(0, 200)
          },
          { status: response.status }
        )
      }

      const data = await response.json()
      console.log('✅ Proxy success')
      return NextResponse.json(data)
    } catch (fetchError: any) {
      clearTimeout(timeoutId)

      if (fetchError.name === 'AbortError') {
        console.error('⏱️ Request timeout')
        return NextResponse.json(
          { error: 'Request timeout - backend server did not respond in 60 seconds' },
          { status: 504 }
        )
      }

      throw fetchError
    }
  } catch (error: any) {
    console.error('❌ Proxy error:', error)
    return NextResponse.json(
      {
        error: 'Failed to connect to backend server',
        detail: error.message || 'Unknown error',
        backendUrl: BACKEND_URL
      },
      { status: 500 }
    )
  }
}

