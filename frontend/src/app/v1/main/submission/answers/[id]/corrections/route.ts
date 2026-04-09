import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

/**
 * 피드백 정정/추가 요청 (학습용) — submission/answers/[id] 경로에서 프록시
 * POST /v1/main/submission/answers/[id]/corrections
 * body: { feedback_id, correction_type, content }
 */
export async function POST(
  request: NextRequest,
  _context: { params: Promise<{ id: string }> }
) {
  try {
    const body = await request.json()
    const feedbackId = body?.feedback_id
    if (!feedbackId || typeof feedbackId !== 'string') {
      return NextResponse.json(
        { detail: 'feedback_id가 필요합니다' },
        { status: 400 }
      )
    }

    const response = await fetch(
      `${BACKEND_URL}/api/v1/feedback/feedbacks/${feedbackId}/corrections`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          correction_type: body.correction_type,
          content: body.content ?? '',
        }),
      }
    )

    if (!response.ok) {
      const text = await response.text()
      let errorData: { detail?: string } = {}
      try {
        errorData = JSON.parse(text)
      } catch {
        errorData = { detail: text || '의견 저장 실패' }
      }
      return NextResponse.json(
        { detail: errorData.detail || '의견 저장 실패' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json(
      { detail: 'Internal Server Error' },
      { status: 500 }
    )
  }
}
