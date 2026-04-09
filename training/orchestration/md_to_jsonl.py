"""
Markdown 파일을 JSONL 형식으로 변환하는 스크립트

문제 MD 파일과 답안 MD 파일을 읽어서 JSONL 형식으로 변환합니다.
"""

import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Optional

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def parse_problem_md(md_path: Path) -> Dict:
    """
    문제 MD 파일 파싱
    
    Returns:
        {
            "problem_id": "57_1",
            "problem_title": "【문제-1】 (30점)",
            "problem_text": "전체 문제 본문",
            "sub_problems": [
                {
                    "sub_problem_id": 1,
                    "sub_problem_text": "설문 (1) 내용",
                    "points": 5
                },
                ...
            ]
        }
    """
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 파일명에서 문제 ID 추출
    problem_id = md_path.stem
    
    # 제목 추출 (첫 번째 줄)
    lines = content.strip().split('\n')
    problem_title = lines[0].strip() if lines else ""
    
    # 문제 본문과 설문 분리
    problem_text_parts = []
    sub_problems = []
    
    current_section = "main"  # "main" or "sub"
    current_sub_problem = None
    
    for i, line in enumerate(lines[1:], start=1):
        line = line.strip()
        
        if not line:
            continue
        
        # 설문 패턴 찾기: ** (1) ... (5점)**
        sub_problem_match = re.match(r'\*\*\s*\((\d+)\)\s*(.+?)\s*\((\d+)점\)\s*\*\*', line)
        if sub_problem_match:
            # 이전 설문 저장
            if current_sub_problem:
                sub_problems.append(current_sub_problem)
            
            sub_id = int(sub_problem_match.group(1))
            sub_text = sub_problem_match.group(2).strip()
            points = int(sub_problem_match.group(3))
            
            current_sub_problem = {
                "sub_problem_id": sub_id,
                "sub_problem_text": sub_text,
                "points": points
            }
            current_section = "sub"
        else:
            if current_sub_problem:
                # 현재 설문에 텍스트 추가
                if current_sub_problem.get("sub_problem_text"):
                    current_sub_problem["sub_problem_text"] += " " + line
                else:
                    current_sub_problem["sub_problem_text"] = line
            else:
                # 문제 본문에 추가
                problem_text_parts.append(line)
    
    # 마지막 설문 저장
    if current_sub_problem:
        sub_problems.append(current_sub_problem)
    
    problem_text = "\n".join(problem_text_parts).strip()
    
    return {
        "problem_id": problem_id,
        "problem_title": problem_title,
        "problem_text": problem_text,
        "sub_problems": sub_problems
    }


def parse_answer_md(md_path: Path) -> Dict:
    """
    답안 MD 파일 파싱
    
    Returns:
        {
            "answer_id": "57_1",
            "answers": [
                {
                    "sub_problem_id": 1,
                    "answer_text": "설문 (1)에 대한 답안",
                    "points": 5
                },
                ...
            ]
        }
    """
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 파일명에서 답안 ID 추출
    answer_id = md_path.stem
    
    # 설문별 답안 분리
    answers = []
    
    # 설문 패턴: "I. 설문 (1)에 대하여(5점)"
    pattern = r'([IVX]+)\.\s*설문\s*\((\d+)\)에\s*대하여\s*\((\d+)점\)'
    
    sections = re.split(pattern, content)
    
    # 첫 번째 섹션은 헤더 (무시)
    for i in range(1, len(sections), 4):
        if i + 3 < len(sections):
            section_num = sections[i]
            sub_id = int(sections[i + 1])
            points = int(sections[i + 2])
            answer_text = sections[i + 3].strip()
            
            answers.append({
                "sub_problem_id": sub_id,
                "answer_text": answer_text,
                "points": points
            })
    
    # 패턴이 없으면 전체를 하나의 답안으로 처리
    if not answers:
        answers.append({
            "sub_problem_id": 1,
            "answer_text": content.strip(),
            "points": None
        })
    
    return {
        "answer_id": answer_id,
        "answers": answers
    }


def combine_problem_and_answer(problem_data: Dict, answer_data: Dict) -> List[Dict]:
    """
    문제와 답안을 결합하여 JSONL 항목 생성
    
    Returns:
        [
            {
                "id": "57_1_1",
                "problem_id": "57_1",
                "sub_problem_id": 1,
                "problem_text": "전체 문제 본문 + 설문 (1)",
                "reference_answer_text": "설문 (1)에 대한 답안",
                "points": 5
            },
            ...
        ]
    """
    results = []
    
    # 문제 ID 확인
    problem_id = problem_data["problem_id"]
    answer_id = answer_data["answer_id"]
    
    if problem_id != answer_id:
        print(f"[WARN] 문제 ID({problem_id})와 답안 ID({answer_id})가 일치하지 않습니다.")
    
    # 답안을 sub_problem_id로 매핑
    answer_map = {ans["sub_problem_id"]: ans for ans in answer_data["answers"]}
    
    # 각 설문에 대해 항목 생성
    for sub_problem in problem_data["sub_problems"]:
        sub_id = sub_problem["sub_problem_id"]
        points = sub_problem["points"]
        
        # 전체 문제 본문 + 해당 설문
        if problem_data["problem_text"]:
            full_problem_text = f"{problem_data['problem_text']}\n\n**설문 ({sub_id})**: {sub_problem['sub_problem_text']}"
        else:
            full_problem_text = f"**설문 ({sub_id})**: {sub_problem['sub_problem_text']}"
        
        # 해당 답안 찾기
        answer = answer_map.get(sub_id)
        if not answer:
            print(f"[WARN] 설문 ({sub_id})에 대한 답안을 찾을 수 없습니다.")
            answer_text = ""
        else:
            answer_text = answer["answer_text"]
        
        # JSONL 항목 생성
        item = {
            "id": f"{problem_id}_{sub_id}",
            "problem_id": problem_id,
            "sub_problem_id": sub_id,
            "problem_text": full_problem_text.strip(),
            "reference_answer_text": answer_text.strip(),
            "points": points
        }
        
        results.append(item)
    
    return results


def md_to_jsonl(
    problem_md_path: str,
    answer_md_path: str,
    output_jsonl_path: str
):
    """
    MD 파일들을 JSONL로 변환
    
    Args:
        problem_md_path: 문제 MD 파일 경로
        answer_md_path: 답안 MD 파일 경로
        output_jsonl_path: 출력 JSONL 파일 경로
    """
    problem_file = Path(problem_md_path)
    answer_file = Path(answer_md_path)
    
    if not problem_file.exists():
        raise FileNotFoundError(f"문제 파일을 찾을 수 없습니다: {problem_file}")
    
    if not answer_file.exists():
        raise FileNotFoundError(f"답안 파일을 찾을 수 없습니다: {answer_file}")
    
    print("=" * 80)
    print("MD → JSONL 변환")
    print("=" * 80)
    print(f"문제 파일: {problem_file}")
    print(f"답안 파일: {answer_file}")
    print(f"출력 파일: {output_jsonl_path}")
    
    # MD 파일 파싱
    print("\n[1단계] 문제 MD 파일 파싱 중...")
    problem_data = parse_problem_md(problem_file)
    print(f"   문제 ID: {problem_data['problem_id']}")
    print(f"   설문 개수: {len(problem_data['sub_problems'])}개")
    
    print("\n[2단계] 답안 MD 파일 파싱 중...")
    answer_data = parse_answer_md(answer_file)
    print(f"   답안 ID: {answer_data['answer_id']}")
    print(f"   답안 개수: {len(answer_data['answers'])}개")
    
    # 문제와 답안 결합
    print("\n[3단계] 문제와 답안 결합 중...")
    jsonl_items = combine_problem_and_answer(problem_data, answer_data)
    print(f"   생성된 항목: {len(jsonl_items)}개")
    
    # JSONL 파일 저장
    print("\n[4단계] JSONL 파일 저장 중...")
    output_file = Path(output_jsonl_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in jsonl_items:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"\n✅ 변환 완료!")
    print(f"   출력 파일: {output_file}")
    print(f"   항목 개수: {len(jsonl_items)}개")
    
    # 샘플 출력
    if jsonl_items:
        print("\n[샘플 항목]")
        sample = jsonl_items[0]
        print(f"   ID: {sample['id']}")
        print(f"   문제 길이: {len(sample['problem_text'])}자")
        print(f"   답안 길이: {len(sample['reference_answer_text'])}자")
        print(f"   문제 미리보기: {sample['problem_text'][:100]}...")
        print(f"   답안 미리보기: {sample['reference_answer_text'][:100]}...")
    
    return output_file


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MD 파일을 JSONL로 변환")
    parser.add_argument(
        "problem_md",
        type=str,
        help="문제 MD 파일 경로"
    )
    parser.add_argument(
        "answer_md",
        type=str,
        help="답안 MD 파일 경로"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="출력 JSONL 파일 경로 (기본값: 문제 파일명.jsonl)"
    )
    
    args = parser.parse_args()
    
    # 출력 파일 경로 설정
    if args.output is None:
        problem_path = Path(args.problem_md)
        output_path = problem_path.parent / f"{problem_path.stem}.jsonl"
    else:
        output_path = args.output
    
    try:
        md_to_jsonl(
            problem_md_path=args.problem_md,
            answer_md_path=args.answer_md,
            output_jsonl_path=str(output_path)
        )
    except Exception as e:
        print(f"\n[ERROR] 변환 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
