import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

/**
 * 피드백에 대한 사용자 정정/추가 요청 (학습용)
 * POST /v1/main/feedback/feedbacks/[feedbackId]/corrections → 백엔드 POST .../corrections
 */
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ feedbackId: string }> }
) {
  try {
    const { feedbackId } = await params
    if (!feedbackId) {
      return NextResponse.json(
        { detail: 'feedback_id가 필요합니다' },
        { status: 400 }
      )
    }

    const body = await request.json()
    const response = await fetch(
      `${BACKEND_URL}/api/v1/feedback/feedbacks/${feedbackId}/corrections`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
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
