# PowerShell API 테스트 (DB 저장 포함)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "FastAPI 엔드포인트 테스트 (DB 저장)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. DB 저장 포함 요청
Write-Host "`n[1/2] LangGraph 워크플로우 테스트 (DB 저장 포함)..." -ForegroundColor Yellow

$body = @{
    text = "긴급송금 필요! 계좌번호 알려주세요!"
    user_id = "test_user_001"
    save_to_db = $true
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
    Write-Host "  Branch: $($response.branch.label) (신뢰도: $([math]::Round($response.branch.confidence, 2)))" -ForegroundColor White

    # DB 저장 확인
    if ($response.db -and $response.db.saved) {
        Write-Host "`n✅ DB 저장 성공!" -ForegroundColor Green
        Write-Host "  input_text_id: $($response.db.input_text_id)" -ForegroundColor White
        Write-Host "  routing_log_id: $($response.db.routing_log_id)" -ForegroundColor White
        Write-Host "  branch_result_id: $($response.db.branch_result_id)" -ForegroundColor White
        Write-Host "  policy_decision_id: $($response.db.policy_decision_id)" -ForegroundColor White
        Write-Host "`n💡 Neon DB 콘솔에서 다음 쿼리로 데이터 확인:" -ForegroundColor Yellow
        Write-Host "   SELECT * FROM input_texts ORDER BY created_at DESC LIMIT 1;" -ForegroundColor Gray
        Write-Host "   SELECT * FROM policy_decisions ORDER BY created_at DESC LIMIT 1;" -ForegroundColor Gray
    } else {
        Write-Host "`n⚠️ DB 저장 실패 또는 스킵됨" -ForegroundColor Yellow
        Write-Host "   응답: $($response.db | ConvertTo-Json)" -ForegroundColor Gray
    }

} catch {
    Write-Host "❌ 실패: $_" -ForegroundColor Red
    Write-Host "상세 에러:" -ForegroundColor Red
    Write-Host $_.Exception.Message
}

# 2. DB 저장 없이 요청 (비교용)
Write-Host "`n[2/2] LangGraph 워크플로우 테스트 (DB 저장 없음)..." -ForegroundColor Yellow

$body2 = @{
    text = "회의 일정을 조율하고 싶습니다."
    user_id = "test_user_002"
    save_to_db = $false
} | ConvertTo-Json

try {
    $response2 = Invoke-RestMethod -Uri "http://localhost:8000/api/mcp/workflow" `
        -Method Post `
        -ContentType "application/json" `
        -Body $body2

    Write-Host "✅ 성공!" -ForegroundColor Green
    Write-Host "  최종 액션: $($response2.final_action)" -ForegroundColor White
    Write-Host "  DB 저장: $($response2.db)" -ForegroundColor White

} catch {
    Write-Host "❌ 실패: $_" -ForegroundColor Red
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "테스트 완료!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
