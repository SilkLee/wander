from app.workflows.langgraph_flow import run_langgraph


_TEST_PAYLOAD = {
    "log_content": (
        "ERROR: Connection timeout at database.py:142\n"
        "Traceback (most recent call last):\n"
        "  File \"database.py\", line 142, in connect\n"
        "    conn = psycopg2.connect(host=DB_HOST, port=5432, timeout=30)\n"
        "psycopg2.OperationalError: timeout expired (30 seconds)\n"
        "Could not establish connection to PostgreSQL database at 10.0.1.50:5432"
    ),
    "log_type": "application",
}


class TestEndToEndLanggraph:
    async def test_end_to_end_with_payload(self):
        result = await run_langgraph(_TEST_PAYLOAD)

        assert result["diagnosis"].root_cause_candidates
