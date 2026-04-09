import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

/**
 * PDF 파일에서 학습 데이터 생성
 *
 * 프론트엔드 라우터 → 백엔드 라우터 (app/api/v1/training.py)
 */
export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    const file = formData.get('file') as File

    if (!file) {
      return NextResponse.json(
        { detail: '파일이 필요합니다' },
        { status: 400 }
      )
    }

    // 파일 확장자 확인
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      return NextResponse.json(
        { detail: 'PDF 파일만 업로드 가능합니다' },
        { status: 400 }
      )
    }

    // 백엔드로 프록시 (multipart/form-data)
    const backendFormData = new FormData()
    backendFormData.append('file', file)

    // 쿼리 파라미터 추가
    const url = new URL(request.url)
    const autoTrigger = url.searchParams.get('auto_trigger') !== 'false'
    const minDataCount = url.searchParams.get('min_data_count') || '10'

    const response = await fetch(
      `${BACKEND_URL}/api/v1/training/data/pdf?auto_trigger=${autoTrigger}&min_data_count=${minDataCount}`,
      {
        method: 'POST',
        body: backendFormData,
      }
    )

    if (!response.ok) {
      // 응답 텍스트로 먼저 읽기
      const text = await response.text()
      let errorData
      try {
        // JSON 파싱 시도
        errorData = JSON.parse(text)
      } catch {
        // JSON이 아닌 경우 텍스트 그대로 사용
        errorData = { detail: text || 'PDF 업로드 실패' }
      }
      return NextResponse.json(
        { detail: errorData.detail || 'PDF 업로드 실패' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('PDF upload error:', error)

    // 백엔드 서버 연결 실패 시 더 명확한 에러 메시지
    if (error instanceof Error && 'code' in error && error.code === 'ECONNREFUSED') {
      return NextResponse.json(
        { detail: '백엔드 서버에 연결할 수 없습니다. 백엔드 서버가 실행 중인지 확인해주세요.' },
        { status: 503 }
      )
    }

    return NextResponse.json(
      { detail: error instanceof Error ? error.message : 'Internal Server Error' },
      { status: 500 }
    )
  }
}
