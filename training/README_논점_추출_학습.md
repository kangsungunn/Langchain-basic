# 논점 추출 ExaOne LoRA 학습 — 실행 가이드

`training/` 에 모델 학습 관련 코드를 모아 두었고, **논점 추출**용 ExaOne LoRA SFT는 아래 순서로 실행하면 됩니다.

---

## 1. 데이터 준비 (이미 했다면 생략)

```bash
# (문제, 논점) JSONL 생성
python scripts/build_problem_issues_jsonl.py

# SFT 형식으로 변환
python scripts/problem_issues_to_sft_jsonl.py

# train / val 분할 (90% / 10%)
python scripts/split_sft_train_val.py
```

→ `training/data/issue_extraction/train.jsonl`, `val.jsonl` 이 있어야 합니다.

---

## 2. 학습 실행 (직접 터미널에 입력)

**프로젝트 루트**에서 실행하세요.

```bash
python -m training.shared.train_exaone_lora --data-dir training/data/issue_extraction --output-dir artifacts/models/finetuned/exaone-issue-extraction
```

- **베이스 모델**: `artifacts/models/base/exaone-2.4b` (없으면 `EXAONE_BASE_MODEL_PATH` 환경 변수로 지정)
- **저장 위치**: `artifacts/models/finetuned/exaone-issue-extraction/` (LoRA 어댑터 + 토크나이저)

### 옵션 예시

```bash
# 에폭·배치 등 변경
python -m training.shared.train_exaone_lora --data-dir training/data/issue_extraction --output-dir artifacts/models/finetuned/exaone-issue-extraction --num-epochs 5 --batch-size 2 --learning-rate 2e-5
```

전체 옵션: `python -m training.shared.train_exaone_lora --help`

---

## 3. 학습 후

- 저장된 LoRA를 쓰려면 추론 시 **베이스 ExaOne + 이 어댑터**를 로드하면 됩니다.
- 논점 추출 서비스/API는 이 모델을 로드해 `problem_content` → 논점 목록을 반환하도록 연결하면 됩니다.

자세한 다음 단계: `app/domain/v1/minso/논점_추출_다음_단계.md`
