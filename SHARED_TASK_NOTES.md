# EagleEye - Shared Task Notes

## Current Status

MVP 구현 완료. 단위 테스트 32개 추가됨 (모든 integration client + models 커버).

## Project Structure

```
src/eagleeye/
├── app.py              # 메인 Slack 봇 (slash command + mention 핸들러)
├── config.py           # pydantic-settings 기반 설정
├── logging.py          # structlog 설정
├── integrations/
│   ├── slack_search.py # Slack 메시지 검색
│   ├── notion.py       # Notion 페이지 검색
│   └── linear.py       # Linear 이슈 검색 (GraphQL)
└── models/
    └── search.py       # 통합 SearchResult 모델

tests/
├── conftest.py         # pytest fixtures (mock responses)
├── test_slack_search.py # SlackSearchClient 테스트 (5개)
├── test_notion.py      # NotionSearchClient 테스트 (11개)
├── test_linear.py      # LinearClient 테스트 (8개)
└── test_models.py      # SearchResult 모델 테스트 (8개)
```

## Next Steps (우선순위 순)

1. **app.py 테스트 작성** (선택)
   - Slack 봇 핸들러 통합 테스트
   - slash command, mention 핸들러 테스트

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

## Test Commands

```bash
# 모든 테스트 실행
pytest tests/ -v

# 특정 모듈 테스트
pytest tests/test_slack_search.py -v
pytest tests/test_notion.py -v
pytest tests/test_linear.py -v
pytest tests/test_models.py -v
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
