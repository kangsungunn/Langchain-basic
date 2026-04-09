# 간단한 PowerShell API 테스트

# LangGraph 워크플로우 테스트
$json = @{
    text = "긴급송금 필요! 계좌번호 알려주세요!"
    user_id = "test_user"
    save_to_db = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/mcp/workflow" `
    -Method Post `
    -ContentType "application/json" `
    -Body $json | ConvertTo-Json -Depth 5
