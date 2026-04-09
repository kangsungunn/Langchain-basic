# 🔧 Tool Calling 가이드

## 📖 Tool Calling이란?

**Tool Calling**은 LLM(대화형 AI)이 대화 중에 **외부 도구나 함수를 자동으로 호출**할 수 있게 해주는 기능입니다.

### 간단한 비유
- **일반 대화**: "지금 몇 시야?" → AI가 학습 데이터 기반으로 추정 답변
- **Tool Calling**: "지금 몇 시야?" → AI가 `get_current_time()` 함수를 호출 → 정확한 현재 시간 반환

---

## 🎯 Tool Calling의 역할

### 1. **실시간 정보 조회**
```python
# 예시: 현재 시간 조회
사용자: "지금 몇 시야?"
AI: [get_server_time() 호출] → "2024-01-15T14:30:00Z"
AI: "지금은 오후 2시 30분입니다."
```

### 2. **외부 시스템과의 상호작용**
- 데이터베이스 조회
- API 호출 (날씨, 주식, 뉴스 등)
- 파일 시스템 접근
- 계산기, 검색 엔진 등

### 3. **동적 작업 수행**
- 계산이 필요한 경우 계산기 도구 사용
- 검색이 필요한 경우 검색 도구 사용
- 데이터 조회가 필요한 경우 DB 조회 도구 사용

---

## 💡 현재 프로젝트의 Tool Calling 상태

### 현재 구현된 Tool
```python
# app/graph.py
@tool
def get_server_time() -> str:
    """Return server time as ISO string."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()

TOOLS = [get_server_time]  # 단 하나의 간단한 예시 tool만 있음
```

### 현재 사용 여부
- ❌ **RAG 모드**: Tool calling **사용 안 함**
- ✅ **Tool calling 모드**: Tool calling **사용** (하지만 프론트엔드에서 호출 안 함)

---

## 🤔 Tool Calling이 필요한가?

### ✅ **필요한 경우**

#### 1. **실시간 정보가 필요한 챗봇**
```
사용자: "오늘 날씨 어때?"
→ 날씨 API tool 호출 필요

사용자: "지금 주식 시세 알려줘"
→ 주식 API tool 호출 필요
```

#### 2. **동작(Action)이 필요한 챗봇**
```
사용자: "이메일 보내줘"
→ 이메일 전송 tool 호출 필요

사용자: "파일 저장해줘"
→ 파일 시스템 tool 호출 필요
```

#### 3. **복잡한 계산이나 검색이 필요한 경우**
```
사용자: "1234 * 5678 계산해줘"
→ 계산기 tool 호출

사용자: "최신 뉴스 검색해줘"
→ 검색 tool 호출
```

### ❌ **필요 없는 경우**

#### 1. **순수 대화형 챗봇**
- 질문에 답변만 하면 되는 경우
- 지식 베이스(RAG)만으로 충분한 경우
- 예: "파이썬이 뭐야?", "RAG 설명해줘"

#### 2. **현재 프로젝트 상황**
- ✅ **RAG 기능**: 이미 구현됨 (벡터 DB 검색)
- ✅ **일반 대화**: Exaone 모델로 충분
- ❌ **실시간 정보**: 필요 없음 (날씨, 주식 등)
- ❌ **외부 시스템 연동**: 필요 없음

---

## 📊 Tool Calling의 장단점

### ✅ 장점

1. **정확성 향상**
   - 학습 데이터 기반 추정이 아닌 실제 데이터 사용
   - 예: "지금 몇 시야?" → 정확한 현재 시간

2. **확장성**
   - 새로운 기능을 tool로 추가 가능
   - 모델 재학습 없이 기능 확장

3. **동적 작업 수행**
   - 계산, 검색, 데이터 조회 등 자동화

### ❌ 단점

1. **복잡도 증가**
   - Tool 정의, 호출 로직, 에러 처리 등 추가 코드 필요
   - 디버깅이 어려워짐

2. **성능 오버헤드**
   - Tool 호출 시 추가 시간 소요
   - Tool 실행 실패 시 재시도 로직 필요

3. **모델 의존성**
   - Tool calling을 잘 지원하는 모델 필요
   - Exaone 모델이 Tool calling을 완벽히 지원하는지 불확실

4. **현재 프로젝트에서는 활용도 낮음**
   - `get_server_time()` 같은 간단한 tool만 있음
   - 실제로 유용한 tool이 없음

---

## 🎯 현재 프로젝트에서의 판단

### 현재 상황 분석

1. **주요 기능**
   - ✅ RAG (지식 베이스 검색) - 이미 구현됨
   - ✅ 일반 대화 - Exaone 모델로 충분
   - ❌ 실시간 정보 조회 - 필요 없음
   - ❌ 외부 시스템 연동 - 필요 없음

2. **현재 Tool**
   - `get_server_time()`: 서버 시간 조회
   - **실제 사용 가치**: 거의 없음 (사용자가 서버 시간을 물어볼 일이 거의 없음)

3. **Exaone 모델의 Tool Calling 지원**
   - HuggingFace 모델이 Tool calling을 완벽히 지원하는지 불확실
   - 테스트 필요

### 💡 추천 사항

#### **현재는 Tool Calling 비활성화 추천** ✅

**이유:**
1. **RAG로 충분**: 지식 베이스 검색이 주요 기능
2. **불필요한 복잡도**: 현재 tool이 실용적이지 않음
3. **성능**: Tool calling 오버헤드 없이 더 빠른 응답
4. **안정성**: Tool 호출 실패 가능성 제거

#### **나중에 필요하면 추가 가능** 🔮

만약 나중에 다음 기능이 필요하면 Tool calling을 활성화:
- 날씨 조회
- 주식 시세 조회
- 계산기
- 검색 엔진 연동
- 데이터베이스 직접 조회
- 파일 시스템 접근

---

## 🛠️ Tool Calling 활성화 방법 (나중에 필요할 때)

### 1. 유용한 Tool 추가
```python
@tool
def search_weather(city: str) -> str:
    """Get current weather for a city."""
    # 날씨 API 호출
    return weather_data

@tool
def calculate(expression: str) -> str:
    """Calculate a mathematical expression."""
    # 계산 수행
    return result

TOOLS = [get_server_time, search_weather, calculate]
```

### 2. RAG 노드에서 Tool calling 활성화
```python
# 현재
langgraph_llm, _ = get_langgraph_llm()  # Tool 없이 사용

# 변경 후
_, langgraph_llm_with_tools = get_langgraph_llm()  # Tool 포함 사용
response = langgraph_llm_with_tools.invoke(messages)
```

### 3. Tool calling 그래프 사용
```python
# Tool calling이 필요한 경우 tool_graph 사용
# Tool calling이 필요 없는 경우 rag_graph 사용
```

---

## 📝 결론

### 현재 프로젝트에서는 **Tool Calling 불필요** ✅

**이유:**
- ✅ RAG 기능으로 충분
- ✅ 일반 대화는 Exaone 모델로 충분
- ❌ 실용적인 tool이 없음
- ❌ 복잡도만 증가

### 나중에 필요하면 추가
- 실시간 정보 조회가 필요할 때
- 외부 시스템 연동이 필요할 때
- 동적 작업 수행이 필요할 때

**현재는 RAG 모드만 사용하는 것을 추천합니다!** 🎯
