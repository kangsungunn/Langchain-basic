# 🌟 Star Topology 하이브리드 아키텍처 설계

## 📋 개요

**작성일**: 2025-01-16
**버전**: 1.0
**선택**: 하이브리드 게이트웨이 (규칙 우선 + ML 보조)

**핵심 결정**:
- ✅ 게이트웨이: 규칙 기반 우선 (70-90%) + KoELECTRA 보조 (10-30%)
- ✅ 허브: EXAONE Hub Router (중앙 집중식 브랜치 관리)
- ✅ 브랜치: EXAONE 베이스 + 특화 LoRA 어댑터
- ✅ DB: PostgreSQL (벡터 스토어 + 관계형 데이터)
- ✅ 워크플로우: LangGraph 기반

**목표**:
- 비용 최적화: 70-90% 요청은 규칙만으로 처리
- 지연 최소화: 대부분 1-5ms, 모호한 경우만 50ms
- 정책 일관성: 명시적 규칙 + 온톨로지 관리
- 확장성: 브랜치 추가 시 규칙만 추가
- 운영성: 디버깅/모니터링 용이

---

## 🏗️ 전체 시스템 아키텍처

### 시스템 구조도

```
┌─────────────────────────────────────────────────────────────────┐
│              Star Topology 하이브리드 아키텍처                    │
└─────────────────────────────────────────────────────────────────┘

[사용자 입력 (화면)]
    ↓
┌──────────────────────────────────────────────────────────────────┐
│  Layer 1: 하이브리드 게이트웨이 (Hybrid Gateway)                  │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 1단계: 규칙 기반 필터 (Rule Engine) ~1ms                │    │
│  │  ├─> 입력 검증 (길이, 형식, 인코딩)                     │    │
│  │  ├─> 안전장치 (인젝션 감지, Rate Limit)                 │    │
│  │  ├─> 명시적 정책 (금칙어, 허용어, 필수 조건)            │    │
│  │  └─> 출력: {route, confidence, matched_rules}          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                   ↓                                              │
│            [confidence?]                                         │
│         ↙             ↘                                          │
│  [high: 70-90%]   [low: 10-30%]                                 │
│         ↓                ↓                                       │
│    즉시 라우팅    ┌─────────────────────────────────────┐        │
│                  │ 2단계: ML 보조 (KoELECTRA) ~50ms    │        │
│                  │  ├─> 모호한 입력 해석               │        │
│                  │  ├─> 컨텍스트 기반 분류             │        │
│                  │  └─> 출력: {route, confidence}      │        │
│                  └─────────────────────────────────────┘        │
└──────────────────────────────────────────────────────────────────┘
    ↓
    출력: {target_branch, confidence, reason, method}
    ↓
┌──────────────────────────────────────────────────────────────────┐
│  Layer 2: EXAONE Hub Router (중앙 허브)                          │
│                                                                  │
│  역할:                                                           │
│  ├─> 온톨로지 관리 (태스크 타입, 라벨 체계)                      │
│  ├─> 브랜치 레지스트리 관리 (활성/비활성, 우선순위)               │
│  ├─> 브랜치 헬스 체크 (모델 로드 상태, 응답 시간)                 │
│  ├─> 라우팅 정책 집행 (브랜치 선택 로직)                         │
│  └─> 로드 밸런싱 (동일 브랜치 복수 인스턴스)                      │
│                                                                  │
│  브랜치 레지스트리:                                               │
│  {                                                               │
│    "spam_agent": {                                              │
│      "adapter_path": "./checkpoints/exaone-spam-v2/...",       │
│      "status": "active",                                        │
│      "priority": 1,                                             │
│      "health": "healthy"                                        │
│    },                                                           │
│    "refund_agent": {...},  # 향후 추가                          │
│    "sentiment_agent": {...}  # 향후 추가                        │
│  }                                                              │
└──────────────────────────────────────────────────────────────────┘
    ↓
    브랜치 선택: spam_agent
    ↓
┌──────────────────────────────────────────────────────────────────┐
│  Layer 3: 브랜치 (Specialized Agents)                            │
│                                                                  │
│  ┌────────────────────┐  ┌────────────────────┐                │
│  │  Branch 1          │  │  Branch 2          │  ...           │
│  │  스팸 에이전트      │  │  환불 에이전트     │                │
│  │                    │  │  (향후 추가)       │                │
│  │  [EXAONE 베이스]   │  │  [EXAONE 베이스]   │                │
│  │        +           │  │        +           │                │
│  │  [스팸 LoRA 어댑터] │  │  [환불 LoRA 어댑터]│                │
│  │        +           │  │        +           │                │
│  │  [스팸 분석 로직]   │  │  [환불 처리 로직]  │                │
│  │        ↓           │  │        ↓           │                │
│  │  결과 반환만!      │  │  결과 반환만!      │                │
│  │  (DB 접근 금지)    │  │  (DB 접근 금지)    │                │
│  └────────────────────┘  └────────────────────┘                │
└──────────────────────────────────────────────────────────────────┘
    ↓
    브랜치 결과: {analysis, action, evidence, ...} → Star로 반환
    ↓
┌──────────────────────────────────────────────────────────────────┐
│  Layer 4: DB Layer (PostgreSQL + PGVector)                       │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 관계형 데이터 (Relational)                               │   │
│  │  ├─> input_history (입력 이력)                          │   │
│  │  ├─> branch_results (브랜치 결과)                       │   │
│  │  ├─> feedback (사용자 피드백)                           │   │
│  │  ├─> adapter_registry (어댑터 레지스트리)               │   │
│  │  └─> routing_logs (라우팅 로그)                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 벡터 데이터 (PGVector)                                   │   │
│  │  ├─> text_embeddings (텍스트 임베딩)                    │   │
│  │  ├─> similar_cases (유사 케이스 검색)                   │   │
│  │  └─> ontology_vectors (온톨로지 벡터)                   │   │
│  └─────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
    ↓
    DB 저장 완료: {input_id, result_id, ...}
    ↓
┌──────────────────────────────────────────────────────────────────┐
│  Layer 5: Response Aggregator (응답 통합)                        │
│                                                                  │
│  역할:                                                           │
│  ├─> 브랜치 결과 통합                                            │
│  ├─> 응답 포맷 표준화                                            │
│  ├─> 메타데이터 추가 (실행 시간, 버전, 추적 ID)                   │
│  └─> 사용자 친화적 메시지 생성                                   │
└──────────────────────────────────────────────────────────────────┘
    ↓
[사용자 응답 (화면)]
    {
        "status": "success",
        "data": {...},
        "metadata": {
            "trace_id": "...",
            "execution_time": {...},
            "gateway_method": "rule_based" | "ml_assisted",
            "branch_used": "spam_agent"
        }
    }
```

---

## 🎯 Layer 1: 하이브리드 게이트웨이 설계

### 게이트웨이 구조

```
입력 → 규칙 필터 → [확실] 즉시 라우팅 (70-90%)
                 → [모호] ML 보조 (10-30%) → 라우팅
```

### 1단계: 규칙 기반 필터 (Rule Engine)

#### 규칙 계층 구조

```
Level 1: 안전장치 규칙 (Security Rules)
  ├─> 입력 검증 (길이, 형식, 인코딩)
  ├─> 인젝션 감지 (프롬프트 인젝션, SQL 인젝션)
  ├─> Rate Limiting (사용자별, IP별)
  └─> 우선순위: 최상 (즉시 차단)

Level 2: 명시적 정책 규칙 (Policy Rules)
  ├─> 금칙어 규칙 (스팸, 욕설, 민감 정보)
  ├─> 허용어 규칙 (화이트리스트)
  ├─> 필수 조건 규칙 (특정 필드 존재 여부)
  └─> 우선순위: 높음 (정책 집행)

Level 3: 브랜치 라우팅 규칙 (Routing Rules)
  ├─> 키워드 기반 라우팅
  ├─> 패턴 기반 라우팅 (정규식)
  ├─> 컨텍스트 기반 라우팅 (메타데이터)
  └─> 우선순위: 중간 (브랜치 선택)

Level 4: 휴리스틱 규칙 (Heuristic Rules)
  ├─> 통계 기반 규칙 (빈도, 길이, 비율)
  ├─> 시간 기반 규칙 (업무 시간, 계절성)
  └─> 우선순위: 낮음 (힌트 제공)
```

#### 규칙 정의 예시

```python
# security_rules.py
class SecurityRules:
    """안전장치 규칙"""

    @staticmethod
    def check_input_validation(text: str) -> RuleResult:
        """입력 검증"""
        # 길이 체크
        if len(text) == 0:
            return RuleResult(
                decision="reject",
                confidence="high",
                reason="입력 비어있음",
                rule_name="empty_input"
            )

        if len(text) > 10000:
            return RuleResult(
                decision="reject",
                confidence="high",
                reason="입력 길이 초과 (max: 10000)",
                rule_name="max_length_exceeded"
            )

        # 인코딩 체크
        try:
            text.encode('utf-8')
        except UnicodeEncodeError:
            return RuleResult(
                decision="reject",
                confidence="high",
                reason="잘못된 인코딩",
                rule_name="invalid_encoding"
            )

        return RuleResult(decision="continue", confidence="high")

    @staticmethod
    def check_injection_patterns(text: str) -> RuleResult:
        """인젝션 패턴 감지"""
        injection_patterns = [
            r"ignore\s+previous\s+instructions",
            r"<script",
            r"javascript:",
            r"SELECT\s+\*\s+FROM",
            r"DROP\s+TABLE"
        ]

        import re
        for pattern in injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return RuleResult(
                    decision="reject",
                    confidence="high",
                    reason=f"인젝션 패턴 감지: {pattern}",
                    rule_name="injection_detected"
                )

        return RuleResult(decision="continue", confidence="high")

    @staticmethod
    def check_rate_limit(user_id: str, request_count: int) -> RuleResult:
        """Rate Limiting"""
        MAX_REQUESTS_PER_MINUTE = 60

        if request_count > MAX_REQUESTS_PER_MINUTE:
            return RuleResult(
                decision="reject",
                confidence="high",
                reason=f"요청 한도 초과 ({request_count}/{MAX_REQUESTS_PER_MINUTE})",
                rule_name="rate_limit_exceeded"
            )

        return RuleResult(decision="continue", confidence="high")


# policy_rules.py
class PolicyRules:
    """명시적 정책 규칙"""

    # 금칙어 정의 (온톨로지 관리)
    SPAM_KEYWORDS = [
        "긴급송금", "계좌번호", "당첨", "무료", "클릭",
        "대출", "현금", "즉시", "확인요망", "비밀번호"
    ]

    REFUND_KEYWORDS = [
        "환불", "취소", "반품", "교환", "불량"
    ]

    SENTIMENT_KEYWORDS = [
        "최고", "최악", "만족", "불만", "화남", "기쁨"
    ]

    @staticmethod
    def check_spam_policy(text: str) -> RuleResult:
        """스팸 정책 체크"""
        matched_keywords = [
            kw for kw in PolicyRules.SPAM_KEYWORDS
            if kw in text
        ]

        # 2개 이상 금칙어 → 확실히 스팸
        if len(matched_keywords) >= 2:
            return RuleResult(
                decision="route_to_spam",
                confidence="high",
                reason=f"금칙어 {len(matched_keywords)}개 감지: {matched_keywords}",
                rule_name="spam_keywords_multi",
                metadata={"matched": matched_keywords}
            )

        # 1개 금칙어 → 의심
        if len(matched_keywords) == 1:
            return RuleResult(
                decision="route_to_spam",
                confidence="medium",
                reason=f"금칙어 1개 감지: {matched_keywords[0]}",
                rule_name="spam_keyword_single",
                metadata={"matched": matched_keywords}
            )

        return RuleResult(decision="continue", confidence="low")

    @staticmethod
    def check_refund_policy(text: str) -> RuleResult:
        """환불 정책 체크"""
        matched_keywords = [
            kw for kw in PolicyRules.REFUND_KEYWORDS
            if kw in text
        ]

        if matched_keywords:
            return RuleResult(
                decision="route_to_refund",
                confidence="high",
                reason=f"환불 키워드 감지: {matched_keywords}",
                rule_name="refund_keywords",
                metadata={"matched": matched_keywords}
            )

        return RuleResult(decision="continue", confidence="low")

    @staticmethod
    def check_sentiment_policy(text: str) -> RuleResult:
        """감성 정책 체크"""
        matched_keywords = [
            kw for kw in PolicyRules.SENTIMENT_KEYWORDS
            if kw in text
        ]

        if len(matched_keywords) >= 2:
            return RuleResult(
                decision="route_to_sentiment",
                confidence="high",
                reason=f"감성 키워드 감지: {matched_keywords}",
                rule_name="sentiment_keywords",
                metadata={"matched": matched_keywords}
            )

        return RuleResult(decision="continue", confidence="low")


# routing_rules.py
class RoutingRules:
    """브랜치 라우팅 규칙"""

    @staticmethod
    def route_by_keywords(text: str) -> RuleResult:
        """키워드 기반 라우팅"""

        # 각 정책 규칙 실행
        spam_result = PolicyRules.check_spam_policy(text)
        if spam_result.confidence == "high":
            return spam_result

        refund_result = PolicyRules.check_refund_policy(text)
        if refund_result.confidence == "high":
            return refund_result

        sentiment_result = PolicyRules.check_sentiment_policy(text)
        if sentiment_result.confidence == "high":
            return sentiment_result

        # 어떤 규칙에도 해당 없음 → ML에 위임
        return RuleResult(
            decision="ml_assist_required",
            confidence="low",
            reason="규칙으로 판단 불가, ML 보조 필요"
        )
```

#### 규칙 엔진 코어

```python
# rule_engine.py
class RuleEngine:
    """규칙 엔진 코어"""

    def __init__(self):
        self.security_rules = SecurityRules()
        self.policy_rules = PolicyRules()
        self.routing_rules = RoutingRules()

    def evaluate(self, text: str, context: dict = None) -> GatewayResult:
        """
        규칙 평가 (계층적 실행)

        Returns:
            GatewayResult with route, confidence, reason, matched_rules
        """
        matched_rules = []

        # Level 1: 안전장치 (최우선)
        validation_result = self.security_rules.check_input_validation(text)
        matched_rules.append(validation_result.rule_name)

        if validation_result.decision == "reject":
            return GatewayResult(
                route="reject",
                confidence=1.0,
                reason=validation_result.reason,
                method="rule_based",
                matched_rules=matched_rules,
                latency_ms=0.5
            )

        injection_result = self.security_rules.check_injection_patterns(text)
        matched_rules.append(injection_result.rule_name)

        if injection_result.decision == "reject":
            return GatewayResult(
                route="reject",
                confidence=1.0,
                reason=injection_result.reason,
                method="rule_based",
                matched_rules=matched_rules,
                latency_ms=0.5
            )

        # Rate Limiting (context에서 user_id 필요)
        if context and "user_id" in context:
            rate_result = self.security_rules.check_rate_limit(
                context["user_id"],
                context.get("request_count", 0)
            )
            matched_rules.append(rate_result.rule_name)

            if rate_result.decision == "reject":
                return GatewayResult(
                    route="reject",
                    confidence=1.0,
                    reason=rate_result.reason,
                    method="rule_based",
                    matched_rules=matched_rules,
                    latency_ms=0.5
                )

        # Level 2-3: 라우팅 규칙
        routing_result = self.routing_rules.route_by_keywords(text)
        matched_rules.append(routing_result.rule_name)

        # 확실한 라우팅 (confidence == "high")
        if routing_result.confidence == "high":
            return GatewayResult(
                route=routing_result.decision.replace("route_to_", "") + "_agent",
                confidence=1.0,
                reason=routing_result.reason,
                method="rule_based",
                matched_rules=matched_rules,
                metadata=routing_result.metadata,
                latency_ms=1.0
            )

        # 모호함 → ML 보조 필요
        return GatewayResult(
            route="ml_assist_required",
            confidence=0.0,
            reason="규칙으로 판단 불가, ML 보조 필요",
            method="rule_based_uncertain",
            matched_rules=matched_rules,
            latency_ms=1.0
        )
```

### 2단계: ML 보조 게이트웨이 (KoELECTRA)

```python
# ml_assistant.py
class MLAssistant:
    """ML 보조 게이트웨이 (KoELECTRA)"""

    def __init__(self):
        self.model = None
        self.tokenizer = None

    def load_model(self, model_path: str = None):
        """KoELECTRA 모델 로드 (캐싱)"""
        if self.model is None:
            from app.services.spam_classifier.inference import load_trained_model
            self.model, self.tokenizer = load_trained_model(model_path)

    def classify(self, text: str) -> GatewayResult:
        """
        모호한 입력 분류

        Note: 규칙으로 확정 못한 10-30%만 여기 도달
        """
        from app.services.spam_classifier.inference import predict_spam

        # KoELECTRA 추론
        result = predict_spam(text, self.model, self.tokenizer)

        # 스팸 확률 기반 라우팅
        if result["spam_prob"] > 0.7:
            route = "spam_agent"
            confidence = result["spam_prob"]
        elif result["spam_prob"] < 0.3:
            route = "default_agent"  # 정상
            confidence = 1 - result["spam_prob"]
        else:
            # 여전히 모호함 (0.3 ~ 0.7)
            route = "spam_agent"  # 보수적 판단
            confidence = 0.5

        return GatewayResult(
            route=route,
            confidence=confidence,
            reason=f"ML 보조: spam_prob={result['spam_prob']:.2f}, confidence={result['confidence']}",
            method="ml_assisted",
            matched_rules=[],
            metadata=result,
            latency_ms=50.0
        )
```

### 하이브리드 게이트웨이 통합

```python
# hybrid_gateway.py
class HybridGateway:
    """하이브리드 게이트웨이: 규칙 우선 + ML 보조"""

    def __init__(self):
        self.rule_engine = RuleEngine()
        self.ml_assistant = MLAssistant()
        self.ml_assistant.load_model()  # 사전 로드

        # 통계 수집
        self.stats = {
            "total_requests": 0,
            "rule_based": 0,
            "ml_assisted": 0,
            "rule_based_ratio": 0.0
        }

    def route(self, text: str, context: dict = None) -> GatewayResult:
        """
        라우팅 결정

        1단계: 규칙 엔진 (빠른 경로)
        2단계: ML 보조 (모호한 경우만)
        """
        import time

        self.stats["total_requests"] += 1

        # 1단계: 규칙 기반 필터
        start_time = time.time()
        rule_result = self.rule_engine.evaluate(text, context)
        rule_time = (time.time() - start_time) * 1000

        # 규칙으로 확정 (confidence > 0)
        if rule_result.route != "ml_assist_required":
            self.stats["rule_based"] += 1
            self.stats["rule_based_ratio"] = self.stats["rule_based"] / self.stats["total_requests"]

            return GatewayResult(
                route=rule_result.route,
                confidence=rule_result.confidence,
                reason=rule_result.reason,
                method="rule_based",
                matched_rules=rule_result.matched_rules,
                metadata=rule_result.metadata,
                latency_ms=rule_time
            )

        # 2단계: ML 보조 (모호한 경우만)
        start_time = time.time()
        ml_result = self.ml_assistant.classify(text)
        ml_time = (time.time() - start_time) * 1000

        self.stats["ml_assisted"] += 1
        self.stats["rule_based_ratio"] = self.stats["rule_based"] / self.stats["total_requests"]

        return GatewayResult(
            route=ml_result.route,
            confidence=ml_result.confidence,
            reason=f"규칙 판단 불가 → {ml_result.reason}",
            method="ml_assisted",
            matched_rules=rule_result.matched_rules,
            metadata=ml_result.metadata,
            latency_ms=rule_time + ml_time
        )

    def get_stats(self) -> dict:
        """게이트웨이 통계 조회"""
        return self.stats
```

---

## 🎯 Layer 2: EXAONE Hub Router 설계

### Hub Router 역할

```
1. 온톨로지 관리
   ├─> 태스크 타입 정의 (spam, refund, sentiment, ...)
   ├─> 라벨 체계 관리
   └─> 정책 버전 관리

2. 브랜치 레지스트리 관리
   ├─> 브랜치 등록/해제
   ├─> 브랜치 활성화/비활성화
   ├─> 브랜치 우선순위 관리
   └─> 브랜치 메타데이터 관리

3. 브랜치 헬스 체크
   ├─> 모델 로드 상태 확인
   ├─> 응답 시간 모니터링
   ├─> 에러율 추적
   └─> 자동 페일오버

4. 라우팅 정책 집행
   ├─> 게이트웨이 결과 기반 브랜치 선택
   ├─> 폴백 브랜치 선택
   └─> 로드 밸런싱 (동일 브랜치 복수 인스턴스)

5. 로깅 및 추적
   ├─> 라우팅 결정 로그
   ├─> 성능 메트릭 수집
   └─> 분산 추적 (Trace ID)
```

### 브랜치 레지스트리 구조

```python
# branch_registry.py
class BranchRegistry:
    """브랜치 레지스트리"""

    def __init__(self):
        self.branches = {}
        self.load_from_db()  # DB에서 로드

    def register(self, branch_config: BranchConfig):
        """브랜치 등록"""
        self.branches[branch_config.name] = {
            "config": branch_config,
            "status": "active",
            "health": "unknown",
            "last_check": None,
            "metrics": {
                "total_requests": 0,
                "avg_latency_ms": 0.0,
                "error_rate": 0.0
            }
        }

    def get_branch(self, branch_name: str) -> dict:
        """브랜치 조회"""
        return self.branches.get(branch_name)

    def get_active_branches(self) -> list:
        """활성 브랜치 목록"""
        return [
            name for name, info in self.branches.items()
            if info["status"] == "active"
        ]

    def update_health(self, branch_name: str, health: str):
        """헬스 상태 업데이트"""
        if branch_name in self.branches:
            self.branches[branch_name]["health"] = health
            self.branches[branch_name]["last_check"] = time.time()


# Branch Config 예시
@dataclass
class BranchConfig:
    """브랜치 설정"""
    name: str
    adapter_path: str
    base_model_path: str
    status: str  # "active", "inactive", "training"
    priority: int
    description: str
    tags: List[str]

    # 성능 설정
    max_concurrent_requests: int = 10
    timeout_seconds: int = 30

    # 폴백 설정
    fallback_branch: Optional[str] = None


# 브랜치 등록 예시
spam_branch = BranchConfig(
    name="spam_agent",
    adapter_path="./checkpoints/exaone-spam-filter-v2/checkpoint-3000",
    base_model_path="app/models/original/exaone-2.4b",
    status="active",
    priority=1,
    description="스팸 이메일 분석 에이전트",
    tags=["spam", "email", "security"],
    max_concurrent_requests=10,
    timeout_seconds=30,
    fallback_branch="default_agent"
)
```

### Hub Router 코어

```python
# hub_router.py
class HubRouter:
    """EXAONE Hub Router"""

    def __init__(self):
        self.registry = BranchRegistry()
        self.health_checker = BranchHealthChecker(self.registry)
        self.ontology = OntologyManager()

        # 주기적 헬스 체크 시작
        self.health_checker.start()

    def route(self, gateway_result: GatewayResult, text: str) -> RoutingDecision:
        """
        브랜치 라우팅

        Args:
            gateway_result: 게이트웨이 결과
            text: 원본 텍스트

        Returns:
            RoutingDecision: 선택된 브랜치 및 이유
        """
        # 1. 게이트웨이 결과 기반 브랜치 선택
        target_branch = gateway_result.route

        # 2. 브랜치 존재 여부 확인
        branch_info = self.registry.get_branch(target_branch)

        if not branch_info:
            # 브랜치 없음 → 폴백
            target_branch = "default_agent"
            branch_info = self.registry.get_branch(target_branch)

        # 3. 브랜치 헬스 체크
        if branch_info["health"] != "healthy":
            # 브랜치 unhealthy → 폴백
            fallback = branch_info["config"].fallback_branch
            if fallback:
                target_branch = fallback
                branch_info = self.registry.get_branch(target_branch)

        # 4. 라우팅 결정
        return RoutingDecision(
            branch_name=target_branch,
            branch_config=branch_info["config"],
            reason=f"게이트웨이 결과: {gateway_result.reason}",
            gateway_result=gateway_result,
            ontology_version=self.ontology.get_version()
        )

    def get_branch_stats(self) -> dict:
        """브랜치 통계 조회"""
        return {
            name: info["metrics"]
            for name, info in self.registry.branches.items()
        }


# health_checker.py
class BranchHealthChecker:
    """브랜치 헬스 체커"""

    def __init__(self, registry: BranchRegistry):
        self.registry = registry
        self.check_interval = 30  # 30초마다 체크

    def start(self):
        """헬스 체크 시작 (백그라운드 스레드)"""
        import threading
        thread = threading.Thread(target=self._check_loop, daemon=True)
        thread.start()

    def _check_loop(self):
        """헬스 체크 루프"""
        while True:
            self.check_all_branches()
            time.sleep(self.check_interval)

    def check_all_branches(self):
        """모든 브랜치 헬스 체크"""
        for branch_name in self.registry.get_active_branches():
            health = self.check_branch(branch_name)
            self.registry.update_health(branch_name, health)

    def check_branch(self, branch_name: str) -> str:
        """개별 브랜치 헬스 체크"""
        try:
            branch_info = self.registry.get_branch(branch_name)
            config = branch_info["config"]

            # 1. 어댑터 파일 존재 확인
            if not os.path.exists(config.adapter_path):
                return "unhealthy_file_missing"

            # 2. 모델 로드 테스트 (가벼운 체크)
            # TODO: 실제 모델 로드 없이 체크하는 방법

            # 3. 에러율 확인
            if branch_info["metrics"]["error_rate"] > 0.1:  # 10% 이상
                return "unhealthy_high_error_rate"

            return "healthy"

        except Exception as e:
            return f"unhealthy_error_{str(e)}"
```

### 온톨로지 관리

```python
# ontology_manager.py
class OntologyManager:
    """온톨로지 관리자"""

    def __init__(self):
        self.version = "1.0.0"
        self.task_types = {}
        self.label_schema = {}
        self.load_ontology()

    def load_ontology(self):
        """온톨로지 로드 (DB 또는 파일에서)"""
        self.task_types = {
            "spam": {
                "description": "스팸 이메일 분류",
                "branch": "spam_agent",
                "labels": ["spam", "ham"],
                "keywords": ["긴급송금", "계좌번호", "당첨"],
                "priority": 1
            },
            "refund": {
                "description": "환불 요청 처리",
                "branch": "refund_agent",
                "labels": ["refund_request", "exchange_request", "normal"],
                "keywords": ["환불", "취소", "반품"],
                "priority": 2
            },
            "sentiment": {
                "description": "감성 분석",
                "branch": "sentiment_agent",
                "labels": ["positive", "negative", "neutral"],
                "keywords": ["최고", "최악", "만족"],
                "priority": 3
            }
        }

    def get_version(self) -> str:
        """온톨로지 버전"""
        return self.version

    def get_task_type(self, task_name: str) -> dict:
        """태스크 타입 조회"""
        return self.task_types.get(task_name)

    def update_task_type(self, task_name: str, config: dict):
        """태스크 타입 업데이트"""
        self.task_types[task_name] = config
        self.version = self._increment_version(self.version)
        # DB에 저장

    def _increment_version(self, version: str) -> str:
        """버전 증가"""
        major, minor, patch = map(int, version.split('.'))
        return f"{major}.{minor}.{patch + 1}"
```

---

## 🎯 Layer 3: 브랜치 (Specialized Agents) 설계

### ⚠️ 중요: Star Topology 원칙

```
✅ 브랜치 = 순수 작업 수행자 (DB 접근 금지!)
   ├─> 명령 수신 (Star로부터)
   ├─> 분석/처리 수행
   ├─> 결과 반환 (Star로)
   └─> DB 접근 금지! (Star만 DB 접근)

✅ Star (Hub Router) = 중앙 통제 센터
   ├─> 브랜치에 명령
   ├─> 브랜치 결과 수신
   ├─> 최종 액션 결정
   └─> DB 저장 수행
```

### 브랜치 인터페이스 (표준화)

```python
# branch_base.py
from abc import ABC, abstractmethod

class BranchAgent(ABC):
    """
    브랜치 에이전트 기본 인터페이스

    ⚠️ 핵심 원칙:
    - 브랜치는 순수하게 "분석/처리" 기능만 수행
    - DB 접근 금지 (Star만 DB 접근)
    - 결과는 BranchResult로만 반환
    """

    def __init__(self, config: BranchConfig):
        self.config = config
        self.model = None
        self.tokenizer = None

    @abstractmethod
    def load_model(self):
        """모델 로드 (EXAONE + 어댑터)"""
        pass

    @abstractmethod
    def process(self, text: str, context: dict) -> BranchResult:
        """
        브랜치 처리 로직 (순수 함수)

        ⚠️ 중요: 이 메서드는 DB에 접근하지 않음!
        ⚠️ 결과만 반환하고, 저장은 Star가 담당
        """
        pass

    def health_check(self) -> bool:
        """헬스 체크"""
        return self.model is not None


@dataclass
class BranchResult:
    """
    브랜치 결과 (순수 데이터)

    브랜치는 이 결과만 반환하고,
    Star가 이를 받아 DB에 저장
    """
    branch_name: str
    analysis: dict  # 분석 결과
    action: str  # 권장 액션 (Star가 최종 결정)
    evidence: List[str]  # 근거
    confidence: float
    execution_time: float
    metadata: dict
```

### 브랜치 1: 스팸 에이전트 (구현 예시)

```python
# spam_agent.py
class SpamAgent(BranchAgent):
    """
    스팸 이메일 분석 에이전트

    역할: 오직 스팸 분석만 수행
    금지: DB 접근 (읽기/쓰기 모두 금지)
    """

    def load_model(self):
        """EXAONE + 스팸 LoRA 어댑터 로드"""
        from app.services.verdict_agent.exaone_inference import load_exaone_model

        self.model, self.tokenizer = load_exaone_model(
            adapter_path=self.config.adapter_path,
            base_model_path=self.config.base_model_path
        )

    def process(self, text: str, context: dict) -> BranchResult:
        """
        스팸 분석 수행 (순수 함수)

        ⚠️ DB 접근 없음! 오직 분석만 수행
        """
        import time
        start_time = time.time()

        from app.services.verdict_agent.exaone_inference import analyze_with_exaone

        # EXAONE 분석
        analysis = analyze_with_exaone(text, self.model, self.tokenizer)

        # 액션 권장 (Star가 최종 결정)
        recommended_action = self._recommend_action(analysis, context)

        execution_time = time.time() - start_time

        # 결과 반환 (DB 저장 없음!)
        return BranchResult(
            branch_name="spam_agent",
            analysis=analysis,
            action=recommended_action,  # 권장만 할 뿐
            evidence=analysis.get("evidence", []),
            confidence=self._calculate_confidence(analysis),
            execution_time=execution_time,
            metadata={
                "adapter_path": self.config.adapter_path,
                "model_version": "v2-checkpoint-3000"
            }
        )
        # ⚠️ DB 저장 없음! Star가 저장함

    def _recommend_action(self, analysis: dict, context: dict) -> str:
        """
        액션 권장 (최종 결정 아님)

        Star (Hub Router)가 이 권장을 참고하여
        온톨로지/정책과 함께 최종 결정
        """
        evidence_count = len(analysis.get("evidence", []))
        gateway_confidence = context.get("gateway_confidence", 0.5)

        # 권장 로직
        if evidence_count >= 3:
            return "block"  # 권장: 차단
        elif evidence_count >= 1 and gateway_confidence > 0.7:
            return "quarantine"  # 권장: 격리
        elif evidence_count >= 1:
            return "deliver_with_warning"  # 권장: 경고와 함께 전달
        else:
            return "deliver"  # 권장: 정상 전달

    def _calculate_confidence(self, analysis: dict) -> float:
        """신뢰도 계산"""
        evidence_count = len(analysis.get("evidence", []))

        if evidence_count >= 3:
            return 0.9
        elif evidence_count >= 1:
            return 0.7
        else:
            return 0.5
```

### 브랜치 2: 환불 에이전트 (향후 구현)

```python
# refund_agent.py
class RefundAgent(BranchAgent):
    """환불 요청 처리 에이전트"""

    def load_model(self):
        """EXAONE + 환불 LoRA 어댑터 로드"""
        # TODO: 향후 구현
        pass

    def process(self, text: str, context: dict) -> BranchResult:
        """환불 처리 로직"""
        # TODO: 향후 구현
        pass

    # ... 기타 메서드
```

---

## 🎯 Layer 4: DB Layer 설계

### DB 스키마

#### 관계형 테이블

```sql
-- 1. 입력 이력
CREATE TABLE input_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    text TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),

    -- 게이트웨이 결과
    gateway_route VARCHAR(100),
    gateway_confidence FLOAT,
    gateway_method VARCHAR(50),  -- "rule_based" | "ml_assisted"
    gateway_reason TEXT,
    gateway_matched_rules JSONB,
    gateway_latency_ms FLOAT,

    -- 허브 라우팅
    hub_branch VARCHAR(100),
    hub_reason TEXT,
    hub_ontology_version VARCHAR(50),

    -- 인덱스
    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at),
    INDEX idx_gateway_route (gateway_route),
    INDEX idx_hub_branch (hub_branch)
);

-- 2. 브랜치 결과
CREATE TABLE branch_results (
    id SERIAL PRIMARY KEY,
    input_id INTEGER REFERENCES input_history(id),
    branch_name VARCHAR(100) NOT NULL,

    -- 분석 결과
    analysis JSONB,
    action VARCHAR(50),
    evidence JSONB,
    confidence FLOAT,

    -- 성능 메트릭
    execution_time FLOAT,
    model_version VARCHAR(100),
    adapter_path TEXT,

    created_at TIMESTAMP DEFAULT NOW(),

    -- 인덱스
    INDEX idx_input_id (input_id),
    INDEX idx_branch_name (branch_name),
    INDEX idx_action (action),
    INDEX idx_created_at (created_at)
);

-- 3. 사용자 피드백
CREATE TABLE feedback (
    id SERIAL PRIMARY KEY,
    input_id INTEGER REFERENCES input_history(id),

    -- 피드백 내용
    is_correct BOOLEAN,
    user_feedback JSONB,
    correct_label VARCHAR(100),

    created_at TIMESTAMP DEFAULT NOW(),

    -- 인덱스
    INDEX idx_input_id (input_id),
    INDEX idx_is_correct (is_correct)
);

-- 4. 어댑터 레지스트리
CREATE TABLE adapter_registry (
    id SERIAL PRIMARY KEY,
    branch_name VARCHAR(100) UNIQUE NOT NULL,

    -- 어댑터 정보
    adapter_path TEXT,
    base_model VARCHAR(100),
    status VARCHAR(50),  -- "active", "inactive", "training"
    priority INTEGER,

    -- 메타데이터
    description TEXT,
    tags JSONB,
    config JSONB,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- 인덱스
    INDEX idx_branch_name (branch_name),
    INDEX idx_status (status)
);

-- 5. 라우팅 로그
CREATE TABLE routing_logs (
    id SERIAL PRIMARY KEY,
    input_id INTEGER REFERENCES input_history(id),

    -- 라우팅 정보
    gateway_decision VARCHAR(100),
    hub_decision VARCHAR(100),
    final_branch VARCHAR(100),

    -- 추적 정보
    trace_id VARCHAR(255),
    parent_trace_id VARCHAR(255),

    -- 타이밍
    gateway_latency_ms FLOAT,
    hub_latency_ms FLOAT,
    branch_latency_ms FLOAT,
    total_latency_ms FLOAT,

    created_at TIMESTAMP DEFAULT NOW(),

    -- 인덱스
    INDEX idx_trace_id (trace_id),
    INDEX idx_final_branch (final_branch)
);

-- 6. 게이트웨이 통계
CREATE TABLE gateway_stats (
    id SERIAL PRIMARY KEY,

    -- 통계 정보
    total_requests INTEGER DEFAULT 0,
    rule_based_requests INTEGER DEFAULT 0,
    ml_assisted_requests INTEGER DEFAULT 0,
    rule_based_ratio FLOAT,

    -- 시간 윈도우
    window_start TIMESTAMP,
    window_end TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),

    -- 인덱스
    INDEX idx_window_start (window_start)
);
```

#### 벡터 테이블 (PGVector)

```sql
-- 벡터 확장 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. 텍스트 임베딩
CREATE TABLE text_embeddings (
    id SERIAL PRIMARY KEY,
    input_id INTEGER REFERENCES input_history(id),

    -- 임베딩
    embedding vector(384),  -- 임베딩 차원 (모델에 따라 조정)

    -- 메타데이터
    text_hash VARCHAR(64),  -- 중복 체크용
    model_name VARCHAR(100),

    created_at TIMESTAMP DEFAULT NOW(),

    -- 인덱스 (벡터 유사도 검색)
    INDEX idx_embedding_ivfflat ON text_embeddings
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
);

-- 2. 유사 케이스 (재학습 데이터)
CREATE TABLE similar_cases (
    id SERIAL PRIMARY KEY,
    input_id INTEGER REFERENCES input_history(id),

    -- 유사 케이스
    similar_input_id INTEGER REFERENCES input_history(id),
    similarity_score FLOAT,

    created_at TIMESTAMP DEFAULT NOW(),

    -- 인덱스
    INDEX idx_input_id (input_id),
    INDEX idx_similarity_score (similarity_score DESC)
);

-- 3. 온톨로지 벡터 (태스크 타입 임베딩)
CREATE TABLE ontology_vectors (
    id SERIAL PRIMARY KEY,

    -- 온톨로지 정보
    task_type VARCHAR(100) NOT NULL,
    label VARCHAR(100),

    -- 임베딩
    embedding vector(384),

    -- 메타데이터
    description TEXT,
    keywords JSONB,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- 인덱스
    INDEX idx_task_type (task_type),
    INDEX idx_ontology_embedding_ivfflat ON ontology_vectors
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
);
```

### CRUD 연산

```python
# crud.py
from sqlalchemy.orm import Session
from app.services.db.models import InputHistory, BranchResult, Feedback

class StarTopologyCRUD:
    """Star Topology DB CRUD"""

    @staticmethod
    def save_input_history(
        db: Session,
        text: str,
        session_id: str,
        gateway_result: GatewayResult,
        routing_decision: RoutingDecision
    ) -> InputHistory:
        """입력 이력 저장"""
        input_record = InputHistory(
            session_id=session_id,
            text=text,
            gateway_route=gateway_result.route,
            gateway_confidence=gateway_result.confidence,
            gateway_method=gateway_result.method,
            gateway_reason=gateway_result.reason,
            gateway_matched_rules=gateway_result.matched_rules,
            gateway_latency_ms=gateway_result.latency_ms,
            hub_branch=routing_decision.branch_name,
            hub_reason=routing_decision.reason,
            hub_ontology_version=routing_decision.ontology_version
        )

        db.add(input_record)
        db.commit()
        db.refresh(input_record)

        return input_record

    @staticmethod
    def save_branch_result(
        db: Session,
        input_id: int,
        branch_result: BranchResult
    ) -> BranchResult:
        """브랜치 결과 저장"""
        result_record = BranchResult(
            input_id=input_id,
            branch_name=branch_result.branch_name,
            analysis=branch_result.analysis,
            action=branch_result.action,
            evidence=branch_result.evidence,
            confidence=branch_result.confidence,
            execution_time=branch_result.execution_time,
            model_version=branch_result.metadata.get("model_version"),
            adapter_path=branch_result.metadata.get("adapter_path")
        )

        db.add(result_record)
        db.commit()
        db.refresh(result_record)

        return result_record

    @staticmethod
    def query_similar_cases(
        db: Session,
        embedding: List[float],
        limit: int = 5
    ) -> List[dict]:
        """유사 케이스 검색 (벡터 검색)"""
        from sqlalchemy import text

        # PGVector 유사도 검색
        query = text("""
            SELECT
                ih.id,
                ih.text,
                ih.gateway_route,
                br.action,
                te.embedding <=> :query_embedding AS distance
            FROM input_history ih
            JOIN text_embeddings te ON ih.id = te.input_id
            JOIN branch_results br ON ih.id = br.input_id
            ORDER BY distance
            LIMIT :limit
        """)

        results = db.execute(
            query,
            {"query_embedding": embedding, "limit": limit}
        ).fetchall()

        return [
            {
                "id": r.id,
                "text": r.text,
                "gateway_route": r.gateway_route,
                "action": r.action,
                "similarity": 1 - r.distance  # distance를 similarity로 변환
            }
            for r in results
        ]

    @staticmethod
    def get_gateway_stats(
        db: Session,
        window_hours: int = 24
    ) -> dict:
        """게이트웨이 통계 조회"""
        from sqlalchemy import func, and_
        from datetime import datetime, timedelta

        window_start = datetime.now() - timedelta(hours=window_hours)

        stats = db.query(
            func.count(InputHistory.id).label("total"),
            func.sum(
                func.cast(InputHistory.gateway_method == "rule_based", Integer)
            ).label("rule_based"),
            func.sum(
                func.cast(InputHistory.gateway_method == "ml_assisted", Integer)
            ).label("ml_assisted")
        ).filter(
            InputHistory.created_at >= window_start
        ).first()

        total = stats.total or 0
        rule_based = stats.rule_based or 0
        ml_assisted = stats.ml_assisted or 0

        return {
            "total_requests": total,
            "rule_based_requests": rule_based,
            "ml_assisted_requests": ml_assisted,
            "rule_based_ratio": rule_based / total if total > 0 else 0.0
        }
```

---

## 🎯 Layer 5: Response Aggregator 설계

```python
# response_aggregator.py
class ResponseAggregator:
    """응답 통합기"""

    @staticmethod
    def aggregate(
        gateway_result: GatewayResult,
        routing_decision: RoutingDecision,
        branch_result: BranchResult,
        db_saved: bool,
        trace_id: str
    ) -> dict:
        """
        응답 통합

        Returns:
            표준화된 응답 형식
        """
        return {
            "status": "success",
            "data": {
                "final_action": branch_result.action,
                "reason": branch_result.analysis.get("risk_summary", ""),
                "user_explanation": branch_result.analysis.get("user_explanation", ""),
                "evidence": branch_result.evidence,
                "confidence": branch_result.confidence,

                # 상세 정보
                "details": {
                    "gateway": {
                        "route": gateway_result.route,
                        "confidence": gateway_result.confidence,
                        "method": gateway_result.method,
                        "reason": gateway_result.reason,
                        "matched_rules": gateway_result.matched_rules
                    },
                    "hub": {
                        "branch": routing_decision.branch_name,
                        "reason": routing_decision.reason,
                        "ontology_version": routing_decision.ontology_version
                    },
                    "branch": {
                        "name": branch_result.branch_name,
                        "analysis": branch_result.analysis
                    }
                }
            },
            "metadata": {
                "trace_id": trace_id,
                "execution_time": {
                    "gateway_ms": gateway_result.latency_ms,
                    "hub_ms": 1.0,  # Hub는 빠름
                    "branch_ms": branch_result.execution_time * 1000,
                    "total_ms": (
                        gateway_result.latency_ms +
                        1.0 +
                        branch_result.execution_time * 1000
                    )
                },
                "gateway_method": gateway_result.method,
                "branch_used": branch_result.branch_name,
                "db_saved": db_saved,
                "model_version": branch_result.metadata.get("model_version"),
                "timestamp": time.time()
            }
        }
```

---

## 🔄 LangGraph 워크플로우 재구성

### Star Topology State

```python
# star_state.py
class StarTopologyState(TypedDict):
    """Star Topology 상태"""

    # 입력
    text: str
    session_id: str
    context: dict

    # 게이트웨이 결과
    gateway_result: Optional[GatewayResult]

    # 허브 라우팅
    routing_decision: Optional[RoutingDecision]

    # 브랜치 결과
    branch_result: Optional[BranchResult]

    # DB
    input_id: Optional[int]
    db_saved: bool

    # 메타데이터
    trace_id: str
    current_step: str
    error_message: Optional[str]

    # 최종 응답
    final_response: Optional[dict]
```

### LangGraph 노드 정의

```python
# star_nodes.py

def gateway_node(state: StarTopologyState) -> Dict[str, Any]:
    """게이트웨이 노드: 규칙 기반 + ML 보조"""

    text = state["text"]
    context = state.get("context", {})

    # 하이브리드 게이트웨이 실행
    gateway = HybridGateway()
    result = gateway.route(text, context)

    return {
        "gateway_result": result,
        "current_step": "gateway"
    }


def hub_router_node(state: StarTopologyState) -> Dict[str, Any]:
    """
    허브 라우터 노드: 브랜치 선택 및 제어

    역할:
    1. 게이트웨이 결과 기반 브랜치 선택
    2. 브랜치에 명령 전달
    3. 브랜치 결과 수신
    """

    gateway_result = state["gateway_result"]
    text = state["text"]

    # Hub Router 실행
    hub = HubRouter()
    routing = hub.route(gateway_result, text)

    return {
        "routing_decision": routing,
        "current_step": "hub_router"
    }


def branch_node(state: StarTopologyState) -> Dict[str, Any]:
    """
    브랜치 노드: 특화 에이전트 실행

    ⚠️ 중요: 브랜치는 오직 분석만 수행!
    ⚠️ DB 접근 없음! 결과만 반환!
    """

    routing = state["routing_decision"]
    text = state["text"]
    context = state.get("context", {})

    # 브랜치 로드
    branch = load_branch(routing.branch_name, routing.branch_config)

    # 브랜치 실행 (순수 분석)
    branch_result = branch.process(text, context)

    # ⚠️ DB 저장 없음! 결과만 State에 저장
    return {
        "branch_result": branch_result,
        "current_step": "branch"
    }


def policy_decision_node(state: StarTopologyState) -> Dict[str, Any]:
    """
    정책 결정 노드: Star가 최종 액션 결정

    역할:
    1. 브랜치 권장 액션 수신
    2. 온톨로지/정책 적용
    3. 최종 액션 결정 (Star가 결정!)
    """

    branch_result = state["branch_result"]
    routing = state["routing_decision"]
    gateway_result = state["gateway_result"]

    # Hub의 온톨로지/정책 적용
    hub = HubRouter()
    ontology = hub.ontology

    # 최종 액션 결정 (Star가 결정!)
    final_action = decide_final_action(
        branch_recommendation=branch_result.action,
        branch_confidence=branch_result.confidence,
        branch_evidence=branch_result.evidence,
        gateway_result=gateway_result,
        ontology_policy=ontology.get_task_type(routing.branch_name)
    )

    return {
        "final_action": final_action,
        "policy_reason": f"Star 결정: 브랜치 권장({branch_result.action}) + 정책 적용",
        "current_step": "policy_decision"
    }


def db_save_node(state: StarTopologyState) -> Dict[str, Any]:
    """
    DB 저장 노드: Star만 DB 접근!

    ⚠️ 중요: 오직 이 노드만 DB에 접근!
    """

    from app.services.db.connection import get_db
    from app.services.db.crud import StarTopologyCRUD

    db = next(get_db())

    try:
        # 1. 입력 이력 저장 (Star가 저장)
        input_record = StarTopologyCRUD.save_input_history(
            db,
            text=state["text"],
            session_id=state["session_id"],
            gateway_result=state["gateway_result"],
            routing_decision=state["routing_decision"]
        )

        # 2. 브랜치 결과 저장 (Star가 저장)
        StarTopologyCRUD.save_branch_result(
            db,
            input_id=input_record.id,
            branch_result=state["branch_result"]
        )

        # 3. 라우팅 로그 저장 (Star가 저장)
        StarTopologyCRUD.save_routing_log(
            db,
            input_id=input_record.id,
            trace_id=state["trace_id"],
            gateway_result=state["gateway_result"],
            routing_decision=state["routing_decision"],
            branch_result=state["branch_result"],
            final_action=state["final_action"]
        )

        return {
            "input_id": input_record.id,
            "db_saved": True,
            "current_step": "db_save"
        }

    except Exception as e:
        return {
            "db_saved": False,
            "error_message": f"DB 저장 실패: {str(e)}",
            "current_step": "db_save"
        }
    finally:
        db.close()


def aggregator_node(state: StarTopologyState) -> Dict[str, Any]:
    """응답 통합 노드"""

    aggregator = ResponseAggregator()

    response = aggregator.aggregate(
        gateway_result=state["gateway_result"],
        routing_decision=state["routing_decision"],
        branch_result=state["branch_result"],
        db_saved=state["db_saved"],
        trace_id=state["trace_id"]
    )

    return {
        "final_response": response,
        "current_step": "aggregator"
    }


def decide_final_action(
    branch_recommendation: str,
    branch_confidence: float,
    branch_evidence: List[str],
    gateway_result: GatewayResult,
    ontology_policy: dict
) -> str:
    """
    Star가 최종 액션 결정

    입력:
    - 브랜치 권장
    - 브랜치 신뢰도
    - 브랜치 증거
    - 게이트웨이 결과
    - 온톨로지 정책

    출력:
    - 최종 액션 (Star의 결정)
    """

    # Star의 정책 적용
    policy_priority = ontology_policy.get("priority", 5)

    # 브랜치 권장 신뢰도 체크
    if branch_confidence < 0.5:
        # 신뢰도 낮음 → Star가 보수적 판단
        return "quarantine"

    # 증거 개수 체크
    evidence_count = len(branch_evidence)

    if evidence_count >= 3:
        # 증거 많음 → 브랜치 권장 따름
        return branch_recommendation
    elif evidence_count >= 1:
        # 증거 적음 → Star가 완화된 판단
        if branch_recommendation == "block":
            return "quarantine"
        else:
            return branch_recommendation
    else:
        # 증거 없음 → Star가 정상 판단
        return "deliver"
```

### LangGraph 빌드

```python
# star_graph.py
def build_star_topology_graph():
    """Star Topology LangGraph 빌드 (중앙 집권화)"""

    from langgraph.graph import StateGraph, END, START

    graph = StateGraph(StarTopologyState)

    # 노드 추가
    graph.add_node("gateway", gateway_node)              # Star 관할
    graph.add_node("hub_router", hub_router_node)        # Star 중심
    graph.add_node("branch", branch_node)                # 작업만 수행
    graph.add_node("policy_decision", policy_decision_node)  # Star 최종 결정
    graph.add_node("db_save", db_save_node)              # Star만 DB 접근
    graph.add_node("aggregator", aggregator_node)        # Star 관할

    # 엣지 추가 (Star 중심 흐름)
    graph.add_edge(START, "gateway")
    graph.add_edge("gateway", "hub_router")
    graph.add_edge("hub_router", "branch")
    graph.add_edge("branch", "policy_decision")      # ⚠️ Star가 최종 결정
    graph.add_edge("policy_decision", "db_save")     # ⚠️ Star가 DB 저장
    graph.add_edge("db_save", "aggregator")
    graph.add_edge("aggregator", END)

    return graph.compile()


"""
흐름 요약 (중앙 집권화):

START
  → gateway (Star 관할)
  → hub_router (Star 중심)
  → branch (작업만 수행, DB 접근 없음) ⚠️
  → policy_decision (Star 최종 결정) ⚠️ 추가!
  → db_save (Star만 DB 접근) ⚠️ Star가 저장!
  → aggregator (Star 관할)
  → END
"""


# 편의 함수
def process_request(text: str, session_id: str = None, context: dict = None) -> dict:
    """요청 처리 (편의 함수)"""
    import uuid

    graph = build_star_topology_graph()

    initial_state = StarTopologyState(
        text=text,
        session_id=session_id or str(uuid.uuid4()),
        context=context or {},
        gateway_result=None,
        routing_decision=None,
        branch_result=None,
        input_id=None,
        db_saved=False,
        trace_id=str(uuid.uuid4()),
        current_step="start",
        error_message=None,
        final_response=None
    )

    result = graph.invoke(initial_state)

    return result["final_response"]
```

---

## 🚀 구현 로드맵

### Phase 1: 하이브리드 게이트웨이 구축 (3일)

**Day 1: 규칙 엔진 구현**
```
1. 디렉토리 구조 생성
   app/services/gateway/
   ├── rule_engine.py
   ├── rules/
   │   ├── security_rules.py
   │   ├── policy_rules.py
   │   └── routing_rules.py
   └── __init__.py

2. 규칙 정의
   - 안전장치 규칙 (입력 검증, 인젝션 감지, Rate Limit)
   - 정책 규칙 (금칙어, 허용어, 필수 조건)
   - 라우팅 규칙 (키워드 기반)

3. 규칙 엔진 코어
   - 계층적 규칙 실행
   - 규칙 매칭 로그
   - 성능 최적화 (캐싱)
```

**Day 2: ML 보조 구현**
```
1. ML Assistant 모듈
   app/services/gateway/
   ├── ml_assistant.py
   └── models/
       └── koelectra_gate.py (기존 코드 재사용)

2. KoELECTRA 래퍼
   - 기존 inference.py 활용
   - 모델 캐싱
   - 에러 처리

3. 통합 테스트
```

**Day 3: 하이브리드 통합**
```
1. HybridGateway 구현
   app/services/gateway/
   └── hybrid_gateway.py

2. 통계 수집
   - 규칙 기반 비율
   - ML 보조 비율
   - 평균 지연 시간

3. 설정 관리
   - 규칙 활성화/비활성화
   - 임계값 설정
```

### Phase 2: Hub Router 구현 (2일)

**Day 4: 브랜치 레지스트리**
```
1. 브랜치 레지스트리
   app/services/hub/
   ├── branch_registry.py
   ├── branch_config.py
   └── health_checker.py

2. 브랜치 설정
   - BranchConfig 데이터 클래스
   - 브랜치 등록/해제
   - 우선순위 관리

3. 헬스 체크
   - 주기적 헬스 체크 (백그라운드 스레드)
   - 브랜치 상태 업데이트
```

**Day 5: Hub Router 코어**
```
1. Hub Router 구현
   app/services/hub/
   ├── hub_router.py
   └── ontology_manager.py

2. 라우팅 로직
   - 게이트웨이 결과 기반 브랜치 선택
   - 폴백 브랜치 선택
   - 로드 밸런싱

3. 온톨로지 관리
   - 태스크 타입 정의
   - 라벨 체계 관리
   - 버전 관리
```

### Phase 3: 브랜치 구현 (2일)

**Day 6: 브랜치 인터페이스**
```
1. 브랜치 기본 인터페이스
   app/services/branches/
   ├── base.py
   └── __init__.py

2. BranchAgent 추상 클래스
   - load_model()
   - process() ⚠️ DB 접근 없음!
   - health_check()

3. BranchResult 데이터 클래스
   ⚠️ 주의: save_to_db(), query_from_db() 메서드 없음!
   ⚠️ Star만 DB 접근!
```

**Day 7: 스팸 브랜치 구현**
```
1. 스팸 에이전트
   app/services/branches/
   └── spam_agent/
       ├── agent.py
       ├── __init__.py
       └── config.py

2. 기존 코드 마이그레이션
   - exaone_inference.py 활용
   - lora_adapter.py 활용

3. ⚠️ DB 연동 없음!
   - 브랜치는 오직 분석만 수행
   - 결과는 BranchResult로 반환
   - Star가 DB 저장 담당
```

### Phase 4: DB Layer 구현 (2일)

**Day 8: DB 스키마 및 모델**
```
1. SQLAlchemy 모델 정의
   app/services/db/
   ├── models.py
   ├── connection.py
   └── __init__.py

2. 스키마 생성
   - 관계형 테이블 (PostgreSQL)
   - 벡터 테이블 (PGVector)

3. 마이그레이션
   - Alembic 설정
   - 초기 마이그레이션
```

**Day 9: CRUD 연산**
```
1. CRUD 구현
   app/services/db/
   └── crud.py

2. 주요 연산
   - save_input_history()
   - save_branch_result()
   - query_similar_cases()
   - get_gateway_stats()

3. 벡터 검색
   - PGVector 유사도 검색
   - 임베딩 저장/조회
```

### Phase 5: LangGraph 통합 (2일)

**Day 10: LangGraph 구조**
```
1. Star Topology Graph
   app/services/star_topology/
   ├── graph.py
   ├── nodes.py
   ├── state.py
   └── __init__.py

2. 노드 정의
   - gateway_node
   - hub_router_node
   - branch_node (DB 접근 없음!)
   - policy_decision_node (Star 최종 결정) ⚠️ 추가!
   - db_save_node (Star만 DB 접근!)
   - aggregator_node

3. 상태 관리
   - StarTopologyState (TypedDict)
   - final_action 필드 추가
```

**Day 11: 워크플로우 통합**
```
1. LangGraph 빌드
   - 노드 연결
   - 엣지 정의
   - 그래프 컴파일

2. 편의 함수
   - process_request()
   - 에러 처리
   - 로깅

3. 통합 테스트
```

### Phase 6: FastAPI 통합 (1일)

**Day 12: API 엔드포인트**
```
1. Star Topology Router
   app/router/
   └── star_router.py

2. 주요 엔드포인트
   - POST /api/star/process (메인 처리)
   - GET /api/star/branches (브랜치 목록)
   - GET /api/star/stats (통계)
   - POST /api/star/feedback (피드백)
   - GET /api/star/health (헬스 체크)

3. 응답 모델
   - Pydantic 모델 정의
```

### Phase 7: 테스트 및 최적화 (2일)

**Day 13: 테스트**
```
1. 단위 테스트
   - 각 레이어별 테스트
   - Mock 활용

2. 통합 테스트
   - 전체 플로우 테스트
   - 다양한 시나리오

3. 부하 테스트
   - 동시 요청 처리
   - 성능 측정
```

**Day 14: 최적화 및 문서화**
```
1. 성능 최적화
   - 모델 캐싱 최적화
   - DB 쿼리 최적화
   - 인덱스 튜닝

2. 모니터링 설정
   - 로깅
   - 메트릭 수집
   - 알람 설정

3. 문서화
   - API 문서
   - 아키텍처 문서
   - 운영 가이드
```

---

## 📁 최종 디렉토리 구조

```
app/
├── services/
│   ├── gateway/                        # Layer 1: 하이브리드 게이트웨이
│   │   ├── __init__.py
│   │   ├── hybrid_gateway.py          # 통합 게이트웨이
│   │   ├── rule_engine.py             # 규칙 엔진 코어
│   │   ├── ml_assistant.py            # ML 보조 (KoELECTRA)
│   │   ├── rules/
│   │   │   ├── __init__.py
│   │   │   ├── security_rules.py      # 안전장치 규칙
│   │   │   ├── policy_rules.py        # 정책 규칙
│   │   │   └── routing_rules.py       # 라우팅 규칙
│   │   └── models/
│   │       └── koelectra_gate.py      # KoELECTRA 래퍼
│   │
│   ├── hub/                            # Layer 2: Hub Router
│   │   ├── __init__.py
│   │   ├── hub_router.py              # Hub Router 코어
│   │   ├── branch_registry.py         # 브랜치 레지스트리
│   │   ├── health_checker.py          # 헬스 체커
│   │   └── ontology_manager.py        # 온톨로지 관리
│   │
│   ├── branches/                       # Layer 3: 브랜치들
│   │   ├── __init__.py
│   │   ├── base.py                    # 브랜치 인터페이스
│   │   ├── spam_agent/                # 스팸 브랜치
│   │   │   ├── __init__.py
│   │   │   ├── agent.py
│   │   │   ├── inference.py           # EXAONE 추론
│   │   │   └── lora_adapter.py        # LoRA 학습
│   │   ├── refund_agent/              # 환불 브랜치 (향후)
│   │   │   └── ...
│   │   └── sentiment_agent/           # 감성 브랜치 (향후)
│   │       └── ...
│   │
│   ├── db/                             # Layer 4: DB Layer
│   │   ├── __init__.py
│   │   ├── models.py                  # SQLAlchemy 모델
│   │   ├── connection.py              # DB 연결
│   │   └── crud.py                    # CRUD 연산
│   │
│   ├── star_topology/                  # Layer 5: LangGraph 통합
│   │   ├── __init__.py
│   │   ├── graph.py                   # LangGraph 정의
│   │   ├── nodes.py                   # 노드 정의
│   │   ├── state.py                   # 상태 관리
│   │   └── aggregator.py              # 응답 통합
│   │
│   └── spam_classifier/                # 레거시 (참고용)
│       └── ...
│
├── router/
│   ├── __init__.py
│   ├── star_router.py                 # Star Topology API
│   └── ...
│
├── models/
│   ├── adapters/                       # LoRA 어댑터들
│   │   ├── spam/
│   │   │   └── checkpoint-3000/
│   │   ├── refund/                    # 향후
│   │   └── sentiment/                 # 향후
│   └── base/
│       └── exaone-2.4b/               # EXAONE 베이스 모델
│
└── api_server_refactored.py          # FastAPI 서버
```

---

## 📊 성능 예상치

### 게이트웨이 성능

| 메트릭 | 규칙 기반 (70-90%) | ML 보조 (10-30%) |
|--------|-------------------|-----------------|
| 지연 시간 | 1-5ms | 50-100ms |
| 처리량 | ~10,000 req/sec | ~20 req/sec |
| 비용 | 거의 0 | GPU 추론 비용 |
| 정확도 | 99% (명확한 케이스) | 85-90% (모호한 케이스) |

### 전체 시스템 성능

| 시나리오 | 지연 시간 | 비용 | 비율 |
|---------|----------|------|------|
| 규칙만 (EXAONE 생략) | 1-5ms | 무료 | 50% |
| 규칙 + EXAONE | 2-3초 | GPU | 20% |
| ML + EXAONE | 2.5-3초 | GPU | 30% |
| **평균** | **~700ms** | **기존 대비 1/10** | **100%** |

**비용 절감 효과**:
- 기존 (ML 온리): 모든 요청에 GPU (100%)
- 개선 (하이브리드): 10-30%만 ML + 20-50% EXAONE
- **절감율: 70-80%**

---

## ⚠️ 주의사항 및 운영 가이드

### 1. 규칙 관리

**규칙 업데이트 절차**:
```
1. 규칙 정의 (Python 코드)
2. 단위 테스트 작성
3. Git으로 버전 관리
4. Code Review
5. 스테이징 배포
6. 프로덕션 배포
```

**규칙 우선순위**:
- 안전장치 > 정책 > 라우팅 > 휴리스틱

### 2. 온톨로지 관리

**온톨로지 업데이트**:
```
1. 온톨로지 변경 제안
2. 도메인 전문가 검토
3. 버전 증가
4. DB 업데이트
5. 게이트웨이 규칙 동기화
```

### 3. 브랜치 추가

**새 브랜치 추가 절차**:
```
1. BranchAgent 구현 (base.py 상속)
2. LoRA 어댑터 학습
3. BranchConfig 등록
4. 게이트웨이 규칙 추가
5. 통합 테스트
6. 배포
```

### 4. 모니터링

**주요 메트릭**:
- 게이트웨이 규칙 기반 비율 (목표: 70-90%)
- ML 보조 비율 (목표: 10-30%)
- 평균 지연 시간 (목표: < 1초)
- 브랜치 헬스 상태
- 에러율

**알람 설정**:
- 규칙 기반 비율 < 50% (규칙 개선 필요)
- 평균 지연 > 2초
- 브랜치 unhealthy
- 에러율 > 5%

---

## 🎯 마일스톤 및 체크포인트

### Week 1: 게이트웨이 + Hub (5일)
- [ ] 규칙 엔진 구현 및 테스트
- [ ] ML 보조 통합
- [ ] Hub Router 구현
- [ ] 브랜치 레지스트리 구현
- [ ] **체크포인트**: 게이트웨이 → Hub 흐름 동작

### Week 2: 브랜치 + DB + LangGraph (5일)
- [ ] 브랜치 인터페이스 정의 (DB 접근 없음!)
- [ ] 스팸 브랜치 구현 (순수 분석만)
- [ ] DB 스키마 및 CRUD (Star만 접근!)
- [ ] LangGraph 통합 (policy_decision_node 추가)
- [ ] **체크포인트**: 전체 플로우 동작 (화면 → Star → 브랜치 → Star → DB → 화면)

### Week 3: API + 테스트 + 최적화 (4일)
- [ ] FastAPI 엔드포인트
- [ ] 단위/통합 테스트
- [ ] 성능 최적화
- [ ] 문서화
- [ ] **최종 체크포인트**: 프로덕션 준비 완료

---

## 📚 참고 자료

### 기존 문서
- `35_VERDICT_AGENT_LANGGRAPH_ARCHITECTURE.md`: 기존 LangGraph 아키텍처
- `34_GATE_BASED_FILTERING_IMPLEMENTATION.md`: Gate 기반 필터링
- `33_TWO_STAGE_FILTERING_TEST_STRATEGY.md`: 2단계 필터링 테스트

### 새 문서 (이 파일)
- `36_STAR_TOPOLOGY_HYBRID_ARCHITECTURE.md`: Star Topology 하이브리드 아키텍처

---

**최종 확인**: 이 전략으로 구현을 진행해도 좋을까요?

승인해주시면 Phase 1 (하이브리드 게이트웨이)부터 구현을 시작하겠습니다! 🚀
