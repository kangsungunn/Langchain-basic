'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'

interface IssueItem {
  title: string
  suggestion?: string
}

interface LogicOrExpressionItem {
  description: string
  suggestion?: string
}

interface AnalysisResult {
  issue_coverage: number
  logic_score: number
  expression_score: number
  identified_issues: IssueItem[]
  missing_issues: IssueItem[]
  logic_issues: LogicOrExpressionItem[]
  expression_issues: LogicOrExpressionItem[]
}

interface Feedback {
  id: string
  overall_score: number
  strengths: string[]
  weaknesses: string[]
  improvements: string[]
  detailed_feedback: {
    issue_analysis: string
    logic_evaluation: string
    expression_review: string
  }
}

export default function ReviewPage() {
  const params = useParams()
  const router = useRouter()
  const answerId = params.id as string

  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null)
  const [feedback, setFeedback] = useState<Feedback | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'issues' | 'logic' | 'expression'>('issues')

  const [correctionType, setCorrectionType] = useState<'correction' | 'addition'>('correction')
  const [correctionContent, setCorrectionContent] = useState('')
  const [correctionSubmitting, setCorrectionSubmitting] = useState(false)
  const [correctionMessage, setCorrectionMessage] = useState<string | null>(null)
  const [problemInfo, setProblemInfo] = useState<{
    problem_id?: string
    problem_title?: string
    question_label?: string
  }>({})

  const fetchStartedRef = useRef<string | null>(null)

  const applyResult = (data: {
    analysis_summary?: Record<string, unknown>
    feedback?: Record<string, unknown>
    problem_id?: string
    problem_title?: string
    question_label?: string
  }) => {
    const summary = data.analysis_summary || {}
    const fb = data.feedback || {}
    const n = (v: unknown) => (typeof v === 'number' && !Number.isNaN(v) ? (v > 1 ? v / 100 : v) : 0)
    const items = (fb.items as Array<{ item_type?: string; title?: string; suggestion?: string; description?: string }>) || []
    setAnalysisResult({
      issue_coverage: n(summary.issue_coverage),
      logic_score: n(summary.logic_coherence),
      expression_score: n(summary.expression_clarity),
      identified_issues: items
        .filter((i) => i.item_type === 'identified_issue')
        .map((i) => ({ title: i.title || '', suggestion: i.suggestion })),
      missing_issues: items
        .filter((i) => i.item_type === 'missing_issue')
        .map((i) => ({ title: i.title || '', suggestion: i.suggestion })),
      logic_issues: items
        .filter((i) => (i.item_type || '').toLowerCase().includes('logic'))
        .map((i) => ({ description: i.description || '', suggestion: i.suggestion })),
      expression_issues: items
        .filter((i) => (i.item_type || '').toLowerCase().includes('expression'))
        .map((i) => ({ description: i.description || '', suggestion: i.suggestion })),
    })
    setFeedback({
      id: (fb.id as string) || '',
      overall_score: fb.overall_score != null ? Number(fb.overall_score) / 100 : 0,
      strengths: (fb.strengths as string[]) || [],
      weaknesses: (fb.weaknesses as string[]) || [],
      improvements: items.map((i) => i.suggestion).filter(Boolean) as string[],
      detailed_feedback: {
        issue_analysis: summary.exaone_analysis ? `[ExaOne 요약]\n${summary.exaone_analysis}` : (fb.meta as Record<string, string> | undefined)?.exaone_analysis || '',
        logic_evaluation: (summary as Record<string, string>).logic_evaluation_text ?? '',
        expression_review: (summary as Record<string, string>).expression_review_text ?? '',
      },
    })
    setProblemInfo({
      problem_id: data.problem_id,
      problem_title: data.problem_title,
      question_label: data.question_label,
    })
  }

  const fetchReview = async (controller?: AbortController) => {
    try {
      setIsLoading(true)
      setError(null)

      // 1) 기존 결과 조회 시도 (이미 완료된 경우 즉시 표시)
      const getRes = await fetch(`/v1/main/submission/answers/${answerId}/review-result`, {
        method: 'GET',
        headers: { Accept: 'application/json' },
        signal: controller?.signal,
      })

      if (getRes.ok) {
        const data = await getRes.json()
        applyResult(data)
        return
      }

      if (getRes.status !== 404) {
        const errData = await getRes.json().catch(() => ({}))
        throw new Error((errData as { detail?: string }).detail || '결과 조회 실패')
      }

      // 2) 없으면 분석·피드백 생성 요청 (최대 10분 대기)
      const postRes = await fetch(`/v1/main/submission/answers/${answerId}/analyze-and-feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
        signal: controller?.signal ?? AbortSignal.timeout(600000), // 10분
      })

      if (!postRes.ok) {
        const errData = await postRes.json().catch(() => ({}))
        throw new Error((errData as { detail?: string }).detail || '분석·첨삭 실패')
      }

      const data = await postRes.json()
      applyResult(data)
    } catch (err) {
      if ((err as Error).name === 'AbortError') return
      setError(err instanceof Error ? err.message : '첨삭 결과를 불러오는 중 오류가 발생했습니다')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (!answerId) return
    if (fetchStartedRef.current === answerId) return
    fetchStartedRef.current = answerId

    const controller = new AbortController()
    fetchReview(controller)
    return () => {
      controller.abort()
      fetchStartedRef.current = null
    }
  }, [answerId])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-gray-600 text-lg">첨삭 결과를 분석하는 중...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="bg-red-50 border border-red-200 text-red-700 px-6 py-4 rounded-lg mb-4">
            {error}
          </div>
          <p className="text-gray-600 text-sm mb-2">
            분석이 백엔드에서 완료되었을 수 있습니다. 다시 시도하면 저장된 결과를 불러옵니다.
          </p>
          <div className="flex gap-3 justify-center flex-wrap">
            <button
              type="button"
              onClick={() => fetchReview()}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg"
            >
              다시 시도하기
            </button>
            <Link
              href="/upload"
              className="px-4 py-2 text-indigo-600 hover:text-indigo-700 font-medium"
            >
              다른 답안지 올리기
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* 헤더 */}
        <header className="mb-8">
          <Link href="/" className="text-indigo-600 hover:text-indigo-700 mb-4 inline-block">
            ← 홈으로 돌아가기
          </Link>
          <h1 className="text-4xl font-bold text-gray-900">첨삭 결과</h1>
          <p className="text-gray-600 mt-2">아래는 ExaOne이 생성한 내용만 표시합니다. 점수·템플릿 문장은 사용하지 않습니다.</p>
          {(problemInfo.problem_title != null || problemInfo.problem_id != null || problemInfo.question_label != null) && (
            <div className="mt-4 p-3 bg-white/80 rounded-lg border border-gray-200 text-sm text-gray-700">
              <span className="font-semibold">이 피드백의 대상: </span>
              {problemInfo.problem_title && <span>문제 — {problemInfo.problem_title}</span>}
              {problemInfo.problem_id && !problemInfo.problem_title && <span>문제 ID — {problemInfo.problem_id}</span>}
              {problemInfo.problem_id && problemInfo.problem_title && (
                <span className="text-gray-500 ml-1">({problemInfo.problem_id})</span>
              )}
              {problemInfo.question_label != null && problemInfo.question_label !== '' ? (
                <span className="ml-2">· 설문 — {problemInfo.question_label}</span>
              ) : (
                <span className="ml-2 text-gray-500">· 설문 — 미지정</span>
              )}
            </div>
          )}
        </header>

        <div className="max-w-6xl mx-auto">
          <div className="bg-white rounded-lg shadow-lg mb-6">
            <div className="border-b border-gray-200">
              <nav className="flex -mb-px">
                {[
                  { id: 'issues', label: '쟁점 (ExaOne 보조)' },
                  { id: 'logic', label: '논리 (ExaOne)' },
                  { id: 'expression', label: '표현 (ExaOne)' },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as 'issues' | 'logic' | 'expression')}
                    className={`px-6 py-4 font-semibold text-sm border-b-2 transition-colors ${
                      activeTab === tab.id
                        ? 'border-indigo-600 text-indigo-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </nav>
            </div>

            <div className="p-6">
              {activeTab === 'issues' && (
                <div>
                  <h3 className="text-xl font-semibold mb-2">쟁점 — ExaOne 보조 분석</h3>
                  {feedback?.detailed_feedback?.issue_analysis?.trim() ? (
                    <div className="p-4 bg-blue-50 rounded-lg">
                      <p className="text-gray-800 whitespace-pre-wrap">{feedback.detailed_feedback.issue_analysis}</p>
                    </div>
                  ) : (
                    <p className="text-gray-500 italic">ExaOne 출력 없음 (이번에는 생성되지 않았거나 반영되지 않았습니다.)</p>
                  )}
                </div>
              )}

              {activeTab === 'logic' && (
                <div>
                  <h3 className="text-xl font-semibold mb-2">논리 — ExaOne 평가</h3>
                  {feedback?.detailed_feedback?.logic_evaluation?.trim() ? (
                    <div className="p-4 bg-green-50 rounded-lg">
                      <p className="text-gray-800 whitespace-pre-wrap">{feedback.detailed_feedback.logic_evaluation}</p>
                    </div>
                  ) : (
                    <p className="text-gray-500 italic">ExaOne 출력 없음 (이번에는 생성되지 않았거나 JSON 파싱 실패로 반영되지 않았습니다.)</p>
                  )}
                </div>
              )}

              {activeTab === 'expression' && (
                <div>
                  <h3 className="text-xl font-semibold mb-2">표현 — ExaOne 검토</h3>
                  {feedback?.detailed_feedback?.expression_review?.trim() ? (
                    <div className="p-4 bg-purple-50 rounded-lg">
                      <p className="text-gray-800 whitespace-pre-wrap">{feedback.detailed_feedback.expression_review}</p>
                    </div>
                  ) : (
                    <p className="text-gray-500 italic">ExaOne 출력 없음 (이번에는 생성되지 않았거나 반영되지 않았습니다.)</p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* 피드백에 대한 의견 (학습용) */}
          {feedback && (
            <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-2">
                이 첨삭 결과에 대한 의견 (모델 개선용)
              </h3>
              <p className="text-sm text-gray-500 mb-4">
                &quot;이 부분은 틀렸다 / 이렇게 내려라&quot; 또는 &quot;이런 포인트를 더 추가·강조해 달라&quot; 등의 의견을 남기시면,
                수집된 데이터로 이후 모델 개선에 활용할 수 있습니다.
              </p>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">유형</label>
                  <select
                    value={correctionType}
                    onChange={(e) => setCorrectionType(e.target.value as 'correction' | 'addition')}
                    className="w-full max-w-xs border border-gray-300 rounded-lg px-3 py-2 text-gray-700 focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="correction">정정 — 이 부분은 틀렸다 / 이렇게 피드백 내려라</option>
                    <option value="addition">추가·강조 — 이런 포인트를 더 넣어·강조해서 내려라</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">의견 내용</label>
                  <textarea
                    value={correctionContent}
                    onChange={(e) => setCorrectionContent(e.target.value)}
                    placeholder="예: 2번 쟁점은 답안에서 이미 다루었으므로 누락이 아니라 식별된 쟁점으로 표시해 달라."
                    rows={3}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-gray-700 focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={async () => {
                      const content = correctionContent.trim()
                      if (!content) {
                        setCorrectionMessage('의견 내용을 입력해 주세요.')
                        return
                      }
                      setCorrectionSubmitting(true)
                      setCorrectionMessage(null)
                      try {
                        const res = await fetch(
                          `/v1/main/submission/answers/${answerId}/corrections`,
                          {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                              feedback_id: feedback.id,
                              correction_type: correctionType,
                              content,
                            }),
                          }
                        )
                        if (!res.ok) {
                          const d = await res.json().catch(() => ({}))
                          throw new Error((d as { detail?: string }).detail || '저장 실패')
                        }
                        setCorrectionContent('')
                        setCorrectionMessage('의견이 저장되었습니다. 학습 데이터로 활용됩니다.')
                      } catch (e) {
                        setCorrectionMessage(e instanceof Error ? e.message : '저장에 실패했습니다.')
                      } finally {
                        setCorrectionSubmitting(false)
                      }
                    }}
                    disabled={correctionSubmitting}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white font-medium rounded-lg transition-colors"
                  >
                    {correctionSubmitting ? '저장 중…' : '의견 보내기'}
                  </button>
                  {correctionMessage && (
                    <span
                      className={
                        correctionMessage.includes('저장되었습니다')
                          ? 'text-green-600 text-sm'
                          : 'text-red-600 text-sm'
                      }
                    >
                      {correctionMessage}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* 액션 버튼 */}
          <div className="flex justify-end space-x-4">
            <Link
              href="/upload"
              className="px-6 py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold rounded-lg transition-colors"
            >
              다른 답안지 첨삭하기
            </Link>
            <button
              onClick={() => window.print()}
              className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-lg transition-colors"
            >
              결과 인쇄하기
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
