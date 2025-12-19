# EC2 배포 디렉토리 구조 전략

## 📋 권장 배포 위치

### ✅ 최적 선택: `/var/www/langchain/`

**이유:**
1. **Linux 표준**: 웹 애플리케이션의 표준 위치
2. **권한 관리**: `www-data` 또는 `ubuntu` 사용자로 실행 가능
3. **보안**: 루트 디렉토리 하위에 있어 관리 용이
4. **백업**: `/var/www/` 전체를 백업하기 쉬움
5. **업계 표준**: 대부분의 프로덕션 환경에서 사용

### 📁 최종 디렉토리 구조

```
/var/www/langchain/                    # 프로젝트 루트
├── app/                               # 애플리케이션 코드
│   ├── __init__.py
│   ├── api_server_refactored.py      # FastAPI 엔트리 포인트
│   ├── router/                       # API 라우터
│   ├── services/                     # 비즈니스 로직
│   ├── models/                       # 모델 관련
│   │   └── midm/                     # Midm 모델 (CPU용)
│   ├── repository/                  # 데이터 레이어
│   ├── config/                      # 설정
│   └── api/                         # API 의존성
├── venv/                             # Python 가상 환경
├── .env                              # 환경 변수 (권한: 600)
├── requirements.txt                  # Python 의존성
├── .git/                             # Git 저장소 (선택사항)
└── README.md                         # 프로젝트 문서

/var/log/langchain/                   # 로그 디렉토리
├── access.log                        # 애플리케이션 액세스 로그
└── error.log                         # 에러 로그

/etc/systemd/system/                  # Systemd 서비스 파일
└── langchain-api.service             # FastAPI 서비스 정의

/etc/nginx/sites-available/           # Nginx 설정
└── langchain                         # 리버스 프록시 설정
```

---

## 🎯 배포 전략

### 1. 프로젝트 구조 유지

**현재 로컬 구조를 그대로 유지:**
- `app/` 디렉토리 구조 유지
- 상대 경로 import (`from app.router import ...`) 그대로 사용
- `requirements.txt` 루트에 유지

**이유:**
- 코드 변경 최소화
- 로컬과 프로덕션 환경 일관성
- Git 저장소 구조와 동일

### 2. CPU 최적화 고려사항

#### 2.1 Midm 모델 위치

**옵션 A: 프로젝트 내부 (권장)**
```
/var/www/langchain/app/models/midm/
```
- 장점: 코드와 함께 관리, Git으로 버전 관리 가능
- 단점: 프로젝트 디렉토리가 커짐 (4.3GB+)

**옵션 B: 별도 디렉토리**
```
/opt/models/midm/
```
- 장점: 프로젝트 디렉토리 분리, 모델만 별도 백업 가능
- 단점: 경로 설정 필요, 심볼릭 링크 또는 환경 변수로 연결

**권장: 옵션 A (프로젝트 내부)**
- CPU 모드에서는 모델이 자주 변경되지 않음
- 배포와 관리가 단순함

#### 2.2 환경 변수 설정

```bash
# /var/www/langchain/.env
LLM_PROVIDER=openai  # CPU에서는 OpenAI 사용 권장 (Midm은 CPU에서 느림)
MIDM_MODEL_PATH=/var/www/langchain/app/models/midm
MIDM_DEVICE=cpu
```

**CPU 모드 권장 설정:**
- `LLM_PROVIDER=openai`: OpenAI API 사용 (CPU에서 Midm보다 훨씬 빠름)
- Midm 모델은 CPU에서 매우 느리므로 (30초~2분) 프로덕션에서는 비권장

---

## 🚀 배포 단계별 가이드

### Step 1: EC2 디렉토리 생성

```bash
# EC2에 SSH 접속
ssh -i "kang.pem" ubuntu@ec2-43-201-10-181.ap-northeast-2.compute.amazonaws.com

# 디렉토리 생성
sudo mkdir -p /var/www/langchain
sudo mkdir -p /var/log/langchain

# 권한 설정
sudo chown -R ubuntu:ubuntu /var/www/langchain
sudo chown -R ubuntu:ubuntu /var/log/langchain
```

### Step 2: 프로젝트 배포

**방법 A: Git으로 배포 (권장)**

```bash
cd /var/www/langchain

# GitHub에서 클론
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git .

# 또는 기존 저장소 pull
git pull origin main
```

**방법 B: SCP로 직접 업로드**

```bash
# 로컬에서 실행
scp -i "kang.pem" -r app/ ubuntu@ec2-43-201-10-181.ap-northeast-2.compute.amazonaws.com:/var/www/langchain/
scp -i "kang.pem" requirements.txt ubuntu@ec2-43-201-10-181.ap-northeast-2.compute.amazonaws.com:/var/www/langchain/
```

### Step 3: 가상 환경 설정

```bash
cd /var/www/langchain

# Python 3.11 가상 환경 생성
python3.11 -m venv venv

# 가상 환경 활성화
source venv/bin/activate

# 의존성 설치 (CPU 최적화)
pip install --upgrade pip
pip install -r requirements.txt

# CPU 전용 PyTorch 설치 (선택사항, 더 가벼움)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### Step 4: 환경 변수 설정

```bash
# .env 파일 생성
cat > /var/www/langchain/.env << 'EOF'
# OpenAI (CPU 모드에서는 OpenAI 사용 권장)
OPENAI_API_KEY=XXX
LLM_PROVIDER=openai

# PostgreSQL (Neon)
POSTGRES_HOST=ep-mute-boat-a1sgw2su-pooler.ap-southeast-1.aws.neon.tech
POSTGRES_PORT=5432
POSTGRES_USER=neondb_owner
POSTGRES_PASSWORD=XXX
POSTGRES_DB=neondb
POSTGRES_SSLMODE=require
PGVECTOR_COLLECTION=langchain_knowledge_base

# Model (CPU 모드)
MIDM_MODEL_PATH=/var/www/langchain/app/models/midm
MIDM_DEVICE=cpu

# Embeddings
EMBEDDINGS_PROVIDER=openai

# Server
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=production
EOF

# 보안을 위해 권한 설정
chmod 600 /var/www/langchain/.env
```

### Step 5: Systemd 서비스 생성

```bash
sudo tee /etc/systemd/system/langchain-api.service > /dev/null << 'EOF'
[Unit]
Description=LangChain FastAPI Application (CPU Mode)
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/var/www/langchain
Environment="PATH=/var/www/langchain/venv/bin"
EnvironmentFile=/var/www/langchain/.env
ExecStart=/var/www/langchain/venv/bin/uvicorn app.api_server_refactored:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10
StandardOutput=append:/var/log/langchain/access.log
StandardError=append:/var/log/langchain/error.log

[Install]
WantedBy=multi-user.target
EOF

# 서비스 활성화
sudo systemctl daemon-reload
sudo systemctl enable langchain-api.service
```

**CPU 모드 최적화:**
- `--workers 2`: CPU 코어 수에 맞게 조정 (일반적으로 `(CPU 코어 수 * 2) + 1`)
- CPU가 2코어면 `--workers 2` 또는 `--workers 1` 권장

### Step 6: Nginx 설정

```bash
sudo tee /etc/nginx/sites-available/langchain > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
EOF

# 심볼릭 링크 생성
sudo ln -sf /etc/nginx/sites-available/langchain /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Nginx 설정 테스트 및 재시작
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
```

---

## 🔄 대안 디렉토리 구조 비교

### 옵션 1: `/var/www/langchain/` (권장) ⭐

**장점:**
- ✅ Linux 표준 위치
- ✅ 웹 서버와 통합 용이
- ✅ 권한 관리 명확
- ✅ 백업 및 관리 용이

**단점:**
- ❌ 루트 권한 필요 (초기 설정 시)

### 옵션 2: `/opt/langchain/`

**장점:**
- ✅ 선택적 소프트웨어 표준 위치
- ✅ 시스템 패키지와 분리

**단점:**
- ❌ 웹 애플리케이션보다는 시스템 소프트웨어용
- ❌ `/var/www/`보다 덜 일반적

### 옵션 3: `/home/ubuntu/langchain/`

**장점:**
- ✅ 사용자 권한으로 쉽게 관리
- ✅ 개발/테스트에 적합

**단점:**
- ❌ 프로덕션 환경 비권장
- ❌ 홈 디렉토리는 사용자별로 다를 수 있음
- ❌ 보안상 덜 안전

### 옵션 4: `/srv/langchain/`

**장점:**
- ✅ 서비스별 데이터 표준 위치
- ✅ 시스템과 분리

**단점:**
- ❌ 웹 애플리케이션보다는 데이터 저장용
- ❌ 덜 일반적

---

## 💡 CPU 모드 최적화 팁

### 1. Midm 모델 사용 시 주의사항

**CPU에서 Midm 모델은 매우 느립니다:**
- 첫 응답: 30초 ~ 2분
- 이후 응답: 30초 ~ 1분
- 메모리: 4~8GB RAM 필요

**프로덕션 권장:**
- `LLM_PROVIDER=openai` 사용 (훨씬 빠름)
- Midm은 개발/테스트용으로만 사용

### 2. 의존성 최적화

**CPU 전용 PyTorch 설치:**
```bash
# GPU 버전 대신 CPU 버전 설치 (용량 절약)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

**bitsandbytes 제거 (CPU에서는 불필요):**
```bash
# requirements.txt에서 제거하거나 주석 처리
# bitsandbytes>=0.41.0  # GPU 전용, CPU에서는 불필요
```

### 3. 워커 수 조정

```bash
# CPU 코어 수 확인
nproc

# 워커 수 계산: (CPU 코어 수 * 2) + 1
# 예: 2코어 → workers=2 또는 1
# 예: 4코어 → workers=4
```

---

## 📊 디스크 공간 고려사항

### 예상 디스크 사용량

```
/var/www/langchain/
├── app/                    ~100MB (코드)
├── venv/                   ~2-3GB (Python 패키지)
├── app/models/midm/        ~4.3GB (Midm 모델, 선택사항)
└── .git/                   ~50-100MB (Git 저장소)

총 예상: ~7-8GB (Midm 포함) 또는 ~3-4GB (Midm 제외)
```

### 디스크 공간 확인

```bash
# 디스크 사용량 확인
df -h /var/www/langchain

# 디렉토리별 크기 확인
du -sh /var/www/langchain/*
```

---

## ✅ 최종 권장사항

### 배포 위치
```
/var/www/langchain/
```

### CPU 모드 설정
```env
LLM_PROVIDER=openai  # CPU에서는 OpenAI 사용
MIDM_DEVICE=cpu      # Midm 사용 시에만
```

### 프로젝트 구조
- 현재 로컬 구조 그대로 유지
- `app/` 디렉토리 구조 유지
- 상대 경로 import 그대로 사용

### 모델 파일
- Midm 모델: `/var/www/langchain/app/models/midm/` (프로젝트 내부)
- 또는 프로덕션에서는 OpenAI만 사용하여 모델 파일 불필요

---

**작성일:** 2024-12-19
**버전:** 1.0

