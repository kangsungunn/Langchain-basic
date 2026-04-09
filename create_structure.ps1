# Legal Answer Review System - 폴더/파일 구조 생성 스크립트
# PowerShell 스크립트

Write-Host "🏗️  Legal Answer Review System 구조 생성 시작..." -ForegroundColor Green

# 루트 폴더
$root = "C:\Users\hi\Documents\rag"
Set-Location $root

# 함수: 폴더 생성
function Create-Folder {
    param($path)
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
        Write-Host "✅ 폴더 생성: $path" -ForegroundColor Cyan
    }
}

# 함수: 빈 파일 생성
function Create-File {
    param($path)
    if (-not (Test-Path $path)) {
        New-Item -ItemType File -Path $path -Force | Out-Null
        Write-Host "📝 파일 생성: $path" -ForegroundColor Yellow
    }
}

# ===== API Layer =====
Write-Host "`n📂 API Layer 생성 중..." -ForegroundColor Magenta

Create-Folder "app\api\routers"
Create-Folder "app\api\schemas"

Create-File "app\api\__init__.py"
Create-File "app\api\main.py"
Create-File "app\api\routers\__init__.py"
Create-File "app\api\routers\reference_router.py"
Create-File "app\api\routers\submission_router.py"
Create-File "app\api\routers\reasoning_router.py"
Create-File "app\api\routers\feedback_router.py"
Create-File "app\api\schemas\__init__.py"
Create-File "app\api\schemas\reference_schemas.py"
Create-File "app\api\schemas\submission_schemas.py"
Create-File "app\api\schemas\reasoning_schemas.py"
Create-File "app\api\schemas\feedback_schemas.py"

# ===== Reference Domain =====
Write-Host "`n📂 Reference Domain 생성 중..." -ForegroundColor Magenta

Create-Folder "app\domain\reference\models"
Create-Folder "app\domain\reference\services"
Create-Folder "app\domain\reference\repositories"

Create-File "app\domain\reference\__init__.py"
Create-File "app\domain\reference\models\__init__.py"
Create-File "app\domain\reference\models\problem.py"
Create-File "app\domain\reference\models\model_answer.py"
Create-File "app\domain\reference\models\issue_structure.py"
Create-File "app\domain\reference\services\__init__.py"
Create-File "app\domain\reference\services\issue_extractor.py"
Create-File "app\domain\reference\services\structure_builder.py"
Create-File "app\domain\reference\services\reference_manager.py"
Create-File "app\domain\reference\repositories\__init__.py"
Create-File "app\domain\reference\repositories\problem_repository.py"
Create-File "app\domain\reference\repositories\model_answer_repository.py"
Create-File "app\domain\reference\repositories\issue_repository.py"

# ===== Submission Domain =====
Write-Host "`n📂 Submission Domain 생성 중..." -ForegroundColor Magenta

Create-Folder "app\domain\submission\models"
Create-Folder "app\domain\submission\services"
Create-Folder "app\domain\submission\repositories"

Create-File "app\domain\submission\__init__.py"
Create-File "app\domain\submission\models\__init__.py"
Create-File "app\domain\submission\models\submission.py"
Create-File "app\domain\submission\models\parsed_answer.py"
Create-File "app\domain\submission\models\answer_structure.py"
Create-File "app\domain\submission\services\__init__.py"
Create-File "app\domain\submission\services\ocr_service.py"
Create-File "app\domain\submission\services\text_parser.py"
Create-File "app\domain\submission\services\structure_normalizer.py"
Create-File "app\domain\submission\services\submission_manager.py"
Create-File "app\domain\submission\repositories\__init__.py"
Create-File "app\domain\submission\repositories\submission_repository.py"

# ===== Reasoning Domain (HUB) =====
Write-Host "`n📂 Reasoning Domain (HUB) 생성 중..." -ForegroundColor Magenta

Create-Folder "app\domain\reasoning\models"
Create-Folder "app\domain\reasoning\agents"
Create-Folder "app\domain\reasoning\orchestrators"
Create-Folder "app\domain\reasoning\repositories"

Create-File "app\domain\reasoning\__init__.py"
Create-File "app\domain\reasoning\models\__init__.py"
Create-File "app\domain\reasoning\models\reasoning_state.py"
Create-File "app\domain\reasoning\models\issue_comparison.py"
Create-File "app\domain\reasoning\models\logic_analysis.py"
Create-File "app\domain\reasoning\models\reasoning_result.py"
Create-File "app\domain\reasoning\agents\__init__.py"
Create-File "app\domain\reasoning\agents\reasoning_agent.py"
Create-File "app\domain\reasoning\agents\issue_detector.py"
Create-File "app\domain\reasoning\agents\logic_analyzer.py"
Create-File "app\domain\reasoning\agents\expression_evaluator.py"
Create-File "app\domain\reasoning\orchestrators\__init__.py"
Create-File "app\domain\reasoning\orchestrators\reasoning_hub.py"
Create-File "app\domain\reasoning\repositories\__init__.py"
Create-File "app\domain\reasoning\repositories\reasoning_repository.py"

# ===== Feedback Domain =====
Write-Host "`n📂 Feedback Domain 생성 중..." -ForegroundColor Magenta

Create-Folder "app\domain\feedback\models"
Create-Folder "app\domain\feedback\services"
Create-Folder "app\domain\feedback\repositories"

Create-File "app\domain\feedback\__init__.py"
Create-File "app\domain\feedback\models\__init__.py"
Create-File "app\domain\feedback\models\feedback.py"
Create-File "app\domain\feedback\models\feedback_item.py"
Create-File "app\domain\feedback\services\__init__.py"
Create-File "app\domain\feedback\services\feedback_generator.py"
Create-File "app\domain\feedback\services\tone_adjuster.py"
Create-File "app\domain\feedback\services\template_manager.py"
Create-File "app\domain\feedback\services\feedback_manager.py"
Create-File "app\domain\feedback\repositories\__init__.py"
Create-File "app\domain\feedback\repositories\feedback_repository.py"

# ===== Shared Domain =====
Write-Host "`n📂 Shared Domain 생성 중..." -ForegroundColor Magenta

Create-Folder "app\domain\shared"

Create-File "app\domain\shared\__init__.py"
Create-File "app\domain\shared\value_objects.py"
Create-File "app\domain\shared\events.py"
Create-File "app\domain\shared\exceptions.py"

# ===== Core Layer =====
Write-Host "`n📂 Core Layer 생성 중..." -ForegroundColor Magenta

Create-Folder "app\core\mcp"
Create-Folder "app\core\orchestration"
Create-Folder "app\core\ml"
Create-Folder "app\core\database"
Create-Folder "app\core\utils"

Create-File "app\core\__init__.py"
Create-File "app\core\config.py"
Create-File "app\core\mcp\__init__.py"
Create-File "app\core\mcp\protocol.py"
Create-File "app\core\mcp\message.py"
Create-File "app\core\mcp\transport.py"
Create-File "app\core\mcp\handlers.py"
Create-File "app\core\orchestration\__init__.py"
Create-File "app\core\orchestration\base_orchestrator.py"
Create-File "app\core\orchestration\workflow_manager.py"
Create-File "app\core\ml\__init__.py"
Create-File "app\core\ml\model_loader.py"
Create-File "app\core\ml\inference.py"
Create-File "app\core\ml\embeddings.py"
Create-File "app\core\database\__init__.py"
Create-File "app\core\database\connection.py"
Create-File "app\core\database\session.py"
Create-File "app\core\database\models.py"
Create-File "app\core\utils\__init__.py"
Create-File "app\core\utils\logger.py"
Create-File "app\core\utils\validators.py"
Create-File "app\core\utils\converters.py"

# ===== Data =====
Write-Host "`n📂 Data 폴더 생성 중..." -ForegroundColor Magenta

Create-Folder "data\raw\civil_procedure\problems"
Create-Folder "data\raw\civil_procedure\model_answers"
Create-Folder "data\processed\civil_procedure"

# ===== Database Schema =====
Write-Host "`n📂 Database Schema 생성 중..." -ForegroundColor Magenta

Create-Folder "database\schema"

Create-File "database\schema\reference_tables.sql"
Create-File "database\schema\submission_tables.sql"
Create-File "database\schema\reasoning_tables.sql"
Create-File "database\schema\feedback_tables.sql"
Create-File "database\schema\init.sql"

# ===== Training =====
Write-Host "`n📂 Training 폴더 생성 중..." -ForegroundColor Magenta

Create-Folder "training\legal"
Create-Folder "training\shared"

Create-File "training\__init__.py"
Create-File "training\legal\train_legal_model.py"
Create-File "training\shared\__init__.py"
Create-File "training\shared\train_exaone_lora.py"
Create-File "training\shared\parse_legal_documents.py"
Create-File "training\shared\data_preprocessor.py"

# ===== Tests =====
Write-Host "`n📂 Tests 폴더 생성 중..." -ForegroundColor Magenta

Create-Folder "tests\unit\domain"
Create-Folder "tests\unit\core"
Create-Folder "tests\integration"
Create-Folder "tests\fixtures"

Create-File "tests\__init__.py"
Create-File "tests\unit\domain\test_reference.py"
Create-File "tests\unit\domain\test_submission.py"
Create-File "tests\unit\domain\test_reasoning.py"
Create-File "tests\unit\domain\test_feedback.py"
Create-File "tests\unit\core\test_mcp.py"
Create-File "tests\unit\core\test_ml.py"
Create-File "tests\integration\test_reference_submission.py"
Create-File "tests\integration\test_reasoning_flow.py"
Create-File "tests\integration\test_end_to_end.py"
Create-File "tests\fixtures\sample_problems.json"
Create-File "tests\fixtures\sample_answers.json"
Create-File "tests\fixtures\sample_feedback.json"

# ===== Scripts =====
Write-Host "`n📂 Scripts 폴더 생성 중..." -ForegroundColor Magenta

Create-Folder "scripts"

Create-File "scripts\init_db.py"
Create-File "scripts\seed_data.py"
Create-File "scripts\migrate.py"

# ===== Frontend API Routes =====
Write-Host "`n📂 Frontend API Routes 생성 중..." -ForegroundColor Magenta

Create-Folder "frontend\src\app\api\reference"
Create-Folder "frontend\src\app\api\submission"
Create-Folder "frontend\src\app\api\reasoning"
Create-Folder "frontend\src\app\api\feedback"

Create-File "frontend\src\app\api\reference\route.ts"
Create-File "frontend\src\app\api\submission\route.ts"
Create-File "frontend\src\app\api\reasoning\route.ts"
Create-File "frontend\src\app\api\feedback\route.ts"

# ===== 루트 파일 =====
Write-Host "`n📂 루트 파일 생성 중..." -ForegroundColor Magenta

Create-File "app\main.py"
Create-File ".env.example"

Write-Host "`n✅ 구조 생성 완료!" -ForegroundColor Green
Write-Host "📁 총 생성된 폴더/파일 수를 확인하세요." -ForegroundColor Cyan
Write-Host "`n다음 단계: 각 파일에 코드 작성" -ForegroundColor Yellow
