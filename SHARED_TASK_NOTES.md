# EagleEye - Shared Task Notes

## Current Status

MVP 구현 완료. structlog 로깅 추가됨 (print() → structlog 교체).

## Project Structure

```
src/eagleeye/
├── app.py              # 메인 Slack 봇 (slash command + mention 핸들러)
├── config.py           # pydantic-settings 기반 설정
├── logging.py          # structlog 설정 (NEW)
├── integrations/
│   ├── slack_search.py # Slack 메시지 검색
│   ├── notion.py       # Notion 페이지 검색
│   └── linear.py       # Linear 이슈 검색 (GraphQL)
└── models/
    └── search.py       # 통합 SearchResult 모델
```

## Next Steps (우선순위 순)

1. **테스트 작성**
   - 각 integration client 단위 테스트
   - mock 응답으로 테스트

2. **Slack App 설정 가이드 작성** (선택)
   - Socket Mode 활성화 방법
   - 필요한 OAuth scopes 목록
   - Slash command 등록 방법

3. **기능 확장** (선택)
   - 검색 필터 옵션 (`/search --slack query`, `/search --notion query`)
   - 결과 캐싱

## How to Run

```bash
# 1. 의존성 설치
pip install -e ".[dev]"

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일 편집하여 API 키 입력

# 3. 봇 실행
python -m eagleeye

# Production 모드 (JSON 로그 출력)
ENVIRONMENT=production python -m eagleeye
```

## Code Quality

```bash
# 타입 체크
mypy src/

# Linting + 포맷
ruff check --fix src/
ruff format src/
```

## Required Slack App Permissions

Bot Token Scopes:
- `commands` - slash command 사용
- `chat:write` - 메시지 전송
- `search:read` - 메시지 검색
- `app_mentions:read` - @mention 수신

App-Level Token:
- `connections:write` - Socket Mode 연결

## API Keys Needed

| Service | Where to get |
|---------|-------------|
| Slack Bot Token | https://api.slack.com/apps → OAuth & Permissions |
| Slack App Token | https://api.slack.com/apps → Basic Information → App-Level Tokens |
| Notion API Key | https://www.notion.so/my-integrations |
| Linear API Key | https://linear.app/settings/api |
