from enum import Enum, auto
import os

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

# Define path to game_data relative to this file's location
# __file__ gives the path to common.py
# os.path.dirname gives the directory containing common.py (puzzle/)
# os.path.join with ".." goes up one level (to alchemist_cipher/)
# os.path.join again adds "game_data"
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "game_data"))

# Validate DATA_DIR exists
if not os.path.isdir(DATA_DIR):
    # Try an alternative relative path assuming script run from project root
    alt_data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", "alchemist_cipher-V2/game_data"))
    if os.path.isdir(alt_data_dir):
        DATA_DIR = alt_data_dir
    else:
        # Or compute based on current working directory as a last resort
        cwd_data_dir = os.path.abspath(os.path.join(os.getcwd(), "alchemist_cipher-V2/game_data"))
        if os.path.isdir(cwd_data_dir):
             DATA_DIR = cwd_data_dir
        else:
            raise FileNotFoundError(f"Could not reliably locate the game_data directory. Looked in: {DATA_DIR}, {alt_data_dir}, {cwd_data_dir}")