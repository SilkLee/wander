"""Dependency injection container for FastAPI application.

Provides singleton instances of application components via FastAPI Depends() pattern.
All dependencies are created once and reused across requests for efficiency.

Usage in endpoints:
    @router.post("/analyze")
    async def analyze(use_case: AnalyzeLogUseCase = Depends(get_analyze_log_use_case)):
        result = await use_case.execute(...)
"""

from functools import lru_cache
from typing import TYPE_CHECKING

from fastapi import Depends

from app.application.ports import AgentPort, ParserPort, RepositoryPort
from app.application.use_cases.analyze_log import AnalyzeLogUseCase
from app.infrastructure.agents.langchain_agent_adapter import LangChainAgentAdapter
from app.infrastructure.parsers.output_parser_adapter import OutputParserAdapter
from app.infrastructure.repositories.memory_analysis_repo import MemoryAnalysisRepository
from app.infrastructure.events import EventBus, MemoryEventBus

if TYPE_CHECKING:
    pass


@lru_cache(maxsize=1)
def get_agent() -> AgentPort:
    """Get singleton AgentPort implementation (LangChainAgentAdapter).
    
    This function creates the agent adapter on first call and caches it.
    All subsequent calls return the same instance.
    
    Returns:
        AgentPort: Implementation of agent interface for log analysis
        
    Raises:
        RuntimeError: If agent initialization fails
    """
    return LangChainAgentAdapter()


@lru_cache(maxsize=1)
def get_parser() -> ParserPort:
    """Get singleton ParserPort implementation (OutputParserAdapter).
    
    This function creates the output parser on first call and caches it.
    All subsequent calls return the same instance.
    
    Returns:
        ParserPort: Implementation of parser interface for result parsing
    """
    return OutputParserAdapter()


@lru_cache(maxsize=1)
def get_repository() -> RepositoryPort:
    """Get singleton RepositoryPort implementation (MemoryAnalysisRepository).
    
    This function creates the analysis repository on first call and caches it.
    All subsequent calls return the same instance.
    
    Note: Uses in-memory storage. For production, replace with database adapter.
    
    Returns:
        RepositoryPort: Implementation of repository interface for persistence
    """
    return MemoryAnalysisRepository()


@lru_cache(maxsize=1)
def get_event_bus() -> EventBus:
    """Get singleton EventBus implementation (MemoryEventBus).
    
    This function creates the event bus on first call and caches it.
    All subsequent calls return the same instance.
    
    Returns:
        EventBus: Implementation of event bus interface for event publishing
    """
    return MemoryEventBus()

def get_analyze_log_use_case(
    agent: AgentPort = Depends(get_agent),
    parser: ParserPort = Depends(get_parser),
    repository: RepositoryPort = Depends(get_repository),
    event_bus: EventBus = Depends(get_event_bus),
) -> AnalyzeLogUseCase:
    """Get AnalyzeLogUseCase with all dependencies injected.
    
    FastAPI automatically resolves the dependencies (agent, parser, repository, event_bus)
    by calling their respective get_* functions and caching results.
    This function then assembles them into the use case.
    
    Args:
        agent: AgentPort instance from get_agent()
        parser: ParserPort instance from get_parser()
        repository: RepositoryPort instance from get_repository()
        event_bus: EventBus instance from get_event_bus()
        
    Returns:
        AnalyzeLogUseCase: Fully initialized use case ready for execution
    """
    return AnalyzeLogUseCase(
        agent=agent,
        parser=parser,
        repository=repository,
        event_bus=event_bus,
    )
