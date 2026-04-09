# MIDM vs Exaone 모델 비교 분석

## 📌 개요

**목적**: 프로젝트에서 사용할 LLM 모델 선택 가이드
**주체**: 개발자/아키텍트
**역할**: 모델 선택 및 최적화 전략 수립

---

## 📊 모델 사양 비교

| 항목 | MIDM 2.0 Mini | Exaone 3.5 2.4B |
|------|---------------|-----------------|
| **파라미터** | 2.3B | 2.4B (2.14B without embeddings) |
| **아키텍처** | Llama 기반 | Exaone 전용 |
| **개발사** | KT (K-intelligence) | LG AI Research |
| **컨텍스트 길이** | 32,768 토큰 | 32,768 토큰 |
| **Vocab 크기** | 131,392 | 102,400 |
| **레이어 수** | 48 | 30 |

---

## 🎯 각 모델의 강점

### MIDM 2.0 Mini의 강점

**주체**: MIDM 2.0 Mini
**역할**: 한국 문화/사회 특화 LLM

1. **한국 중심 AI (Korea-centric AI)**
   - 한국 사회의 고유한 가치, 인지 프레임워크, 상식 추론에 특화
   - 단순 한국어 처리 이상의 한국 사회 문화적 이해
   - 한국 사회 규범과 가치 반영

2. **한국어 벤치마크 성능**
   - **Society & Culture**: K-Refer 66.4, HAERAE 70.8 (우수)
   - **Instruction Following**: Ko-IFEval 73.3, Ko-MTBench 74.0 (최고 수준)
   - 한국 문화/사회 관련 질문에 강점

3. **깊은 레이어 구조**
   - 48 레이어 (Exaone 30 레이어 대비)
   - 복잡한 추론 작업에 유리할 수 있음

---

### Exaone 3.5 2.4B의 강점

**주체**: Exaone 3.5 2.4B
**역할**: 범용 LLM (Real-world Use Cases 최적화)

1. **Real-world Use Cases 최적화**
   - 실제 사용 사례에 특화된 학습
   - **MT-Bench**: 7.81 (동급 모델 중 최고)
   - **LiveBench**: 33.0 (실시간 작업 성능 우수)
   - **Arena-Hard**: 48.2 (어려운 작업 처리)

2. **다국어 지원**
   - 한국어/영어 모두 우수한 성능
   - **IFEval**: 73.6 (영어 Instruction Following)
   - 국제적 사용 사례에 적합

3. **최적화된 아키텍처**
   - Exaone 전용 아키텍처로 효율성 최적화
   - 30 레이어로 더 빠른 추론 가능
   - 리소스 제약 환경에 적합

4. **배포 옵션 다양**
   - TensorRT-LLM, vLLM, SGLang, llama.cpp, Ollama 지원
   - 양자화 모델 제공 (AWQ, GGUF)

---

## 🔍 벤치마크 비교 (한국어)

### Society & Culture
- **K-Refer**: MIDM 66.4 vs Exaone 64.0 (MIDM 우세)
- **K-Refer-Hard**: Exaone 67.1 vs MIDM 61.4 (Exaone 우세)
- **HAERAE**: MIDM 70.8 vs Exaone 61.3 (MIDM 우세)

### Instruction Following
- **Ko-IFEval**: MIDM 73.3 vs Exaone 65.4 (MIDM 우세)
- **Ko-MTBench**: MIDM 74.0 vs Exaone 74.0 (동등)

### Comprehension
- **K-Prag**: MIDM 69.5 vs Exaone 68.7 (비슷)
- **Ko-Best**: Exaone 87.2 vs MIDM 80.5 (Exaone 우세)

---

## 💡 사용 시나리오 추천

### MIDM 2.0 Mini를 사용하는 경우

**주체**: 개발자/아키텍트
**역할**: 한국 문화 특화 작업에 MIDM 선택

✅ **추천 상황:**
- 한국 문화/사회 관련 질문
- 한국어 상식 추론이 중요한 작업
- 한국 사회 규범과 가치를 이해해야 하는 작업
- Instruction Following 정확도가 중요한 경우
- 한국어 중심 애플리케이션

**예시:**
- "한국의 전통 문화에 대해 설명해주세요"
- "한국 사회의 특성을 반영한 답변이 필요한 경우"
- "한국어로 된 복잡한 지시사항 처리"

---

### Exaone 3.5 2.4B를 사용하는 경우

**주체**: 개발자/아키텍트
**역할**: 범용 작업에 Exaone 선택

✅ **추천 상황:**
- 다국어 (한국어/영어) 지원이 필요한 경우
- Real-world use cases (실제 사용 사례)
- 빠른 응답 속도가 중요한 경우
- 다양한 배포 환경 지원이 필요한 경우
- 일반적인 대화형 AI 애플리케이션

**예시:**
- "일반적인 질문 답변"
- "다국어 지원이 필요한 서비스"
- "실시간 대화형 애플리케이션"
- "리소스 제약이 있는 환경"

---

## 🤔 둘 다 사용할 실익이 있을까?

### ✅ 둘 다 사용하는 것이 유리한 경우

**주체**: 개발자/아키텍트
**역할**: 하이브리드 모델 전략 수립

1. **작업 유형별 분리**
   - 한국 문화/사회 관련 → MIDM
   - 일반 대화/다국어 → Exaone

2. **성능 비교 및 검증**
   - 같은 질문에 대해 두 모델의 답변 비교
   - 더 정확한 답변 선택 가능

3. **Fallback 메커니즘**
   - 한 모델이 실패 시 다른 모델로 대체
   - 안정성 향상

4. **사용자 선택권 제공**
   - 사용자가 모델을 선택할 수 있도록
   - "한국 문화 모드" vs "일반 모드"

---

### ❌ Exaone만 써도 무방한 경우

**주체**: 개발자/아키텍트
**역할**: 단일 모델 전략 수립

1. **리소스 제약**
   - 모델 두 개를 동시에 로드하기 어려운 경우
   - 메모리/GPU 제약이 있는 경우

2. **일반적인 사용 사례**
   - 한국 문화 특화 기능이 필요 없는 경우
   - 일반적인 Q&A만 필요한 경우

3. **배포 단순화**
   - 하나의 모델만 관리하는 것이 더 간단
   - 운영 복잡도 감소

---

## 📝 결론 및 권장사항

### 권장 전략

**주체**: 개발자/아키텍트
**역할**: 프로젝트 요구사항에 맞는 모델 선택

1. **리소스가 충분한 경우**: 둘 다 사용
   - MIDM: 한국 문화/사회 관련 질문
   - Exaone: 일반 대화 및 다국어 지원

2. **리소스가 제한적인 경우**: Exaone만 사용
   - 더 범용적이고 배포 옵션이 다양
   - Real-world use cases에 최적화

3. **한국 문화 특화 서비스**: MIDM 우선
   - 한국 사회 문화 이해가 핵심인 경우
   - Instruction Following 정확도가 중요한 경우

---

### 현재 프로젝트 적용

**현재 프로젝트 상황**:
- Star Topology Hybrid Architecture
- LangChain과 LangGraph 모두 지원
- RAG 기능 포함
- 스팸 필터링 (일반적인 작업)

**현재 사용 모델**:
- **Branch (SpamAgent)**: Exaone 3.5 2.4B + LoRA 어댑터
- **Gateway (ML 보조)**: KoELECTRA

**권장사항**:
→ **Exaone만 사용해도 충분하지만, MIDM을 추가하면 한국 문화 관련 질문에서 더 나은 성능을 기대할 수 있습니다.**

**하이브리드 접근**:
- 기본 모델: Exaone (범용성)
- 특화 모델: MIDM (한국 문화 관련 질문 시 자동 선택)

---

## 🔄 프로젝트 통합 전략

### 현재 아키텍처에서의 모델 위치

```
Gateway (KoELECTRA)
   ↓
Hub Router (Star)
   ↓
Branch (Exaone 3.5 2.4B + LoRA)
```

### MIDM 통합 시나리오

```
Gateway (KoELECTRA)
   ↓
Hub Router (Star)
   ↓
Branch 선택:
   - SpamAgent (Exaone)      ← 현재
   - CultureAgent (MIDM)     ← 추가 가능
   - DefaultAgent (Exaone)   ← 현재
```

**주체**: Hub Router (Star)
**역할**: 작업 유형에 따라 적절한 모델 선택

---

## 📚 참고 문서

- `strategy/36_STAR_TOPOLOGY_HYBRID_ARCHITECTURE.md`: 전체 아키텍처
- `strategy/37.ARCHITECTURE_MAP.md`: 파일 구조 및 역할
- `app/services/branches/spam_agent.py`: 현재 Exaone 사용 예시

---

**마지막 업데이트**: Phase 5 완료 시점
