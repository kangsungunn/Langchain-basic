'use client'

import Link from 'next/link'

export default function HomePage() {
    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
            <div className="container mx-auto px-4 py-16">
                {/* 헤더 */}
                <header className="text-center mb-16">
                    <h1 className="text-5xl font-bold text-gray-900 mb-4">
                        변리사 민사소송법 답안지 첨삭 서비스
                    </h1>
                    <p className="text-xl text-gray-600">
                        AI 기반 자동 첨삭으로 답안의 쟁점, 논리, 표현을 종합적으로 분석합니다
                    </p>
                </header>

                {/* 메인 콘텐츠 */}
                <div className="max-w-4xl mx-auto">
                    {/* 기능 소개 */}
                    <div className="grid md:grid-cols-3 gap-8 mb-12">
                        <div className="bg-white rounded-lg shadow-lg p-6 text-center">
                            <div className="text-4xl mb-4">📊</div>
                            <h3 className="text-xl font-semibold mb-2">쟁점 분석</h3>
                            <p className="text-gray-600">
                                모범 답안과 비교하여 쟁점 포함 여부를 정확히 분석합니다
                            </p>
                        </div>

                        <div className="bg-white rounded-lg shadow-lg p-6 text-center">
                            <div className="text-4xl mb-4">🧠</div>
                            <h3 className="text-xl font-semibold mb-2">논리 평가</h3>
                            <p className="text-gray-600">
                                논리 일관성과 논증 강도를 체계적으로 평가합니다
                            </p>
                        </div>

                        <div className="bg-white rounded-lg shadow-lg p-6 text-center">
                            <div className="text-4xl mb-4">✍️</div>
                            <h3 className="text-xl font-semibold mb-2">표현 검토</h3>
                            <p className="text-gray-600">
                                명료성, 격식성, 문법을 종합적으로 검토합니다
                            </p>
                        </div>
                    </div>

                    {/* 시작 버튼 */}
                    <div className="text-center space-y-4">
                        <Link
                            href="/upload"
                            className="inline-block bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-lg px-8 py-4 rounded-lg shadow-lg transition-colors duration-200"
                        >
                            답안지 첨삭 시작하기 →
                        </Link>
                        <div className="pt-4">
                            <Link
                                href="/v1/admin"
                                className="inline-block bg-purple-600 hover:bg-purple-700 text-white font-semibold px-6 py-3 rounded-lg shadow-md transition-colors duration-200"
                            >
                                관리자 페이지
                            </Link>
                        </div>
                    </div>

                    {/* 사용 방법 */}
                    <div className="mt-16 bg-white rounded-lg shadow-lg p-8">
                        <h2 className="text-2xl font-bold mb-6 text-center">사용 방법</h2>
                        <ol className="space-y-4 text-gray-700">
                            <li className="flex items-start">
                                <span className="flex-shrink-0 w-8 h-8 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center font-semibold mr-4">
                                    1
                                </span>
                                <span>PDF 형식의 문제와 답안지를 준비합니다</span>
                            </li>
                            <li className="flex items-start">
                                <span className="flex-shrink-0 w-8 h-8 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center font-semibold mr-4">
                                    2
                                </span>
                                <span>답안지 업로드 화면에서 파일을 드래그하거나 선택합니다</span>
                            </li>
                            <li className="flex items-start">
                                <span className="flex-shrink-0 w-8 h-8 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center font-semibold mr-4">
                                    3
                                </span>
                                <span>첨삭 시작 버튼을 클릭하여 자동 분석을 시작합니다</span>
                            </li>
                            <li className="flex items-start">
                                <span className="flex-shrink-0 w-8 h-8 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center font-semibold mr-4">
                                    4
                                </span>
                                <span>분석 결과를 확인하고 상세 피드백을 받습니다</span>
                            </li>
                        </ol>
                    </div>
                </div>
            </div>
        </div>
    )
}
