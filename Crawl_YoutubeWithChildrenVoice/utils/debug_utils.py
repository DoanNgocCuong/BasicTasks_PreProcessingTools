"""
Debug Utilities

Centralized debug printing functionality with consistent formatting
and level-based output control.

Author: Refactoring Assistant
"""


def debug_print(message: str, level: str = "DEBUG"):
    """Centralized debug printing with consistent formatting.
    
    Args:
        message (str): Message to print
        level (str): Debug level (DEBUG, SUCCESS, ERROR, WARNING, INFO, PROCESS)
    """
    emoji_map = {
        "DEBUG": "🔧",
        "SUCCESS": "✅", 
        "ERROR": "❌",
        "WARNING": "⚠️",
        "INFO": "📋",
        "PROCESS": "🎯"
    }
    emoji = emoji_map.get(level, "📝")
    print(f"{emoji} [DEBUG] {message}")


def log_operation(operation: str, details: str = None):
    """Log an operation with optional details.
    
    Args:
        operation (str): The operation being performed
        details (str, optional): Additional details about the operation
    """
    if details:
        debug_print(f"{operation}: {details}", "INFO")
    else:
        debug_print(operation, "INFO")


def log_error(error: Exception, context: str = None):
    """Log an error with optional context.
    
    Args:
        error (Exception): The error that occurred
        context (str, optional): Context about where the error occurred
    """
    if context:
        debug_print(f"Error in {context}: {error}", "ERROR")
    else:
        debug_print(f"Error: {error}", "ERROR")