"""Infrastructure layer adapters for external dependencies.

This layer implements the application ports (interfaces) from application/ports.py,
providing concrete implementations for agents, parsers, repositories, and LLM services.

Adapters in this layer:
- Wrap existing application logic (agents, analyzers)
- Adapt external libraries (LangChain) to match domain ports
- Handle technical concerns (persistence, LLM selection)
- Maintain separation between domain and external dependencies
"""
