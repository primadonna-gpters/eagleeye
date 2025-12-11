"""Slack message formatting utilities using Block Kit."""

from typing import Any


def create_header_block(text: str, emoji: str = ":mag:") -> dict[str, Any]:
    """Create a header block with emoji.

    Args:
        text: Header text.
        emoji: Emoji to prepend.

    Returns:
        Slack Block Kit header block.
    """
    return {
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f"{emoji} {text}",
            "emoji": True,
        },
    }


def create_section_block(text: str) -> dict[str, Any]:
    """Create a section block with mrkdwn text.

    Args:
        text: Markdown text content.

    Returns:
        Slack Block Kit section block.
    """
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": text,
        },
    }


def create_context_block(elements: list[str]) -> dict[str, Any]:
    """Create a context block for metadata.

    Args:
        elements: List of mrkdwn text elements.

    Returns:
        Slack Block Kit context block.
    """
    return {
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": el} for el in elements],
    }


def create_divider_block() -> dict[str, Any]:
    """Create a divider block.

    Returns:
        Slack Block Kit divider block.
    """
    return {"type": "divider"}


def format_search_loading(query: str) -> dict[str, Any]:
    """Format a search loading message.

    Args:
        query: User's search query.

    Returns:
        Slack message payload with blocks.
    """
    return {
        "text": f"검색 중: {query}",  # Fallback for notifications
        "blocks": [
            create_section_block(f":mag: *{query}*"),
            create_context_block(["_검색 중..._"]),
        ],
    }


# Tool name to display name mapping
TOOL_DISPLAY_NAMES: dict[str, tuple[str, str]] = {
    # (emoji, display_name)
    "slack": (":slack:", "Slack"),
    "notion": (":notion:", "Notion"),
    "linear": (":linear:", "Linear"),
    "github": (":github:", "GitHub"),
}


def format_search_progress(
    query: str,
    current_tool: str | None = None,
    completed_tools: list[str] | None = None,
    status: str = "searching",
) -> dict[str, Any]:
    """Format a search progress message for chat.update.

    Args:
        query: User's search query.
        current_tool: Currently executing tool (e.g., "slack", "notion").
        completed_tools: List of completed tool names.
        status: Current status ("thinking", "searching", "consolidating").

    Returns:
        Slack message payload with blocks.
    """
    blocks: list[dict[str, Any]] = [
        create_section_block(f":mag: *{query}*"),
    ]

    completed_tools = completed_tools or []

    # Build progress text
    progress_parts: list[str] = []

    # Show completed tools
    for tool in completed_tools:
        emoji, name = TOOL_DISPLAY_NAMES.get(tool, (":white_check_mark:", tool))
        progress_parts.append(f"{emoji} ~{name}~ :white_check_mark:")

    # Show current tool
    if current_tool:
        emoji, name = TOOL_DISPLAY_NAMES.get(
            current_tool, (":hourglass_flowing_sand:", current_tool)
        )
        progress_parts.append(f"{emoji} *{name}* 검색 중...")

    if progress_parts:
        blocks.append(create_section_block(" • ".join(progress_parts)))

    # Status message
    status_messages = {
        "thinking": "_Claude가 분석 중..._",
        "searching": "_검색 중..._",
        "consolidating": "_결과 종합 중..._",
    }
    blocks.append(create_context_block([status_messages.get(status, "_처리 중..._")]))

    return {
        "text": f"검색 중: {query}",
        "blocks": blocks,
    }


def format_search_response(text: str) -> dict[str, Any]:
    """Format Claude's search response with Block Kit.

    Args:
        text: Claude's response text (already formatted with mrkdwn).

    Returns:
        Slack message payload with blocks.
    """
    blocks: list[dict[str, Any]] = []

    lines = text.strip().split("\n")
    current_section: list[str] = []

    for line in lines:
        if line.strip() == "---":
            if current_section:
                blocks.append(create_section_block("\n".join(current_section)))
                current_section = []
            blocks.append(create_divider_block())
        else:
            current_section.append(line)

    if current_section:
        blocks.append(create_section_block("\n".join(current_section)))

    # Extract plain text summary for notifications (first 150 chars)
    plain_text = text.replace("*", "").replace("_", "").replace("`", "")[:150]

    return {"text": plain_text, "blocks": blocks}


def format_error_response(error: str) -> dict[str, Any]:
    """Format an error response.

    Args:
        error: Error message.

    Returns:
        Slack message payload with blocks.
    """
    return {
        "text": f"검색 오류: {error}",
        "blocks": [
            create_section_block(":x: *검색 중 오류가 발생했습니다*"),
            create_section_block(f"```{error}```"),
            create_context_block(["다시 시도해주세요."]),
        ],
    }


def format_help_response() -> dict[str, Any]:
    """Format the help/welcome message.

    Returns:
        Slack message payload with blocks.
    """
    return {
        "text": "EagleEye 검색 어시스턴트입니다. @EagleEye로 검색하세요.",
        "blocks": [
            create_section_block(
                ":eagle: *안녕하세요! EagleEye 검색 어시스턴트입니다.*"
            ),
            create_section_block(
                "Slack, Notion, Linear, GitHub에서 정보를 찾아드립니다."
            ),
            create_divider_block(),
            create_section_block("*사용법:*\n`@EagleEye <질문>` - 멘션으로 검색"),
            create_section_block(
                "*예시:*\n"
                "• `@EagleEye 지난주 배포 관련 논의`\n"
                "• `@EagleEye 인증 버그 이슈`\n"
                "• `@EagleEye ai-tutor 레포 최근 PR`"
            ),
        ],
    }
