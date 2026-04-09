"""
임베딩 모델은 artifacts/embedding_models 에 두고 사용합니다.

기본 사용 모델: jhgan/ko-sroberta-multitask (Sentence-BERT 형식, 768차원)
- 이미 artifacts/embedding_models/jhgan--ko-sroberta-multitask 에 있다면 별도 다운로드 불필요.
- 없으면 아래 중 하나로 준비하세요.

방법 1) sentence_transformers로 한 번 다운로드 (권장):

  pip install sentence-transformers
  python -c "
  from sentence_transformers import SentenceTransformer
  path = 'artifacts/embedding_models/jhgan--ko-sroberta-multitask'
  model = SentenceTransformer('jhgan/ko-sroberta-multitask')
  model.save(path)
  print('저장 완료:', path)
  "

방법 2) .env 에 경로만 지정

  EMBEDDING_MODEL_PATH=절대경로/artifacts/embedding_models/원하는모델폴더

DB/코드는 768차원을 가정하므로, 다른 모델 사용 시 차원이 768인지 확인하세요.
"""
# 이 파일은 안내용입니다. 실제 다운로드는 위 방법 1을 터미널에서 실행하세요.
if __name__ == "__main__":
    print(__doc__)
