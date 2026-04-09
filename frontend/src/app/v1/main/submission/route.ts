import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

/**
 * 답안지 파일 업로드 (이미지/PDF)
 *
 * 프론트엔드 라우터 → 백엔드 라우터 (app/api/v1/submission.py)
 */
export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    const file = formData.get('file') as File
    const problemId = formData.get('problem_id') as string || ''
    const questionLabel = formData.get('question_label') as string | null
    const problemFile = formData.get('problem_file') as File | null

    if (!file) {
      return NextResponse.json(
        { detail: '파일이 필요합니다' },
        { status: 400 }
      )
    }

    const backendFormData = new FormData()
    backendFormData.append('file', file)
    if (problemId) {
      backendFormData.append('problem_id', problemId)
    }
    if (problemFile && problemFile.size > 0) {
      backendFormData.append('problem_file', problemFile)
    }
    if (questionLabel && String(questionLabel).trim()) {
      backendFormData.append('question_label', String(questionLabel).trim())
    }

    const response = await fetch(`${BACKEND_URL}/api/v1/submission/answers/image`, {
      method: 'POST',
      body: backendFormData,
    })

    if (!response.ok) {
      // 응답 텍스트로 먼저 읽기
      const text = await response.text()
      let errorData
      try {
        // JSON 파싱 시도
        errorData = JSON.parse(text)
      } catch {
        // JSON이 아닌 경우 텍스트 그대로 사용
        errorData = { detail: text || '업로드 실패' }
      }
      return NextResponse.json(
        { detail: errorData.detail || '업로드 실패' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Upload error:', error)

    // 백엔드 서버 연결 실패 시 더 명확한 에러 메시지
    if (error instanceof Error && 'code' in error && error.code === 'ECONNREFUSED') {
      return NextResponse.json(
        { detail: '백엔드 서버에 연결할 수 없습니다. 백엔드 서버가 실행 중인지 확인해주세요.' },
        { status: 503 }
      )
    }

    return NextResponse.json(
      { detail: 'Internal Server Error' },
      { status: 500 }
    )
  }
}
