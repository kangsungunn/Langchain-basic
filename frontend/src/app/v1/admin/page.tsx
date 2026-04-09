'use client'

import { useState, useCallback } from 'react'
import Link from 'next/link'

interface UploadResult {
  success: number
  failed: number
  total: number
  results: any[]
  errors: Array<{ data: string; error: string }>
  summary?: {
    sample_count: number
    has_labels: boolean
    label_types: string[]
    sample_previews: Array<{
      problem_preview: string
      reference_preview: string
      has_user_answer: boolean
    }>
  }
}

export default function AdminPage() {
  const [jsonlFile, setJsonlFile] = useState<File | null>(null)
  const [pdfFile, setPdfFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isDraggingPdf, setIsDraggingPdf] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [isUploadingPdf, setIsUploadingPdf] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null)
  const [pdfUploadResult, setPdfUploadResult] = useState<any>(null)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent, type: 'jsonl' | 'pdf') => {
    e.preventDefault()
    if (type === 'jsonl') {
      setIsDragging(false)
    } else {
      setIsDraggingPdf(false)
    }

    const files = Array.from(e.dataTransfer.files)

    if (type === 'jsonl') {
      const jsonlFile = files.find(file => file.name.endsWith('.jsonl'))
      if (!jsonlFile) {
        setError('JSONL 파일만 업로드 가능합니다')
        return
      }
      setJsonlFile(jsonlFile)
      setError(null)
      setUploadResult(null)
    } else {
      const pdfFile = files.find(file => file.name.toLowerCase().endsWith('.pdf'))
      if (!pdfFile) {
        setError('PDF 파일만 업로드 가능합니다')
        return
      }
      setPdfFile(pdfFile)
      setError(null)
      setPdfUploadResult(null)
    }
  }, [])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>, type: 'jsonl' | 'pdf') => {
    const file = e.target.files?.[0]
    if (!file) return

    if (type === 'jsonl') {
      if (!file.name.endsWith('.jsonl')) {
        setError('JSONL 파일만 업로드 가능합니다')
        return
      }
      setJsonlFile(file)
      setError(null)
      setUploadResult(null)
    } else {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setError('PDF 파일만 업로드 가능합니다')
        return
      }
      setPdfFile(file)
      setError(null)
      setPdfUploadResult(null)
    }
  }, [])

  const handleSubmit = useCallback(async () => {
    if (!jsonlFile) {
      setError('JSONL 파일을 업로드해주세요')
      return
    }

    setIsUploading(true)
    setError(null)
    setUploadResult(null)

    try {
      console.log('📤 JSONL 파일 업로드 시작:', jsonlFile.name, `(${(jsonlFile.size / 1024).toFixed(2)} KB)`)

      // FormData 생성
      const formData = new FormData()
      formData.append('file', jsonlFile)

      // 백엔드 API 호출 (프론트엔드 API Route를 통해)
      console.log('🔄 프론트엔드 API Route 호출: POST /v1/admin/training')
      const response = await fetch('/v1/admin/training', {
        method: 'POST',
        body: formData,
      })

      console.log('📥 응답 상태:', response.status, response.statusText)

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || '업로드 실패')
      }

      const result: UploadResult = await response.json()
      console.log('✅ 업로드 결과:', {
        성공: result.success,
        실패: result.failed,
        전체: result.total,
        요약: result.summary
      })
      setUploadResult(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : '업로드 중 오류가 발생했습니다')
    } finally {
      setIsUploading(false)
    }
  }, [jsonlFile])

  const removeFile = useCallback((type: 'jsonl' | 'pdf') => {
    if (type === 'jsonl') {
      setJsonlFile(null)
      setUploadResult(null)
    } else {
      setPdfFile(null)
      setPdfUploadResult(null)
    }
  }, [])

  const handlePdfSubmit = useCallback(async () => {
    if (!pdfFile) {
      setError('PDF 파일을 업로드해주세요')
      return
    }

    setIsUploadingPdf(true)
    setError(null)
    setPdfUploadResult(null)

    try {
      // FormData 생성
      const formData = new FormData()
      formData.append('file', pdfFile)

      // 백엔드 API 호출 (프론트엔드 API Route를 통해)
      const response = await fetch('/v1/admin/training/pdf', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'PDF 업로드 실패')
      }

      const result = await response.json()
      setPdfUploadResult(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'PDF 업로드 중 오류가 발생했습니다')
    } finally {
      setIsUploadingPdf(false)
    }
  }, [pdfFile])

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-pink-100">
      <div className="container mx-auto px-4 py-8">
        {/* 헤더 */}
        <header className="mb-8">
          <Link href="/" className="text-purple-600 hover:text-purple-700 mb-4 inline-block">
            ← 홈으로 돌아가기
          </Link>
          <h1 className="text-4xl font-bold text-gray-900">학습 데이터셋 관리</h1>
          <p className="text-gray-600 mt-2">JSONL 형식의 학습 데이터셋을 업로드하여 모델 학습을 시작하세요</p>
        </header>

        {/* 업로드 영역 */}
        <div className="max-w-4xl mx-auto space-y-8">
          {/* PDF 파일 업로드 (자동 파싱) */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-semibold mb-4">
              PDF 파일 업로드 (자동 파싱) <span className="text-red-500">*</span>
            </h2>
            <p className="text-sm text-gray-600 mb-4">
              문제와 모범답안이 포함된 PDF 파일을 업로드하면 자동으로 학습 데이터로 변환됩니다.
            </p>
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${isDraggingPdf ? 'border-purple-500 bg-purple-50' : 'border-gray-300'
                }`}
              onDragOver={(e) => {
                e.preventDefault()
                setIsDraggingPdf(true)
              }}
              onDragLeave={(e) => {
                e.preventDefault()
                setIsDraggingPdf(false)
              }}
              onDrop={(e) => handleDrop(e, 'pdf')}
            >
              {pdfFile ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-center">
                    <div className="bg-green-100 rounded-full p-3">
                      <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                  </div>
                  <p className="text-gray-700 font-medium">{pdfFile.name}</p>
                  <p className="text-sm text-gray-500">{(pdfFile.size / 1024 / 1024).toFixed(2)} MB</p>
                  <button
                    onClick={() => removeFile('pdf')}
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
                  <p className="text-gray-600 mb-2">PDF 파일을 드래그하거나 클릭하여 업로드</p>
                  <p className="text-sm text-gray-500 mb-4">문제와 모범답안이 포함된 PDF 파일</p>
                  <label className="inline-block bg-purple-600 hover:bg-purple-700 text-white font-semibold px-6 py-2 rounded-lg cursor-pointer transition-colors">
                    파일 선택
                    <input
                      type="file"
                      accept=".pdf"
                      className="hidden"
                      onChange={(e) => handleFileSelect(e, 'pdf')}
                    />
                  </label>
                </div>
              )}
            </div>
            {pdfUploadResult && (
              <div className="mt-4 bg-green-50 border border-green-200 rounded-lg p-4">
                <h3 className="font-semibold text-green-900 mb-2">✅ PDF 파싱 완료</h3>
                <p className="text-sm text-green-800">
                  {pdfUploadResult.total}개의 학습 데이터가 생성되었습니다.
                </p>
                {pdfUploadResult.items && pdfUploadResult.items.length > 0 && (
                  <div className="mt-2 text-xs text-green-700">
                    첫 번째 항목: {pdfUploadResult.items[0].problem_text.substring(0, 50)}...
                  </div>
                )}
              </div>
            )}
            <div className="mt-4 flex justify-end">
              <button
                onClick={handlePdfSubmit}
                disabled={!pdfFile || isUploadingPdf}
                className="px-6 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors"
              >
                {isUploadingPdf ? '처리 중...' : 'PDF 업로드 및 파싱'}
              </button>
            </div>
          </div>

          {/* 구분선 */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-purple-50 text-gray-500">또는</span>
            </div>
          </div>

          {/* JSONL 파일 업로드 */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-semibold mb-4">
              학습 데이터셋 업로드 <span className="text-red-500">*</span>
            </h2>
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${isDragging ? 'border-purple-500 bg-purple-50' : 'border-gray-300'
                }`}
              onDragOver={(e) => {
                e.preventDefault()
                setIsDragging(true)
              }}
              onDragLeave={(e) => {
                e.preventDefault()
                setIsDragging(false)
              }}
              onDrop={(e) => handleDrop(e, 'jsonl')}
            >
              {jsonlFile ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-center">
                    <div className="bg-green-100 rounded-full p-3">
                      <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                  </div>
                  <p className="text-gray-700 font-medium">{jsonlFile.name}</p>
                  <p className="text-sm text-gray-500">{(jsonlFile.size / 1024 / 1024).toFixed(2)} MB</p>
                  <button
                    onClick={() => removeFile('jsonl')}
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
                  <p className="text-gray-600 mb-2">JSONL 파일을 드래그하거나 클릭하여 업로드</p>
                  <p className="text-sm text-gray-500 mb-4">JSONL 파일만 지원됩니다</p>
                  <label className="inline-block bg-purple-600 hover:bg-purple-700 text-white font-semibold px-6 py-2 rounded-lg cursor-pointer transition-colors">
                    파일 선택
                    <input
                      type="file"
                      accept=".jsonl"
                      className="hidden"
                      onChange={(e) => handleFileSelect(e, 'jsonl')}
                    />
                  </label>
                </div>
              )}
            </div>
          </div>

          {/* JSONL 형식 안내 */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h3 className="font-semibold text-blue-900 mb-2">📋 JSONL 파일 형식</h3>
            <p className="text-sm text-blue-800 mb-2">각 줄은 하나의 JSON 객체여야 합니다:</p>
            <pre className="bg-white p-3 rounded text-xs overflow-x-auto">
              {`{
  "problem_text": "문제 내용...",
  "reference_answer_text": "모범 답안...",
  "user_answer_text": "사용자 답안...",
  "labels": {
    "issue_coverage": 0.75,
    "logic_score": 0.8
  }
}`}
            </pre>
            <p className="text-xs text-blue-700 mt-2">
              💡 참고: <code>problem</code>, <code>reference_answer</code>, <code>user_answer</code> 형식도 지원됩니다.
            </p>
          </div>

          {/* 에러 메시지 */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          {/* 업로드 결과 */}
          {uploadResult && (
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h3 className="text-xl font-semibold mb-4">업로드 결과</h3>
              <div className="grid md:grid-cols-3 gap-4 mb-6">
                <div className="bg-green-50 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-green-600 mb-2">
                    {uploadResult.success}
                  </div>
                  <div className="text-gray-600">성공</div>
                </div>
                <div className="bg-red-50 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-red-600 mb-2">
                    {uploadResult.failed}
                  </div>
                  <div className="text-gray-600">실패</div>
                </div>
                <div className="bg-blue-50 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-blue-600 mb-2">
                    {uploadResult.total}
                  </div>
                  <div className="text-gray-600">전체</div>
                </div>
              </div>

              {/* 학습 데이터 요약 */}
              {uploadResult.summary && uploadResult.success > 0 && (
                <div className="mt-6 bg-indigo-50 border border-indigo-200 rounded-lg p-4">
                  <h4 className="font-semibold text-indigo-900 mb-3">📚 학습 데이터 요약</h4>
                  <div className="space-y-3 text-sm">
                    <div>
                      <span className="font-medium text-indigo-800">학습 샘플 수:</span>
                      <span className="ml-2 text-indigo-700">{uploadResult.summary.sample_count}개</span>
                    </div>

                    {uploadResult.summary.has_labels && uploadResult.summary.label_types.length > 0 && (
                      <div>
                        <span className="font-medium text-indigo-800">포함된 라벨:</span>
                        <span className="ml-2 text-indigo-700">
                          {uploadResult.summary.label_types.join(', ')}
                        </span>
                      </div>
                    )}

                    {!uploadResult.summary.has_labels && (
                      <div className="text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
                        ⚠️ 라벨이 없는 데이터입니다. 학습은 가능하지만 평가 메트릭이 제한적일 수 있습니다.
                      </div>
                    )}

                    {uploadResult.summary.sample_previews.length > 0 && (
                      <div className="mt-4">
                        <span className="font-medium text-indigo-800 block mb-2">샘플 미리보기:</span>
                        <div className="space-y-3">
                          {uploadResult.summary.sample_previews.map((preview, idx) => (
                            <div key={idx} className="bg-white rounded p-3 border border-indigo-100">
                              <div className="mb-2">
                                <span className="text-xs font-semibold text-indigo-600">문제 {idx + 1}:</span>
                                <p className="text-gray-700 mt-1 text-xs">
                                  {preview.problem_preview}
                                  {preview.problem_preview.length >= 100 && '...'}
                                </p>
                              </div>
                              <div>
                                <span className="text-xs font-semibold text-indigo-600">모범답안 {idx + 1}:</span>
                                <p className="text-gray-700 mt-1 text-xs">
                                  {preview.reference_preview}
                                  {preview.reference_preview.length >= 100 && '...'}
                                </p>
                              </div>
                              {preview.has_user_answer && (
                                <div className="mt-2 text-xs text-green-600">
                                  ✓ 사용자 답안 포함
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {uploadResult.errors.length > 0 && (
                <div className="mt-4">
                  <h4 className="font-semibold text-red-700 mb-2">실패한 항목:</h4>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {uploadResult.errors.map((err, idx) => (
                      <div key={idx} className="bg-red-50 border border-red-200 rounded p-2 text-sm">
                        <div className="font-medium text-red-800">{err.data}</div>
                        <div className="text-red-600">{err.error}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
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
              disabled={!jsonlFile || isUploading}
              className="px-6 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors"
            >
              {isUploading ? '업로드 중...' : '학습 데이터셋 업로드'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
