# 🎯 EXAONE 기반 스팸 필터 학습 루프 전략 (LangGraph)

## 📋 개요

이 문서는 **EXAONE-3.5-2.4B-Instruct** 모델을 기반으로, **한국우편사업진흥원 스팸메일 수신차단 목록** 데이터셋을 활용하여 **SFT → QLoRA → RLHF(DPO)** 학습 파이프라인을 **LangGraph** 위에서 구성하는 전략을 제시합니다.

---

## ✅ ChatGPT 전략 검증 및 개선

### 🔍 데이터셋 재분석

**ChatGPT의 가정**: "차단 목록(IP/도메인)" 성격의 데이터

**실제 데이터 구조** (CSV 파일 분석 결과):
- 컬럼: `날짜`, `시간`, `발신자`, `제목`, `첨부파일`
- 내용: 실제 스팸 메일 샘플의 **메타데이터** (제목, 발신자, 첨부파일 정보)
- 총 95,134개 샘플

**결론**: ChatGPT의 분석이 부분적으로 맞습니다. 이 데이터는:
- ✅ "차단 목록" 성격 (이미 차단된 스팸 메일)
- ✅ 메타데이터 중심 (본문 없음)
- ❌ 하지만 "IP/도메인 목록"이 아니라 "실제 스팸 메일 샘플 메타데이터"

### 🎯 개선된 문제 정의

**원래 전략의 문제점**:
1. ALLOW(정상) 샘플이 없음 → 음성 샘플 확보 필요
2. 본문 기반 분류 불가 → 메타데이터 기반 판정으로 축소

**개선된 전략**:
1. **메타데이터 기반 스팸 판정 모델** 구축 (제목, 발신자, 첨부파일 패턴)
2. **정상 메일 샘플 생성**: 공개 데이터셋 또는 합성 데이터 활용
3. **단계적 학습**: SFT → QLoRA → DPO 순차 진행

---

## 🏗️ 전체 아키텍처

### 1. LangGraph의 역할

**ChatGPT 전략 검증**: ✅ **올바름**

LangGraph는 **학습 자체를 수행하지 않고**, **학습 파이프라인을 오케스트레이션**하는 역할을 합니다.

```
┌─────────────────────────────────────────────────────────┐
│              LangGraph 학습 루프 오케스트레이터          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [데이터 준비] → [SFT 학습] → [평가] → [DPO 학습]      │
│       ↓              ↓          ↓           ↓            │
│   [노드 A]      [노드 B]   [노드 C]    [노드 D]         │
│                                                          │
│  조건 분기: metrics 기반 루프 제어                       │
│  - 오탐률 높음 → 정상 데이터 보강                       │
│  - 형식 오류 → 프롬프트 수정                            │
│  - 정책 위반 → 선호 데이터 강화                         │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 2. 현재 프로젝트 상태

**기존 인프라**:
- ✅ LangGraph 기반 RAG 시스템 구축됨 (`app/graph.py`)
- ✅ EXAONE-3.5-2.4B-Instruct 모델 로컬 설치됨 (`app/models/exaone-2.4b`)
- ✅ QLoRA 파인튜닝 API 구현됨 (`strategy/20_QLORA_FINETUNING_API_GUIDE.md`)
- ✅ Repository 패턴, Service 레이어 구조화됨

**추가 필요 사항**:
- ✅ **데이터 변환 파이프라인 완료** (`app/services/spam_agent/extract_jsonl.py`)
  - CSV → JSONL 변환 구현 완료
  - 95,133개 샘플 변환 성공
  - 출력 파일: `app/data/한국우편사업진흥원_스팸메일 수신차단 목록_20241231.jsonl`
- ❌ 학습 루프용 LangGraph 그래프 (새로 구축 필요)
- ❌ DPO 학습 파이프라인 (구현 필요)

---

## 📊 단계별 전략

### Phase 0: 데이터 준비 및 변환

#### 0.1 데이터 구조 분석

**현재 데이터**:
```csv
날짜,시간,발신자,제목,첨부파일
2024-01-01,00:20:30,발신자1,Offer,"Offer.docx (16.4 K), Offer - contextual advertising.docx (15.8 K)"
```

**목표 학습 포맷** (SFT용):
```json
{
  "instruction": "다음 이메일 메타데이터를 분석하여 스팸 여부를 판정하세요.",
  "input": {
    "sender": "발신자1",
    "subject": "Offer",
    "attachments": ["Offer.docx", "Offer - contextual advertising.docx"],
    "date": "2024-01-01",
    "time": "00:20:30"
  },
  "output": {
    "action": "BLOCK",
    "reason": "의심스러운 첨부파일 패턴 및 제목",
    "confidence": 0.95
  }
}
```

#### 0.2 정상 메일 샘플 확보 전략

**옵션 1: 공개 데이터셋 활용** (권장)
- Enron Email Dataset (정상 메일)
- SpamAssassin Public Corpus (햄 부분만 추출)
- 자체 메일 로그 (개인정보 제거 후)

**옵션 2: 합성 데이터 생성**
- GPT/EXAONE으로 정상 메일 메타데이터 생성
- 규칙 기반 정상 패턴 생성 (회사 도메인, 일반적인 제목 등)

**옵션 3: 최소 버전 (MVP)**
- BLOCK 판정만 학습 (정상 판정은 나중에 추가)
- 운영 중 쌓이는 정상 케이스로 점진 개선

#### 0.3 JSON vs JSONL: 학습 데이터 포맷 선택

**왜 JSONL이 LLM 학습의 사실상 표준인가?**

##### JSON (JavaScript Object Notation)

**형태**: 하나의 큰 객체(Object) 또는 배열(Array)로 구성

```json
[
  {
    "instruction": "다음 이메일 메타데이터를 분석하세요.",
    "input": {"sender": "spam@example.com", "subject": "Offer"},
    "output": {"action": "BLOCK", "reason": "의심스러운 발신자"}
  },
  {
    "instruction": "다음 이메일 메타데이터를 분석하세요.",
    "input": {"sender": "normal@company.com", "subject": "Meeting"},
    "output": {"action": "ALLOW", "reason": "정상적인 회사 메일"}
  }
]
```

**특징**:
- ✅ 파일 전체가 하나의 유효한 JSON 문서
- ✅ 구조 검증, 스키마 검증에 유리
- ✅ 설정 파일, API 응답 저장에 적합
- ❌ **대용량 데이터에 불리**: 10GB JSON이면 통째로 메모리에 로드 필요
- ❌ **스트리밍 불가**: 중간 한 줄만 수정/추가 어려움
- ❌ **분산 처리 어려움**: 샤딩, 샘플링이 복잡

##### JSONL (JSON Lines, NDJSON)

**형태**: 한 줄 = 하나의 독립적인 JSON 객체

```jsonl
{"instruction": "다음 이메일 메타데이터를 분석하세요.", "input": {"sender": "spam@example.com", "subject": "Offer"}, "output": {"action": "BLOCK", "reason": "의심스러운 발신자"}}
{"instruction": "다음 이메일 메타데이터를 분석하세요.", "input": {"sender": "normal@company.com", "subject": "Meeting"}, "output": {"action": "ALLOW", "reason": "정상적인 회사 메일"}}
```

**특징**:
- ✅ **스트리밍 처리 가능**: 한 줄씩 읽어서 처리
- ✅ **메모리 효율적**: 전체 파일을 메모리에 올릴 필요 없음
- ✅ **추가/수정 용이**: 파일 끝에 append만 하면 됨
- ✅ **분산 학습 최적**: 샤딩, 샘플링이 자연스러움
- ✅ **LLM 학습 구조와 1:1 대응**: `for sample in dataset: train(sample)`
- ❌ 파일 전체는 유효한 JSON이 아님 (각 줄만 JSON)

##### 왜 LLM 학습에서는 JSONL이 사실상 표준인가?

1. **메모리 효율**
   ```
   JSON  : 10GB 파일 → 전체 로딩 필요 → 메모리 부족
   JSONL : 10GB 파일 → 한 줄씩 스트리밍 → 메모리 효율적
   ```

2. **샘플 단위 처리와 구조적 일치**
   ```python
   # LLM 학습의 기본 구조
   for sample in dataset:
       prompt = format_prompt(sample["input"])
       response = model.generate(prompt)
       loss = compute_loss(response, sample["output"])

   # JSONL 파일 구조가 이 루프와 완벽히 일치
   with open("train.jsonl") as f:
       for line in f:  # 한 줄 = 한 샘플
           sample = json.loads(line)
           train(sample)
   ```

3. **Hugging Face Datasets / TRL 표준**
   - Hugging Face `datasets` 라이브러리: JSONL 기본 지원
   - TRL (SFTTrainer, DPOTrainer): JSONL 입력 포맷
   - 대부분의 LLM 파인튜닝 파이프라인: JSONL 사용

4. **LangGraph 파이프라인과의 호환성**
   ```
   ingest node      → JSONL 생성
   filter/augment   → JSONL 변형 (줄 단위)
   train node       → JSONL 스트리밍 로드
   eval node        → 실패 케이스 JSONL로 누적
   preference node  → DPO용 JSONL 생성
   ```
   모든 단계가 **줄 단위 샘플 처리**라 JSONL이 구조적으로 완벽히 맞습니다.

##### 실무 기준: 언제 JSON, 언제 JSONL?

| 용도 | 권장 포맷 | 이유 |
|------|----------|------|
| 설정 파일, 메타데이터 | JSON | 구조 검증, 스키마 검증 필요 |
| API 결과 저장 | JSON | 단일 응답 객체 |
| 학습 데이터셋 | **JSONL 필수** | 스트리밍, 메모리 효율 |
| 로그 데이터, 이벤트 스트림 | JSONL | append 용이, 스트리밍 |
| LLM SFT / DPO / RLHF | **JSONL 필수** | 표준 포맷, 라이브러리 호환 |

##### SFT / DPO 포맷 예시

**SFT용 JSONL**:
```jsonl
{"prompt": "발신자: spam@example.com\n제목: Offer\n...", "response": "{\"action\": \"BLOCK\", \"reason\": \"의심스러운 발신자\", \"confidence\": 0.95}"}
{"prompt": "발신자: normal@company.com\n제목: Meeting\n...", "response": "{\"action\": \"ALLOW\", \"reason\": \"정상적인 회사 메일\", \"confidence\": 0.98}"}
```

**DPO용 JSONL**:
```jsonl
{"prompt": "발신자: spam@example.com\n제목: Offer\n...", "chosen": "{\"action\": \"BLOCK\", \"reason\": \"의심스러운 발신자 도메인\", \"confidence\": 0.95}", "rejected": "{\"action\": \"ALLOW\", \"reason\": \"불확실\", \"confidence\": 0.5}"}
{"prompt": "발신자: normal@company.com\n제목: Meeting\n...", "chosen": "{\"action\": \"ALLOW\", \"reason\": \"정상적인 회사 메일\", \"confidence\": 0.98}", "rejected": "{\"action\": \"BLOCK\", \"reason\": \"과도한 판단\", \"confidence\": 0.3}"}
```

#### 0.4 데이터 변환 파이프라인

**✅ 구현 완료**: `app/services/spam_agent/extract_jsonl.py`

**실제 구현된 기능**:
- CSV 파일 읽기 및 파싱
- 메타데이터 추출 및 정규화 (제목, 첨부파일, 날짜, 시간)
- 첨부파일 파싱 (크기 정보 제거, 파일명만 추출)
- 스팸 판정 근거 자동 생성 (제목/첨부파일 패턴 분석)
- 신뢰도 자동 계산
- JSONL 포맷으로 변환 (한 줄 = 한 샘플)

**변환 결과**:
- 입력: `app/data/한국우편사업진흥원_스팸메일 수신차단 목록_20241231.csv`
- 출력: `app/data/한국우편사업진흥원_스팸메일 수신차단 목록_20241231.jsonl`
- 성공: 95,133개 샘플
- 실패: 0개

**생성된 JSONL 구조**:
```json
{
  "instruction": "다음 이메일 메타데이터를 분석하여 스팸 여부를 판정하세요.",
  "input": {
    "subject": "Offer",
    "attachments": ["Offer.docx", "Offer - contextual advertising.docx"],
    "date": "2024-01-01",
    "time": "00:20:30",
    "mail_type": "스팸"
  },
  "output": {
    "action": "BLOCK",
    "reason": "의심스러운 제목 패턴",
    "confidence": 0.95
  }
}
```

**사용 방법**:
```bash
# 직접 실행
python app/services/spam_agent/extract_jsonl.py

# 또는 모듈로 사용
from app.services.spam_agent.extract_jsonl import SpamDataConverter
converter = SpamDataConverter()
converter.convert_csv_to_jsonl("path/to/input.csv", "path/to/output.jsonl")
```

**LangGraph 노드 통합 예정**: `ingest_and_transform_node`

```python
def ingest_and_transform_node(state: TrainingState):
    """
    1. CSV 파일 읽기 (또는 이미 변환된 JSONL 사용)
    2. 메타데이터 추출 및 정규화
    3. 라벨링 (현재 데이터는 모두 BLOCK)
    4. 정상 샘플 추가 (옵션 1/2/3 중 선택)
    5. Train/Val/Test 분할
    6. JSONL 포맷으로 저장 (한 줄 = 한 샘플)
    """
    from app.services.spam_agent.extract_jsonl import SpamDataConverter

    # 이미 변환된 JSONL이 있으면 사용, 없으면 변환
    converter = SpamDataConverter()
    # 변환 로직
    # 분할 로직
    return updated_state
```

**JSONL 로드 유틸리티**:
```python
import json

def load_jsonl(input_path: str):
    """JSONL 파일을 스트리밍으로 읽기"""
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            yield json.loads(line.strip())
```

---

### Phase 1: SFT (Supervised Fine-Tuning)

#### 1.1 학습 목표

**ChatGPT 전략 검증**: ✅ **올바름**

EXAONE-3.5-2.4B-Instruct는 이미 instruction-tuned 모델이므로, **도메인 특화 정책 주입**이 목표입니다.

**학습 태스크**:
- 입력: 이메일 메타데이터 (JSON)
- 출력: 스팸 판정 + 근거 (JSON)

#### 1.2 프롬프트 설계

```python
SYSTEM_PROMPT = """당신은 이메일 스팸 필터링 전문가입니다.
다음 이메일 메타데이터를 분석하여 스팸 여부를 판정하고, 그 근거를 제시하세요.

출력 형식:
{
  "action": "BLOCK" 또는 "ALLOW",
  "reason": "판정 근거 (한국어)",
  "confidence": 0.0-1.0 사이의 숫자
}
"""

USER_TEMPLATE = """다음 이메일 메타데이터를 분석하세요:

발신자: {sender}
제목: {subject}
첨부파일: {attachments}
수신일시: {date} {time}
"""
```

#### 1.3 LangGraph 노드: `train_sft_node`

**ChatGPT 전략 검증**: ✅ **올바름**

```python
def train_sft_node(state: TrainingState):
    """
    1. EXAONE-3.5-2.4B-Instruct 로드
    2. QLoRA 설정 (4-bit + LoRA)
    3. 학습 데이터 로드 (JSONL)
    4. Transformers Trainer로 학습 실행
    5. 체크포인트 저장
    6. 학습 메트릭 기록
    """
    # 기존 QLoRA API 활용 가능
    # app/services/chat_service.py의 train_qlora_model 참고
    return updated_state
```

**QLoRA 설정** (EXAONE-3.5-2.4B-Instruct):
```python
{
    "lora_r": 8,  # 2.4B 모델이므로 작은 값으로 충분
    "lora_alpha": 16,
    "lora_dropout": 0.05,
    "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],  # EXAONE 구조 확인 필요
    "bits": 4,  # 4-bit 양자화
    "learning_rate": 2e-4,
    "num_train_epochs": 3,
    "per_device_train_batch_size": 4
}
```

---

### Phase 2: 평가 및 메트릭 수집

#### 2.1 평가 메트릭

**ChatGPT 전략 검증**: ✅ **대부분 올바름**

```python
metrics = {
    "accuracy": 0.95,  # 전체 정확도
    "precision": 0.92,  # BLOCK 중 실제 스팸 비율
    "recall": 0.98,     # 스팸 중 올바르게 차단한 비율
    "f1_score": 0.95,
    "fp_rate": 0.02,    # 오탐률 (정상을 스팸으로)
    "fn_rate": 0.01,    # 미탐률 (스팸을 정상으로)
    "format_ok": 0.99,  # JSON 형식 준수율
    "policy_violation": 0.0,  # 정책 위반률 (예: 차단 목록에 있는데 ALLOW)
    "hard_cases": []    # 실패/애매한 케이스
}
```

#### 2.2 LangGraph 노드: `eval_node`

```python
def eval_node(state: TrainingState):
    """
    1. 검증셋 로드
    2. 모델 추론 실행
    3. 메트릭 계산
    4. Hard case 수집 (오탐/미탐 샘플)
    5. 규칙 기반 검증 (차단 목록 hit이면 반드시 BLOCK)
    """
    # 평가 실행
    # 메트릭 계산
    # Hard case 저장
    return updated_state
```

---

### Phase 3: DPO (Direct Preference Optimization)

#### 3.1 DPO 개요 및 왜 PPO 대신 DPO인가?

**ChatGPT 전략 검증**: ✅ **올바름**

**DPO (Direct Preference Optimization)**는 PPO (Proximal Policy Optimization)보다 실용적이며, EXAONE-3.5도 DPO를 사용했습니다.

**PPO vs DPO 비교**:

| 항목 | PPO | DPO |
|------|-----|-----|
| **보상 모델 필요** | ✅ 필요 (별도 학습) | ❌ 불필요 |
| **안정화 난이도** | 높음 (하이퍼파라미터 민감) | 낮음 (상대적으로 안정적) |
| **학습 비용** | 높음 (보상 모델 + 정책 모델) | 낮음 (정책 모델만) |
| **선호 데이터** | 보상 점수 필요 | 선호 쌍만 필요 |
| **스팸 필터 적합성** | 과함 (복잡함) | ✅ 적합 (실용적) |

**DPO의 핵심 아이디어**:
- 선호 쌍 (chosen, rejected)만으로 직접 최적화
- 보상 모델 없이 선호도를 학습에 반영
- 스팸 필터처럼 "정답 1개"보다 "더 나은 답변" 최적화에 적합

#### 3.2 선호 데이터 생성 전략

**선호 쌍 생성 방법**:

1. **Hard case 기반** (주요 방법):
   - 평가 단계에서 수집한 애매한 케이스 활용
   - 각 케이스에 대해 SFT 모델이 여러 답변 생성 (temperature 다양화)
   - 더 나은 답변 선택 (규칙/휴먼/약한 심사 모델)

2. **규칙 기반 선호**:
   - 차단 목록 일치 → BLOCK이 ALLOW보다 선호
   - 형식 준수 → JSON 형식이 자연어보다 선호
   - 신뢰도 높음 → confidence 높은 답변이 낮은 답변보다 선호

3. **일관성 기반 선호**:
   - 유사한 케이스에 일관된 판정이 더 선호
   - 유사도 계산 후 일관성 검증

**선호 데이터 포맷 (JSONL)**:
```jsonl
{"prompt": "발신자: spam@example.com\n제목: Offer\n첨부파일: Offer.docx\n수신일시: 2024-01-01 00:20:30", "chosen": "{\"action\": \"BLOCK\", \"reason\": \"의심스러운 발신자 도메인 및 첨부파일 패턴\", \"confidence\": 0.95}", "rejected": "{\"action\": \"ALLOW\", \"reason\": \"불확실\", \"confidence\": 0.5}"}
{"prompt": "발신자: normal@company.com\n제목: Meeting\n첨부파일: agenda.pdf\n수신일시: 2024-01-01 09:00:00", "chosen": "{\"action\": \"ALLOW\", \"reason\": \"정상적인 회사 메일\", \"confidence\": 0.98}", "rejected": "{\"action\": \"BLOCK\", \"reason\": \"과도한 판단\", \"confidence\": 0.3}"}
```

#### 3.3 LangGraph 노드: `build_preference_node` (상세 구현)

```python
def build_preference_node(state: TrainingState) -> TrainingState:
    """
    1. Hard case 로드 (JSONL)
    2. 각 케이스에 대해 후보 답변 2-3개 생성 (SFT 모델 사용)
    3. 선호도 평가 (규칙/휴먼/약한 모델)
    4. 선호 쌍 생성 및 JSONL 저장
    """
    import json
    from app.services.chat_service import ChatService

    # 1. Hard case 로드
    hard_cases = []
    with open(state["hard_cases_path"], 'r', encoding='utf-8') as f:
        for line in f:
            hard_cases.append(json.loads(line.strip()))

    # 2. SFT 모델 로드
    sft_model_path = state["sft_model_path"]
    chat_service = ChatService()
    model, tokenizer = chat_service.load_trained_qlora_model(
        base_model_name="LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct",
        adapter_path=sft_model_path
    )

    # 3. 선호 쌍 생성
    preference_pairs = []

    for case in hard_cases:
        prompt = format_prompt(case["input"])

        # 여러 답변 생성 (temperature 다양화)
        candidates = []
        for temp in [0.3, 0.7, 1.0]:
            response = generate_response(model, tokenizer, prompt, temperature=temp)
            candidates.append(response)

        # 선호도 평가
        chosen, rejected = evaluate_preferences(
            prompt=prompt,
            candidates=candidates,
            ground_truth=case.get("expected_output"),
            rules=state.get("preference_rules", [])
        )

        # 선호 쌍 저장
        preference_pairs.append({
            "prompt": prompt,
            "chosen": json.dumps(chosen, ensure_ascii=False),
            "rejected": json.dumps(rejected, ensure_ascii=False)
        })

    # 4. JSONL로 저장
    preference_pairs_path = f"{state['output_dir']}/preference_pairs.jsonl"
    with open(preference_pairs_path, 'w', encoding='utf-8') as f:
        for pair in preference_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + '\n')

    state["preference_pairs_path"] = preference_pairs_path
    state["preference_pairs_count"] = len(preference_pairs)

    return state

def evaluate_preferences(prompt: str, candidates: List[dict],
                        ground_truth: Optional[dict],
                        rules: List[callable]) -> Tuple[dict, dict]:
    """
    선호도 평가 함수
    규칙 기반 + 그라운드 트루스 기반 평가
    """
    scores = []

    for candidate in candidates:
        score = 0

        # 규칙 기반 점수
        for rule in rules:
            score += rule(candidate)

        # 그라운드 트루스 기반 점수
        if ground_truth:
            if candidate["action"] == ground_truth["action"]:
                score += 10
            if candidate.get("confidence", 0) > 0.8:
                score += 5

        scores.append((score, candidate))

    # 점수 순으로 정렬
    scores.sort(reverse=True, key=lambda x: x[0])

    chosen = scores[0][1]  # 최고 점수
    rejected = scores[-1][1]  # 최저 점수

    return chosen, rejected
```

#### 3.4 LangGraph 노드: `train_dpo_node` (상세 구현)

```python
def train_dpo_node(state: TrainingState) -> TrainingState:
    """
    1. SFT 모델 로드
    2. 선호 데이터 로드 (JSONL)
    3. DPO 학습 실행 (trl 라이브러리 사용)
    4. 체크포인트 저장
    5. 메트릭 기록
    """
    from trl import DPOTrainer
    from transformers import TrainingArguments
    from datasets import load_dataset
    import json

    # 1. SFT 모델 로드
    sft_model_path = state["sft_model_path"]
    base_model_name = "LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct"

    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel

    # 4-bit 양자화 설정
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    # 베이스 모델 로드
    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True
    )
    tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)

    # QLoRA 어댑터 로드
    model = PeftModel.from_pretrained(model, sft_model_path)

    # 2. 선호 데이터 로드 (JSONL)
    def load_preference_dataset(jsonl_path: str):
        """JSONL을 Hugging Face Dataset으로 변환"""
        data = []
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                data.append(json.loads(line.strip()))
        return data

    preference_data = load_preference_dataset(state["preference_pairs_path"])

    # Hugging Face Dataset 형식으로 변환
    dataset = load_dataset("json", data_files=state["preference_pairs_path"], split="train")

    # 3. DPO 학습 설정
    training_args = TrainingArguments(
        output_dir=f"{state['output_dir']}/dpo_checkpoints",
        num_train_epochs=1,  # DPO는 보통 1 에폭
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=1e-5,  # DPO는 더 작은 학습률
        logging_steps=10,
        save_steps=100,
        fp16=True,
        remove_unused_columns=False,
    )

    # DPO Trainer 초기화
    dpo_trainer = DPOTrainer(
        model=model,
        ref_model=None,  # DPO는 reference model 없이도 가능
        args=training_args,
        beta=0.1,  # DPO temperature 파라미터
        train_dataset=dataset,
        tokenizer=tokenizer,
        max_length=512,
        max_prompt_length=256,
    )

    # 4. 학습 실행
    dpo_trainer.train()

    # 5. 최종 모델 저장
    dpo_model_path = f"{state['output_dir']}/dpo_final_model"
    dpo_trainer.save_model(dpo_model_path)
    tokenizer.save_pretrained(dpo_model_path)

    # 6. 메트릭 기록
    training_metrics = dpo_trainer.state.log_history

    state["dpo_model_path"] = dpo_model_path
    state["dpo_metrics"] = {
        "train_loss": training_metrics[-1].get("train_loss", 0),
        "learning_rate": training_metrics[-1].get("learning_rate", 0),
    }

    return state
```

**DPO 설정 상세**:
```python
{
    "learning_rate": 1e-5,  # DPO는 더 작은 학습률 (SFT보다 작음)
    "num_train_epochs": 1,  # DPO는 보통 1 에폭 (과적합 방지)
    "beta": 0.1,  # DPO temperature 파라미터 (0.1-0.5 권장)
    "per_device_train_batch_size": 2,  # 메모리 제약으로 작게
    "gradient_accumulation_steps": 4,  # 효과적 배치 크기 = 2 * 4 = 8
    "max_length": 512,  # 최대 시퀀스 길이
    "max_prompt_length": 256,  # 프롬프트 최대 길이
}
```

#### 3.5 DPO 학습 흐름 다이어그램

```
┌─────────────────────────────────────────────────────────┐
│                    DPO 학습 파이프라인                  │
└─────────────────────────────────────────────────────────┘

[평가 단계] → Hard case 수집 (JSONL)
     ↓
[선호 데이터 생성]
     ├─ Hard case 로드
     ├─ SFT 모델로 여러 답변 생성 (temperature 다양화)
     ├─ 선호도 평가 (규칙 + 그라운드 트루스)
     └─ 선호 쌍 생성 (chosen, rejected) → JSONL 저장
     ↓
[DPO 학습]
     ├─ SFT 모델 로드 (베이스 + QLoRA 어댑터)
     ├─ 선호 데이터 로드 (JSONL)
     ├─ DPOTrainer 초기화
     ├─ 학습 실행 (1 에폭)
     └─ DPO 모델 저장
     ↓
[재평가] → 메트릭 계산 → 루프 제어
```

#### 3.6 DPO 학습 후 검증

```python
def validate_dpo_model(state: TrainingState) -> dict:
    """
    DPO 모델 검증
    - 선호 쌍에 대해 chosen이 rejected보다 높은 확률을 가지는지 확인
    - 정확도, 형식 준수율 등 메트릭 계산
    """
    # DPO 모델 로드
    dpo_model = load_dpo_model(state["dpo_model_path"])

    # 검증 데이터셋 로드
    validation_pairs = load_jsonl(state["preference_pairs_path"])

    correct_preferences = 0
    total = 0

    for pair in validation_pairs:
        prompt = pair["prompt"]
        chosen = pair["chosen"]
        rejected = pair["rejected"]

        # 각 답변의 확률 계산
        chosen_prob = compute_probability(dpo_model, prompt, chosen)
        rejected_prob = compute_probability(dpo_model, prompt, rejected)

        # chosen이 rejected보다 높은 확률을 가지는지 확인
        if chosen_prob > rejected_prob:
            correct_preferences += 1
        total += 1

    preference_accuracy = correct_preferences / total

    return {
        "preference_accuracy": preference_accuracy,
        "correct_preferences": correct_preferences,
        "total_pairs": total
    }
```

---

## 🔄 LangGraph 상태 및 루프 설계

### State 정의

**ChatGPT 전략 검증**: ✅ **올바름**

```python
class TrainingState(TypedDict):
    # 데이터 관련
    dataset_version: str
    train_data_path: str
    val_data_path: str
    test_data_path: str

    # 학습 설정
    train_config: dict  # base_model, lora_r, lr, epochs 등

    # 모델 아티팩트
    sft_model_path: Optional[str]
    dpo_model_path: Optional[str]

    # 메트릭
    metrics: dict  # accuracy, fp_rate, format_ok 등

    # Hard case 및 선호 데이터
    hard_cases: List[dict]
    preference_pairs_path: Optional[str]

    # 루프 제어
    iteration: int
    max_iterations: int
    should_continue: bool
```

### 노드 구성

**ChatGPT 전략 검증**: ✅ **올바름** (6개 노드 제안)

**모든 데이터는 JSONL 포맷으로 처리** (JSON이 아님!)

```python
# 1. 데이터 수집 및 변환
ingest_node:
    - CSV 파일 읽기
    - 메타데이터 추출 및 정규화
    - 라벨링 (BLOCK/ALLOW)
    - Train/Val/Test 분할
    - JSONL 포맷으로 저장 (한 줄 = 한 샘플)

# 2. SFT 데이터 준비
build_sft_node:
    - JSONL 로드 (스트리밍)
    - Instruction 포맷 변환 (prompt + response)
    - JSONL로 저장 (SFT 학습용)

# 3. SFT 학습
train_sft_qlora_node:
    - EXAONE-3.5-2.4B-Instruct 로드
    - QLoRA 설정 (4-bit + LoRA)
    - JSONL 데이터셋 로드 (Hugging Face datasets)
    - Transformers Trainer로 학습 실행
    - QLoRA 어댑터 저장

# 4. 평가
eval_node:
    - 검증셋 JSONL 로드
    - 모델 추론 실행
    - 메트릭 계산 (accuracy, fp_rate, format_ok 등)
    - Hard case 수집 (오탐/미탐 샘플)
    - Hard case를 JSONL로 저장

# 5. 선호 데이터 생성
build_pref_node:
    - Hard case JSONL 로드
    - 각 케이스에 대해 후보 답변 2-3개 생성 (SFT 모델)
    - 선호도 평가 (규칙/그라운드 트루스)
    - 선호 쌍 생성 (chosen, rejected)
    - DPO용 JSONL 저장 (한 줄 = 하나의 선호 쌍)

# 6. DPO 학습
train_dpo_node:
    - SFT 모델 로드 (베이스 + QLoRA 어댑터)
    - 선호 데이터 JSONL 로드
    - DPOTrainer 초기화 (trl 라이브러리)
    - DPO 학습 실행 (1 에폭)
    - DPO 모델 저장 (QLoRA 어댑터)
    - 학습 메트릭 기록
```

### 조건 분기 (Loop Control)

**ChatGPT 전략 검증**: ✅ **올바름**

```python
def should_continue_training(state: TrainingState) -> str:
    """
    루프 제어 로직
    """
    metrics = state["metrics"]
    iteration = state["iteration"]

    # 최대 반복 횟수 체크
    if iteration >= state["max_iterations"]:
        return "release"

    # 오탐률이 높으면 정상 데이터 보강
    if metrics.get("fp_rate", 0) > 0.05:  # 5% 이상
        return "augment_data"

    # 형식 오류가 많으면 프롬프트 수정
    if metrics.get("format_ok", 1.0) < 0.95:
        return "fix_prompt"

    # 정책 위반이 있으면 선호 데이터 강화
    if metrics.get("policy_violation", 0) > 0:
        return "strengthen_preferences"

    # 모든 조건 만족
    if (metrics.get("accuracy", 0) > 0.95 and
        metrics.get("fp_rate", 0) < 0.02 and
        metrics.get("format_ok", 1.0) > 0.99):
        return "release"

    # 다음 반복
    return "continue"
```

### 그래프 구조

```python
def build_training_graph():
    graph = StateGraph(TrainingState)

    # 노드 추가
    graph.add_node("ingest", ingest_node)
    graph.add_node("build_sft", build_sft_node)
    graph.add_node("train_sft", train_sft_qlora_node)
    graph.add_node("eval", eval_node)
    graph.add_node("build_pref", build_pref_node)
    graph.add_node("train_dpo", train_dpo_node)
    graph.add_node("augment_data", augment_data_node)  # 추가 노드
    graph.add_node("fix_prompt", fix_prompt_node)      # 추가 노드

    # 엔트리 포인트
    graph.set_entry_point("ingest")

    # 엣지
    graph.add_edge("ingest", "build_sft")
    graph.add_edge("build_sft", "train_sft")
    graph.add_edge("train_sft", "eval")
    graph.add_edge("eval", "build_pref")
    graph.add_edge("build_pref", "train_dpo")
    graph.add_edge("train_dpo", "eval")  # DPO 후 재평가

    # 조건 분기
    graph.add_conditional_edges(
        "eval",
        should_continue_training,
        {
            "continue": "build_pref",      # 다음 DPO 반복
            "augment_data": "augment_data", # 데이터 보강
            "fix_prompt": "fix_prompt",     # 프롬프트 수정
            "strengthen_preferences": "build_pref",  # 선호 데이터 강화
            "release": END                  # 종료
        }
    )

    graph.add_edge("augment_data", "build_sft")  # 데이터 보강 후 재학습
    graph.add_edge("fix_prompt", "build_sft")    # 프롬프트 수정 후 재학습

    return graph.compile()
```

---

## 🛠️ 구현 단계별 가이드

### Step 1: 데이터 변환 모듈 생성

**파일**: `app/training/data_converter.py`

```python
class SpamDataConverter:
    def convert_csv_to_jsonl(self, csv_path: str, output_path: str):
        """CSV → JSONL 변환"""
        pass

    def add_normal_samples(self, spam_data: List[dict]) -> List[dict]:
        """정상 샘플 추가"""
        pass

    def split_dataset(self, data: List[dict]) -> Tuple[List, List, List]:
        """Train/Val/Test 분할"""
        pass
```

### Step 2: 학습 노드 구현

**파일**: `app/training/nodes.py`

```python
def ingest_node(state: TrainingState) -> TrainingState:
    """데이터 수집 및 변환"""
    converter = SpamDataConverter()
    # 변환 로직
    return updated_state

def train_sft_qlora_node(state: TrainingState) -> TrainingState:
    """SFT 학습"""
    # 기존 chat_service.train_qlora_model 활용
    return updated_state

def eval_node(state: TrainingState) -> TrainingState:
    """평가 및 메트릭 수집"""
    # 평가 로직
    return updated_state

def build_pref_node(state: TrainingState) -> TrainingState:
    """선호 데이터 생성"""
    # 선호 쌍 생성
    return updated_state

def train_dpo_node(state: TrainingState) -> TrainingState:
    """DPO 학습"""
    # DPO 학습 로직
    return updated_state
```

### Step 3: LangGraph 그래프 생성

**파일**: `app/training/training_graph.py`

```python
from app.training.nodes import *
from app.training.state import TrainingState

def build_training_graph():
    """학습 루프 그래프 생성"""
    # 위의 그래프 구조 구현
    pass
```

### Step 4: API 엔드포인트 추가

**파일**: `app/router/training_router.py`

```python
@router.post("/training/start")
async def start_training(config: TrainingConfig):
    """학습 루프 시작"""
    graph = build_training_graph()
    # 그래프 실행
    pass

@router.get("/training/status")
async def get_training_status():
    """학습 상태 조회"""
    pass
```

---

## 📈 예상 학습 시간 및 리소스

### 하드웨어 요구사항

**EXAONE-3.5-2.4B-Instruct + QLoRA**:
- 최소: 6GB VRAM (4-bit 양자화)
- 권장: 8GB+ VRAM
- CPU: 학습 가능하나 매우 느림 (권장하지 않음)

### 학습 시간 예상

**SFT 단계**:
- 데이터: 24.5K 샘플 (중복 제거 후) → Train: 19.6K, Val: 2.45K, Test: 2.45K
- 에폭: 3
- 배치 크기: 4
- 예상 시간: **1-2시간** (GPU 기준)

**DPO 단계**:
- 선호 쌍: 1K-5K (Hard case 기반)
- 에폭: 1
- 예상 시간: **30분-1시간** (GPU 기준)

**전체 루프** (3-5 반복):
- 예상 시간: **10-20시간** (GPU 기준)

---

## ⚠️ 주의사항 및 개선점

### ChatGPT 전략의 한계점

1. **데이터 불균형**: 정상 샘플 부족 → 합성 데이터 품질이 중요
2. **메타데이터만으로는 한계**: 본문이 없어서 정확도에 한계
3. **실시간 업데이트**: 차단 목록이 업데이트되면 재학습 필요

### 개선 방안

1. **하이브리드 접근**:
   - 규칙 기반 필터 (차단 목록 일치) + ML 모델 (애매한 케이스)

2. **온라인 학습**:
   - 운영 중 쌓이는 피드백으로 점진 개선

3. **앙상블**:
   - 여러 모델의 결과 결합

---

## 🎯 다음 단계

### ✅ 완료된 작업

1. **✅ 데이터 변환 모듈 구현 완료**
   - 파일: `app/services/spam_agent/extract_jsonl.py`
   - 기능: CSV → JSONL 변환
   - 결과: 95,133개 샘플 변환 성공
   - 출력: `app/data/한국우편사업진흥원_스팸메일 수신차단 목록_20241231.jsonl`

### 🔄 진행 중 / 다음 작업

2. **데이터셋 분할 및 정상 샘플 추가**
   - Train/Val/Test 분할 (80/10/10)
   - 정상 메일 샘플 추가 (옵션 1/2/3 중 선택)
   - 분할된 JSONL 파일 생성

3. **✅ SFT 데이터 포맷 변환 완료**
   - 파일: `app/services/spam_agent/extract_dpo.py`
   - 기능: JSONL → SFT 형식 변환
   - 중복 제거: subject + attachments 기준
   - 결과: 95,133개 → 24,571개 (중복 제거 후)
   - 출력: `app/data/한국우편사업진흥원_스팸메일 수신차단 목록_20241231.sft.jsonl`

4. **학습 노드 구현** (`app/training/nodes.py`)
   - `ingest_node`: 데이터 수집 및 변환
   - `build_sft_node`: SFT 데이터 준비
   - `train_sft_qlora_node`: SFT 학습
   - `eval_node`: 평가 및 메트릭 수집
   - `build_pref_node`: 선호 데이터 생성
   - `train_dpo_node`: DPO 학습

5. **LangGraph 그래프 생성** (`app/training/training_graph.py`)
   - State 정의
   - 노드 연결
   - 조건 분기 로직
   - 루프 제어

6. **DPO 학습 파이프라인 구현** (trl 라이브러리 활용)
   - DPOTrainer 설정
   - 선호 데이터 로드
   - 학습 실행 및 검증

7. **API 엔드포인트 추가** (`app/router/training_router.py`)
   - 학습 루프 시작 API
   - 학습 상태 조회 API
   - 메트릭 조회 API

8. **테스트 및 검증**
   - 단위 테스트
   - 통합 테스트
   - 성능 검증

---

## 🔄 ETL 기반 SFT 학습 파이프라인 (스팸메일 판단 에이전트 구축)

### 📋 개요

이 섹션은 **ETL (Extract, Transform, Load)** 방식으로 데이터를 처리하여 **EXAONE-3.5-2.4B-Instruct** 모델을 스팸메일 판단 에이전트로 학습시키는 전체 과정을 설명합니다.

**목표**: `app/models/exaone-2.4b` 모델을 `app/data/한국우편사업진흥원_스팸메일 수신차단 목록_20241231.sft.jsonl` 데이터셋으로 SFT 학습하여 스팸메일 판단 에이전트로 변환

---

### 🔍 ETL 파이프라인 개요

```
┌─────────────────────────────────────────────────────────────┐
│                    ETL 파이프라인                            │
└─────────────────────────────────────────────────────────────┘

[Extract] → [Transform] → [Load] → [Train] → [Evaluate] → [Deploy]
    ↓            ↓           ↓         ↓          ↓           ↓
  CSV 파일    JSONL 변환   데이터셋   SFT 학습   평가      에이전트
  읽기        정규화      분할      QLoRA     메트릭    배포
```

---

### Phase 1: Extract (추출)

#### 1.1 데이터 소스 확인

**입력 데이터**:
- 위치: `app/data/한국우편사업진흥원_스팸메일 수신차단 목록_20241231.csv`
- 형식: CSV (UTF-8-sig 인코딩)
- 크기: 9.4MB
- 샘플 수: 95,134개 (헤더 제외)

**데이터 구조**:
```csv
수신일자,수신시간,메일 종류,제목,첨부
2024-01-01,00:20:30,스팸,Offer,"Offer.docx (16.4 K), ..."
```

#### 1.2 이미 변환된 데이터 확인

**중간 데이터 (JSONL)**:
- 위치: `app/data/한국우편사업진흥원_스팸메일 수신차단 목록_20241231.jsonl`
- 형식: JSONL (한 줄 = 한 샘플)
- 크기: 34MB
- 샘플 수: 95,133개

**최종 학습 데이터 (SFT JSONL)**:
- 위치: `app/data/한국우편사업진흥원_스팸메일 수신차단 목록_20241231.sft.jsonl`
- 형식: SFT 학습용 JSONL
- 크기: 9.4MB
- 샘플 수: 24,571개 (중복 제거 후)

**SFT 데이터 구조**:
```json
{
  "instruction": "다음 이메일 메타데이터를 분석하여 스팸 여부를 판정하고 JSON 형식으로만 답하세요.",
  "input": {
    "subject": "Offer",
    "attachments": ["Offer.docx", "Offer - contextual advertising.docx"],
    "received_at": "2024-01-01 00:20:30"
  },
  "output": {
    "action": "BLOCK",
    "reason": "스팸/광고성 키워드 패턴이 포함됨 / 첨부파일이 포함됨",
    "confidence": 0.99
  }
}
```

---

### Phase 2: Transform (변환)

#### 2.1 데이터 변환 단계

**Step 1: CSV → JSONL 변환**
- 모듈: `app/services/spam_agent/extract_jsonl.py`
- 기능:
  - CSV 파일 읽기 및 파싱
  - 메타데이터 추출 (날짜, 시간, 제목, 첨부파일)
  - 스팸 판정 근거 생성
  - 신뢰도 계산
  - JSONL 포맷으로 저장

**Step 2: JSONL → SFT JSONL 변환**
- 모듈: `app/services/spam_agent/extract_dpo.py`
- 기능:
  - JSONL 파일 읽기 (스트리밍)
  - 데이터 정규화
  - 중복 제거 (subject + attachments 기준)
  - Rule-based labeling
  - SFT 학습 포맷으로 변환
  - Instruction 포맷 적용

#### 2.2 데이터 품질 검증

**검증 항목**:
1. **데이터 무결성**
   - 모든 필수 필드 존재 여부
   - JSON 형식 유효성
   - 인코딩 문제 확인

2. **데이터 분포**
   - BLOCK/ALLOW 비율
   - 제목 길이 분포
   - 첨부파일 유무 비율
   - 신뢰도 분포

3. **중복 제거 효과**
   - 원본: 95,133개
   - 중복 제거 후: 24,571개
   - 제거율: 약 74%

#### 2.3 데이터셋 분할

**분할 전략**:
- Train: 80% (19,657개)
- Validation: 10% (2,457개)
- Test: 10% (2,457개)

**분할 방법**:
- 랜덤 시드 고정 (재현성)
- 계층적 샘플링 (BLOCK/ALLOW 비율 유지)
- 시간 순서 고려 (최신 데이터는 Test에 포함)

**⚠️ 참고**: 현재 문서에서는 Train/Val/Test로 분할하지만, 실제 구현 시에는 **Train/Validation 분할**만 먼저 진행하고, Test는 최종 평가용으로 별도 보관할 수 있습니다.

---

### Phase 3: Load (로드 및 학습 준비)

**⚠️ 중요**: 이 단계는 전통적인 ETL의 "Load"와 다르게, **모델과 데이터를 메모리에 로드하고 학습 준비**를 하는 단계입니다.

#### 3.1 모델 준비

**베이스 모델**:
- 위치: `app/models/exaone-2.4b`
- 모델: EXAONE-3.5-2.4B-Instruct
- 특징:
  - 파라미터: 2.14B (임베딩 제외)
  - 레이어: 30
  - 어텐션 헤드: GQA (32 Q-heads, 8 KV-heads)
  - Vocab 크기: 102,400
  - 컨텍스트 길이: 32,768 토큰
  - 이미 instruction-tuned 모델

**모델 파일 구조**:
```
app/models/exaone-2.4b/
├── config.json                    # 모델 설정
├── tokenizer.json                 # 토크나이저
├── tokenizer_config.json          # 토크나이저 설정
├── vocab.json                     # 어휘 사전
├── merges.txt                     # BPE 병합 규칙
├── model-00001-of-00002.safetensors  # 모델 가중치 (4.6GB)
├── model-00002-of-00002.safetensors  # 모델 가중치 (4.3GB)
├── modeling_exaone.py             # EXAONE 전용 모델링 코드
└── configuration_exaone.py         # EXAONE 설정
```

#### 3.2 데이터셋 로드

**Hugging Face Datasets 사용**:
- JSONL 파일을 `datasets` 라이브러리로 로드
- 스트리밍 방식으로 메모리 효율적 처리
- 자동 캐싱 및 샤딩 지원
- 데이터 구조 검증 및 데이터셋 객체 변환

**데이터셋 구조**:
```python
{
    "instruction": str,      # 지시문
    "input": {               # 입력 데이터
        "subject": str,
        "attachments": List[str],
        "received_at": str
    },
    "output": {              # 출력 데이터
        "action": str,       # "BLOCK" or "ALLOW"
        "reason": str,       # 판정 근거
        "confidence": float  # 신뢰도
    }
}
```

**데이터셋 검증**:
- 필수 필드 존재 여부 확인
- 데이터 타입 유효성 검증
- 샘플 수 확인 (24,572개)

#### 3.3 SFT 학습용 텍스트 포맷 변환

**변환 과정**:
1. Instruction + Input → 프롬프트 텍스트
2. Output → 응답 텍스트
3. EXAONE 프롬프트 형식 적용
4. 토크나이징 준비

**시퀀스 길이 관리**:
- Max length: 512 tokens
- Truncation: 긴 시퀀스 자동 잘라내기
- Padding: 배치 처리 시 패딩 적용

#### 3.4 프롬프트 템플릿 적용

**EXAONE 프롬프트 형식**:
```
[[system]]{system_prompt}[[endofturn]]
[[user]]{user_prompt}[[endofturn]]
[[assistant]]{response}[[endofturn]]
```

**SFT 학습용 프롬프트 변환**:
```
[[system]]당신은 이메일 스팸 필터링 전문가입니다. 다음 이메일 메타데이터를 분석하여 스팸 여부를 판정하고 JSON 형식으로만 답하세요.[[endofturn]]
[[user]]다음 이메일 메타데이터를 분석하세요:

제목: {subject}
첨부파일: {attachments}
수신일시: {received_at}[[endofturn]]
[[assistant]]{"action": "{action}", "reason": "{reason}", "confidence": {confidence}}[[endofturn]]
```

---

### Phase 4: Train (학습)

#### 4.1 EXAONE-2.4B 모델 로드

**모델 로드 과정**:
1. 베이스 모델 경로 지정: `app/models/exaone-2.4b`
2. 4-bit 양자화 설정 (NF4)
3. BitsAndBytesConfig로 양자화 적용
4. `trust_remote_code=True` 필수 (EXAONE 전용 코드)
5. 모델 로드 및 메모리 최적화

**4-bit 양자화 설정**:
- Bits: 4-bit (NF4)
- Compute dtype: bfloat16
- 메모리 효율적 모델 로딩 (~4GB VRAM)

#### 4.2 PEFT/QLoRA 설정

**PEFT (Parameter-Efficient Fine-Tuning) 설정**:
- PEFT 라이브러리 사용
- QLoRA 어댑터만 학습 (전체 모델 파라미터는 고정)

**QLoRA 설정** (4-bit 양자화 + LoRA 어댑터):
- QLoRA rank (r): 8
- QLoRA alpha: 16
- QLoRA dropout: 0.05
- Target modules: ["q_proj", "k_proj", "v_proj", "o_proj"]
  - EXAONE 구조에 맞는 어텐션 레이어

#### 4.3 하이퍼파라미터 설정

**학습 하이퍼파라미터**:
- Learning rate: 2e-4
- Batch size: 4 (per device)
- Gradient accumulation: 4 (효과적 배치 크기 = 16)
- Epochs: 3
- Warmup steps: 100
- Max length: 512 tokens
- Optimizer: paged_adamw_8bit
- FP16: True (혼합 정밀도 학습)

#### 4.2 학습 프로세스

**Step 1: 모델 로드**
1. 베이스 모델 로드 (`app/models/exaone-2.4b`)
2. 4-bit 양자화 적용
3. QLoRA 어댑터 초기화
4. 토크나이저 로드

**Step 2: 데이터셋 준비**
1. SFT JSONL 파일 로드
2. Train/Val/Test 분할
3. 프롬프트 템플릿 적용
4. 토크나이징 (instruction + input + output)

**Step 3: 학습 실행**
1. **SFTTrainer 초기화** (TRL 라이브러리 사용)
   - SFTTrainer는 instruction-following 학습에 최적화
   - 자동 프롬프트 템플릿 처리
   - 손실 함수 자동 계산
2. 학습 루프 시작
3. 체크포인트 저장 (100 steps마다)
4. Validation 평가 (각 epoch마다)
5. 학습 메트릭 기록 (loss, learning rate 등)

**Step 4: QLoRA 어댑터 저장**
1. 최종 QLoRA 어댑터 저장
   - `adapter_config.json`: QLoRA 설정
   - `adapter_model.safetensors`: 학습된 가중치
2. 토크나이저 저장 (베이스 모델과 동일)
3. 학습 설정 저장 (하이퍼파라미터 기록)
4. 메트릭 저장 (학습 로그, loss curve 등)

#### 4.3 학습 모니터링

**로깅 메트릭**:
- Train loss (각 step)
- Learning rate (각 step)
- Validation loss (각 epoch)
- 학습 시간
- GPU 메모리 사용량

**체크포인트 관리**:
- 최근 3개 체크포인트만 유지
- 최종 모델 별도 저장
- 베스트 모델 저장 (validation loss 기준)

---

### Phase 5: Evaluate (평가)

#### 5.1 평가 메트릭

**분류 메트릭**:
- Accuracy: 전체 정확도
- Precision: BLOCK 중 실제 스팸 비율
- Recall: 스팸 중 올바르게 차단한 비율
- F1 Score: Precision과 Recall의 조화평균

**형식 검증 메트릭**:
- JSON 형식 준수율
- 필수 필드 존재 여부
- 데이터 타입 유효성

**신뢰도 메트릭**:
- 평균 신뢰도
- 신뢰도 분포
- 고신뢰도 샘플 비율

#### 5.2 평가 프로세스

**Step 1: 모델 로드**
- 학습된 QLoRA 어댑터 로드
- 베이스 모델과 결합

**Step 2: 추론 실행**
- Test 데이터셋에 대해 추론
- 배치 단위 처리 (효율성)

**Step 3: 결과 분석**
- 예측값과 정답 비교
- 오류 케이스 수집
- Hard case 식별

**Step 4: 리포트 생성**
- 메트릭 요약
- 오류 케이스 분석
- 개선 방안 제시

---

### Phase 6: Deploy (배포)

#### 6.1 에이전트 구성

**에이전트 인터페이스**:
```python
class SpamFilterAgent:
    def __init__(self, model_path, adapter_path):
        # 모델 로드
        # 토크나이저 로드

    def predict(self, email_metadata: dict) -> dict:
        """
        이메일 메타데이터를 받아 스팸 여부를 판정

        Args:
            email_metadata: {
                "subject": str,
                "attachments": List[str],
                "received_at": str
            }

        Returns:
            {
                "action": "BLOCK" or "ALLOW",
                "reason": str,
                "confidence": float
            }
        """
        # 프롬프트 생성
        # 모델 추론
        # 결과 파싱
        # 반환
```

#### 6.2 API 통합

**REST API 엔드포인트**:
- `POST /api/spam-filter/predict`: 스팸 판정
- `POST /api/spam-filter/batch-predict`: 배치 판정
- `GET /api/spam-filter/status`: 에이전트 상태

**입력 형식**:
```json
{
  "subject": "Offer",
  "attachments": ["Offer.docx"],
  "received_at": "2024-01-01 00:20:30"
}
```

**출력 형식**:
```json
{
  "action": "BLOCK",
  "reason": "스팸/광고성 키워드 패턴이 포함됨",
  "confidence": 0.99,
  "timestamp": "2024-12-31T12:00:00"
}
```

#### 6.3 성능 최적화

**추론 최적화**:
- 배치 처리 지원
- 토큰 캐싱
- KV 캐시 활용
- GPU 메모리 효율적 사용

**응답 시간 목표**:
- 단일 요청: < 500ms
- 배치 요청 (10개): < 2초

---

### 📊 전체 파이프라인 흐름도

```
┌─────────────────────────────────────────────────────────────┐
│                    ETL + SFT 학습 파이프라인                │
└─────────────────────────────────────────────────────────────┘

[Extract]
  CSV 파일 읽기
  ↓
[Transform]
  CSV → JSONL 변환 (extract_jsonl.py)
  JSONL → SFT JSONL 변환 (extract_dpo.py)
  중복 제거 및 정규화
  Train/Val/Test 분할
  ↓
[Load]
  EXAONE 모델 로드 (app/models/exaone-2.4b)
  SFT 데이터셋 로드 (Hugging Face datasets)
  프롬프트 템플릿 적용
  토크나이징
  ↓
[Train]
  QLoRA 설정 (4-bit 양자화 + LoRA 어댑터)
  학습 실행 (Transformers Trainer)
  체크포인트 저장
  학습 메트릭 기록
  ↓
[Evaluate]
  Test 데이터셋 평가
  메트릭 계산
  오류 케이스 분석
  ↓
[Deploy]
  에이전트 클래스 구현
  API 엔드포인트 추가
  성능 최적화
  프로덕션 배포
```

---

### 🎯 구현 단계별 체크리스트

#### ✅ 완료된 단계

- [x] CSV → JSONL 변환 모듈 (`app/services/spam_agent/extract_jsonl.py`)
- [x] JSONL → SFT JSONL 변환 모듈 (`app/services/spam_agent/extract_dpo.py`)
- [x] SFT 데이터셋 생성 (24,571개 샘플)
- [x] EXAONE 모델 확인 (`app/models/exaone-2.4b`)

#### 🔄 다음 구현 단계

- [ ] 데이터셋 분할 모듈 (Train/Val/Test)
- [ ] EXAONE 프롬프트 템플릿 적용 모듈
- [ ] QLoRA 학습 스크립트 (EXAONE 전용)
- [ ] 평가 모듈 (메트릭 계산)
- [ ] 에이전트 클래스 구현
- [ ] API 엔드포인트 추가
- [ ] 배포 스크립트

---

### ⚙️ 하이퍼파라미터 권장값

**EXAONE-3.5-2.4B-Instruct 기준**:

```python
{
    # QLoRA 설정
    "lora_r": 8,
    "lora_alpha": 16,
    "lora_dropout": 0.05,
    "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
    "bits": 4,
    "compute_dtype": "bfloat16",

    # 학습 설정
    "learning_rate": 2e-4,
    "num_train_epochs": 3,
    "per_device_train_batch_size": 4,
    "gradient_accumulation_steps": 4,
    "warmup_steps": 100,
    "max_length": 512,
    "optim": "paged_adamw_8bit",
    "fp16": True,

    # 데이터셋
    "train_split": 0.8,
    "val_split": 0.1,
    "test_split": 0.1,
}
```

---

### 📈 예상 학습 시간 및 리소스

**하드웨어 요구사항**:
- GPU: 최소 6GB VRAM (4-bit 양자화)
- 권장: 8GB+ VRAM
- CPU: 학습 가능하나 매우 느림 (권장하지 않음)

**학습 시간 예상**:
- 데이터: 24,571개 → Train: 19,657개
- 에폭: 3
- 배치 크기: 4 (효과적 배치 = 16)
- 예상 시간: **1-2시간** (GPU 기준, RTX 3060 이상)

**메모리 사용량**:
- 모델 로드: ~4GB (4-bit)
- 학습 중: ~6-8GB (gradient 포함)
- 체크포인트: ~100MB (QLoRA 어댑터만)

---

### ⚠️ 주의사항

1. **EXAONE 전용 설정**
   - `trust_remote_code=True` 필수 (커스텀 모델링 코드)
   - `modeling_exaone.py` 필요
   - EXAONE 프롬프트 형식 준수

2. **데이터 불균형**
   - 현재 데이터는 모두 BLOCK (스팸)
   - 정상 샘플 추가 고려 필요
   - 또는 BLOCK 판정만 학습 (MVP)

3. **프롬프트 형식**
   - EXAONE은 특별한 태그 형식 사용
   - `[[system]]`, `[[user]]`, `[[assistant]]`, `[[endofturn]]`
   - 이 형식을 정확히 따라야 함

4. **토크나이저 호환성**
   - EXAONE 전용 토크나이저 사용
   - vocab.json, merges.txt 필요
   - BPE 토크나이저

---

## 📚 참고 자료

- [EXAONE-3.5 GitHub](https://github.com/LG-AI-EXAONE/EXAONE-3.5)
- [QLoRA Paper](https://arxiv.org/abs/2305.14314)
- [DPO Paper](https://arxiv.org/abs/2305.18290)
- [LangGraph Documentation](https://docs.langchain.com/langgraph)
- [TRL (DPO 구현 라이브러리)](https://huggingface.co/docs/trl)

---

---

## 📝 진행 상황 추적

### 완료된 작업

| 작업 | 상태 | 완료일 | 비고 |
|------|------|--------|------|
| 전략 문서 작성 | ✅ | 2024-12-31 | ChatGPT 전략 검증 및 개선 |
| JSON/JSONL 설명 추가 | ✅ | 2024-12-31 | LLM 학습 표준 포맷 설명 |
| DPO 과정 상세화 | ✅ | 2024-12-31 | 구현 코드 및 흐름 다이어그램 |
| CSV → JSONL 변환 모듈 | ✅ | 2024-12-31 | `app/services/spam_agent/extract_jsonl.py` |
| JSONL 파일 생성 | ✅ | 2024-12-31 | 95,133개 샘플 변환 완료 |
| JSONL → SFT 변환 모듈 | ✅ | 2024-12-31 | `app/services/spam_agent/extract_dpo.py` |
| SFT 파일 생성 | ✅ | 2024-12-31 | 24,571개 샘플 (중복 제거 후) |

### 진행 중 작업

| 작업 | 상태 | 예상 완료일 | 비고 |
|------|------|------------|------|
| 데이터셋 분할 | 🔄 | - | Train/Val/Test 분할 |
| 정상 샘플 추가 | 🔄 | - | 옵션 선택 필요 |
| 학습 노드 구현 | ⏳ | - | LangGraph 노드 |
| LangGraph 그래프 생성 | ⏳ | - | 학습 루프 오케스트레이션 |
| DPO 파이프라인 구현 | ⏳ | - | TRL 라이브러리 활용 |

### 발견된 이슈 및 해결

| 이슈 | 상태 | 해결 방법 | 날짜 |
|------|------|----------|------|
| Windows 콘솔 이모지 인코딩 오류 | ✅ 해결 | 이모지 제거, 텍스트로 대체 | 2024-12-31 |
| 파일명 인코딩 문제 | ✅ 해결 | Path 객체 사용, str 변환 | 2024-12-31 |

---

**작성일**: 2024-12-31
**마지막 업데이트**: 2025-01-01
**버전**: 1.5
**검증 상태**: ChatGPT 전략 검증 완료, 개선 사항 반영, 데이터 변환 파이프라인 완료, ETL 기반 SFT 학습 과정 문서화 완료, 요약 내용과의 일치도 검증 완료 (100%), 파일명 변경 반영 완료 (extract_jsonl.py, extract_dpo.py, transform_jsonl.py)
