# CLAUDE.md - EagleEye Development Guide

## Project Overview

EagleEye는 Claude Agent SDK와 MCP(Model Context Protocol)를 사용하여 Slack, Notion, Linear, GitHub를 통합 검색하는 AI 기반 Slack 봇입니다.

## Quick Start

```bash
# 의존성 설치
uv sync

# 환경 변수 설정
cp .env.example .env
# .env 파일에 API 키 입력

# 실행
uv run python -m src

# 디버그 모드 실행
DEBUG=true uv run python -m src

# 테스트 실행
uv run pytest tests/ -v
```

## Architecture

```
src/
├── __main__.py         # 진입점
├── app.py              # EagleEyeBot 클래스 (Slack Bolt)
├── claude_agent.py     # ClaudeSearchAgent (Claude Agent SDK)
├── config.py           # Settings (pydantic-settings)
├── log_config.py       # structlog 설정
├── slack_formatter.py  # Block Kit 포맷터
└── models/
    └── search.py       # SearchResult, SearchResultType
```

## Key Components

### 1. EagleEyeBot (`app.py`)
Slack Bolt 기반 봇 애플리케이션
- `@EagleEye` 멘션 처리
- Socket Mode로 실시간 연결
- 실시간 진행 상태 업데이트 (chat.update)

### 2. ClaudeSearchAgent (`claude_agent.py`)
Claude Agent SDK를 사용한 검색 에이전트
- MCP 서버 자동 관리 (npx로 실행)
- 자연어 쿼리 → 도구 호출 → 결과 종합
- 시스템 프롬프트에 Slack mrkdwn 포맷 지침 포함

### 3. Slack Formatter (`slack_formatter.py`)
Slack Block Kit 메시지 포맷터
- `format_search_loading()` - 검색 중 표시
- `format_search_response()` - 검색 결과
- `format_error_response()` - 에러 메시지
- `format_help_response()` - 도움말

## MCP Servers

| 서버 | 패키지 | 용도 |
|-----|--------|------|
| Slack | `@modelcontextprotocol/server-slack` | 채널/메시지 검색 |
| Notion | `@notionhq/notion-mcp-server` | 페이지/문서 검색 |
| Linear | `@tacticlaunch/mcp-linear` | 이슈/프로젝트 검색 |
| GitHub | `@modelcontextprotocol/server-github` | 코드/이슈/PR 검색 |

## Coding Standards

### Python Style
- Python 3.12+ 타입 힌트 사용
- MyPy strict 모드 준수
- Ruff 포맷터/린터 사용 (88자 라인 길이)

### 로깅 규칙
```python
from log_config import get_logger
logger = get_logger(__name__)

# 구조화된 로깅
logger.info("event_name", key="value", elapsed_ms=123.45)
logger.debug("debug_event", data={"nested": "value"})
logger.error("error_event", error=str(e), context="additional info")
```

### 타입 힌트
```python
# 좋은 예
def search(self, query: str) -> str:
    results: list[SearchResult] = []

# 피해야 할 것
def search(self, query):  # 타입 없음
    results = []  # Any 타입
```

## Environment Variables

필수:
- `SLACK_BOT_TOKEN` - Slack 봇 토큰
- `SLACK_APP_TOKEN` - Socket Mode 앱 토큰
- `SLACK_SIGNING_SECRET` - 서명 시크릿
- `SLACK_TEAM_ID` - 워크스페이스 ID
- `NOTION_API_KEY` - Notion API 키
- `LINEAR_API_KEY` - Linear API 키

선택:
- `GITHUB_TOKEN` - GitHub Personal Access Token (코드/이슈/PR 검색)
- `CLAUDE_MODEL` - Claude 모델 (기본: claude-sonnet-4-20250514)
- `DEBUG` - 디버그 로깅 활성화
- `ENABLE_SLACK_MCP` / `ENABLE_NOTION_MCP` / `ENABLE_LINEAR_MCP` / `ENABLE_GITHUB_MCP` - MCP 서버 활성화

## Testing

```bash
# 전체 테스트
uv run pytest tests/ -v

# 특정 테스트
uv run pytest tests/test_app.py -v

# 커버리지
uv run pytest tests/ --cov=src --cov-report=term-missing
```

## Debugging

### 성능 디버깅
`DEBUG=true`로 실행하면 상세 타이밍 로그 출력:
- `first_message_received` - 첫 응답까지 시간
- `tool_use_requested` - 도구 호출 시점
- `tool_result_received` - 도구 결과 수신 시점
- `claude_search_completed` - 전체 검색 시간

### 일반적인 문제
1. **MCP 서버 시작 느림**: npx 첫 실행 시 패키지 다운로드
2. **타임아웃**: Claude API 응답 대기 또는 MCP 도구 실행 지연
3. **인증 오류**: `.env` 파일의 API 키 확인

## Common Tasks

### 새 MCP 서버 추가
1. `claude_agent.py`의 `create_mcp_server_configs()` 수정
2. `_build_allowed_tools()` 에 도구 목록 추가
3. `config.py`에 설정 추가

### Slack 메시지 포맷 수정
`slack_formatter.py` 수정 후 `tests/test_slack_formatter.py` 테스트

### 시스템 프롬프트 수정
`claude_agent.py`의 `SYSTEM_PROMPT` 상수 수정

## Deployment

### Docker (권장)

가장 쉬운 배포 방법입니다. Python, Node.js, Claude CLI가 모두 포함됩니다.

```bash
# 1. Claude CLI 인증 (로컬에서 한 번만)
claude login

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일에 API 키 입력

# 3. Docker 빌드 및 실행
docker compose up -d

# 로그 확인
docker compose logs -f
```

### 수동 배포 (서버 직접 설치)

```bash
# 1. 필수 도구 설치
# - Python 3.12+
# - Node.js 20+ (npx 포함)
# - uv (Python 패키지 매니저)

# 2. Claude CLI 설치 및 인증
npm install -g @anthropic-ai/claude-code
claude login

# 3. 프로젝트 설정
git clone <repo-url>
cd eagleeye
uv sync
cp .env.example .env
# .env 파일에 API 키 입력

# 4. 실행 (systemd 서비스로 등록 권장)
uv run python -m src
```

### 환경 변수 체크리스트

배포 전 `.env` 파일에 다음 값들이 설정되어 있는지 확인:

- [ ] `SLACK_BOT_TOKEN` - Slack 봇 토큰
- [ ] `SLACK_APP_TOKEN` - Socket Mode 앱 토큰
- [ ] `SLACK_SIGNING_SECRET` - 서명 시크릿
- [ ] `SLACK_TEAM_ID` - 워크스페이스 ID
- [ ] `NOTION_API_KEY` - Notion API 키
- [ ] `LINEAR_API_KEY` - Linear API 키
- [ ] `GITHUB_TOKEN` - GitHub Personal Access Token (선택)
- [ ] `GITHUB_ORG` - GitHub 조직명 (선택, 검색 범위 제한)
