"""
File Utilities

Common functions for file operations, directory management,
and safe file handling.

Author: Refactoring Assistant
"""

import os
import json
import shutil
from pathlib import Path
from typing import Any, Optional, Union
from .debug_utils import debug_print, log_error


def ensure_directory(directory: Union[str, Path]) -> Path:
    """Ensure directory exists, create if necessary.
    
    Args:
        directory (Union[str, Path]): Directory path
        
    Returns:
        Path: Path object for the directory
    """
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def safe_file_operation(operation_func, *args, operation_name: str = "file operation", **kwargs) -> Any:
    """Safely perform a file operation with error handling.
    
    Args:
        operation_func: Function to execute
        *args: Arguments for the function
        operation_name (str): Name of the operation for error logging
        **kwargs: Keyword arguments for the function
        
    Returns:
        Any: Result of the operation or None if error
    """
    try:
        return operation_func(*args, **kwargs)
    except Exception as e:
        log_error(e, f"performing {operation_name}")
        return None


def safe_json_load(file_path: Union[str, Path]) -> Optional[dict]:
    """Safely load JSON file with error handling.
    
    Args:
        file_path (Union[str, Path]): Path to JSON file
        
    Returns:
        Optional[dict]: Loaded JSON data or None if error
    """
    def load_operation():
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return safe_file_operation(load_operation, operation_name=f"loading JSON from {file_path}")


def safe_json_save(data: Any, file_path: Union[str, Path], indent: int = 2) -> bool:
    """Safely save data to JSON file with error handling.
    
    Args:
        data (Any): Data to save
        file_path (Union[str, Path]): Path to save file
        indent (int): JSON indentation level
        
    Returns:
        bool: True if successful, False otherwise
    """
    def save_operation():
        # Ensure directory exists
        ensure_directory(Path(file_path).parent)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    
    result = safe_file_operation(save_operation, operation_name=f"saving JSON to {file_path}")
    return result is not None


def backup_file(file_path: Union[str, Path], backup_suffix: str = ".backup") -> Optional[Path]:
    """Create a backup of a file.
    
    Args:
        file_path (Union[str, Path]): Path to file to backup
        backup_suffix (str): Suffix to add to backup file
        
    Returns:
        Optional[Path]: Path to backup file or None if error
    """
    file_path = Path(file_path)
    if not file_path.exists():
        debug_print(f"File does not exist for backup: {file_path}", "WARNING")
        return None
    
    backup_path = file_path.with_suffix(file_path.suffix + backup_suffix)
    
    def backup_operation():
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    return safe_file_operation(backup_operation, operation_name=f"backing up {file_path}")


def clean_filename(filename: str) -> str:
    """Clean filename by removing/replacing invalid characters.
    
    Args:
        filename (str): Original filename
        
    Returns:
        str: Cleaned filename safe for filesystem
    """
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Ensure not empty
    if not filename:
        filename = "unnamed_file"
    
    return filename


def get_unique_filename(base_path: Union[str, Path], extension: str = "") -> Path:
    """Get a unique filename by adding numbers if file exists.
    
    Args:
        base_path (Union[str, Path]): Base file path
        extension (str): File extension (optional)
        
    Returns:
        Path: Unique file path
    """
    base_path = Path(base_path)
    if extension and not extension.startswith('.'):
        extension = '.' + extension
    
    if extension:
        base_path = base_path.with_suffix(extension)
    
    if not base_path.exists():
        return base_path
    
    counter = 1
    stem = base_path.stem
    suffix = base_path.suffix
    parent = base_path.parent
    
    while True:
        new_path = parent / f"{stem}_{counter}{suffix}"
        if not new_path.exists():
            return new_path
        counter += 1