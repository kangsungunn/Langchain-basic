# PowerShell API 테스트 스크립트

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "FastAPI 엔드포인트 테스트" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. 루트 엔드포인트 확인
Write-Host "`n[1/2] 루트 엔드포인트 테스트..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/" -Method Get
    Write-Host "✅ 성공!" -ForegroundColor Green
    Write-Host ($response | ConvertTo-Json -Depth 3)
} catch {
    Write-Host "❌ 실패: $_" -ForegroundColor Red
}

# 2. LangGraph 워크플로우 테스트
Write-Host "`n[2/2] LangGraph 워크플로우 테스트..." -ForegroundColor Yellow

$body = @{
    text = "긴급송금 필요! 계좌번호 알려주세요!"
    user_id = "test_user"
    save_to_db = $false
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/mcp/workflow" `
        -Method Post `
        -ContentType "application/json" `
        -Body $body

    Write-Host "✅ 성공!" -ForegroundColor Green
    Write-Host "`n응답 내용:" -ForegroundColor Cyan
    Write-Host ($response | ConvertTo-Json -Depth 5)

    Write-Host "`n요약:" -ForegroundColor Cyan
    Write-Host "  최종 액션: $($response.final_action)" -ForegroundColor White
    Write-Host "  근거: $($response.policy_reason)" -ForegroundColor White
    Write-Host "  Gateway: $($response.gateway.route) ($($response.gateway.method))" -ForegroundColor White
    Write-Host "  Branch: $($response.branch.label) (신뢰도: $([math]::Round($response.branch.confidence, 2)))" -ForegroundColor White
    Write-Host "  전체 지연: $([math]::Round($response.performance.total_latency_ms, 2))ms" -ForegroundColor White

} catch {
    Write-Host "❌ 실패: $_" -ForegroundColor Red
    Write-Host "상세 에러:" -ForegroundColor Red
    Write-Host $_.Exception.Message
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "테스트 완료!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
