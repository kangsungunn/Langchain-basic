# 🧪 LangGraph 오케스트레이터 테스트 명령어

## 📋 테스트 전 준비사항

1. **환경 변수 확인**
   ```bash
   # .env 파일에 DATABASE_URL이 설정되어 있는지 확인
   ```

2. **백엔드 서버 실행** (별도 터미널)
   ```bash
   python -m uvicorn app.main:app --reload
   ```

---

## 🚀 테스트 실행 명령어

### 방법 1: 직접 테스트 스크립트 실행

```bash
# 프로젝트 루트에서 실행
python test_langgraph_orchestrator.py
```

**예상 출력**:
- 규칙 기반 요청 테스트 결과
- 정책 기반 요청 테스트 결과
- 테스트 결과 요약

---

### 방법 2: API 엔드포인트 직접 테스트

#### 규칙 기반 요청 테스트 (학습 데이터 생성)

```bash
curl -X POST http://localhost:8000/api/v1/training/data \
  -H "Content-Type: application/json" \
  -d '{
    "problem_text": "민사소송법에서 소송요건의 의미를 설명하시오.",
    "reference_answer_text": "소송요건은 소송을 제기하기 위해 필요한 요건으로...",
    "user_answer_text": "소송요건은 소송을 제기하기 위한 조건입니다.",
    "labels": {}
  }'
```

**예상 로그** (백엔드 콘솔):
```
🎯 오케스트레이터 요청 처리 시작 (LangGraph)
   └─ 도메인: training
   └─ 액션: create_training_data
🔍 데이터 검증 시작: training.create_training_data
✅ 데이터 검증 완료
📊 전략 판단 시작: training.create_training_data
✅ 규칙 기반 판단 (사전 필터링): training.create_training_data
📋 규칙 기반 처리 시작: training.create_training_data
✅ 규칙 기반 처리 완료
✅ 오케스트레이터 요청 처리 완료 (LangGraph)
   └─ 전략: rule
```

---

#### 정책 기반 요청 테스트 (종합 분석)

```bash
curl -X POST http://localhost:8000/api/v1/reasoning/analyze/comprehensive \
  -H "Content-Type: application/json" \
  -d '{
    "user_answer_id": "test-user-answer-id",
    "reference_answer_id": null,
    "problem_id": null,
    "save_result": false
  }'
```

**예상 로그** (백엔드 콘솔):
```
🎯 오케스트레이터 요청 처리 시작 (LangGraph)
   └─ 도메인: reasoning
   └─ 액션: comprehensive_analysis
🔍 데이터 검증 시작: reasoning.comprehensive_analysis
✅ 데이터 검증 완료
📊 전략 판단 시작: reasoning.comprehensive_analysis
✅ 정책 기반 판단 (사전 필터링): reasoning.comprehensive_analysis
🎯 정책 기반 처리 시작: reasoning.comprehensive_analysis
🌟 Reasoning Hub 처리 시작: reasoning.comprehensive_analysis
✅ 정책 기반 처리 완료
✅ 오케스트레이터 요청 처리 완료 (LangGraph)
   └─ 전략: policy
```

---

### 방법 3: 기존 테스트 스크립트 사용

```bash
# 기존 오케스트레이터 테스트 스크립트 (API 서버 필요)
python scripts/test_orchestrator_manual.py
```

---

## 🔍 확인 사항

### 성공 시 확인할 로그

1. **LangGraph 관련 로그**:
   - `🎯 오케스트레이터 요청 처리 시작 (LangGraph)`
   - `🔍 데이터 검증 시작`
   - `📊 전략 판단 시작`
   - `🎯 정책 기반 처리 시작` 또는 `📋 규칙 기반 처리 시작`
   - `✅ 오케스트레이터 요청 처리 완료 (LangGraph)`

2. **전략 타입 확인**:
   - 규칙 기반: `└─ 전략: rule`
   - 정책 기반: `└─ 전략: policy`

### 실패 시 확인할 사항

1. **에러 메시지 확인**:
   - 백엔드 콘솔의 에러 로그
   - `❌ 워크플로우 처리 중 오류 발생` 메시지

2. **일반적인 문제**:
   - 데이터베이스 연결 실패
   - 세션 관리 문제
   - LangGraph 그래프 빌드 실패

---

## 📝 빠른 테스트 체크리스트

- [ ] 백엔드 서버 실행 중 (`python -m uvicorn app.main:app --reload`)
- [ ] 데이터베이스 연결 확인
- [ ] 규칙 기반 요청 테스트 실행
- [ ] 정책 기반 요청 테스트 실행
- [ ] 백엔드 로그에서 LangGraph 관련 메시지 확인

---

**참고**: 테스트 중 문제가 발생하면 백엔드 콘솔의 에러 로그를 확인하세요.
