import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

/**
 * 학습 데이터셋 업로드 (JSONL 파일)
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
    if (!file.name.endsWith('.jsonl')) {
      return NextResponse.json(
        { detail: 'JSONL 파일만 업로드 가능합니다' },
        { status: 400 }
      )
    }

    // 파일 내용 읽기
    const fileContent = await file.text()

    // JSONL 파일 파싱 및 검증
    const lines = fileContent.trim().split('\n').filter(line => line.trim())
    const trainingDataList = []

    for (let i = 0; i < lines.length; i++) {
      try {
        const data = JSON.parse(lines[i])

        // 필드명 매핑 (두 가지 형식 지원)
        // 형식 1: problem_text, reference_answer_text, user_answer_text (권장)
        // 형식 2: problem, reference_answer, user_answer (호환성)
        const problemText = data.problem_text || data.problem
        const referenceAnswerText = data.reference_answer_text || data.reference_answer
        const userAnswerText = data.user_answer_text !== undefined ? data.user_answer_text : (data.user_answer !== undefined ? data.user_answer : '')

        // 필수 필드 확인
        if (!problemText || !referenceAnswerText) {
          return NextResponse.json(
            {
              detail: `줄 ${i + 1}: 필수 필드가 누락되었습니다. 다음 중 하나의 형식을 사용하세요:\n` +
                `  형식 1: problem_text, reference_answer_text, user_answer_text\n` +
                `  형식 2: problem, reference_answer, user_answer\n` +
                `  (현재 발견된 필드: ${Object.keys(data).join(', ')})`
            },
            { status: 400 }
          )
        }

        trainingDataList.push({
          problem_text: problemText,
          reference_answer_text: referenceAnswerText,
          user_answer_text: userAnswerText,
          labels: data.labels || {},
          problem_id: data.problem_id || null,
          reference_answer_id: data.reference_answer_id || null,
          user_answer_id: data.user_answer_id || null,
        })
      } catch (parseError) {
        return NextResponse.json(
          { detail: `줄 ${i + 1}: JSON 파싱 실패 - ${parseError instanceof Error ? parseError.message : '알 수 없는 오류'}` },
          { status: 400 }
        )
      }
    }

    if (trainingDataList.length === 0) {
      return NextResponse.json(
        { detail: '유효한 데이터가 없습니다' },
        { status: 400 }
      )
    }

    // 백엔드 API로 각 데이터 전송
    const results = []
    const errors = []

    console.log(`🔄 백엔드로 ${trainingDataList.length}개의 학습 데이터 전송 시작...`)

    for (let idx = 0; idx < trainingDataList.length; idx++) {
      const data = trainingDataList[idx]
      try {
        console.log(`📤 [${idx + 1}/${trainingDataList.length}] 백엔드 API 호출: POST ${BACKEND_URL}/api/v1/training/data`)
        console.log(`   └─ 문제: ${data.problem_text.substring(0, 50)}...`)

        const response = await fetch(`${BACKEND_URL}/api/v1/training/data`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        })

        console.log(`   └─ 응답 상태: ${response.status}`)

        if (!response.ok) {
          const errorData = await response.json()
          console.error(`   ❌ 실패: ${errorData.detail || '생성 실패'}`)
          errors.push({
            data: data.problem_text.substring(0, 50) + '...',
            error: errorData.detail || '생성 실패'
          })
        } else {
          const result = await response.json()
          console.log(`   ✅ 성공: ID=${result.id}`)
          results.push(result)
        }
      } catch (error) {
        console.error(`   ❌ 네트워크 오류: ${error instanceof Error ? error.message : '알 수 없는 오류'}`)
        errors.push({
          data: data.problem_text.substring(0, 50) + '...',
          error: error instanceof Error ? error.message : '알 수 없는 오류'
        })
      }
    }

    console.log(`✅ 전송 완료: 성공 ${results.length}개, 실패 ${errors.length}개`)

    return NextResponse.json({
      success: results.length,
      failed: errors.length,
      total: trainingDataList.length,
      results: results.slice(0, 10), // 처음 10개만 반환
      errors: errors.slice(0, 10), // 처음 10개만 반환
      // 학습 데이터 요약 정보 추가
      summary: {
        sample_count: results.length,
        has_labels: results.some((r: any) => r.labels && Object.keys(r.labels).length > 0),
        label_types: results.length > 0
          ? Array.from(new Set(results.flatMap((r: any) => r.labels ? Object.keys(r.labels) : [])))
          : [],
        sample_previews: results.slice(0, 3).map((r: any) => ({
          problem_preview: r.problem_text?.substring(0, 100) || '',
          reference_preview: r.reference_answer_text?.substring(0, 100) || '',
          has_user_answer: !!r.user_answer_text && r.user_answer_text.length > 0
        }))
      }
    })
  } catch (error) {
    console.error('Training data upload error:', error)

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
