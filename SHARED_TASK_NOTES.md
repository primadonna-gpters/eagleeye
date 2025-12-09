# EagleEye - Shared Task Notes

## Current Status

MCP 기반으로 재구성 완료. 올바른 npm 패키지명과 tool name으로 검증됨.

- 단위 테스트 65개 (모든 코어 모듈 커버)
- mypy strict 모드 통과
- ruff 린팅 통과

## MCP Server Configuration (검증됨)

| 서버 | NPM 패키지 | Tool Name | 환경 변수 |
|------|-----------|-----------|----------|
| Slack | `@modelcontextprotocol/server-slack` | `slack_get_channel_history`* | `SLACK_BOT_TOKEN`, `SLACK_TEAM_ID` |
| Notion | `@notionhq/notion-mcp-server` | `notion_search` | `NOTION_TOKEN` |
| Linear | `linear-mcp-server` | `linear_search_issues` | `LINEAR_API_KEY` |

\* Slack MCP 서버에는 검색 도구가 없음. `slack_list_channels` + `slack_get_channel_history` 조합 후 클라이언트 필터링으로 구현.

## Slack 검색 구현 방식

공식 `@modelcontextprotocol/server-slack`에는 `search_messages` 도구가 없음:
1. `slack_list_channels`로 채널 목록 조회
2. 각 채널에서 `slack_get_channel_history`로 최근 메시지 조회
3. 클라이언트에서 쿼리 문자열로 필터링

제한사항:
- 최근 메시지만 검색 가능 (전체 검색 불가)
- 채널 5개, 메시지 20개씩 조회 후 필터링

## Next Steps

1. **E2E 통합 테스트**
   - 실제 MCP 서버 연결 테스트
   - Node.js/npx 환경 필요
   - `.env` 설정 후 `python -m eagleeye` 실행

2. **Slack 검색 개선 옵션**
   - 커뮤니티 MCP 서버 (`slack-mcp-server`) 사용 고려 - 실제 검색 API 지원
   - 또는 Slack SDK 직접 사용 fallback 구현

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

## Required Environment Variables

| 변수 | 설명 |
|------|------|
| `SLACK_BOT_TOKEN` | Slack Bot Token (xoxb-...) |
| `SLACK_APP_TOKEN` | Slack App Token for Socket Mode (xapp-...) |
| `SLACK_SIGNING_SECRET` | Slack Signing Secret |
| `NOTION_TOKEN` | Notion Integration Token |
| `LINEAR_API_KEY` | Linear API Key |

## Test Commands

```bash
pytest tests/ -v                    # 모든 테스트 (65개)
mypy src/                           # 타입 체크
ruff check src/ tests/              # 린팅
```
