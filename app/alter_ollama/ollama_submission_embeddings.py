"""
Submission 임베딩 모델 코드 생성 스크립트

ExaOne 모델을 사용하여 UserAnswerEmbedding SQLAlchemy ORM 모델 코드를 자동 생성.
"""

import os
import sys
import ast
import torch
from pathlib import Path
from typing import Optional
from transformers import AutoTokenizer, AutoModelForCausalLM

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import settings
from app.core.utils.logger import get_logger

logger = get_logger()


def read_existing_model_file() -> str:
    """기존 Submission 모델 파일 읽기"""
    model_file = project_root / "app" / "domain" / "v1" / "minso" / "models" / "bases" / "submission.py"

    if not model_file.exists():
        raise FileNotFoundError(f"기존 모델 파일을 찾을 수 없습니다: {model_file}")

    return model_file.read_text(encoding="utf-8")


def build_prompt(existing_model_content: str) -> str:
    """ExaOne 코드 생성 프롬프트 구성"""
    prompt = f"""다음 SQLAlchemy UserAnswer 모델을 참고하여 UserAnswerEmbedding ORM 클래스를 작성하세요.

=== UserAnswer 모델 코드 ===
{existing_model_content}

=== Alembic 마이그레이션 테이블 스키마 ===
테이블명: user_answer_embeddings
컬럼:
- id: BigInteger, PK, autoincrement=True, nullable=False, comment='임베딩 레코드 고유 식별자'
- user_answer_id: String(36), FK -> user_answers.id, nullable=False, ondelete='CASCADE', comment='사용자 답안 ID'
- content: Text, nullable=False, comment='임베딩 생성에 사용된 원본 텍스트'
- embedding: Vector(768), nullable=False, comment='768차원 임베딩 벡터 (KoELECTRA)'
- created_at: TIMESTAMP(timezone=True), server_default=now(), nullable=False, comment='레코드 생성 시간'

=== 요구사항 ===
1. Base 클래스: from app.core.database.connection import Base 사용 (declarative_base() 직접 사용 금지)
2. pgvector: from pgvector.sqlalchemy import Vector 사용 (from pgvector import Vector 금지)
3. Vector 사용법: Vector(768) 형식 사용 (Vector('768'), Vector['768d'] 등 금지)
4. SQLAlchemy imports: Column, BigInteger, String, Text, ForeignKey, TIMESTAMP, relationship
5. 타임스탬프: from sqlalchemy.sql import func 사용하여 server_default=func.now() 설정
6. ForeignKey: ondelete='CASCADE' 반드시 포함 (예: ForeignKey("user_answers.id", ondelete='CASCADE'))
7. relationship: user_answer (back_populates="embeddings") 설정 (UserAnswer 모델에 embeddings 관계가 있다고 가정)
8. submission.py의 코딩 스타일과 일관성 유지 (주석 형식, Column 정의 방식 등)
9. 모든 Column에 comment 추가 (nullable=False인 경우에도 명시)
10. __tablename__ = "user_answer_embeddings" 사용
11. 파일 헤더 docstring: """Submission Embedding - 모델 (자동 생성)\n\nUserAnswer 엔티티의 임베딩 모델.\nExaOne 모델로 자동 생성됨.\n"""
12. 클래스 docstring: """UserAnswer 임베딩 엔티티\n\n사용자 답안에 대한 벡터 임베딩 정보를 저장합니다.\n"""
13. Python 코드만 출력 (주석이나 설명 없이 순수 코드만, 원본 모델 클래스(UserAnswer, AnswerStructure 등) 포함 금지)
14. Relationships 섹션 주석 추가

=== 출력 형식 ===
파일 전체 코드를 출력하세요. import 문부터 시작하여 완전한 Python 파일 형태로 작성하세요."""
    return prompt.strip()


def load_exaone_model():
    """ExaOne 모델 로드 (코드 생성용)"""
    model_path = settings.EXAONE_BASE_MODEL_PATH

    if not Path(model_path).exists():
        raise FileNotFoundError(
            f"ExaOne 모델을 찾을 수 없습니다: {model_path}\n"
            f"환경 변수 EXAONE_BASE_MODEL_PATH를 확인하거나 모델을 다운로드하세요."
        )

    print("[ExaOne] 모델 로딩 중...")
    tokenizer = AutoTokenizer.from_pretrained(str(model_path), trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        str(model_path),
        dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True
    )

    print("[ExaOne] 모델 로드 완료")
    return model, tokenizer


def generate_code_with_exaone(model, tokenizer, prompt: str) -> str:
    """ExaOne 모델로 코드 생성"""
    messages = [
        {
            "role": "system",
            "content": "You are EXAONE model from LG AI Research, a helpful assistant specialized in generating Python SQLAlchemy ORM code."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    input_ids = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt"
    ).to(model.device)

    outputs = model.generate(
        input_ids,
        max_new_tokens=1200,
        do_sample=True,
        temperature=0.7,
        top_p=0.9,
        eos_token_id=tokenizer.eos_token_id,
        pad_token_id=tokenizer.pad_token_id
    )

    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

    if "assistant" in generated_text.lower() or "답변" in generated_text:
        if "```python" in generated_text:
            code_start = generated_text.find("```python") + 9
            code_end = generated_text.find("```", code_start)
            if code_end != -1:
                generated_code = generated_text[code_start:code_end].strip()
            else:
                generated_code = generated_text[code_start:].strip()
        elif "```" in generated_text:
            code_start = generated_text.find("```") + 3
            code_end = generated_text.find("```", code_start)
            if code_end != -1:
                generated_code = generated_text[code_start:code_end].strip()
            else:
                generated_code = generated_text[code_start:].strip()
        else:
            if "assistant" in generated_text.lower():
                parts = generated_text.split("assistant", 1)
                if len(parts) > 1:
                    generated_code = parts[-1].strip()
                else:
                    generated_code = generated_text
            else:
                generated_code = generated_text
    else:
        generated_code = generated_text

    return generated_code


def validate_generated_code(code: str) -> tuple[bool, Optional[str]]:
    """생성된 코드 검증 (AST 파싱)"""
    try:
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, f"문법 오류: {e.msg} (line {e.lineno})"
    except Exception as e:
        return False, f"검증 실패: {str(e)}"


def main():
    """메인 함수"""
    print("[ExaOne] Submission 임베딩 모델 코드 생성 시작...")

    try:
        print("[ExaOne] 기존 Submission 모델 파일 읽기...")
        existing_model_content = read_existing_model_file()

        print("[ExaOne] 코드 생성 프롬프트 구성...")
        prompt = build_prompt(existing_model_content)

        print("[ExaOne] 모델 로딩 중...")
        model, tokenizer = load_exaone_model()

        print("[ExaOne] 코드 생성 중...")
        generated_code = generate_code_with_exaone(model, tokenizer, prompt)

        print("\n=== 생성된 코드 ===")
        print(generated_code)
        print("\n=== 코드 생성 완료 ===\n")

        is_valid, error_msg = validate_generated_code(generated_code)
        if not is_valid:
            print(f"[경고] 코드 검증 실패: {error_msg}")
            print("[경고] 생성된 코드를 수동으로 확인하세요.")
        else:
            print("[OK] 코드 검증 통과")

        output_path = project_root / "app" / "domain" / "v1" / "minso" / "models" / "bases" / "submission_embeddings.py"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(generated_code, encoding="utf-8")

        print(f"[완료] 코드가 {output_path}에 저장되었습니다.")

    except Exception as e:
        print(f"[오류] 코드 생성 실패: {e}")
        raise


if __name__ == "__main__":
    main()
