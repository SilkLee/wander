"""Custom output parser for handling verbose LLM output.

This module provides error handling for LLMs that produce verbose output
(like instruction-tuned models) which may include extra context after
Final Answer, causing parsing failures in strict ReAct parsers.
"""

import re
from langchain_core.exceptions import OutputParserException


def extract_final_answer_from_verbose_output(exception: OutputParserException) -> str:
    """
    Custom error handler for handle_parsing_errors.
    
    Extracts clean Final Answer from verbose LLM output that triggered parsing failure.
    Specifically handles cases where LLM adds extra context/notes after Final Answer.
    
    Args:
        exception: OutputParserException with llm_output containing the verbose response
        
    Returns:
        Cleaned observation message to send back to the agent
    """
    # Get the full LLM output that failed parsing
    llm_output = getattr(exception, 'llm_output', None) or str(exception)
    
    # Case 1: "Final Answer and parsable action" error
    # This happens when LLM includes both Final Answer and mentions "Action" in notes
    if "both a final answer and a parse-able action" in str(exception):
        # Extract everything after "Final Answer:" up to first double newline or "Note:"
        if llm_output and "Final Answer:" in llm_output:
            # Find Final Answer section
            answer_start = llm_output.find("Final Answer:")
            if answer_start != -1:
                answer_text = llm_output[answer_start + len("Final Answer:"):].strip()
                
                # Stop at common verbose markers
                stop_markers = ["\n\nNote:", "\n\nFor troubleshooting", "For troubleshooting"]
                for marker in stop_markers:
                    marker_pos = answer_text.find(marker)
                    if marker_pos != -1:
                        answer_text = answer_text[:marker_pos].strip()
                
                # If we extracted a meaningful answer, tell agent to use it
                if answer_text and len(answer_text) > 10:
                    return (
                        "The previous response contained a valid Final Answer but included "
                        "extra context that caused parsing issues. Please reformat your "
                        "response with ONLY the Final Answer section, without additional "
                        "notes or explanations after it."
                    )
    
    # Case 2: Standard parsing errors - use default behavior
    if hasattr(exception, 'send_to_llm') and exception.send_to_llm:
        return getattr(exception, 'observation', "Invalid or incomplete response")
    
    # Case 3: Unknown error - generic message
    return (
        "Output format error. Please follow the exact format:\n"
        "Thought: [your reasoning]\n"
        "Action: [tool name]\n"
        "Action Input: [tool input]\n"
        "... (or) ...\n"
        "Thought: [your reasoning]\n"
        "Final Answer: [your answer]"
    )


def create_lenient_parsing_error_handler():
    """
    Factory function to create a parsing error handler for agent initialization.
    
    This handler is more lenient with verbose LLM output, attempting to extract
    useful information from parsing failures instead of just returning generic errors.
    
    Usage:
        executor = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            handle_parsing_errors=create_lenient_parsing_error_handler(),
            ...
        )
    
    Returns:
        Callable error handler function
    """
    return extract_final_answer_from_verbose_output
