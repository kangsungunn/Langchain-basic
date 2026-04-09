'use client'

import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

export default function UploadPage() {
  const router = useRouter()
  const [problemFile, setProblemFile] = useState<File | null>(null)
  const [answerFile, setAnswerFile] = useState<File | null>(null)
  const [questionLabel, setQuestionLabel] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent, type: 'problem' | 'answer') => {
    e.preventDefault()
    setIsDragging(false)

    const files = Array.from(e.dataTransfer.files)
    const pdfFile = files.find(file => file.type === 'application/pdf')

    if (!pdfFile) {
      setError('PDF 파일만 업로드 가능합니다')
      return
    }

    if (type === 'problem') {
      setProblemFile(pdfFile)
    } else {
      setAnswerFile(pdfFile)
    }
    setError(null)
  }, [])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>, type: 'problem' | 'answer') => {
    const file = e.target.files?.[0]
    if (!file) return

    if (file.type !== 'application/pdf') {
      setError('PDF 파일만 업로드 가능합니다')
      return
    }

    if (type === 'problem') {
      setProblemFile(file)
    } else {
      setAnswerFile(file)
    }
    setError(null)
  }, [])

  const handleSubmit = useCallback(async () => {
    if (!answerFile) {
      setError('답안지 파일을 업로드해주세요')
      return
    }

    setIsUploading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', answerFile)
      formData.append('problem_id', '')

      if (questionLabel.trim()) {
        formData.append('question_label', questionLabel.trim())
      }

      // 문제 PDF가 있으면 함께 전송 → 백엔드에서 파싱 후 DB에 문제 등록·논점 추출로 새 문제도 첨삭 가능
      if (problemFile) {
        formData.append('problem_file', problemFile)
      }

      // 백엔드 API 호출 (프론트엔드 API Route를 통해)
      // 프론트엔드 라우터 → 백엔드 라우터 (app/api/v1/submission.py)
      const response = await fetch('/v1/main/submission', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || '업로드 실패')
      }

      const data = await response.json()

      // OCR 처리 (자동)
      // 프론트엔드 라우터 → 백엔드 라우터 (app/api/v1/submission.py)
      if (data.submission_type === 'image') {
        const ocrResponse = await fetch(`/v1/main/submission/answers/${data.id}/ocr`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ confidence_threshold: 0.6 }),
        })

        if (!ocrResponse.ok) {
          const ocrError = await ocrResponse.json()
          throw new Error(ocrError.detail || 'OCR 처리 실패')
        }
      }

      // 첨삭 결과 페이지로 이동
      router.push(`/review/${data.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : '업로드 중 오류가 발생했습니다')
      setIsUploading(false)
    }
  }, [answerFile, problemFile, questionLabel, router])

  const removeFile = useCallback((type: 'problem' | 'answer') => {
    if (type === 'problem') {
      setProblemFile(null)
    } else {
      setAnswerFile(null)
    }
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* 헤더 */}
        <header className="mb-8">
          <Link href="/" className="text-indigo-600 hover:text-indigo-700 mb-4 inline-block">
            ← 홈으로 돌아가기
          </Link>
          <h1 className="text-4xl font-bold text-gray-900">답안지 업로드</h1>
          <p className="text-gray-600 mt-2">PDF 형식의 문제와 답안지를 업로드해주세요</p>
        </header>

        {/* 업로드 영역 */}
        <div className="max-w-4xl mx-auto space-y-8">
          {/* 문제 파일 업로드 (선택사항) */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-semibold mb-4">문제 파일 (선택사항)</h2>
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${isDragging ? 'border-indigo-500 bg-indigo-50' : 'border-gray-300'
                }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, 'problem')}
            >
              {problemFile ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-center">
                    <div className="bg-green-100 rounded-full p-3">
                      <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                  </div>
                  <p className="text-gray-700 font-medium">{problemFile.name}</p>
                  <p className="text-sm text-gray-500">{(problemFile.size / 1024 / 1024).toFixed(2)} MB</p>
                  <button
                    onClick={() => removeFile('problem')}
                    className="text-red-600 hover:text-red-700 text-sm"
                  >
                    제거
                  </button>
                </div>
              ) : (
                <div>
                  <div className="mb-4">
                    <svg className="w-16 h-16 text-gray-400 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                  </div>
                  <p className="text-gray-600 mb-2">파일을 드래그하거나 클릭하여 업로드</p>
                  <p className="text-sm text-gray-500 mb-4">PDF 파일만 지원됩니다</p>
                  <label className="inline-block bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-6 py-2 rounded-lg cursor-pointer transition-colors">
                    파일 선택
                    <input
                      type="file"
                      accept="application/pdf"
                      className="hidden"
                      onChange={(e) => handleFileSelect(e, 'problem')}
                    />
                  </label>
                </div>
              )}
            </div>
          </div>

          {/* 설문 지정 (선택) */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-semibold mb-2">설문 구분 (선택사항)</h2>
            <p className="text-sm text-gray-500 mb-3">이 답안이 해당하는 설문을 적어두면, 첨삭 결과에서 「문제·설문」으로 표시됩니다.</p>
            <input
              type="text"
              value={questionLabel}
              onChange={(e) => setQuestionLabel(e.target.value)}
              placeholder="예: 설문 (1), 설문 (2), II. 설문 (2)"
              className="w-full max-w-md border border-gray-300 rounded-lg px-3 py-2 text-gray-700 focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* 답안지 파일 업로드 (필수) */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-semibold mb-4">
              답안지 파일 <span className="text-red-500">*</span>
            </h2>
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${isDragging ? 'border-indigo-500 bg-indigo-50' : 'border-gray-300'
                }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, 'answer')}
            >
              {answerFile ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-center">
                    <div className="bg-green-100 rounded-full p-3">
                      <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                  </div>
                  <p className="text-gray-700 font-medium">{answerFile.name}</p>
                  <p className="text-sm text-gray-500">{(answerFile.size / 1024 / 1024).toFixed(2)} MB</p>
                  <button
                    onClick={() => removeFile('answer')}
                    className="text-red-600 hover:text-red-700 text-sm"
                  >
                    제거
                  </button>
                </div>
              ) : (
                <div>
                  <div className="mb-4">
                    <svg className="w-16 h-16 text-gray-400 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                  </div>
                  <p className="text-gray-600 mb-2">파일을 드래그하거나 클릭하여 업로드</p>
                  <p className="text-sm text-gray-500 mb-4">PDF 파일만 지원됩니다</p>
                  <label className="inline-block bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-6 py-2 rounded-lg cursor-pointer transition-colors">
                    파일 선택
                    <input
                      type="file"
                      accept="application/pdf"
                      className="hidden"
                      onChange={(e) => handleFileSelect(e, 'answer')}
                    />
                  </label>
                </div>
              )}
            </div>
          </div>

          {/* 에러 메시지 */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          {/* 제출 버튼 */}
          <div className="flex justify-end space-x-4">
            <Link
              href="/"
              className="px-6 py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold rounded-lg transition-colors"
            >
              취소
            </Link>
            <button
              onClick={handleSubmit}
              disabled={!answerFile || isUploading}
              className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors"
            >
              {isUploading ? '처리 중...' : '첨삭 시작'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
