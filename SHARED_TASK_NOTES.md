# EagleEye - Shared Task Notes

## Current Status

MCP 기반으로 재구성 완료. 기존 API 클라이언트 제거하고 MCP (Model Context Protocol)를 통한 통합 검색으로 전환.

- 단위 테스트 58개 (모든 코어 모듈 커버)
- mypy strict 모드 통과
- ruff 린팅 통과

## Architecture Change (v0.2.0)

**이전 (API 방식)**:
- `slack-sdk` → Slack API 직접 호출
- `notion-client` → Notion API 직접 호출
- `httpx` → Linear GraphQL API 직접 호출

**현재 (MCP 방식)**:
- `mcp` SDK → 표준화된 MCP 서버 연결
- Slack, Notion, Linear 각각 MCP 서버로 연결
- stdio transport 사용

## Project Structure

```
src/eagleeye/
├── app.py              # 메인 Slack 봇 (MCP 기반 검색)
├── config.py           # pydantic-settings 기반 설정
├── logging.py          # structlog 설정
├── mcp/                # MCP 클라이언트 모듈 (신규)
│   ├── __init__.py
│   ├── client.py       # MCPSearchClient, MCPConnection
│   └── servers.py      # MCPServerConfig, ServerType
├── integrations/       # (기존 API 클라이언트 제거됨)
│   └── __init__.py
└── models/
    └── search.py       # 통합 SearchResult 모델

tests/
├── conftest.py         # pytest fixtures
├── test_app.py         # EagleEyeBot 테스트 (24개)
├── test_mcp.py         # MCP 클라이언트 테스트 (26개, 신규)
└── test_models.py      # SearchResult 모델 테스트 (8개)
```

## MCP Server Configuration

앱은 다음 MCP 서버들에 연결:

| 서버 | NPM 패키지 | 환경 변수 |
|------|-----------|----------|
| Slack | `@anthropic-ai/mcp-server-slack` | `SLACK_BOT_TOKEN` |
| Notion | `@notionhq/notion-mcp-server` | `NOTION_API_KEY` |
| Linear | `mcp-server-linear` | `LINEAR_API_KEY` |

MCP 서버 활성화/비활성화는 환경 변수로 제어:
- `ENABLE_SLACK_MCP=true/false`
- `ENABLE_NOTION_MCP=true/false`
- `ENABLE_LINEAR_MCP=true/false`

## Search Filter Feature

```bash
/search --slack api error          # Slack만 검색
/search --notion documentation     # Notion만 검색
/search --linear bug               # Linear만 검색
/search --slack --notion api       # Slack + Notion 검색
/search api error                  # 전체 검색 (기본값)
```

## Next Steps

1. **MCP 서버 npm 패키지 검증**
   - 각 MCP 서버 패키지가 실제로 존재하고 작동하는지 확인
   - tool name 매핑이 올바른지 확인 (`search_messages`, `notion_search`, `search_issues`)

2. **E2E 통합 테스트**
   - 실제 MCP 서버 연결 테스트
   - Node.js/npx 환경 필요

3. **에러 처리 강화**
   - MCP 서버 연결 실패 시 폴백 처리
   - 타임아웃 설정

## How to Run

```bash
# 1. 의존성 설치
pip install -e ".[dev]"

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일 편집

# 3. 봇 실행 (Node.js 필요 - MCP 서버용)
python -m eagleeye
```

## Test Commands

```bash
pytest tests/ -v                    # 모든 테스트
pytest tests/test_app.py -v         # EagleEyeBot 테스트
pytest tests/test_mcp.py -v         # MCP 클라이언트 테스트
pytest tests/test_models.py -v      # 모델 테스트
```

## Code Quality

```bash
mypy src/                           # 타입 체크
ruff check src/ tests/              # 린팅
ruff format src/ tests/             # 포맷팅
```

## Required Environment Variables

| 변수 | 설명 |
|------|------|
| `SLACK_BOT_TOKEN` | Slack Bot Token (xoxb-...) |
| `SLACK_APP_TOKEN` | Slack App Token for Socket Mode (xapp-...) |
| `SLACK_SIGNING_SECRET` | Slack Signing Secret |
| `NOTION_API_KEY` | Notion Integration Token |
| `LINEAR_API_KEY` | Linear API Key |

## Dependencies Changed

**추가됨**:
- `mcp>=1.0.0` - MCP Python SDK

**제거됨**:
- `notion-client` - (MCP 서버가 대체)
- `httpx` - (MCP 서버가 대체, Slack SDK가 내부적으로 사용)
