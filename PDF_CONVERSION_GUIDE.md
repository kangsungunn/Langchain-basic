# 📄 PDF 특허법 → 학습 데이터 변환 가이드

## ✅ Step 1: PDF 파일 저장

다운로드한 특허법 PDF 파일을 다음 위치에 저장하세요:

```
data/raw/patent_law/특허법.pdf
```

**또는 파일명이 다르면:**
- `data/raw/patent_law/` 폴더 안에 `.pdf` 파일만 있으면 자동으로 인식됩니다.

---

## 🔧 Step 2: 필요한 패키지 설치

```powershell
pip install PyPDF2
```

---

## 🚀 Step 3: 변환 실행

```powershell
python training/shared/parse_law_documents.py
```

---

## 📊 예상 결과

```
============================================================
법령 문서 → 학습 데이터 변환
============================================================
🔄 처리 중: 특허법.pdf
  ✅ 234개 조문 발견

✅ 총 234개 샘플 생성

✅ 저장 완료: data/processed/patent/train.jsonl (187개 샘플)
✅ 저장 완료: data/processed/patent/val.jsonl (23개 샘플)
✅ 저장 완료: data/processed/patent/test.jsonl (24개 샘플)

📊 데이터 분할:
  Train: 187개 (80.0%)
  Val: 23개 (10.0%)
  Test: 24개 (10.0%)

============================================================
✅ 변환 완료!
============================================================
```

---

## 🔍 Step 4: 결과 확인

```powershell
# 생성된 파일 확인
Get-ChildItem data\processed\patent\

# 샘플 개수 확인
Get-Content data\processed\patent\train.jsonl | Measure-Object -Line

# 첫 번째 샘플 확인
Get-Content data\processed\patent\train.jsonl -First 1
```

---

## ⚠️ 문제 해결

### PDF 파싱 오류 시

**문제**: "PyPDF2가 설치되지 않았습니다"
**해결**: `pip install PyPDF2`

**문제**: "텍스트 추출 실패"
**해결**:
- PDF가 이미지 기반인 경우 OCR 필요
- 또는 DOCX 형식으로 다시 다운로드

**문제**: "조문 발견 0개"
**해결**:
- PDF 텍스트 추출이 제대로 되지 않음
- PDF를 텍스트로 변환하거나 DOCX로 다시 다운로드

---

## 🎯 다음 단계

변환이 완료되면:

```powershell
# 모델 훈련 실행
python training/examination/patent/train.py
```
