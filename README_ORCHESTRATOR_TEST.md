# 🧪 오케스트레이터 테스트 가이드

## 📋 테스트 방법

### 방법 1: 수동 테스트 스크립트 (추천)

**파일**: `scripts/test_orchestrator_manual.py`

**실행 방법**:
```bash
# 1. 백엔드 서버 실행 (별도 터미널)
python -m uvicorn app.main:app --reload

# 2. 테스트 스크립트 실행
python scripts/test_orchestrator_manual.py
```

**테스트 항목**:
- ✅ 규칙 기반 요청: 학습 데이터 생성
- ✅ 정책 기반 요청: 종합 분석
- ✅ 정책 기반 요청: 피드백 생성

---

### 방법 2: 직접 API 호출

#### 규칙 기반 요청 테스트

```bash
curl -X POST http://localhost:8000/api/v1/training/data \
  -H "Content-Type: application/json" \
  -d '{
    "problem_text": "민사소송법에서 소송요건의 의미를 설명하시오.",
    "reference_answer_text": "소송요건은 소송을 제기하기 위해 필요한 요건으로...",
    "user_answer_text": "소송요건은 소송을 제기하기 위한 조건입니다."
  }'
```

**예상 로그**:
```
✅ 규칙 기반 판단 (사전 필터링): training.create_training_data
📋 규칙 기반 전략: 일반 서비스로 직접 라우팅 - training.create_training_data
✅ 일반 서비스 처리 완료: training.create_training_data
```

#### 정책 기반 요청 테스트

```bash
curl -X POST http://localhost:8000/api/v1/reasoning/analyze/comprehensive \
  -H "Content-Type: application/json" \
  -d '{
    "user_answer_id": "test-user-answer-id",
    "reference_answer_id": "test-reference-answer-id",
    "problem_id": "test-problem-id",
    "save_result": true
  }'
```

**예상 로그**:
```
✅ 정책 기반 판단 (사전 필터링): reasoning.comprehensive_analysis
🎯 정책 기반 전략: Star 토폴로지로 라우팅 - reasoning.comprehensive_analysis
🌟 Reasoning Hub 처리 시작: reasoning.comprehensive_analysis
✅ Star 토폴로지 처리 완료: reasoning.comprehensive_analysis
```

---

### 방법 3: Swagger UI 테스트

1. **백엔드 서버 실행**
   ```bash
   python -m uvicorn app.main:app --reload
   ```

2. **브라우저에서 접속**
   - http://localhost:8000/docs

3. **엔드포인트 테스트**
   - `/api/v1/training/data` (규칙 기반)
   - `/api/v1/reasoning/analyze/comprehensive` (정책 기반)
   - `/api/v1/feedback/generate` (정책 기반)

---

## 🔍 확인 사항

### 백엔드 로그에서 확인할 내용

#### 규칙 기반 요청
```
🎯 오케스트레이터 요청 처리 시작
   └─ 도메인: training
   └─ 액션: create_training_data
========================================
✅ 규칙 기반 판단 (사전 필터링): training.create_training_data
📊 판단 결과: rule 기반
📋 규칙 기반 전략: 일반 서비스로 직접 라우팅 - training.create_training_data
✅ 일반 서비스 처리 완료: training.create_training_data
========================================
✅ 오케스트레이터 요청 처리 완료
   └─ 전략: rule
   └─ 도메인: training
   └─ 액션: create_training_data
========================================
```

#### 정책 기반 요청
```
🎯 오케스트레이터 요청 처리 시작
   └─ 도메인: reasoning
   └─ 액션: comprehensive_analysis
========================================
✅ 정책 기반 판단 (사전 필터링): reasoning.comprehensive_analysis
📊 판단 결과: policy 기반
🎯 정책 기반 전략: Star 토폴로지로 라우팅 - reasoning.comprehensive_analysis
🌟 Reasoning Hub 처리 시작: reasoning.comprehensive_analysis
✅ Star 토폴로지 처리 완료: reasoning.comprehensive_analysis
========================================
✅ 오케스트레이터 요청 처리 완료
   └─ 전략: policy
   └─ 도메인: reasoning
   └─ 액션: comprehensive_analysis
========================================
```

---

## ⚠️ 문제 해결

### 문제 1: KoELECTRA 모델 없음

**증상**:
```
⚠️  KoELECTRA 모델을 사용할 수 없습니다. 기본값으로 규칙 기반 처리합니다.
```

**해결**:
- 사전 필터링으로 동작하므로 문제 없음
- 더 정확한 판단을 원하면 KoELECTRA 모델 다운로드

### 문제 2: 서비스 메서드 찾을 수 없음

**증상**:
```
ValueError: 알 수 없는 액션: training.create_training_data (서비스 메서드: create)
```

**해결**:
- `app/core/orchestration/strategies/rule_strategy.py`의 `_action_mapping` 확인
- 필요시 매핑 추가

### 문제 3: Reasoning Hub에서 처리 실패

**증상**:
```
❌ Reasoning Hub 처리 실패: reasoning.comprehensive_analysis
```

**해결**:
- `app/domain/reasoning/orchestrators/reasoning_hub.py` 확인
- 액션 이름이 올바른지 확인

---

## 📊 테스트 결과 예시

### 성공적인 테스트

```
🧪 오케스트레이터 통합 테스트
========================================

========================================
📋 규칙 기반 요청 테스트: 학습 데이터 생성
========================================
✅ 상태 코드: 201
📊 응답: {
  "id": "xxx-xxx-xxx",
  "problem_text": "민사소송법에서 소송요건의 의미를 설명하시오.",
  ...
}
✅ 규칙 기반 요청 성공!

========================================
🎯 정책 기반 요청 테스트: 종합 분석
========================================
✅ 상태 코드: 200
📊 응답 키: ['task_id', 'results', 'summary']
✅ 정책 기반 요청 성공!

========================================
✅ 테스트 완료!
========================================
```

---

## 🎯 다음 단계

1. ✅ 테스트 실행
2. ✅ 로그 확인
3. ✅ 동작 검증
4. ⏭️ KoELECTRA 모델 다운로드 (선택)
5. ⏭️ 추가 라우터 연동 (필요시)
