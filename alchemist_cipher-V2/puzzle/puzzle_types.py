from typing import Dict, List, Tuple, Optional, Any, Union, Set
import random
import logging

# Import Enums from common.py
from puzzle.common import ClueType, HumanScenarioType, VOWELS

class Puzzle:
    """Represents a single Symbol Cipher puzzle with educational elements."""
    def __init__(self, level: int, symbols: List[str], letters: List[str],
                 solution_mapping: Dict[str, str], clues: List[Tuple[str, ClueType]],
                 is_verified: bool = False):
        self.level = level
        self.symbols = symbols
        self.letters = letters
        self.solution_mapping = solution_mapping
        self.clues = clues # List of (clue_text, ClueType)
        self.num_elements = len(symbols)
        self.clue_types_used = {clue_type for _, clue_type in clues}
        self.is_verified = is_verified
        self.is_scenario = False # Flag to differentiate

        # Basic validation
        if self.num_elements != len(letters) or self.num_elements != len(solution_mapping):
             logging.error(f"Symbol Cipher Initialization Error: Counts mismatch symbols({len(symbols)}) vs letters({len(letters)}) vs solution({len(solution_mapping)})")
             # Consider raising an error or handling invalid state

    def check_solution(self, user_mapping: Dict[str, str]) -> bool:
        """Checks if the user's mapping matches the solution."""
        # Check if all symbols are present in the user mapping
        if len(user_mapping) != self.num_elements:
            logging.debug(f"Solution check failed: Incorrect number of mappings provided ({len(user_mapping)} vs {self.num_elements} required).")
            return False
        # Check if the provided mapping is identical to the solution
        is_correct = user_mapping == self.solution_mapping
        logging.debug(f"Solution check result: {is_correct}. User: {user_mapping}, Solution: {self.solution_mapping}")
        return is_correct

    def get_hint(self, user_mapping: Dict[str, str]) -> Optional[Tuple[str, str, str]]:
        """Provides a hint with explanation of the logical reasoning."""
        unrevealed = {s: l for s, l in self.solution_mapping.items()
                     if user_mapping.get(s) != l} # Symbols not correctly mapped by user

        if not unrevealed:
            logging.info("Hint requested, but puzzle is already solved according to user_mapping.")
            return None # No hints needed if puzzle is solved

        if not self.clues:
            # If there are no clues defined for the puzzle, provide a direct reveal hint
            logging.warning("Hint requested for puzzle with no clues defined.")
            unrevealed_keys = list(unrevealed.keys())
            if not unrevealed_keys: return None # Should not happen if unrevealed is not empty
            symbol_to_reveal = random.choice(unrevealed_keys)
            return (symbol_to_reveal, self.solution_mapping[symbol_to_reveal],
                    "No specific clues available for this hint.")

        shuffled_unrevealed_symbols = list(unrevealed.keys())
        random.shuffle(shuffled_unrevealed_symbols)

        # Try to find a hint based on a clue related to an incorrectly mapped symbol
        for symbol in shuffled_unrevealed_symbols:
            # Check clues directly related to this symbol
            relevant_clues = [(text, ctype) for text, ctype in self.clues if f"'{symbol}'" in text or f"'{symbol}' " in text]
            random.shuffle(relevant_clues)

            if relevant_clues:
                clue_text, clue_type = relevant_clues[0]
                hint_reason = f"Consider the clue ({clue_type.name}): {clue_text}"
                return (symbol, self.solution_mapping[symbol], hint_reason)

        # Fallback hint if no directly relevant clue was found for any unrevealed symbol
        logging.info("No specific clue found for unrevealed symbols. Providing general fallback hint.")
        symbol_to_reveal = random.choice(shuffled_unrevealed_symbols) # Use the already shuffled list
        return (symbol_to_reveal, self.solution_mapping[symbol_to_reveal],
                "No specific clue directly guides the next step. Try focusing on elimination or relational clues.")


class ScenarioPuzzle:
    """Represents a logic puzzle based on a human-centric scenario."""
    def __init__(self, level: int, puzzle_type: HumanScenarioType,
                 description: str, characters: List[Dict[str, Any]],
                 setting: Dict[str, Any], goal: str,
                 information: List[str], solution: Dict[str, Any],
                 rules: Optional[List[str]] = None,
                 options: Optional[List[str]] = None,
                 elements: Optional[Dict[str, List[str]]] = None,
                 is_verified: bool = False, # Added default for consistency
                 **kwargs):
        # Pop or ignore unexpected args from kwargs if needed
        if kwargs:
            logging.warning(f"Ignoring unexpected arguments when creating ScenarioPuzzle ({puzzle_type.name}): {list(kwargs.keys())}")

        self.level = level
        self.puzzle_type = puzzle_type
        self.description = description
        self.characters = characters if characters is not None else []
        self.setting = setting if setting is not None else {}
        self.goal = goal
        self.information = information if information is not None else [] # Renamed from 'clues' for broader meaning
        self.solution = solution if solution is not None else {} # The correct answer/state
        self.is_scenario = True        # Flag to differentiate from symbol puzzles
        self.is_verified = is_verified

        # Store type-specific attributes safely using getattr on self if needed, or directly
        self.rules = rules if rules is not None else [] # Store the rules for relevant types
        self.options = options # Store options for dilemma puzzles (can be None)
        self.elements = elements # Store elements for logic grid UI (can be None)

        # Basic validation
        if not isinstance(self.solution, dict):
             logging.error(f"Scenario Puzzle ({self.puzzle_type.name}) initialized with non-dict solution: {type(self.solution)}")
             # Potentially raise error or set to empty dict?
             self.solution = {}

    def check_solution(self, user_solution: Dict[str, Any]) -> bool:
        """Checks if the user's solution matches the correct one, handling different types."""
        if not isinstance(user_solution, dict):
            logging.warning(f"Scenario check failed ({self.puzzle_type.name}): User solution is not a dict ({type(user_solution)}).")
            return False # User solution must be a dictionary

        # Ensure the official solution is a dict before proceeding
        if not isinstance(self.solution, dict):
            logging.error(f"Cannot check solution for {self.puzzle_type.name}: Internal solution is not a dict.")
            return False

        logging.debug(f"Checking solution for {self.puzzle_type.name}. User: {user_solution}. Expected: {self.solution}")

        try:
            # --- Logic Grid Check ---
            if self.puzzle_type == HumanScenarioType.LOGIC_GRID:
                 required_key = 'grid'
                 if required_key not in self.solution or required_key not in user_solution:
                      logging.warning(f"Missing '{required_key}' key in solution check for {self.puzzle_type.name}.")
                      return False
                 if not isinstance(self.solution[required_key], dict) or not isinstance(user_solution[required_key], dict):
                      logging.warning(f"Invalid '{required_key}' format in solution check for {self.puzzle_type.name}.")
                      return False
                 # Direct comparison of the grid dictionaries
                 return self.solution[required_key] == user_solution[required_key]

            # --- Simple Answer Check (Social Deduction, Common Sense Gap, AGENT_SIMULATION) ---
            elif self.puzzle_type in [HumanScenarioType.SOCIAL_DEDUCTION, HumanScenarioType.COMMON_SENSE_GAP, HumanScenarioType.AGENT_SIMULATION]:
                 required_key = 'answer'
                 if required_key not in self.solution or required_key not in user_solution:
                     logging.warning(f"Missing '{required_key}' key in solution check for {self.puzzle_type.name}.")
                     return False

                 # Normalize answers (string, strip whitespace, lowercase) for comparison
                 correct_answer = str(self.solution.get(required_key, '')).strip().lower()
                 user_answer = str(user_solution.get(required_key, '')).strip().lower()

                 return user_answer == correct_answer

            # --- Ordering Check ---
            elif self.puzzle_type == HumanScenarioType.ORDERING:
                 required_key = 'order'
                 if required_key not in self.solution or required_key not in user_solution:
                      logging.warning(f"Missing '{required_key}' key in solution check for {self.puzzle_type.name}.")
                      return False
                 sol_order = self.solution.get(required_key, [])
                 user_order = user_solution.get(required_key, [])
                 if not isinstance(sol_order, list) or not isinstance(user_order, list):
                      logging.warning(f"Invalid '{required_key}' format in solution check for {self.puzzle_type.name}.")
                      return False
                 return sol_order == user_order

            # --- Relationship Map Check ---
            elif self.puzzle_type == HumanScenarioType.RELATIONSHIP_MAP:
                required_key = 'map'
                if required_key not in self.solution or required_key not in user_solution:
                    logging.warning(f"Missing '{required_key}' key in solution check for {self.puzzle_type.name}.")
                    return False
                sol_map = self.solution.get(required_key, {})
                user_map = user_solution.get(required_key, {})
                if not isinstance(sol_map, dict) or not isinstance(user_map, dict):
                    logging.warning(f"Invalid '{required_key}' format in solution check for {self.puzzle_type.name}.")
                    return False

                # Normalize maps to sets of frozensets for robust comparison
                def normalize_map(relationship_map: Dict[str, str]) -> Set[frozenset]:
                    normalized_pairs = set()
                    processed_keys = set()
                    for key, value in relationship_map.items():
                        # Ensure key and value are strings for frozenset
                        s_key, s_value = str(key), str(value)
                        if s_key not in processed_keys and s_value not in processed_keys:
                            normalized_pairs.add(frozenset({s_key, s_value}))
                            processed_keys.add(s_key)
                            processed_keys.add(s_value)
                    return normalized_pairs

                try:
                    normalized_solution_pairs = normalize_map(sol_map)
                    normalized_user_pairs = normalize_map(user_map)
                    return normalized_solution_pairs == normalized_user_pairs
                except Exception as e:
                    logging.error(f"Error normalizing relationship maps for comparison: {e}", exc_info=True)
                    return False

            # --- Scheduling Check ---
            elif self.puzzle_type == HumanScenarioType.SCHEDULING:
                required_key = 'schedule'
                if required_key not in self.solution or required_key not in user_solution:
                    logging.warning(f"Missing '{required_key}' key in solution check for {self.puzzle_type.name}.")
                    return False
                if not isinstance(self.solution.get(required_key), dict) or not isinstance(user_solution.get(required_key), dict):
                     logging.warning(f"Invalid '{required_key}' format in solution check for {self.puzzle_type.name}.")
                     return False
                # Basic dict comparison (assumes same structure, keys, and values)
                return self.solution.get(required_key, {}) == user_solution.get(required_key, {})

            # --- Dilemma Check ---
            elif self.puzzle_type == HumanScenarioType.DILEMMA:
                required_key = 'choice'
                if required_key not in self.solution or required_key not in user_solution:
                     logging.warning(f"Missing '{required_key}' key in solution check for {self.puzzle_type.name}.")
                     return False
                # Compare selected choice string (case-sensitive comparison)
                return self.solution.get(required_key) == user_solution.get(required_key)

            else:
                 # Fallback for potentially unimplemented types: basic dictionary comparison
                 logging.warning(f"Using basic dictionary comparison for unhandled type: {self.puzzle_type.name}")
                 return self.solution == user_solution

        except Exception as e:
             # Handle potential errors during comparison (e.g., type mismatches in data)
             logging.error(f"Error during solution check for type {self.puzzle_type.name}: {e}", exc_info=True)
             return False

    def get_hint(self, user_state: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Provides a scenario-based hint."""
        # Base case: No specific information pieces to point to
        if not self.information:
             # Check if description or goal provide substance
             base_text = []
             if self.description: base_text.append("description")
             if self.goal: base_text.append("goal")
             if base_text:
                 return f"Try re-reading the scenario { ' and '.join(base_text) } carefully. (No specific hints available)"
             else:
                 return "No hints available for this puzzle." # Truly empty scenario?

        # Simple hint: point to a random piece of information/clue
        # Filter out potential previous hints if they exist
        non_hint_info = [info for info in self.information if not info.lower().startswith("hint:")]
        if not non_hint_info:
             # If only hints remain, maybe show the goal again?
             return f"Focus on the main goal: {self.goal}"

        hint_info = random.choice(non_hint_info)

        # Make hints slightly more context-aware
        if self.puzzle_type == HumanScenarioType.LOGIC_GRID:
             return f"Consider this clue and how it affects the grid: '{hint_info}'"
        elif self.puzzle_type == HumanScenarioType.ORDERING:
             return f"How does this piece of information constrain the sequence? '{hint_info}'"
        elif self.puzzle_type == HumanScenarioType.RELATIONSHIP_MAP:
             return f"What does this tell you about potential pairs? '{hint_info}'"
        elif self.puzzle_type == HumanScenarioType.SOCIAL_DEDUCTION:
             return f"What might this statement reveal about someone's knowledge or motive? '{hint_info}'"
        elif self.puzzle_type == HumanScenarioType.DILEMMA:
            return f"How does this factor weigh into the decision? '{hint_info}'"
        else:
            # Generic hint for other types
            return f"Pay close attention to this detail: '{hint_info}' What might it imply in this situation?"