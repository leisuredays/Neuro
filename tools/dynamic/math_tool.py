"""
Math Tool - Dynamic tool for mathematical calculations
Based on AIAvatarKit math_tool implementation
"""
import logging
import math
import re
from typing import Dict, Any
from ..base.tool_base import BaseTool, ToolMetadata, ToolType

logger = logging.getLogger(__name__)

class MathTool(BaseTool):
    """Tool for performing mathematical calculations"""
    
    def __init__(self):
        metadata = ToolMetadata(
            name="calculate_math",
            type=ToolType.DYNAMIC,
            description="Perform mathematical calculations and solve equations",
            version="1.0.0"
        )
        super().__init__(metadata)
    
    async def execute(self, expression: str) -> Dict[str, Any]:
        """Calculate mathematical expression safely"""
        try:
            # Clean and validate expression
            cleaned_expr = self._clean_expression(expression)
            
            if not self._is_safe_expression(cleaned_expr):
                return {
                    "status": "error",
                    "error": "Expression contains unsafe operations",
                    "expression": expression
                }
            
            # Evaluate expression safely
            # Allow basic math functions
            allowed_names = {
                "abs": abs, "round": round, "min": min, "max": max,
                "sum": sum, "pow": pow, "sqrt": math.sqrt,
                "sin": math.sin, "cos": math.cos, "tan": math.tan,
                "log": math.log, "log10": math.log10,
                "pi": math.pi, "e": math.e
            }
            
            result = eval(cleaned_expr, {"__builtins__": {}}, allowed_names)
            
            return {
                "status": "success",
                "result": result,
                "expression": expression,
                "cleaned_expression": cleaned_expr
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "expression": expression
            }
    
    def _clean_expression(self, expression: str) -> str:
        """Clean mathematical expression"""
        # Remove common prefixes
        expression = expression.strip()
        if expression.lower().startswith("calculate"):
            expression = expression[9:].strip()
        if expression.startswith("="):
            expression = expression[1:].strip()
        
        # Replace common symbols
        expression = expression.replace("×", "*").replace("÷", "/")
        expression = expression.replace("^", "**")  # Power operator
        
        return expression
    
    def _is_safe_expression(self, expression: str) -> bool:
        """Check if expression is safe to evaluate"""
        # Block dangerous keywords
        dangerous_keywords = [
            "import", "exec", "eval", "open", "file", "input", "raw_input",
            "__", "getattr", "setattr", "delattr", "globals", "locals",
            "vars", "dir", "help", "reload", "compile"
        ]
        
        expression_lower = expression.lower()
        for keyword in dangerous_keywords:
            if keyword in expression_lower:
                return False
        
        # Only allow specific characters
        allowed_chars = set("0123456789+-*/().= abcdefghijklmnopqrstuvwxyz,")
        if not all(c.lower() in allowed_chars for c in expression):
            return False
        
        return True
    
    def get_spec(self) -> Dict[str, Any]:
        """Get OpenAI function calling specification"""
        return {
            "name": "calculate_math",
            "description": "Perform mathematical calculations, solve equations, and evaluate expressions",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate (e.g., '2+2', 'sqrt(16)', 'sin(pi/2)')"
                    }
                },
                "required": ["expression"]
            }
        }