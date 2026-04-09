# 📚 법령 데이터 준비 가이드

## 🎯 목표

법제처에서 다운로드한 특허법/상표법 문서를 학습 가능한 JSONL 형식으로 변환

---

## 📥 Step 1: 법제처에서 법령 다운로드

### 1-1. 특허법 다운로드

1. **국가법령정보센터 접속**
   - URL: https://www.law.go.kr/
   - 검색: "특허법"

2. **저장 옵션 설정**
   - **범위설정**: "일부저장" 또는 "선택저장"
   - **파일 형식**: 다음 중 선택
     - ✅ **PDF 파일** (권장 - 파싱 쉬움)
     - ✅ **DOC 파일** (권장 - 파싱 쉬움)
     - ⚠️ HWP 파일 (변환 필요)

3. **다운로드**
   - `data/raw/patent_law/` 폴더에 저장
   - 예: `data/raw/patent_law/특허법.pdf`

### 1-2. 상표법 다운로드

- 동일한 방법으로 상표법 다운로드
- `data/raw/trademark_law/` 폴더에 저장

---

## 🔧 Step 2: 필요한 패키지 설치

```powershell
# PDF 파싱
pip install PyPDF2

# DOCX 파싱
pip install python-docx

# HWP 파일은 DOCX로 변환 필요 (별도 프로그램)
```

---

## 🚀 Step 3: 데이터 변환 실행

```powershell
# 특허법 변환
python training/shared/parse_law_documents.py
```

**실행 결과:**
```
🔄 처리 중: 특허법.pdf
  ✅ 234개 조문 발견
✅ 총 234개 샘플 생성

📊 데이터 분할:
  Train: 187개 (80.0%)
  Val: 23개 (10.0%)
  Test: 24개 (10.0%)

✅ 저장 완료: data/processed/patent/train.jsonl
✅ 저장 완료: data/processed/patent/val.jsonl
✅ 저장 완료: data/processed/patent/test.jsonl
```

---

## 📊 생성되는 데이터 형식

### JSONL 파일 구조

각 줄은 하나의 JSON 객체:

```json
{
  "input": "제1조(목적)",
  "output": "이 법은 발명을 보호·장려하고 그 이용을 도모함으로써 기술의 발전을 촉진하여 산업발전에 이바지함을 목적으로 한다.",
  "metadata": {
    "article": "1",
    "title": "목적",
    "law_type": "patent",
    "source": "법제처"
  }
}
```

### 파일 위치

```
data/processed/patent/
├── train.jsonl    (80% - 학습용)
├── val.jsonl      (10% - 검증용)
└── test.jsonl     (10% - 테스트용)
```

---

## 🔍 Step 4: 데이터 확인

```powershell
# 샘플 개수 확인
Get-Content data/processed/patent/train.jsonl | Measure-Object -Line

# 첫 번째 샘플 확인
Get-Content data/processed/patent/train.jsonl -First 1 | ConvertFrom-Json | ConvertTo-Json
```

---

## ⚠️ 주의사항

### HWP 파일 처리

HWP 파일은 직접 파싱이 어려우므로:

1. **옵션 A**: DOCX로 변환
   - 한글 뷰어로 열기 → "다른 이름으로 저장" → DOCX 선택

2. **옵션 B**: PDF로 변환
   - 한글 뷰어로 열기 → "인쇄" → "PDF로 저장"

3. **옵션 C**: 텍스트 복사
   - 한글 뷰어로 열기 → 전체 선택 → 복사
   - `data/raw/patent_law/특허법.txt` 파일로 저장

### 파싱 오류 시

조문 패턴이 맞지 않으면 수동으로 수정:

```python
# training/shared/parse_law_documents.py의 parse_articles 메서드 수정
pattern = r'제(\d+)조\s*(?:\(([^)]+)\))?\s*(.*?)(?=제\d+조|$)'
```

---

## 🎯 다음 단계

데이터 준비가 완료되면:

```powershell
# 모델 훈련 실행
python training/examination/patent/train.py
```

---

## 📋 체크리스트

- [ ] 법제처에서 특허법 다운로드 (PDF/DOCX)
- [ ] `data/raw/patent_law/` 폴더에 저장
- [ ] 필요한 패키지 설치 (PyPDF2, python-docx)
- [ ] 변환 스크립트 실행
- [ ] 생성된 JSONL 파일 확인
- [ ] 데이터 개수 확인 (최소 100개 이상 권장)

---

**작성일**: 2026-01-20
**버전**: 1.0
