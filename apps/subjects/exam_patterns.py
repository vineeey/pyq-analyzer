"""
Default exam patterns for different university schemes.
"""

# KTU (Kerala Technological University) Standard Pattern
KTU_STANDARD_PATTERN = {
    "name": "KTU Standard Pattern",
    "description": "Standard KTU exam pattern for engineering subjects",
    "part_a": {
        "marks_per_question": 3,
        "questions": {
            "1": 1, "2": 1,  # Q1-Q2 → Module 1
            "3": 2, "4": 2,  # Q3-Q4 → Module 2
            "5": 3, "6": 3,  # Q5-Q6 → Module 3
            "7": 4, "8": 4,  # Q7-Q8 → Module 4
            "9": 5, "10": 5  # Q9-Q10 → Module 5
        }
    },
    "part_b": {
        "marks_per_question": 14,
        "questions": {
            "11": 1, "12": 1,  # Q11-Q12 → Module 1
            "13": 2, "14": 2,  # Q13-Q14 → Module 2
            "15": 3, "16": 3,  # Q15-Q16 → Module 3
            "17": 4, "18": 4,  # Q17-Q18 → Module 4
            "19": 5, "20": 5   # Q19-Q20 → Module 5
        }
    }
}

# Generic 5-module pattern
GENERIC_5_MODULE_PATTERN = {
    "name": "Generic 5 Module Pattern",
    "description": "Generic pattern for subjects with 5 modules",
    "part_a": {
        "marks_per_question": 3,
        "questions": {
            str(i): ((i-1) // 2) + 1 for i in range(1, 11)
        }
    },
    "part_b": {
        "marks_per_question": 14,
        "questions": {
            str(i): ((i-11) // 2) + 1 for i in range(11, 21)
        }
    }
}

# Generic 6-module pattern
GENERIC_6_MODULE_PATTERN = {
    "name": "Generic 6 Module Pattern",
    "description": "Generic pattern for subjects with 6 modules",
    "part_a": {
        "marks_per_question": 2,
        "questions": {
            str(i): ((i-1) // 2) + 1 for i in range(1, 13)
        }
    },
    "part_b": {
        "marks_per_question": 12,
        "questions": {
            str(i): ((i-13) // 2) + 1 for i in range(13, 25)
        }
    }
}


def get_pattern_by_name(name: str) -> dict:
    """Get exam pattern by name."""
    patterns = {
        "ktu_standard": KTU_STANDARD_PATTERN,
        "generic_5_module": GENERIC_5_MODULE_PATTERN,
        "generic_6_module": GENERIC_6_MODULE_PATTERN,
    }
    return patterns.get(name, KTU_STANDARD_PATTERN)


def get_module_from_question(question_number: str, part: str, pattern: dict) -> int:
    """
    Get module number from question number and part using pattern.
    
    Args:
        question_number: Question number (e.g., "1", "11a", "15b")
        part: Part letter ("A" or "B")
        pattern: Exam pattern dictionary
        
    Returns:
        Module number or None if not found
    """
    # Extract numeric part from question number
    import re
    match = re.match(r'(\d+)', str(question_number))
    if not match:
        return None
    
    q_num = match.group(1)
    part_key = f"part_{part.lower()}"
    
    if part_key not in pattern:
        return None
    
    questions_map = pattern[part_key].get("questions", {})
    return questions_map.get(q_num)


def create_custom_pattern(num_modules: int, part_a_questions: int = 10, part_b_questions: int = 10) -> dict:
    """
    Create a custom exam pattern.
    
    Args:
        num_modules: Number of modules
        part_a_questions: Total questions in Part A
        part_b_questions: Total questions in Part B
        
    Returns:
        Pattern dictionary
    """
    # Distribute questions evenly across modules
    a_per_module = part_a_questions // num_modules
    b_per_module = part_b_questions // num_modules
    
    pattern = {
        "name": f"Custom {num_modules} Module Pattern",
        "description": f"Custom pattern for {num_modules} modules",
        "part_a": {
            "marks_per_question": 3,
            "questions": {}
        },
        "part_b": {
            "marks_per_question": 14,
            "questions": {}
        }
    }
    
    # Part A mapping
    for i in range(1, part_a_questions + 1):
        module = min(((i - 1) // a_per_module) + 1, num_modules)
        pattern["part_a"]["questions"][str(i)] = module
    
    # Part B mapping
    for i in range(1, part_b_questions + 1):
        q_num = part_a_questions + i
        module = min(((i - 1) // b_per_module) + 1, num_modules)
        pattern["part_b"]["questions"][str(q_num)] = module
    
    return pattern
