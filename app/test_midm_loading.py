"""
Midm 모델 로딩 테스트

환경 변수를 설정하고 모델이 제대로 로드되는지 확인합니다.
"""
import os

# 환경 변수 설정
os.environ["LLM_PROVIDER"] = "local_llama"
os.environ["MIDM_MODEL_PATH"] = "app/models/midm"

print("=" * 70)
print("🧪 Midm 모델 로딩 테스트")
print("=" * 70)

print(f"\n환경 변수:")
print(f"  LLM_PROVIDER: {os.getenv('LLM_PROVIDER')}")
print(f"  MIDM_MODEL_PATH: {os.getenv('MIDM_MODEL_PATH')}")

try:
    print("\n🔄 모델 팩토리에서 LLM 생성 중...")
    from app.models.factory import ModelFactory

    llm = ModelFactory.create_llm()

    print(f"✅ LLM 생성 완료!")
    print(f"   모델 이름: {llm.get_model_name()}")
    print(f"   모델 설정: {llm.get_model_config()}")

    print("\n🔄 실제 모델 인스턴스 가져오는 중...")
    model = llm.get_model()

    print(f"✅ 모델 인스턴스 로드 완료!")
    print(f"   타입: {type(model)}")

    print("\n🧪 간단한 테스트...")
    response = model.invoke("안녕하세요!")
    print(f"✅ 응답: {response}")

    print("\n" + "=" * 70)
    print("✅ Midm 모델 로딩 테스트 완료!")
    print("=" * 70)

except Exception as e:
    print(f"\n❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()

