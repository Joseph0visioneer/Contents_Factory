# YouTube Shorts 데이터 수집기 v2

YouTube Shorts 영상의 메타데이터, 댓글, 자막, 썸네일을 자동으로 수집하는 도구입니다.

## 주요 기능

### v2 새로운 기능
- ✅ **CSV 파일 배치 처리**: 여러 URL을 한번에 처리
- ✅ **키워드 태깅**: 각 영상에 키워드 자동 부여
- ✅ **썸네일 다운로드**: 고해상도 썸네일 자동 저장
- ✅ **자막 추출**: 한국어/영어 자막 자동 추출
- ✅ **진행 상황 저장**: 중단 후 이어서 진행 가능
- ✅ **Rate Limiting**: API 할당량 안전하게 관리
- ✅ **중복 제거**: 이미 수집한 영상 자동 건너뛰기
- ✅ **오류 로깅**: 실패한 URL 자동 기록

### 기본 기능
- YouTube Shorts 영상 정보 수집
- 제목, 설명, 조회수, 좋아요, 댓글 수 등
- 댓글 내용 및 작성자 정보
- 채널 구독자 수
- Excel 및 JSON 형식으로 저장

## 설치 방법

### 1. Python 설치 확인
```bash
python3 --version
```

### 2. 필요한 라이브러리 설치
```bash
pip install -r requirements.txt
```

또는 개별 설치:
```bash
pip install google-api-python-client
pip install pandas
pip install openpyxl
pip install youtube-transcript-api
pip install requests
```

### 3. YouTube Data API 키 발급

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 새 프로젝트 생성
3. "API 및 서비스" > "라이브러리" 이동
4. "YouTube Data API v3" 검색 및 활성화
5. "사용자 인증 정보" > "API 키 만들기"
6. 생성된 API 키 복사

## 사용 방법

### CSV 파일 준비

CSV 파일 형식:
```csv
키워드,URL1,URL2,URL3,...
ai 업무 효율화,https://youtube.com/shorts/...,https://youtube.com/shorts/...
ai 프롬프트 활용,https://youtube.com/shorts/...,https://youtube.com/shorts/...
```

### 프로그램 실행

```bash
python3 youtube_collector_v2.py
```

### 실행 단계

1. **API 키 입력**: YouTube Data API 키 입력
2. **CSV 파일 선택**: 수집할 URL 목록이 담긴 CSV 파일 경로 입력
3. **자동 수집**: 프로그램이 자동으로 모든 영상 수집
4. **결과 확인**: 완료 후 생성된 파일 확인

## 출력 파일

### 1. Excel 파일 (`YouTube_Shorts_Data_YYYYMMDD_HHMMSS.xlsx`)
- **영상정보 시트**: 제목, 조회수, 좋아요 등 기본 정보
- **댓글정보 시트**: 댓글 내용 및 작성자
- **스크립트 시트**: 자막이 있는 영상의 스크립트

### 2. JSON 파일 (`YouTube_Shorts_Data_YYYYMMDD_HHMMSS.json`)
- 백업용 원본 데이터

### 3. 썸네일 폴더 (`thumbnails/`)
- 각 영상의 썸네일 이미지 (`{영상ID}.jpg`)

### 4. 진행 상황 파일 (`progress.json`)
- 수집 진행 상황 자동 저장
- 중단 후 이어서 진행 가능

### 5. 실패 목록 (`Failed_URLs_YYYYMMDD_HHMMSS.json`)
- 수집 실패한 URL 목록

### 6. 로그 파일 (`youtube_collector.log`)
- 전체 실행 로그

## 주의사항

### API 할당량
- **무료 할당량**: 하루 10,000 units
- **영상 1개당 소모**: 약 3 units
- **하루 최대 수집 가능**: 약 3,000개 영상

### Rate Limiting
- API 호출 사이에 0.5초 대기
- 너무 빠른 요청 시 차단될 수 있음

### 자막
- 자막이 있는 영상만 스크립트 추출
- 한국어 > 자동생성 한국어 > 영어 순으로 시도
- 자막 없으면 빈 값으로 저장

## 문제 해결

### "API 키 오류"
- API 키가 올바른지 확인
- YouTube Data API v3가 활성화되어 있는지 확인
- 할당량이 남아있는지 확인

### "CSV 파일 읽기 오류"
- 파일 경로가 올바른지 확인
- CSV 파일이 UTF-8 인코딩인지 확인
- 첫 행에 키워드가 있는지 확인

### "자막 추출 실패"
- 일부 영상은 자막이 없을 수 있음 (정상)
- 자막이 비활성화된 영상도 있음

## 버전 히스토리

### v2 (2025-01-XX)
- CSV 배치 처리 추가
- 키워드 태깅 기능
- 썸네일 다운로드
- 자막 추출
- 진행 상황 저장/재개
- Rate Limiting
- 중복 제거
- 통계 출력

### v1
- 기본 데이터 수집 기능
- 수동 URL 입력

## 라이선스

MIT License

## 문의

이슈 또는 개선 제안은 GitHub Issues에 등록해주세요.