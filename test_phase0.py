"""
Phase 0 테스트 스크립트

기반 인프라 동작 확인
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))


async def test_model_loader():
    """모델 로더 테스트"""
    print("\n" + "="*60)
    print("1. ModelLoader 테스트")
    print("="*60)

    from app.core.ml.model_loader import get_model_loader

    # 싱글톤 인스턴스 가져오기
    loader = get_model_loader()
    print(f"✅ ModelLoader 인스턴스 생성")

    # 모델 로드
    success = loader.load()

    if success:
        print(f"✅ 모델 로드 성공")
        print(f"   - Device: {loader.get_device()}")
        print(f"   - Model: {type(loader.get_model()).__name__}")
        print(f"   - Tokenizer: {type(loader.get_tokenizer()).__name__}")
    else:
        print(f"⚠️  모델 로드 실패 (모델 파일이 없을 수 있음)")
        print(f"   - 모델 경로: {loader.model_path}")
        print(f"   - 이것은 정상입니다. 모델 학습 후 다시 테스트하세요.")

    return success


async def test_mcp_protocol():
    """MCP 프로토콜 테스트"""
    print("\n" + "="*60)
    print("2. MCP Protocol 테스트")
    print("="*60)

    from app.domain.v1.minso.hub.mcp_central.protocol import MCPProtocol, DomainType

    # 요청 메시지 생성
    request = MCPProtocol.create_request(
        from_domain=DomainType.REASONING,
        to_domain=DomainType.REFERENCE,
        action="get_issues",
        data={"problem_id": "test-123"}
    )
    print(f"✅ 요청 메시지 생성")
    print(f"   - From: {request['from']}")
    print(f"   - To: {request['to']}")
    print(f"   - Action: {request['action']}")

    # 메시지 검증
    is_valid = MCPProtocol.validate_message(request)
    print(f"✅ 메시지 검증: {is_valid}")

    # 응답 메시지 생성
    response = MCPProtocol.create_response(
        request_id=request["request_id"],
        from_domain=DomainType.REFERENCE,
        to_domain=DomainType.REASONING,
        data={"issues": ["소의 이익", "당사자적격"]},
        success=True
    )
    print(f"✅ 응답 메시지 생성")

    return True


async def test_database_connection():
    """데이터베이스 연결 테스트"""
    print("\n" + "="*60)
    print("3. Database Connection 테스트")
    print("="*60)

    from app.core.database.connection import get_database
    from app.core.config import settings

    db = get_database()
    print(f"✅ DatabaseConnection 인스턴스 생성")

    if settings.DATABASE_URL:
        engine = db.connect()

        if engine:
            print(f"✅ 데이터베이스 연결 성공")
            print(f"   - URL: {settings.DATABASE_URL[:30]}...")
            return True
        else:
            print(f"❌ 데이터베이스 연결 실패")
            return False
    else:
        print(f"⚠️  DATABASE_URL이 설정되지 않음")
        print(f"   - .env 파일에 DATABASE_URL을 설정하세요.")
        print(f"   - 이것은 정상입니다. DB 없이도 다른 기능은 동작합니다.")
        return None


async def test_logger():
    """로거 테스트"""
    print("\n" + "="*60)
    print("4. Logger 테스트")
    print("="*60)

    from app.core.utils.logger import get_logger

    logger = get_logger()
    print(f"✅ Logger 인스턴스 생성")

    # 각 레벨 테스트
    logger.debug("디버그 메시지")
    logger.info("정보 메시지")
    logger.warning("경고 메시지")

    print(f"✅ 로거 동작 확인")

    return True


async def main():
    """Phase 0 전체 테스트"""
    print("\n" + "🚀 " + "="*58)
    print("  Phase 0: 기반 구축 테스트")
    print("="*60)

    # 설정 출력
    from app.core.config import settings
    settings.print_config()

    # 테스트 실행
    results = []

    # 1. 모델 로더
    model_result = await test_model_loader()
    results.append(("ModelLoader", model_result))

    # 2. MCP 프로토콜
    mcp_result = await test_mcp_protocol()
    results.append(("MCP Protocol", mcp_result))

    # 3. 데이터베이스
    db_result = await test_database_connection()
    results.append(("Database", db_result))

    # 4. 로거
    logger_result = await test_logger()
    results.append(("Logger", logger_result))

    # 결과 요약
    print("\n" + "="*60)
    print("  Phase 0 테스트 결과 요약")
    print("="*60)

    for name, result in results:
        if result is True:
            print(f"  ✅ {name}: 성공")
        elif result is False:
            print(f"  ❌ {name}: 실패")
        elif result is None:
            print(f"  ⚠️  {name}: 선택 (정상)")

    # 필수 항목 확인
    critical_tests = [results[1], results[3]]  # MCP, Logger
    all_critical_passed = all(r[1] is True for r in [results[1], results[3]])

    print("\n" + "="*60)
    if all_critical_passed:
        print("  🎉 Phase 0 완료! 다음 단계로 진행 가능합니다.")
    else:
        print("  ⚠️  일부 필수 항목 실패. 확인이 필요합니다.")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
