from typing import Dict, List, Any, Optional, Union, TypedDict
from dataclasses import dataclass
from enum import Enum

# ===== ENUMS =====
class DifficultyLevel(str, Enum):
    EASY = 'easy'
    BEGINNER = 'beginner'
    INTERMEDIATE = 'intermediate'
    ADVANCED = 'advanced'

class ProblemType(str, Enum):
    EIPL = 'eipl'
    FUNCTION_REDEFINITION = 'function_redefinition'

# ===== REQUEST/RESPONSE SCHEMAS =====
class TestCaseSchema(TypedDict):
    inputs: List[Any]
    expected_output: Any
    description: Optional[str]
    is_hidden: bool
    is_sample: bool
    order: int

class ProblemCreateSchema(TypedDict):
    title: str
    description: str
    difficulty: DifficultyLevel
    problem_type: ProblemType
    category_ids: List[int]
    function_name: str
    function_signature: str
    reference_solution: str
    hints: Optional[str]
    memory_limit: int
    tags: List[str]
    is_active: bool
    test_cases: List[TestCaseSchema]

class ProblemUpdateSchema(TypedDict, total=False):
    title: Optional[str]
    description: Optional[str]
    difficulty: Optional[DifficultyLevel]
    problem_type: Optional[ProblemType]
    category_ids: Optional[List[int]]
    function_name: Optional[str]
    function_signature: Optional[str]
    reference_solution: Optional[str]
    hints: Optional[str]
    memory_limit: Optional[int]
    tags: Optional[List[str]]
    is_active: Optional[bool]
    test_cases: Optional[List[TestCaseSchema]]

# ===== VALIDATION SCHEMAS =====
@dataclass
class ValidationError:
    field: str
    message: str
    code: str

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]

# ===== TEST EXECUTION SCHEMAS =====
@dataclass
class TestResult:
    passed: bool
    test_number: int
    inputs: List[Any]
    expected_output: Any
    actual_output: Optional[Any] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None

@dataclass
class TestExecutionResult:
    success: bool
    passed: int
    total: int
    score: float
    results: List[TestResult]
    execution_time: float
    memory_used: Optional[int] = None

# ===== AI GENERATION SCHEMAS =====
@dataclass
class AIGenerationRequest:
    description: str
    function_name: str
    function_signature: str
    reference_solution: str

@dataclass
class AIGenerationResult:
    test_cases: List[TestCaseSchema]
    generation_time: float
    model_used: str
    success: bool
    error: Optional[str] = None