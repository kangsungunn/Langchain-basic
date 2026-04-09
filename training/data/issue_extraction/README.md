# 논점 추출 학습 데이터 (ExaOne SFT)

이 디렉터리에는 **논점 추출** ExaOne LoRA SFT용 `train.jsonl`, `val.jsonl`이 들어갑니다.

## 데이터 형식

한 줄당 하나의 JSON 객체:

- `instruction`: 지시문 (고정 문구)
- `input`: 문제 지문 전체
- `output`: 논점 제목을 한 줄에 하나씩 나열한 문자열

## 생성 방법

1. **(문제, 논점) JSONL 생성** (이미 되어 있으면 생략)
   ```bash
   python scripts/build_problem_issues_jsonl.py
   ```

2. **SFT 형식으로 변환**
   ```bash
   python scripts/problem_issues_to_sft_jsonl.py
   ```
   → `data/raw/civil_procedure/problem_issues/gy_saeryejip_sft.jsonl` 생성

3. **train / val 분할**
   ```bash
   python scripts/split_sft_train_val.py
   ```
   → 이 디렉터리에 `train.jsonl`, `val.jsonl` 생성 (기본 90% / 10%)

## 학습 실행

프로젝트 루트에서:

```bash
python -m training.shared.train_exaone_lora --data-dir training/data/issue_extraction --output-dir artifacts/models/finetuned/exaone-issue-extraction
```

옵션: `--num-epochs`, `--batch-size`, `--learning-rate` 등은 `python -m training.shared.train_exaone_lora --help` 참고.
