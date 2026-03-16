import asyncio

from app.agents.review_roles import diff_parser, risk_analyst, reviewer, summarizer


def test_review_roles_execute():
    async def run():
        parsed = await diff_parser({"diff": "diff --git a/x b/x"})
        report = await risk_analyst(parsed)
        comments = await reviewer(parsed)
        summary = await summarizer({"report": report, "comments": comments})
        return report, comments, summary

    report, comments, summary = asyncio.run(run())
    assert report.risk_level
    assert comments
    assert summary["analysis"]
