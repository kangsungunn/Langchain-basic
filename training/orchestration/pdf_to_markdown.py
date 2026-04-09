"""
PDF를 Markdown으로 변환하는 스크립트

PDF 파일의 특정 페이지 범위를 추출하여 Markdown 파일로 저장합니다.
"""

import sys
from pathlib import Path
import re

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    try:
        import PyPDF2 as pypdf
        PYPDF_AVAILABLE = True
    except ImportError:
        PYPDF_AVAILABLE = False
        print("[ERROR] pypdf가 설치되지 않았습니다.")
        sys.exit(1)


def extract_text_from_pdf(pdf_path: Path, start_page: int = 0, end_page: int = None) -> str:
    """
    PDF에서 텍스트 추출
    
    Args:
        pdf_path: PDF 파일 경로
        start_page: 시작 페이지 (0-based)
        end_page: 끝 페이지 (0-based, None이면 끝까지)
    
    Returns:
        추출된 텍스트
    """
    full_text = ""
    
    with open(pdf_path, 'rb') as file:
        pdf_reader = pypdf.PdfReader(file)
        total_pages = len(pdf_reader.pages)
        
        if end_page is None:
            end_page = total_pages
        
        print(f"총 페이지 수: {total_pages}")
        print(f"추출 범위: {start_page+1}페이지 ~ {end_page}페이지 ({end_page - start_page}페이지)")
        
        for page_num in range(start_page, min(end_page, total_pages)):
            try:
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    # 페이지 구분자 추가
                    full_text += f"\n\n---\n\n## 페이지 {page_num + 1}\n\n"
                    full_text += page_text + "\n"
                    print(f"페이지 {page_num+1}: {len(page_text)}자 추출")
            except Exception as e:
                print(f"[WARN] 페이지 {page_num+1} 추출 실패: {e}")
    
    return full_text.strip()


def clean_text_for_markdown(text: str) -> str:
    """
    Markdown 형식에 맞게 텍스트 정리
    
    Args:
        text: 원본 텍스트
    
    Returns:
        정리된 텍스트
    """
    # 연속된 공백 정리
    text = re.sub(r' +', ' ', text)
    
    # 연속된 줄바꿈 정리 (최대 2개)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 페이지 구분자 앞뒤 정리
    text = re.sub(r'\n+---\n+', '\n\n---\n\n', text)
    
    return text.strip()


def pdf_to_markdown(
    pdf_path: str,
    output_path: str,
    start_page: int = 0,
    end_page: int = None
):
    """
    PDF를 Markdown으로 변환
    
    Args:
        pdf_path: PDF 파일 경로
        output_path: 출력 MD 파일 경로
        start_page: 시작 페이지 (0-based, 기본값: 0)
        end_page: 끝 페이지 (0-based, None이면 끝까지)
    """
    pdf_file = Path(pdf_path).resolve()
    
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_file}")
    
    print("=" * 80)
    print("PDF → Markdown 변환")
    print("=" * 80)
    print(f"입력 파일: {pdf_file}")
    print(f"출력 파일: {output_path}")
    
    # 텍스트 추출
    print("\n[1단계] 텍스트 추출 중...")
    text = extract_text_from_pdf(pdf_file, start_page, end_page)
    
    if not text.strip():
        raise ValueError("텍스트를 추출할 수 없습니다.")
    
    # 텍스트 정리
    print("\n[2단계] 텍스트 정리 중...")
    cleaned_text = clean_text_for_markdown(text)
    
    # Markdown 헤더 추가
    markdown_content = f"""# PDF 변환 문서

**원본 파일**: {pdf_file.name}
**추출 범위**: {start_page+1}페이지 ~ {end_page if end_page else '끝'}페이지
**변환 일시**: {Path(__file__).stat().st_mtime if Path(__file__).exists() else 'N/A'}

---

{cleaned_text}
"""
    
    # 파일 저장
    print("\n[3단계] Markdown 파일 저장 중...")
    output_file = Path(output_path).resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    print(f"\n✅ 변환 완료!")
    print(f"   출력 파일: {output_file}")
    print(f"   파일 크기: {len(markdown_content)}자")
    
    return output_file


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="PDF를 Markdown으로 변환")
    parser.add_argument(
        "pdf_file",
        type=str,
        help="PDF 파일 경로"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="출력 MD 파일 경로 (기본값: PDF 파일명.md)"
    )
    parser.add_argument(
        "--start-page",
        type=int,
        default=0,
        help="시작 페이지 (1-based, 기본값: 1)"
    )
    parser.add_argument(
        "--end-page",
        type=int,
        default=None,
        help="끝 페이지 (1-based, 기본값: 끝까지)"
    )
    
    args = parser.parse_args()
    
    # 1-based를 0-based로 변환
    start_page = args.start_page - 1 if args.start_page > 0 else 0
    end_page = args.end_page if args.end_page is None else args.end_page
    
    # 출력 파일 경로 설정
    if args.output is None:
        pdf_path = Path(args.pdf_file)
        output_path = pdf_path.parent / f"{pdf_path.stem}_pages{start_page+1}-{end_page or 'end'}.md"
    else:
        output_path = args.output
    
    try:
        pdf_to_markdown(
            pdf_path=args.pdf_file,
            output_path=str(output_path),
            start_page=start_page,
            end_page=end_page
        )
    except Exception as e:
        print(f"\n[ERROR] 변환 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
