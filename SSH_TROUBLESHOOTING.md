# SSH 연결 문제 해결 가이드

## 🔴 "Connection closed by [IP] port 22" 에러

### 증상
```
Connection closed by 43.201.106.146 port 22
```

### 가능한 원인 및 해결 방법

#### 1. Security Group 설정 확인 (가장 흔한 원인)
**AWS 콘솔에서 확인:**
1. EC2 Dashboard → Instances → 해당 인스턴스 선택
2. Security 탭 → Security groups 클릭
3. Inbound rules 확인:
   - Type: SSH
   - Protocol: TCP
   - Port: 22
   - Source: `0.0.0.0/0` (또는 특정 IP)

**해결:**
- SSH 규칙이 없으면 추가
- Source를 `0.0.0.0/0`으로 설정 (SSH 키로 보안 유지)

#### 2. EC2 인스턴스 상태 확인
**AWS 콘솔에서:**
- 인스턴스 상태가 "running"인지 확인
- 상태가 "stopped"면 시작
- 상태가 "pending"이면 대기

#### 3. SSH 키 파일 권한 (Windows)
PowerShell에서:
```powershell
# 키 파일이 현재 디렉토리에 있는지 확인
ls kang.pem

# 키 파일 경로를 절대 경로로 지정
ssh -i "C:\Users\hi\Documents\hatchery.kr\langchain\kang.pem" ubuntu@ec2-43-201-106-146.ap-northeast-2.compute.amazonaws.com
```

#### 4. 상세 디버깅
```powershell
# 상세 로그로 연결 시도
ssh -v -i "kang.pem" ubuntu@ec2-43-201-106-146.ap-northeast-2.compute.amazonaws.com

# 더 상세한 로그
ssh -vv -i "kang.pem" ubuntu@ec2-43-201-106-146.ap-northeast-2.compute.amazonaws.com
```

#### 5. 네트워크 연결 테스트
```powershell
# 호스트 연결 확인
Test-NetConnection -ComputerName ec2-43-201-106-146.ap-northeast-2.compute.amazonaws.com -Port 22

# 또는 ping 테스트
ping ec2-43-201-106-146.ap-northeast-2.compute.amazonaws.com
```

#### 6. EC2 인스턴스 재시작
**AWS 콘솔에서:**
1. EC2 Dashboard → Instances
2. 인스턴스 선택 → Instance state → Reboot
3. 재시작 후 1-2분 대기 후 다시 시도

#### 7. SSH 서비스 확인 (EC2에 접속 가능한 경우)
```bash
# SSH 서비스 상태 확인
sudo systemctl status ssh

# SSH 서비스 재시작
sudo systemctl restart ssh
```

## ✅ 연결 성공 확인

연결이 성공하면 다음 메시지가 표시됩니다:
```
Welcome to Ubuntu 24.04.3 LTS
```

## 🔧 빠른 체크리스트

- [ ] Security Group에 SSH (포트 22) 규칙이 있는가?
- [ ] EC2 인스턴스 상태가 "running"인가?
- [ ] SSH 키 파일 경로가 정확한가?
- [ ] 네트워크 연결이 정상인가? (ping 테스트)
- [ ] 이전에 연결이 성공했던 적이 있는가? (일시적 문제일 수 있음)

## 📝 참고

- Windows에서 PEM 파일 권한 문제는 드뭅니다
- "Connection closed"는 보통 Security Group 또는 인스턴스 상태 문제입니다
- 연결이 한 번 성공하면 키와 설정은 정상입니다

