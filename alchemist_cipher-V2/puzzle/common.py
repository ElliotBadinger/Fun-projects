from enum import Enum, auto
import os
# Removed logging import if no longer needed here
# from utils import resource_path # Removed import

# Removed logger setup if no longer needed here

class ClueType(Enum):
    DIRECT = auto()
    EXCLUSION = auto()
    POSITIONAL = auto()
    RELATIONAL = auto()
    CATEGORY = auto()
    LOGICAL = auto()

class HumanScenarioType(Enum):
    LOGIC_GRID = auto()
    SCHEDULING = auto()
    RELATIONSHIP_MAP = auto()
    ORDERING = auto()
    SOCIAL_DEDUCTION = auto()
    COMMON_SENSE_GAP = auto()
    DILEMMA = auto()
    AGENT_SIMULATION = auto()

# --- Constants ---
LETTERS_POOL = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
VOWELS = "AEIOU"
CONSONANTS = "".join(c for c in LETTERS_POOL if c not in VOWELS)
SYMBOLS_POOL = ["α", "β", "γ", "δ", "ε", "ζ", "η", "θ", "ι", "κ", "λ", "μ", "ν", "ξ", "ο", "π", "ρ", "σ", "τ", "υ", "φ", "χ", "ψ", "ω"]

LOGIC_GRID_YES = '✔️'
LOGIC_GRID_NO = '❌'
LOGIC_GRID_UNKNOWN = '?'

# --- DATA_DIR definition removed ---