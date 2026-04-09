import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

/**
 * 답안 분석 + 피드백 한 번에 (Phase 1 파이프라인)
 * GET /v1/main/submission/answers/[id]/analyze-and-feedback → 백엔드 POST .../analyze-and-feedback
 * (실제로는 POST로 호출하는 것이 맞지만, 동일 경로에서 POST만 받음)
 */
export async function POST(
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
      `${BACKEND_URL}/api/v1/submission/answers/${answerId}/analyze-and-feedback`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
        signal: AbortSignal.timeout(600000), // 10분 (ExaOne 로드·여러 추론으로 5분 초과 시도 많음)
      }
    )

    if (!response.ok) {
      const text = await response.text()
      let errorData: { detail?: string } = {}
      try {
        errorData = JSON.parse(text)
      } catch {
        errorData = { detail: text || '분석·피드백 생성 실패' }
      }
      return NextResponse.json(
        { detail: errorData.detail || '분석·피드백 생성 실패' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    if (error instanceof Error && error.name === 'TimeoutError') {
      return NextResponse.json(
        { detail: '요청 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.' },
        { status: 504 }
      )
    }
    return NextResponse.json(
      { detail: 'Internal Server Error' },
      { status: 500 }
    )
  }
}
