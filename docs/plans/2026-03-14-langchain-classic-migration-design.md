# LangChain Classic Migration Design

## Goal
Remove all `langchain_classic` usage and migrate to the latest LangChain APIs without changing workflow behavior.

## Recommended Approach
Use a minimal-risk migration (Option A): replace `langchain_classic` imports with current LangChain modules and keep existing execution behavior. Defer any large refactors (LCEL pipelines) to later work.

## Architecture
- Replace `langchain_classic.agents` usage with `langchain.agents`.
- Replace `langchain.tools.BaseTool` with `langchain_core.tools.BaseTool`.
- Keep tool interfaces and workflow contracts unchanged.
- Remove test shims that simulate `langchain_classic` availability.

## Data Flow
Input flow remains identical: agents are constructed with tools and prompts, executed via `AgentExecutor`, and return the same outputs. Changes are confined to the agent base setup and import paths.

## Error Handling & Compatibility
- Preserve executor settings (`max_iterations`, `return_intermediate_steps`, `handle_parsing_errors`, `agent_kwargs`).
- If upstream API changes affect return shapes, adapt at the boundary in `BaseAgent` or output parsing only.

## Testing & Verification
- Update tests to remove `langchain_classic` shims.
- Run agent orchestrator unit tests with Python 3.11 and latest LangChain installed.
- Verify full suite passes, especially workflow execution and tool agent tests.
