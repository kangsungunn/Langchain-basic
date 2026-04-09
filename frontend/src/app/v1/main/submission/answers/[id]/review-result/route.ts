import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

/**
 * 이미 생성된 첨삭 결과 조회 (리뷰 페이지용)
 * GET /v1/main/submission/answers/[id]/review-result → 백엔드 GET .../review-result
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: answerId } = await params
    if (!answerId) {
      return NextResponse.json(
        { detail: 'answer_id가 필요합니다' },
        { status: 400 }
      )
    }

    const response = await fetch(
      `${BACKEND_URL}/api/v1/submission/answers/${answerId}/review-result`,
      {
        method: 'GET',
        headers: { Accept: 'application/json' },
        signal: AbortSignal.timeout(30000), // 30초
      }
    )

    if (response.status === 404) {
      return NextResponse.json(
        { detail: '해당 답안에 대한 첨삭 결과가 없습니다.' },
        { status: 404 }
      )
    }

    if (!response.ok) {
      const text = await response.text()
      let errorData: { detail?: string } = {}
      try {
        errorData = JSON.parse(text)
      } catch {
        errorData = { detail: text || '결과 조회 실패' }
      }
      return NextResponse.json(
        { detail: errorData.detail || '결과 조회 실패' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    if (error instanceof Error && error.name === 'TimeoutError') {
      return NextResponse.json(
        { detail: '요청 시간이 초과되었습니다.' },
        { status: 504 }
      )
    }
    return NextResponse.json(
      { detail: 'Internal Server Error' },
      { status: 500 }
    )
  }
}
