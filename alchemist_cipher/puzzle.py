# puzzle.py

from typing import Dict, List, Tuple, Optional, Any, Union, Set
import random
from collections import defaultdict
from enum import Enum, auto
import itertools
import re
import math
import logging
import json # Added
import os   # Added

# Define constants at the module level
LETTERS_POOL = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
VOWELS = "AEIOU"
CONSONANTS = "".join(c for c in LETTERS_POOL if c not in VOWELS)
SYMBOLS_POOL = ["α", "β", "γ", "δ", "ε", "ζ", "η", "θ", "ι", "κ", "λ", "μ", "ν", "ξ", "ο", "π", "ρ", "σ", "τ", "υ", "φ", "χ", "ψ", "ω"]

# --- Constants ---
LOGIC_GRID_YES = '✔️'
LOGIC_GRID_NO = '❌'
LOGIC_GRID_UNKNOWN = '?'
DATA_DIR = os.path.join(os.path.dirname(__file__), "game_data") # Added path to data


# --- Main Classes ---

class ClueType(Enum):
    DIRECT = auto()
    EXCLUSION = auto()
    POSITIONAL = auto()
    RELATIONAL = auto()
    CATEGORY = auto()
    LOGICAL = auto()

class Puzzle:
    """Represents a single Symbol Cipher puzzle with educational elements."""
    def __init__(self, level: int, symbols: List[str], letters: List[str],
                 solution_mapping: Dict[str, str], clues: List[Tuple[str, ClueType]],
                 is_verified: bool = False):
        self.level = level
        self.symbols = symbols
        self.letters = letters
        self.solution_mapping = solution_mapping
        self.clues = clues
        self.num_elements = len(symbols)
        self.clue_types_used = {clue_type for _, clue_type in clues}
        self.is_verified = is_verified
        self.is_scenario = False

    def check_solution(self, user_mapping: Dict[str, str]) -> bool:
        """Checks if the user's mapping matches the solution."""
        if len(user_mapping) != self.num_elements:
            return False
        return user_mapping == self.solution_mapping

    def get_hint(self, user_mapping: Dict[str, str]) -> Optional[Tuple[str, str, str]]:
        """Provides a hint with explanation of the logical reasoning."""
        unrevealed = {s: l for s, l in self.solution_mapping.items()
                     if user_mapping.get(s) != l}
        if not unrevealed:
            return None

        if not self.clues:
            unrevealed_keys = list(unrevealed.keys())
            if not unrevealed_keys: return None
            symbol_to_reveal = random.choice(unrevealed_keys)
            return (symbol_to_reveal, self.solution_mapping[symbol_to_reveal],
                    "No specific clues available for this hint.")

        shuffled_unrevealed = list(unrevealed.keys())
        random.shuffle(shuffled_unrevealed)

        for symbol in shuffled_unrevealed:
            shuffled_clues = list(self.clues)
            random.shuffle(shuffled_clues)
            for clue_text, clue_type in shuffled_clues:
                # Basic relevance check (can be improved with more robust parsing)
                if f"'{symbol}'" in clue_text or clue_text.startswith(f"{symbol} "):
                    hint_reason = f"Consider the clue: {clue_text}"
                    # Could add more specific reasoning per type here if needed
                    return (symbol, self.solution_mapping[symbol], hint_reason)

        # Fallback hint if *no* relevant clue was found for *any* unrevealed symbol after checking all
        symbol_to_reveal = random.choice(shuffled_unrevealed) # Use the already shuffled list
        return (symbol_to_reveal, self.solution_mapping[symbol_to_reveal],
                "No specific clue directly helps with the remaining symbols. Try making an educated guess.")


class HumanScenarioType(Enum):
    LOGIC_GRID = auto()
    SCHEDULING = auto()
    RELATIONSHIP_MAP = auto()
    ORDERING = auto()
    SOCIAL_DEDUCTION = auto()
    COMMON_SENSE_GAP = auto()
    DILEMMA = auto()
    AGENT_SIMULATION = auto()


class ScenarioPuzzle:
    """Represents a logic puzzle based on a human-centric scenario."""
    def __init__(self, level: int, puzzle_type: HumanScenarioType,
                 description: str, characters: List[Dict[str, Any]],
                 setting: Dict[str, Any], goal: str,
                 information: List[str], solution: Dict[str, Any],
                 rules: Optional[List[str]] = None,
                 options: Optional[List[str]] = None,
                 elements: Optional[Dict[str, List[str]]] = None,
                 **kwargs):
        # Pop or ignore 'is_verified' and other unexpected args from kwargs if needed
        kwargs.pop('is_verified', None) # Example: explicitly ignore is_verified
        if kwargs:
            logging.warning(f"Ignoring unexpected arguments when creating ScenarioPuzzle: {list(kwargs.keys())}")

        self.level = level
        self.puzzle_type = puzzle_type
        self.description = description
        self.characters = characters
        self.setting = setting
        self.goal = goal
        self.information = information # Renamed from 'clues' for broader meaning
        self.solution = solution       # The correct answer/state
        self.is_scenario = True        # Flag to differentiate from symbol puzzles
        self.rules = rules if rules is not None else [] # Store the rules for relevant types
        self.options = options # Store options for dilemma puzzles
        self.elements = elements # Store elements for logic grid UI

    def check_solution(self, user_solution: Dict[str, Any]) -> bool:
        """Checks if the user's solution matches the correct one, handling different types."""
        if not isinstance(user_solution, dict):
            return False # User solution must be a dictionary

        try:
            # --- Logic Grid Check ---
            if self.puzzle_type == HumanScenarioType.LOGIC_GRID:
                 if 'grid' not in self.solution or 'grid' not in user_solution:
                      logging.warning("Missing 'grid' key in solution check for LOGIC_GRID.")
                      return False
                 # Direct comparison of the grid dictionaries
                 return self.solution['grid'] == user_solution['grid']

            # --- Simple Answer Check (Social Deduction, Common Sense Gap, AGENT_SIMULATION) ---
            elif self.puzzle_type in [HumanScenarioType.SOCIAL_DEDUCTION, HumanScenarioType.COMMON_SENSE_GAP, HumanScenarioType.AGENT_SIMULATION]:
                 if 'answer' not in self.solution or 'answer' not in user_solution:
                     logging.warning(f"Missing 'answer' key in solution check for {self.puzzle_type.name}.")
                     return False

                 correct_answer = str(self.solution.get('answer', '')).strip().lower()
                 user_answer = str(user_solution.get('answer', '')).strip().lower()

                 return user_answer == correct_answer

            # --- Ordering Check ---
            elif self.puzzle_type == HumanScenarioType.ORDERING:
                 if 'order' not in self.solution or 'order' not in user_solution:
                      logging.warning(f"Missing 'order' key in solution check for {self.puzzle_type.name}.")
                      return False
                 sol_order = self.solution.get('order', [])
                 user_order = user_solution.get('order', [])
                 if not isinstance(sol_order, list) or not isinstance(user_order, list):
                      logging.warning(f"Invalid 'order' format in solution check for {self.puzzle_type.name}.")
                      return False
                 return sol_order == user_order

            # --- Relationship Map Check ---
            elif self.puzzle_type == HumanScenarioType.RELATIONSHIP_MAP:
                if 'map' not in self.solution or 'map' not in user_solution:
                    logging.warning(f"Missing 'map' key in solution check for {self.puzzle_type.name}.")
                    return False
                sol_map = self.solution.get('map', {})
                user_map = user_solution.get('map', {})
                if not isinstance(sol_map, dict) or not isinstance(user_map, dict):
                    logging.warning(f"Invalid 'map' format in solution check for {self.puzzle_type.name}.")
                    return False

                def normalize_map(relationship_map: Dict[str, str]) -> Set[frozenset]:
                    normalized_pairs = set()
                    processed_keys = set()
                    for key, value in relationship_map.items():
                        if key not in processed_keys and value not in processed_keys:
                            normalized_pairs.add(frozenset({key, value}))
                            processed_keys.add(key)
                            processed_keys.add(value)
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
                if 'schedule' not in self.solution or 'schedule' not in user_solution:
                    logging.warning(f"Missing 'schedule' key in solution check for {self.puzzle_type.name}.")
                    return False
                # Basic dict comparison for now (assumes same structure)
                return self.solution.get('schedule', {}) == user_solution.get('schedule', {})

            # --- Dilemma Check ---
            elif self.puzzle_type == HumanScenarioType.DILEMMA:
                if 'choice' not in self.solution or 'choice' not in user_solution:
                     logging.warning(f"Missing 'choice' key in solution check for {self.puzzle_type.name}.")
                     return False
                # Compare selected choice string
                return self.solution.get('choice') == user_solution.get('choice')

            else:
                 # Fallback for unimplemented types: basic dictionary comparison
                 logging.warning(f"Using basic dictionary comparison for unhandled type: {self.puzzle_type.name}")
                 return self.solution == user_solution

        except Exception as e:
             # Handle potential errors during comparison (e.g., type mismatches)
             logging.error(f"Error during solution check for type {self.puzzle_type.name}: {e}", exc_info=True)
             return False

    def get_hint(self, user_state: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Provides a scenario-based hint."""
        if not self.information:
             return "Try re-reading the scenario description and goal carefully. (No specific hints available)"

        # Simple hint: point to a random piece of information
        hint_info = random.choice(self.information)
        if self.puzzle_type == HumanScenarioType.LOGIC_GRID:
             return f"Consider this clue: '{hint_info}'"
        else:
            return f"Pay close attention to this detail: '{hint_info}' What might it imply in this situation?"


class ScenarioPuzzleVerifier:
    """Verifies scenario puzzles for unique solvability and internal consistency. (Placeholder)"""

    def __init__(self, puzzle: ScenarioPuzzle):
        self.puzzle = puzzle
        self.puzzle_type = puzzle.puzzle_type
        # Basic check: Logic Grids use the dedicated verifier
        if self.puzzle_type == HumanScenarioType.LOGIC_GRID:
            try:
                 # Expecting elements and clues to be available
                 self.internal_verifier = _LogicGridInternalVerifier(
                     categories=list(puzzle.elements.keys()),
                     elements=list(puzzle.elements.values()),
                     clues=puzzle.information # Assuming logic grid info are the clues
                 )
            except Exception as e:
                 logging.error(f"Failed to initialize LogicGridInternalVerifier for verification: {e}")
                 self.internal_verifier = None
        else:
            self.internal_verifier = None # No internal verifier for other types yet

    def verify(self) -> Tuple[bool, Optional[Dict]]:
        """
        Verifies if the puzzle has a unique solution.
        (Currently only supports Logic Grids via internal verifier)

        Returns:
            Tuple[bool, Optional[Dict]]:
                - bool: True if a unique solution exists, False otherwise
                - Optional[Dict]: The solution if unique, otherwise None
        """
        if self.puzzle_type == HumanScenarioType.LOGIC_GRID and self.internal_verifier:
            # Delegate to the logic grid verifier
            return self.internal_verifier.verify()
        else:
            # For other types, verification is complex and not implemented yet.
            # We often rely on the generator to produce a solvable puzzle.
            # Assume 'verified' based on generator intent, return the stored solution.
            # This is a simplification! Real verification would need solvers per type.
            logging.warning(f"Verification not implemented for {self.puzzle_type.name}. Assuming generator created valid puzzle.")
            return True, self.puzzle.solution # Return the solution embedded in the puzzle

    # Placeholder methods for other verification types (not implemented)
    def _verify_social_deduction(self) -> Tuple[bool, Optional[Dict]]: return True, self.puzzle.solution
    def _evaluate_statement(self, statement: str, truth_assignment: Dict[str, bool]) -> bool: return False
    def _verify_relationship_map(self) -> Tuple[bool, Optional[Dict]]: return True, self.puzzle.solution
    def _check_relationship_constraints(self, mapping: Dict[str, str], clues: List[Dict]) -> bool: return True
    def _verify_agent_simulation(self) -> Tuple[bool, Optional[Dict]]: return True, self.puzzle.solution
    def _generate_possible_rule_sets(self) -> List[Dict]: return []
    def _simulate_agent_behavior(self, rule_set: Dict, observations: List[Dict]) -> bool: return True
    def _apply_rules_to_state(self, rule_set: Dict, initial_state: Dict) -> Dict: return initial_state
    def _verify_ordering(self) -> Tuple[bool, Optional[Dict]]: return True, self.puzzle.solution
    def _verify_scheduling(self) -> Tuple[bool, Optional[Dict]]: return True, self.puzzle.solution
    def _verify_dilemma(self) -> Tuple[bool, Optional[Dict]]: return True, self.puzzle.solution
    def _verify_common_sense_gap(self) -> Tuple[bool, Optional[Dict]]: return True, self.puzzle.solution


class PuzzleGenerator:
    """Generates verified Symbol Cipher OR human-centric Scenario puzzles."""
    # Symbol puzzle constants (not loaded from JSON)
    SYMBOLS_POOL = SYMBOLS_POOL
    LETTERS_POOL = LETTERS_POOL
    VOWELS = VOWELS
    CONSONANTS = CONSONANTS

    # Scenario settings
    SCENARIO_START_LEVEL = 3
    HUMAN_SCENARIO_CHANCE_INCREASE = 0.15
    MAX_HUMAN_SCENARIO_CHANCE = 0.80
    MAX_GENERATION_ATTEMPTS = 10 # For specific scenario types

    def __init__(self, min_elements: int = 4, max_elements: int = 8, max_tries: int = 300):
        if not (isinstance(min_elements, int) and min_elements > 0):
            raise ValueError("min_elements must be a positive integer")
        if not (isinstance(max_elements, int) and max_elements > 0):
            raise ValueError("max_elements must be a positive integer")
        if not (isinstance(max_tries, int) and max_tries > 0):
            raise ValueError("max_tries must be a positive integer")
        if min_elements > max_elements:
            raise ValueError("min_elements cannot be greater than max_elements")

        # Clamp max_elements based on symbol/letter pools
        clamped_max = min(max_elements, len(self.SYMBOLS_POOL), len(self.LETTERS_POOL))
        if clamped_max < max_elements:
            logging.warning(f"max_elements ({max_elements}) exceeds symbol/letter pool size. Clamping to {clamped_max}.")
            max_elements = clamped_max
        if min_elements > max_elements:
            raise ValueError(f"min_elements ({min_elements}) exceeds clamped max_elements ({max_elements}).")

        self.min_symbol_elements = min_elements
        self.max_symbol_elements = max_elements
        self.max_verification_tries = max_tries

        # Load scenario data from JSON files
        self._load_scenario_data()

    def _load_data_from_json(self, filename: str) -> Union[Dict, List]:
        """Helper to load data from a JSON file in the DATA_DIR."""
        filepath = os.path.join(DATA_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error(f"Data file not found: {filepath}")
            raise FileNotFoundError(f"Required data file missing: {filepath}")
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON from {filepath}: {e}")
            raise ValueError(f"Invalid JSON format in {filepath}")
        except Exception as e:
            logging.error(f"Unexpected error loading data from {filepath}: {e}")
            raise

    def _load_scenario_data(self):
        """Loads all necessary scenario data pools from JSON files."""
        try:
            common_data = self._load_data_from_json("common_elements.json")
            self.SCENARIO_NAMES = common_data.get("SCENARIO_NAMES", [])
            self.SCENARIO_TRAITS = common_data.get("SCENARIO_TRAITS", [])
            self.SCENARIO_OCCUPATIONS = common_data.get("SCENARIO_OCCUPATIONS", [])
            self.SCENARIO_RELATIONSHIPS = common_data.get("SCENARIO_RELATIONSHIPS", [])
            self.SCENARIO_SETTINGS = common_data.get("SCENARIO_SETTINGS", [])
            self.SCENARIO_GOALS = common_data.get("SCENARIO_GOALS", [])

            self.COMMON_SENSE_ITEMS = self._load_data_from_json("common_sense_scenarios.json")
            self.AGENT_SIMULATION_RULES = self._load_data_from_json("agent_simulation_rules.json")
            self.LOGIC_GRID_THEMES = self._load_data_from_json("logic_grid_themes.json")
            self.DILEMMA_SCENARIOS = self._load_data_from_json("dilemma_scenarios.json")

            # Basic validation after loading
            if not all([self.SCENARIO_NAMES, self.SCENARIO_TRAITS, self.SCENARIO_SETTINGS]):
                 logging.warning("One or more essential common data pools are empty after loading.")
            if not self.LOGIC_GRID_THEMES: logging.warning("Logic Grid themes data pool is empty.")
            if not self.DILEMMA_SCENARIOS: logging.warning("Dilemma scenarios data pool is empty.")
            # Add more checks as needed

        except (FileNotFoundError, ValueError) as e:
            logging.exception(f"Fatal error loading game data: {e}")
            # Depending on design, might want to raise or exit
            raise RuntimeError("Failed to load essential game data. Cannot continue.") from e


    def generate_puzzle(self, level: int, **kwargs) -> Union[Puzzle, ScenarioPuzzle]:
        """Generates either a symbol cipher or a human scenario puzzle based on level."""
        force_type = kwargs.get('force_type')

        # --- Handle Forced Type ---
        if force_type == "Symbol":
            return self._attempt_generation(self._generate_symbol_puzzle, level, "Symbol")
        elif isinstance(force_type, HumanScenarioType):
            return self._attempt_generation(self._generate_human_scenario_puzzle, level, f"Scenario ({force_type.name})", specific_type=force_type)
        elif force_type == "Scenario":
            return self._attempt_generation(self._generate_human_scenario_puzzle, level, "Scenario (Random)", specific_type=None)

        # --- Level-Based Probability ---
        scenario_chance = 0.0
        if level >= self.SCENARIO_START_LEVEL:
             scenario_chance = min(0.2 + (level - self.SCENARIO_START_LEVEL) * self.HUMAN_SCENARIO_CHANCE_INCREASE, self.MAX_HUMAN_SCENARIO_CHANCE)

        if random.random() < scenario_chance:
            # Try Scenario first, fallback to Symbol
            try:
                return self._generate_human_scenario_puzzle(level, specific_type=None)
            except Exception as e:
                logging.warning(f"Scenario generation failed (Level {level}): {e}. Falling back to Symbol.")
                return self._generate_symbol_puzzle(level) # Fallback guarantees a Puzzle or raises its own error
        else:
            # Try Symbol first, fallback to Scenario
            try:
                return self._generate_symbol_puzzle(level)
            except Exception as e:
                 logging.warning(f"Symbol generation failed (Level {level}): {e}. Falling back to Scenario.")
                 return self._generate_human_scenario_puzzle(level, specific_type=None) # Fallback

    def _attempt_generation(self, generation_func, level, type_name, **gen_kwargs):
        """Helper to attempt generation and handle errors."""
        try:
            return generation_func(level, **gen_kwargs)
        except Exception as e:
            logging.error(f"Error explicitly generating {type_name} puzzle (Level {level}): {e}", exc_info=True)
            # If forced generation fails, raise an error to indicate it couldn't fulfill the request
            raise ValueError(f"Failed to generate requested puzzle type '{type_name}'.") from e

    def _generate_symbol_puzzle(self, level: int) -> Puzzle:
        """Generates a verified symbol cipher puzzle."""
        for attempt in range(self.max_verification_tries):
            num_elements = min(self.min_symbol_elements + level // 2, self.max_symbol_elements)
            num_elements = max(self.min_symbol_elements, num_elements)

            # Use instance pools (already clamped)
            symbols = random.sample(self.SYMBOLS_POOL, num_elements)
            letters = random.sample(self.LETTERS_POOL, num_elements)
            random.shuffle(letters)
            intended_solution = dict(zip(symbols, letters))

            clues = self._generate_symbol_clues(symbols, letters, intended_solution, level)

            if not clues or len(clues) < num_elements // 3:
                continue

            verifier = PuzzleVerifier(puzzle_type='symbol', symbols=symbols, letters=letters, clues=clues)
            is_unique, solutions = verifier.verify()

            if is_unique and len(solutions) == 1:
                if solutions[0] == intended_solution:
                     return Puzzle(level, symbols, letters, intended_solution, clues, is_verified=True)
                # else: (Handle mismatch case if necessary)

        raise ValueError(f"Failed to generate a verifiable symbol puzzle after {self.max_verification_tries} attempts for level {level}.")

    def _generate_symbol_clues(self, symbols: List[str], letters: List[str],
                                  solution_mapping: Dict[str, str], level: int) -> List[Tuple[str, ClueType]]:
        """Generates clues for symbol cipher puzzles."""
        clues = []
        if not symbols or not letters or not solution_mapping:
             logging.warning("Cannot generate symbol clues with empty symbols, letters, or solution.")
             return []

        symbol_list = list(solution_mapping.keys())
        random.shuffle(symbol_list)

        num_elements = len(symbols)
        num_clues = min(num_elements + level // 2, num_elements * 2)
        num_clues = max(num_elements // 2 + 1, num_clues)

        possible_clue_generators = {
            ClueType.DIRECT: self._generate_direct_clue,
            ClueType.EXCLUSION: self._generate_exclusion_clue,
            ClueType.POSITIONAL: self._generate_positional_clue,
            ClueType.RELATIONAL: self._generate_relational_clue,
            ClueType.CATEGORY: self._generate_category_clue,
            ClueType.LOGICAL: self._generate_logical_clue,
        }

        available_clue_types = [ClueType.DIRECT, ClueType.EXCLUSION]
        if level >= 1 and num_elements >= 2: available_clue_types.append(ClueType.CATEGORY)
        if level >= 2 and num_elements >= 3: available_clue_types.extend([ClueType.POSITIONAL, ClueType.RELATIONAL])
        if level >= 4 and num_elements >= 4: available_clue_types.append(ClueType.LOGICAL)

        generated_clue_texts = set()
        current_symbol_pool = list(symbol_list)

        for _ in range(num_clues):
             if not current_symbol_pool: break
             clue_type = random.choice(available_clue_types)
             generator_func = possible_clue_generators[clue_type]

             for retry in range(5):
                 try:
                     clue_text = generator_func(symbols, letters, solution_mapping, current_symbol_pool)
                     if clue_text and clue_text not in generated_clue_texts:
                         clues.append((clue_text, clue_type))
                         generated_clue_texts.add(clue_text)
                         break
                 except Exception as e:
                     # logging.debug(f"Minor error generating {clue_type.name} clue (attempt {retry+1}): {e}")
                     pass

        return clues

    def _generate_human_scenario_puzzle(self, level: int, specific_type: Optional[HumanScenarioType] = None) -> ScenarioPuzzle:
        """Generates a human-centric scenario puzzle. If specific_type is None, chooses randomly."""
        # Define mapping from enum to generation function
        generation_function_map = {
            HumanScenarioType.LOGIC_GRID: self._generate_logic_grid_puzzle,
            HumanScenarioType.AGENT_SIMULATION: self._generate_agent_simulation_puzzle,
            HumanScenarioType.SOCIAL_DEDUCTION: self._generate_social_deduction_puzzle,
            HumanScenarioType.COMMON_SENSE_GAP: self._generate_common_sense_gap_puzzle,
            HumanScenarioType.RELATIONSHIP_MAP: self._generate_relationship_map_puzzle,
            HumanScenarioType.ORDERING: self._generate_ordering_puzzle,
            HumanScenarioType.SCHEDULING: self._generate_scheduling_puzzle,
            HumanScenarioType.DILEMMA: self._generate_dilemma_puzzle,
        }
        generatable_types = list(generation_function_map.keys())

        if specific_type:
             if specific_type in generatable_types:
                 chosen_type = specific_type
             else:
                 logging.warning(f"Requested scenario type {specific_type.name} cannot be generated. Choosing random.")
                 chosen_type = random.choice(generatable_types)
        else:
             chosen_type = random.choice(generatable_types)

        logging.info(f"Attempting to generate puzzle type: {chosen_type.name}")
        generator_func = generation_function_map[chosen_type]

        try:
            # Call the specific generator method for the chosen type
            return generator_func(level)
        except NotImplementedError:
            logging.error(f"Generation function for {chosen_type.name} is marked as not implemented.")
            raise # Re-raise if it's explicitly not implemented
        except Exception as e:
            logging.exception(f"Failed to generate {chosen_type.name}. Trying fallback.")
            # Fallback Logic - Choose a different type
            fallback_types = [t for t in generatable_types if t != chosen_type]
            if not fallback_types: # Should not happen if more than one type exists
                fallback_types = [HumanScenarioType.SOCIAL_DEDUCTION] # Default fallback
            fallback_choice = random.choice(fallback_types)
            logging.info(f"Falling back to generate type: {fallback_choice.name}")
            fallback_func = generation_function_map[fallback_choice]
            try:
                return fallback_func(level)
            except Exception as fallback_e:
                logging.exception(f"Fallback generation for {fallback_choice.name} also failed.")
                raise ValueError(f"Failed to generate primary type {chosen_type.name} and fallback type {fallback_choice.name}.") from fallback_e


    # --- Specific Scenario Generation Methods ---

    def _generate_logic_grid_puzzle(self, level: int) -> ScenarioPuzzle:
        """Generates a classic logic grid puzzle, returned as a ScenarioPuzzle."""
        if not self.LOGIC_GRID_THEMES: raise ValueError("Logic grid themes not loaded.")
        theme_name = random.choice(list(self.LOGIC_GRID_THEMES.keys()))
        theme_data = self.LOGIC_GRID_THEMES[theme_name]
        categories = theme_data["categories"]
        element_pool = theme_data["elements"]

        if not element_pool or not all(isinstance(p, list) for p in element_pool):
             raise ValueError(f"Invalid element pool format for theme '{theme_name}'.")
        if len(set(len(p) for p in element_pool)) != 1:
             raise ValueError(f"Inconsistent element pool sizes for theme '{theme_name}'.")
        grid_size = len(element_pool[0])
        if grid_size < 2:
             raise ValueError(f"Logic grid size must be at least 2 for theme '{theme_name}'.")

        # --- Create the ground truth solution grid ---
        solution_elements = {}
        primary_category = categories[0]
        primary_elements = element_pool[0]
        other_category_indices = list(range(1, len(categories)))
        shuffled_elements = [list(element_pool[cat_idx]) for cat_idx in other_category_indices]
        for elem_list in shuffled_elements: random.shuffle(elem_list)

        for i in range(grid_size):
            entity_name = primary_elements[i]
            solution_elements[entity_name] = {}
            for list_idx, cat_idx in enumerate(other_category_indices):
                category_name = categories[cat_idx]
                element_value = shuffled_elements[list_idx][i]
                solution_elements[entity_name][category_name] = element_value

        # --- Generate Clues (Using the internal verifier's logic for selection is ideal, but complex) ---
        # Simplified clue generation heuristic:
        potential_clues = []
        # Direct positive
        for entity, assignments in solution_elements.items():
            for category, value in assignments.items():
                potential_clues.append(f"{entity} is associated with {value}.")
        # Direct negative
        for entity, assignments in solution_elements.items():
             for category, value in assignments.items():
                 for other_val in element_pool[categories.index(category)]:
                     if other_val != value:
                         potential_clues.append(f"{entity} is not associated with {other_val}.")
                 for other_entity in primary_elements:
                     if other_entity != entity:
                         potential_clues.append(f"{other_entity} is not associated with {value}.")
        # Relative clues (simplified generation)
        if len(categories) >= 3:
             for entity, assignments in solution_elements.items():
                  cat_indices = random.sample(range(1, len(categories)), 2)
                  cat1_name, cat2_name = categories[cat_indices[0]], categories[cat_indices[1]]
                  val1, val2 = assignments[cat1_name], assignments[cat2_name]
                  potential_clues.append(f"The {primary_category} associated with {val1} is also associated with {val2}.")
                  # Add some negative relative clues
                  other_val2_pool = [e for e in element_pool[cat_indices[1]] if e != val2]
                  if other_val2_pool:
                       potential_clues.append(f"The {primary_category} associated with {val1} is NOT associated with {random.choice(other_val2_pool)}.")

        # Select a subset of clues - THIS IS THE HARD PART WITHOUT A SOLVER
        num_clues_target = int(grid_size * len(categories) * 0.7 + level) # Heuristic target
        num_clues_target = max(num_clues_target, grid_size * (len(categories)-1)) # Minimum?
        final_clues = random.sample(potential_clues, min(len(potential_clues), num_clues_target))

        # --- Construct Puzzle ---
        joined_secondary_categories = ", ".join(categories[1:])
        description = f"Logic Puzzle ({theme_name} - {grid_size}x{grid_size}): Deduce the correct pairings.\n"
        description += f"Categories: {primary_category} (Rows) vs {joined_secondary_categories} (Columns).\n"
        for i, cat_name in enumerate(categories):
            elements_str = ", ".join(element_pool[i])
            description += f"  {cat_name}: {elements_str}\n"

        puzzle_characters = [{"name": name, "details": f"{primary_category}"} for name in primary_elements]
        puzzle_setting = {"name": f"Logic Grid Context: {theme_name}", "details": categories[1:]}
        puzzle_goal = f"Complete the grid to show how the categories match for each {primary_category}."
        puzzle_solution = {"grid": solution_elements}

        logging.warning("Logic Grid puzzle uniqueness not strictly verified by generator.")
        return ScenarioPuzzle(
            level=level, puzzle_type=HumanScenarioType.LOGIC_GRID, description=description,
            characters=puzzle_characters, setting=puzzle_setting, goal=puzzle_goal,
            information=final_clues, solution=puzzle_solution,
            elements={cat: elem_list for cat, elem_list in zip(categories, element_pool)}
        )

    def _generate_social_deduction_puzzle(self, level: int) -> ScenarioPuzzle:
        """Generates a SOCIAL_DEDUCTION scenario puzzle."""
        if not self.SCENARIO_SETTINGS or not self.SCENARIO_NAMES or not self.SCENARIO_OCCUPATIONS or not self.SCENARIO_TRAITS or not self.SCENARIO_RELATIONSHIPS or not self.SCENARIO_GOALS:
             raise ValueError("Cannot generate social deduction puzzle: Required data pools missing.")

        setting = random.choice(self.SCENARIO_SETTINGS)
        num_chars = min(3 + level // 3, len(self.SCENARIO_NAMES))
        num_chars = max(2, num_chars)
        if num_chars > len(self.SCENARIO_NAMES): raise ValueError(f"Not enough unique names")

        char_names = random.sample(self.SCENARIO_NAMES, num_chars)
        occupations = random.sample(self.SCENARIO_OCCUPATIONS, min(num_chars, len(self.SCENARIO_OCCUPATIONS)))
        assigned_occupations = [occupations[i % len(occupations)] for i in range(num_chars)]
        characters = []
        for i, name in enumerate(char_names):
            trait = random.choice(self.SCENARIO_TRAITS)
            occupation = assigned_occupations[i]
            characters.append({"name": name, "trait": trait, "occupation": occupation})
        relationship = random.choice(self.SCENARIO_RELATIONSHIPS)

        goal = random.choice([g for g in self.SCENARIO_GOALS if any(k in g.lower() for k in ["who", "identify", "reason", "source", "motive", "discrepancy"])])
        target_person_info = random.choice(characters)
        target_person = target_person_info['name']
        solution = {"answer": target_person}

        involved_people_str = ", ".join([f"{c['name']} (a {c['occupation']}, described as {c['trait']})" for c in characters])
        description = f"Context: A group of {relationship} find themselves in a {setting['name']}. Observed details include: {', '.join(setting['details'])}. An issue has arisen: {goal}. The individuals involved are: {involved_people_str}."

        statements = []
        for char in characters:
            is_target = (char['name'] == target_person)
            stmt = self._generate_social_deduction_statement(char, target_person, characters, is_target, setting)
            statements.append(stmt)

        observation = self._generate_social_deduction_observation(target_person, characters, setting, goal)
        red_herring = self._generate_red_herring(characters, setting)
        information = [observation, f"Also noted: {red_herring}"] + statements
        random.shuffle(information)

        return ScenarioPuzzle(level=level, puzzle_type=HumanScenarioType.SOCIAL_DEDUCTION, description=description, characters=characters, setting=setting, goal=goal, information=information, solution=solution)

    def _generate_common_sense_gap_puzzle(self, level: int) -> ScenarioPuzzle:
        """Generates a COMMON_SENSE_GAP scenario puzzle."""
        if not self.COMMON_SENSE_ITEMS or not self.SCENARIO_SETTINGS or not self.SCENARIO_NAMES or not self.SCENARIO_TRAITS:
            raise ValueError("Cannot generate common sense puzzle: Required data pools missing.")

        setting = random.choice(self.SCENARIO_SETTINGS)
        char_name = random.choice(self.SCENARIO_NAMES)
        characters = [{"name": char_name, "trait": random.choice(self.SCENARIO_TRAITS)}]

        scenario_key = random.choice(list(self.COMMON_SENSE_ITEMS.keys()))
        scenario_data = self.COMMON_SENSE_ITEMS[scenario_key]
        if not scenario_data.get("present") or not scenario_data.get("missing"):
             raise ValueError(f"Invalid data format for common sense scenario: {scenario_key}")

        k_present = random.randint(max(1, len(scenario_data["present"]) // 2), len(scenario_data["present"]))
        items_present = random.sample(scenario_data["present"], k=k_present)
        missing_item = random.choice(scenario_data["missing"])
        solution = {"answer": missing_item}
        goal = f"Identify the essential missing item/tool needed to complete the task: {scenario_key}."

        description = f"Task Context: In a {setting['name']}, {char_name} is preparing to '{scenario_key}'. They have gathered the following: {', '.join(items_present)}."

        information = [f"They seem ready to proceed but something feels incomplete."]
        distractor_items = [i for i in scenario_data["present"] if i not in items_present]
        if distractor_items: information.append(f"Nearby, one can also see a {random.choice(distractor_items)}.")
        if setting.get('details'): information.append(f"Relevant context: {random.choice(setting['details'])}.")

        # Add hint based on missing item purpose
        hints = {
            "oven mitts": "Protection from heat is needed.", "rain boots": "Protection from weather is needed.", "umbrella": "Protection from weather is needed.",
            "baking pan": "A container is required.", "envelope": "A container is required.", "filter": "A specific medium is required.", "pot": "A container is required.", "wrapping paper": "A covering is required.",
            "whisk": "A tool for mixing is needed.", "stamp": "A consumable for postage is needed.", "tea bag": "The core consumable is missing.", "soil": "The growing medium is needed.", "tape": "An adhesive tool is required.", "scissors": "A cutting tool is needed.", "webcam": "A tool for visual input is required.", "microphone": "A tool for audio input is needed.",
            "address": "Crucial information is missing.", "meeting link": "Crucial information is missing.", "water": "A vital liquid is needed.", "coffee grounds": "The core consumable is missing.", "insect repellent": "Protection from pests is needed.", "flashlight": "A light source is needed.", "water bottle": "A container for hydration is needed.", "napkin": "Something for cleaning up is needed.", "spoon": "An eating utensil is missing.", "glass": "A drinking vessel is missing."
        }
        hint = hints.get(missing_item, "Think about the next logical step in the process.")
        information.append(f"Hint: {hint}")
        random.shuffle(information)

        return ScenarioPuzzle(level=level, puzzle_type=HumanScenarioType.COMMON_SENSE_GAP, description=description, characters=characters, setting=setting, goal=goal, information=information, solution=solution)

    def _generate_relationship_map_puzzle(self, level: int) -> ScenarioPuzzle:
         """Generates a RELATIONSHIP_MAP scenario puzzle."""
         if not self.SCENARIO_SETTINGS or not self.SCENARIO_NAMES or not self.SCENARIO_OCCUPATIONS or not self.SCENARIO_TRAITS or not self.SCENARIO_RELATIONSHIPS:
             raise ValueError("Cannot generate relationship map puzzle: Required data pools missing.")

         setting = random.choice(self.SCENARIO_SETTINGS)
         num_chars = min(4 + (level // 2) * 2, len(self.SCENARIO_NAMES))
         num_chars = max(4, num_chars if num_chars % 2 == 0 else num_chars - 1) # Ensure even, min 4
         if num_chars > len(self.SCENARIO_NAMES): raise ValueError(f"Not enough unique names")

         char_names = random.sample(self.SCENARIO_NAMES, num_chars)
         occupations = random.sample(self.SCENARIO_OCCUPATIONS, min(num_chars, len(self.SCENARIO_OCCUPATIONS)))
         assigned_occupations = [occupations[i % len(occupations)] for i in range(num_chars)]
         characters = []
         for i, name in enumerate(char_names):
             trait = random.choice(self.SCENARIO_TRAITS)
             occupation = assigned_occupations[i]
             characters.append({"name": name, "trait": trait, "occupation": occupation})
         relationship = random.choice(self.SCENARIO_RELATIONSHIPS)

         goal = random.choice([
             "Determine who is partnered with whom.", "Map out the reporting structure (direct pairs only).",
             "Identify the mentor for each trainee (1-to-1 pairing)."
         ])
         num_pairs = num_chars // 2
         shuffled_chars = list(characters)
         random.shuffle(shuffled_chars)

         solution_map = {}
         for i in range(num_pairs):
             char1_info, char2_info = shuffled_chars[2*i], shuffled_chars[2*i + 1]
             char1_name, char2_name = char1_info['name'], char2_info['name']
             solution_map[char1_name] = char2_name
             solution_map[char2_name] = char1_name # Assume bidirectional

         solution = {"map": solution_map}

         involved_people_str = ", ".join([f"{c['name']} ({c['occupation']})" for c in characters])
         description = f"Context: A group of {relationship} are involved in a task at {setting['name']}. Details: {', '.join(setting.get('details',[]))}. Goal: {goal}. The individuals are: {involved_people_str}."

         clues = []
         potential_clue_pairs = list(itertools.combinations(characters, 2))
         random.shuffle(potential_clue_pairs)
         num_clues_target = num_chars # Target roughly one clue per person
         clues_generated = 0
         added_clue_pairs = set() # Avoid redundant positive/negative clues about the same pair

         for char_a_info, char_b_info in potential_clue_pairs:
             if clues_generated >= num_clues_target: break
             char_a_name, char_b_name = char_a_info['name'], char_b_info['name']
             pair_key = frozenset({char_a_name, char_b_name})
             if pair_key in added_clue_pairs: continue

             are_paired = solution_map.get(char_a_name) == char_b_name

             # Generate clue based on relationship and traits
             clue_text = None
             if are_paired:
                 # Positive clue
                 if random.random() < 0.7: # Higher chance for positive clues for pairs
                     if char_a_info['trait'] == "Cooperative" or char_b_info['trait'] == "Helpful": clue_text = f"{char_a_name} was seen working closely with {char_b_name}."
                     elif char_a_info['trait'] == "Organized": clue_text = f"{char_a_name}'s notes mention frequent meetings with {char_b_name}."
                     else: clue_text = f"There's evidence linking {char_a_name} and {char_b_name} on this task."
             else:
                 # Negative clue (generate less frequently)
                 if random.random() < 0.5:
                     if char_a_info['trait'] == "Skeptical" or char_b_info['trait'] == "Independent": clue_text = f"{char_a_name} explicitly stated they prefer not to work with {char_b_name}."
                     elif char_a_info['trait'] == "Busy": clue_text = f"{char_a_name} mentioned having conflicting schedules with {char_b_name}."
                     else: clue_text = f"It is known that {char_a_name} and {char_b_name} are in different project groups."

             if clue_text:
                  clues.append(clue_text)
                  added_clue_pairs.add(pair_key)
                  clues_generated += 1

         # Ensure enough clues (rough heuristic)
         while clues_generated < num_pairs + level // 2:
              clues.append("Further investigation might be needed to confirm all relationships.")
              clues_generated += 1

         information = clues
         random.shuffle(information)
         logging.warning("Relationship map puzzle uniqueness not strictly verified by generator.")
         return ScenarioPuzzle(level=level, puzzle_type=HumanScenarioType.RELATIONSHIP_MAP, description=description, characters=characters, setting=setting, goal=goal, information=information, solution=solution)

    def _generate_ordering_puzzle(self, level: int) -> ScenarioPuzzle:
        """Generates an ORDERING scenario puzzle."""
        if not self.SCENARIO_SETTINGS: raise ValueError("Settings data not loaded.")
        logging.info(f"Attempting to generate Ordering Puzzle (Level {level})...")

        num_elements = random.randint(min(3 + level // 2, 4), min(4 + level // 2, 5))
        # Use generic items or tasks for ordering
        items = [f"Step {chr(65+i)}" for i in range(num_elements)]
        correct_order = list(items)
        random.shuffle(correct_order)
        solution = {"order": correct_order}
        indices = {item: i for i, item in enumerate(correct_order)}

        clues = []
        added_clue_info = set() # Track (type, item1, item2) to avoid redundant info

        # 1. Direct Position Clue (optional)
        if random.random() < 0.4 + (level * 0.1):
            idx = random.randrange(num_elements)
            item = correct_order[idx]
            position_word = ["first", "second", "third", "fourth", "fifth"][idx % 5]
            clue_text = f"{item} is {position_word}."
            if ("pos", item, idx) not in added_clue_info:
                clues.append(clue_text)
                added_clue_info.add(("pos", item, idx))

        # 2. Relative Position Clues (Ensure enough constraints)
        num_relative_clues_target = max(1, num_elements -1 + level // 2)
        clues_generated_count = len(clues)

        attempts = 0
        max_clue_attempts = num_relative_clues_target * 4 # More attempts to find non-redundant clues

        while clues_generated_count < num_relative_clues_target and attempts < max_clue_attempts:
             attempts += 1
             i1, i2 = random.sample(range(num_elements), 2)
             item1, item2 = correct_order[i1], correct_order[i2]
             pair = tuple(sorted((item1, item2)))
             clue_text = None
             clue_key = None

             if i1 < i2: # item1 is before item2
                  if i2 == i1 + 1 and random.random() < 0.4: # Immediately before
                       clue_text = f"{item1} is immediately before {item2}."
                       clue_key = ("imm_before", item1, item2)
                  elif random.random() < 0.6: # Standard before clue
                       clue_text = f"{item1} comes somewhere before {item2}."
                       clue_key = ("before", item1, item2)
             else: # item1 is after item2
                  if i1 == i2 + 1 and random.random() < 0.4: # Immediately after
                       clue_text = f"{item1} is immediately after {item2}."
                       clue_key = ("imm_after", item1, item2)
                  elif random.random() < 0.6: # Standard after clue
                       clue_text = f"{item1} comes somewhere after {item2}."
                       clue_key = ("after", item1, item2)

             if clue_text and clue_key not in added_clue_info:
                 # Avoid adding direct opposites if the other exists
                 if clue_key[0] == "before" and ("after", item2, item1) in added_clue_info: continue
                 if clue_key[0] == "after" and ("before", item2, item1) in added_clue_info: continue
                 if clue_key[0] == "imm_before" and ("imm_after", item2, item1) in added_clue_info: continue
                 if clue_key[0] == "imm_after" and ("imm_before", item2, item1) in added_clue_info: continue

                 clues.append(clue_text)
                 added_clue_info.add(clue_key)
                 clues_generated_count += 1

        # 3. First/Last Clues (maybe)
        if random.random() < 0.5 and ("pos", correct_order[0], 0) not in added_clue_info:
             clues.append(f"{correct_order[0]} is not last.")
        if random.random() < 0.5 and ("pos", correct_order[-1], num_elements-1) not in added_clue_info:
             clues.append(f"{correct_order[-1]} is not first.")

        if not clues: # Ensure at least one clue
            clues.append(f"{correct_order[0]} is somewhere in the sequence.")

        # --- Construct ---
        goal = f"Determine the correct sequence of the following: {', '.join(items)}."
        description = f"A series of steps occurred, but the exact order is unclear. Use the information provided to reconstruct the sequence."
        information = clues
        random.shuffle(information)

        logging.warning("Ordering puzzle uniqueness not strictly verified by generator.")
        return ScenarioPuzzle(level=level, puzzle_type=HumanScenarioType.ORDERING, description=description, characters=[], setting=random.choice(self.SCENARIO_SETTINGS), goal=goal, information=information, solution=solution)

    def _generate_scheduling_puzzle(self, level: int) -> ScenarioPuzzle:
        """Generates a SCHEDULING scenario puzzle."""
        if not self.SCENARIO_NAMES or not self.SCENARIO_TRAITS:
             raise ValueError("Cannot generate scheduling puzzle: Required data pools missing.")
        logging.info("Generating SCHEDULING puzzle...")

        num_people = random.randint(min(2 + level // 2, 3), min(3 + level // 2, 4)) # Smaller scale for scheduling
        num_slots = random.randint(min(3 + level // 2, 4), min(4 + level // 2, 5))
        num_constraints = int(num_people * num_slots * 0.5 + level) # ~50% density + level

        if num_people > len(self.SCENARIO_NAMES): raise ValueError(f"Not enough names for {num_people} people.")

        people = random.sample(self.SCENARIO_NAMES, k=num_people)
        start_hour = random.choice([8, 9, 10])
        time_slots = []
        for i in range(num_slots):
            hour = start_hour + i
            am_pm = "AM" if hour < 12 else "PM"
            display_hour = hour if hour <= 12 else hour - 12
            if display_hour == 0: display_hour = 12 # Handle midnight if applicable, though unlikely with start_hour
            time_slots.append(f"{display_hour} {am_pm}")

        max_attempts = 50
        final_solution = None
        constraints = []

        for attempt in range(max_attempts):
            constraints = []
            # 1. Generate constraints
            potential_constraints = []
            # Availability/Unavailability (higher weight)
            for _ in range(int(num_constraints * 0.6)):
                person = random.choice(people)
                slot = random.choice(time_slots)
                if random.random() < 0.3 and level > 1: # Must_be is rarer, needs higher level
                    potential_constraints.append(('must_be', person, slot))
                else:
                    potential_constraints.append(('unavailable', person, slot))
            # Relational
            for _ in range(int(num_constraints * 0.4)):
                if num_people < 2: break
                p1, p2 = random.sample(people, 2)
                constraint_type = random.choice(['before', 'together', 'apart'])
                potential_constraints.append((constraint_type, p1, p2))

            # 2. Attempt to find a valid solution for these constraints
            solver = _SchedulingSolver(people, time_slots, potential_constraints)
            solution = solver.find_solution()

            if solution:
                # TODO: Check for uniqueness (requires more complex solver)
                final_solution = solution
                constraints = potential_constraints # Keep the constraints that led to a solution
                break # Found a solvable set of constraints

        if not final_solution:
            raise ValueError(f"Failed to generate a valid scheduling puzzle solution after {max_attempts} attempts.")

        # --- Generate Clue Text from Constraints ---
        information = []
        constraint_texts = {
            'unavailable': "{p} is unavailable at {s}.",
            'must_be': "{p}'s appointment must be at {s}.",
            'before': "{p1}'s appointment is scheduled before {p2}'s.",
            'together': "{p1} and {p2} have appointments at the same time.",
            'apart': "{p1} and {p2} have appointments at different times."
        }
        # Add some noise/redundancy? Or keep it clean? Keep clean for now.
        for constraint in constraints:
            ctype = constraint[0]
            if ctype in ['unavailable', 'must_be']: info = constraint_texts[ctype].format(p=constraint[1], s=constraint[2])
            elif ctype in ['before', 'together', 'apart']: info = constraint_texts[ctype].format(p1=constraint[1], p2=constraint[2])
            else: continue
            information.append(info)

        random.shuffle(information)

        # --- Construct Puzzle Object ---
        goal = f"Determine the schedule for {', '.join(people)} across: {', '.join(time_slots)}. Mark each slot as 'Available' or 'Booked'."
        description = f"Coordinate the schedules for {len(people)} individuals using the constraints."
        characters_list = [{"name": p, "trait": random.choice(self.SCENARIO_TRAITS)} for p in people]
        setting_dict = {"name": "Scheduling Coordination", "details": time_slots}

        logging.warning("Scheduling puzzle uniqueness not strictly verified by generator.")
        return ScenarioPuzzle(
            level=level, puzzle_type=HumanScenarioType.SCHEDULING, description=description,
            characters=characters_list, setting=setting_dict, goal=goal,
            information=information, solution={"schedule": final_solution}, rules=None
        )

    def _generate_dilemma_puzzle(self, level: int) -> ScenarioPuzzle:
        """Generates a DILEMMA scenario puzzle."""
        if not self.DILEMMA_SCENARIOS:
             raise ValueError("Cannot generate dilemma puzzle: Dilemma scenarios not loaded.")
        logging.info("Generating DILEMMA puzzle...")

        # Select a scenario (can add level-based filtering later)
        chosen_dilemma = random.choice(self.DILEMMA_SCENARIOS)

        solution = {"choice": chosen_dilemma["solution"]}
        goal = "Analyze the situation and choose the most appropriate course of action from the options provided."
        description = chosen_dilemma["desc"]
        information = list(chosen_dilemma["info"]) # Make a copy
        random.shuffle(information)
        hint = "Consider the immediate and long-term consequences, ethics, and relationships."
        information.append(f"Hint: {hint}")

        return ScenarioPuzzle(
            level=level, puzzle_type=HumanScenarioType.DILEMMA, description=description,
            characters=[], setting={"name": "Workplace Scenario", "details": []}, goal=goal,
            information=information, solution=solution, rules=None,
            options=chosen_dilemma["options"]
        )

    def _generate_agent_simulation_puzzle(self, level: int) -> ScenarioPuzzle:
        """Generates a puzzle based on observing a simple agent simulation."""
        if not self.AGENT_SIMULATION_RULES or not self.SCENARIO_NAMES or not self.SCENARIO_TRAITS or not self.SCENARIO_SETTINGS:
             raise ValueError("Cannot generate agent sim puzzle: Required data pools missing.")
        logging.info("Generating AGENT_SIMULATION puzzle...")

        num_agents = random.randint(2, min(3 + level // 2, 4))
        locations_available = [s['name'] for s in self.SCENARIO_SETTINGS if len(s.get('details',[])) > 0] # Use settings with names as locations
        if len(locations_available) < num_agents: raise ValueError("Not enough unique locations from settings.")
        num_locations = random.randint(min(num_agents, 3 + level // 2), min(len(locations_available), 5))
        num_time_steps = random.randint(min(3 + level // 3, 4), min(4 + level // 2, 5))

        # Setup Initial State
        locations = random.sample(locations_available, num_locations)
        setting = {"name": "Interaction Zone", "details": locations}
        char_names = random.sample(self.SCENARIO_NAMES, min(num_agents, len(self.SCENARIO_NAMES)))
        if len(char_names) < num_agents: char_names.extend([f"Agent {i+1}" for i in range(num_agents - len(char_names))])
        initial_locations = random.sample(locations, k=num_agents)
        characters = []
        for i in range(num_agents):
            trait = random.choice(self.SCENARIO_TRAITS)
            possible_targets = locations + [c['name'] for c in characters if c['name'] != char_names[i]]
            target = random.choice([t for t in possible_targets if t != initial_locations[i]]) if possible_targets else initial_locations[i]
            goal_type = random.choice(["REACH", "AVOID"])
            agent_goal = f"{goal_type} {target}"
            characters.append({
                "name": char_names[i], "trait": trait, "goal": agent_goal,
                "location": initial_locations[i],
                "state_history": {0: initial_locations[i]}
            })

        # Select Rules
        num_rules = random.randint(2, min(len(self.AGENT_SIMULATION_RULES), 4))
        selected_rule_dicts = random.sample(self.AGENT_SIMULATION_RULES, num_rules)
        rules_in_effect = []
        rule_texts_for_display = []
        for rule_template in selected_rule_dicts:
            rule_id, rule_text_template = rule_template["id"], rule_template["text"]
            params, final_rule_text = {}, rule_text_template
            # Parameterize (Refined)
            param_subs = {}
            if "{location_A}" in rule_text_template: param_subs["{location_A}"] = random.choice(locations)
            if "{location_B}" in rule_text_template: param_subs["{location_B}"] = random.choice(locations)
            if "{location_C}" in rule_text_template: param_subs["{location_C}"] = random.choice(locations)
            # Apply substitutions
            for placeholder, value in param_subs.items():
                 final_rule_text = final_rule_text.replace(placeholder, value)
                 params[placeholder[1:-1]] = value # Store param name without braces

            rules_in_effect.append((rule_id, params))
            rule_texts_for_display.append(final_rule_text)

        # --- Run Simulation (Simplified - Needs robust implementation) ---
        # This part remains complex and prone to issues without a proper simulation engine.
        # Placeholder logic for state update based on rules:
        for t in range(1, num_time_steps + 1):
            current_locations = {agent["name"]: agent["state_history"][t-1] for agent in characters}
            next_locations = current_locations.copy() # Start with current positions

            # Extremely simplified simulation: apply first matching rule, ignore conflicts for now
            for agent in characters:
                moved = False
                for rule_id, params in rules_in_effect:
                    if moved: break
                    current_loc = agent["state_history"][t-1]
                    new_loc = current_loc # Default stay
                    # Basic logic check based on rule ID
                    if rule_id == "MOVE_TOWARDS_GOAL_LOC":
                         goal_parts = agent['goal'].split(" ", 1)
                         if goal_parts[0] == "REACH" and goal_parts[1] in locations and current_loc != goal_parts[1]:
                              possible_moves = [loc for loc in locations if loc != current_loc]
                              if possible_moves: new_loc = random.choice(possible_moves)
                    elif rule_id == "MOVE_RANDOM_IF_NO_GOAL": # Example fallback
                          possible_moves = [loc for loc in locations if loc != current_loc]
                          if possible_moves: new_loc = random.choice(possible_moves)
                    # Add more basic rule applications...

                    if new_loc != current_loc:
                        next_locations[agent["name"]] = new_loc
                        moved = True

            # Update history
            for agent in characters:
                 agent['state_history'][t] = next_locations[agent['name']]


        # --- Generate Observations ---
        information = []
        num_rules_to_reveal = min(len(rule_texts_for_display), max(1, num_rules // 2 + level // 4))
        revealed_rules_text = random.sample(rule_texts_for_display, k=num_rules_to_reveal)
        information.extend(f"Rule Observed: {r}" for r in revealed_rules_text)

        num_observations = random.randint(num_agents + 1, int(num_agents * num_time_steps * 0.6))
        added_observations = set()
        for _ in range(num_observations * 2): # Try more times to get unique observations
            if len(added_observations) >= num_observations: break
            t = random.randint(0, num_time_steps)
            agent = random.choice(characters)
            location = agent['state_history'][t]
            obs_key = (t, agent['name'])
            if obs_key not in added_observations:
                 information.append(f"At T={t}, {agent['name']} was observed in {location}.")
                 added_observations.add(obs_key)
        random.shuffle(information)

        # --- Define Goal & Solution ---
        goal_type = random.choice(["IDENTIFY_TRAIT", "IDENTIFY_RULE"]) # Predict state is too complex without better sim
        puzzle_goal, solution = "", {}

        if goal_type == "IDENTIFY_TRAIT":
            target_agent = random.choice(characters)
            puzzle_goal = f"Based on actions and rules, what is the most likely trait of {target_agent['name']}?"
            solution = {"answer": target_agent['trait']}
        else: # IDENTIFY_RULE
            unrevealed_rules = [r for r in rule_texts_for_display if r not in revealed_rules_text]
            if not unrevealed_rules and rule_texts_for_display:
                unrevealed_rules = rule_texts_for_display # Fallback
                puzzle_goal = "Which revealed rule seems most influential?"
            elif not rule_texts_for_display: raise ValueError("No rules generated for IDENTIFY_RULE goal.")
            else: puzzle_goal = "Identify an unstated rule likely governing agent interactions."
            solution = {"answer": random.choice(unrevealed_rules)}

        # --- Construct Description ---
        agent_names_str_desc = ", ".join(a['name'] for a in characters)
        locations_str_desc = ", ".join(locations)
        description = f"Observe {num_agents} agents ({agent_names_str_desc}) in {num_locations} areas ({locations_str_desc}) over {num_time_steps} time steps. Deduce the logic."

        logging.warning("Agent simulation puzzle logic is simplified; complex interactions/conflicts may not be accurate.")
        return ScenarioPuzzle(
            level=level, puzzle_type=HumanScenarioType.AGENT_SIMULATION, description=description,
            characters=characters, setting=setting, goal=puzzle_goal,
            information=information, solution=solution, rules=rule_texts_for_display
        )


    # --- Symbol Cipher Clue Generation Helpers ---

    def _generate_direct_clue(self, symbols: List[str], letters: List[str],
                              solution: Dict[str, str], symbol_pool: List[str]) -> Optional[str]:
        if not symbol_pool: return None
        symbol = random.choice(symbol_pool)
        letter = solution[symbol]
        return f"'{symbol}' directly represents the letter '{letter}'."

    def _generate_exclusion_clue(self, symbols: List[str], letters: List[str],
                                 solution: Dict[str, str], symbol_pool: List[str]) -> Optional[str]:
        if not symbol_pool or len(letters) < 2: return None
        symbol = random.choice(symbol_pool)
        actual_letter = solution[symbol]
        possible_wrong_letters = [l for l in letters if l != actual_letter]
        if not possible_wrong_letters: return None
        wrong_letter = random.choice(possible_wrong_letters)
        return f"The symbol '{symbol}' does not represent the letter '{wrong_letter}'."

    def _generate_positional_clue(self, symbols: List[str], letters: List[str],
                                  solution: Dict[str, str], symbol_pool: List[str]) -> Optional[str]:
        # Relies on the original `symbols` list order passed to the generator
        if len(symbols) < 2: return None
        idx = random.randrange(len(symbols))
        symbol = symbols[idx]
        position_word = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth"] # Extend as needed
        if idx < len(position_word):
             pos_str = position_word[idx]
             letter = solution[symbol]
             prop = "a vowel" if letter in self.VOWELS else "a consonant"
             return f"In the sequence shown, the {pos_str} symbol represents {prop}."
        return None

    def _generate_relational_clue(self, symbols: List[str], letters: List[str],
                                  solution: Dict[str, str], symbol_pool: List[str]) -> Optional[str]:
        if len(symbol_pool) < 2: return None
        s1, s2 = random.sample(symbol_pool, 2)
        l1, l2 = solution[s1], solution[s2]
        if ord(l1) < ord(l2):
            return f"The letter for '{s1}' comes earlier in the alphabet than the letter for '{s2}'."
        elif ord(l1) > ord(l2):
             return f"The letter for '{s1}' comes later in the alphabet than the letter for '{s2}'."
        else: return None

    def _generate_category_clue(self, symbols: List[str], letters: List[str],
                                solution: Dict[str, str], symbol_pool: List[str]) -> Optional[str]:
        if not symbol_pool: return None
        symbol = random.choice(symbol_pool)
        letter = solution[symbol]
        category = "a vowel" if letter in self.VOWELS else "a consonant"
        return f"The symbol '{symbol}' represents {category}."

    def _generate_logical_clue(self, symbols: List[str], letters: List[str],
                               solution: Dict[str, str], symbol_pool: List[str]) -> Optional[str]:
        if len(symbol_pool) < 2: return None
        s1, s2 = random.sample(symbol_pool, 2)
        l1, l2 = solution[s1], solution[s2]
        l1_prop_is_vowel = l1 in self.VOWELS
        l2_prop_is_vowel = l2 in self.VOWELS
        l1_prop_text = "a vowel" if l1_prop_is_vowel else "a consonant"
        l2_prop_text = "a vowel" if l2_prop_is_vowel else "a consonant"

        premise_matches_solution = random.choice([True, False])
        if premise_matches_solution:
            return f"If '{s1}' represents {l1_prop_text}, then '{s2}' represents {l2_prop_text}."
        else:
            l1_opposite_prop_text = "a consonant" if l1_prop_is_vowel else "a vowel"
            l2_random_prop_text = random.choice(["a vowel", "a consonant"])
            return f"If '{s1}' represents {l1_opposite_prop_text}, then '{s2}' represents {l2_random_prop_text}."

    # --- Social Deduction Helper Methods ---
    def _generate_social_deduction_statement(self, character: Dict, target_person_name: str, all_characters: List[Dict], is_target: bool, setting: Dict) -> str:
        name, trait = character['name'], character['trait']
        others = [c for c in all_characters if c['name'] != name]
        other_person = random.choice(others)['name'] if others else "someone else"

        if is_target:
            statements = {
                "Secretive": f"{name} claims they were focused and didn't notice anything.",
                "Evasive": f"{name} vaguely mentions being 'around' but can't recall specifics.",
                "Anxious": f"{name} seems flustered, saying, 'I... I don't think I saw anything important.'",
                "Forgetful": f"{name} frowns, 'I might have seen something, but details are fuzzy.'",
                "Argumentative": f"{name} deflects, questioning why everyone is focused on them.",
                "Honest": f"{name} states, 'I was involved, but there's a misunderstanding.'",
                "_default": f"{name} provides a simple denial."
            }
            return statements.get(trait, statements["_default"])
        else:
             statements = {
                "Honest": f"{name} states they observed {target_person_name} acting suspiciously.",
                "Observant": f"{name} mentions noticing {target_person_name} hastily putting something away.",
                "Talkative": f"{name} heard {other_person} gossiping about {target_person_name}'s behavior.",
                "Skeptical": f"{name} expresses doubt about {target_person_name}'s routine.",
                "Distracted": f"{name} thinks they saw {other_person} nearby, but isn't sure.",
                "Quiet": f"{name} hesitates, suggesting asking {target_person_name} directly.",
                "Helpful": f"{name} tries to reconstruct the timeline, inadvertently giving {target_person_name} an alibi.",
                "Nitpicky": f"{name} focuses on an irrelevant inconsistency in {other_person}'s account.",
                 "_default": f"{name} says they didn't see {target_person_name}, but noticed {other_person}."
             }
             return statements.get(trait, statements["_default"])

    def _generate_social_deduction_observation(self, target_person_name: str, all_characters: List[Dict], setting: Dict, goal: str) -> str:
        setting_detail = random.choice(setting.get('details', ["a nearby object"]))
        goal_lower = goal.lower()
        if any(k in goal_lower for k in ["document", "report", "note"]):
             return f"A crumpled draft related to the issue was found near {target_person_name}'s workspace."
        if any(k in goal_lower for k in ["email", "message", "log"]):
             return f"System logs show {target_person_name} was logged in around the relevant time."
        if any(k in goal_lower for k in ["meeting", "schedule", "appointment"]):
             return f"{target_person_name}'s calendar had a conflicting entry during that time."
        if any(k in goal_lower for k in ["tool", "item", "stapler"]):
             return f"An item similar to the missing one was seen at {target_person_name}'s desk earlier."
        return f"Regarding the {setting_detail}, witnesses recall {target_person_name} being the last person near it."

    def _generate_red_herring(self, all_characters: List[Dict], setting: Dict) -> str:
        others = [c['name'] for c in all_characters]
        if not others: return "An unrelated discussion about the weather occurred."
        p1 = random.choice(others)
        p2 = random.choice([p for p in others if p != p1] or [p1]) # Avoid error if only one person
        details_options = setting.get('details', ["the nearby window", "a poster", "a plant"])
        options = [
            f"{p1} was complaining about the coffee machine.",
            f"There was a brief discussion about {p2}'s vacation.",
            f"Someone mentioned the {random.choice(details_options)} needs attention.",
            f"{p1} and {p2} had a short chat about weekend plans.",
            f"An announcement was made about a company event."
        ]
        return random.choice(options)


class _LogicGridInternalVerifier:
    """(Internal) Verifies logic grid puzzles using constraint propagation."""
    def __init__(self, categories: List[str], elements: List[List[str]], clues: List[str]):
        if not categories or not elements or len(categories) != len(elements):
            raise ValueError("Invalid categories or elements provided to LogicGridVerifier.")
        if len(set(len(e) for e in elements)) != 1:
             raise ValueError("Element lists must have the same size.")

        self.categories = categories
        self.elements = {cat: list(elem_list) for cat, elem_list in zip(categories, elements)}
        self.clues = clues
        self.grid_size = len(elements[0])
        self.primary_category = categories[0]
        self.primary_elements = self.elements[self.primary_category]
        self.grid = {} # Initialized in _initialize_grid
        self.relative_clues_parsed = []
        self._initialize_grid()


    def _initialize_grid(self):
        """Resets the grid to the initial state with all possibilities."""
        self.grid = {
            p_elem: {
                cat: set(self.elements[cat]) for cat in self.categories[1:]
            }
            for p_elem in self.primary_elements
        }
        self.relative_clues_parsed = []

    def _parse_and_apply_clues(self) -> bool:
        """Parses clues and applies initial constraints. Returns False on immediate contradiction."""
        self._initialize_grid()
        # Regex patterns (simplified)
        pattern_positive = re.compile(r"(\w+)\s+(?:is associated with|is)\s+(\w+)\.?$", re.IGNORECASE)
        pattern_negative_entity = re.compile(r"(\w+)\s+(?:is not associated with|is not)\s+(\w+)\.?$", re.IGNORECASE)
        pattern_relative_positive = re.compile(r"The\s+\w+\s+associated with\s+(\w+)\s*(?:\((\w+)\))?\s+is also associated with\s+(\w+)\s*(?:\((\w+)\))?\s*\.?$", re.IGNORECASE)
        pattern_relative_negative = re.compile(r"The\s+\w+\s+associated with\s+(\w+)\s*(?:\((\w+)\))?\s+is NOT associated with\s+(\w+)\s*(?:\((\w+)\))?\s*\.?$", re.IGNORECASE)

        for clue in self.clues:
            applied = False
            # Positive
            match_pos = pattern_positive.match(clue)
            if match_pos:
                e1, e2 = match_pos.groups()
                cat1, cat2 = self._find_categories(e1, e2)
                if cat1 == self.primary_category and cat2:
                    if not self._apply_direct_positive(e1, cat2, e2): return False
                    applied = True
                elif cat2 == self.primary_category and cat1:
                    if not self._apply_direct_positive(e2, cat1, e1): return False
                    applied = True

            # Negative
            match_neg = pattern_negative_entity.match(clue)
            if not applied and match_neg:
                e1, e2 = match_neg.groups()
                cat1, cat2 = self._find_categories(e1, e2)
                if cat1 == self.primary_category and cat2:
                    if not self._apply_direct_negative(e1, cat2, e2): return False
                    applied = True
                elif cat2 == self.primary_category and cat1:
                     if not self._apply_direct_negative(e2, cat1, e1): return False
                     applied = True

            # Relative Positive
            match_rel_pos = pattern_relative_positive.match(clue)
            if not applied and match_rel_pos:
                e1, c1, e2, c2 = match_rel_pos.groups()
                c1, c2 = c1 or self._find_category(e1), c2 or self._find_category(e2) # Infer category if not provided
                if c1 and c2 and e1 in self.elements.get(c1,[]) and e2 in self.elements.get(c2,[]):
                    self.relative_clues_parsed.append(("relative_positive", e1, c1, e2, c2))
                    applied = True

            # Relative Negative
            match_rel_neg = pattern_relative_negative.match(clue)
            if not applied and match_rel_neg:
                 e1, c1, e2, c2 = match_rel_neg.groups()
                 c1, c2 = c1 or self._find_category(e1), c2 or self._find_category(e2)
                 if c1 and c2 and e1 in self.elements.get(c1,[]) and e2 in self.elements.get(c2,[]):
                     self.relative_clues_parsed.append(("relative_negative", e1, c1, e2, c2))
                     applied = True

            # if not applied and "hint" not in clue.lower():
            #     logging.debug(f"Verifier could not parse clue: '{clue}'")

        return True

    def _find_category(self, element: str) -> Optional[str]:
        """Finds the category of a single element."""
        for cat, elems in self.elements.items():
            if element in elems:
                return cat
        return None

    def _find_categories(self, item1: str, item2: str) -> Tuple[Optional[str], Optional[str]]:
        """Find which categories item1 and item2 belong to."""
        return self._find_category(item1), self._find_category(item2)

    def _apply_direct_positive(self, primary_elem: str, other_category: str, value: str) -> bool:
        """Applies a confirmed positive link. Returns False on contradiction."""
        if primary_elem not in self.primary_elements or other_category not in self.elements or value not in self.elements.get(other_category,[]):
            return True # Ignore invalid data

        current_possibilities = self.grid[primary_elem][other_category]
        if value not in current_possibilities: return False # Contradiction
        if len(current_possibilities) == 1: return True # Already set

        self.grid[primary_elem][other_category] = {value}
        for other_p_elem in self.primary_elements:
            if other_p_elem != primary_elem:
                if not self._apply_direct_negative(other_p_elem, other_category, value):
                    return False
        return True

    def _apply_direct_negative(self, primary_elem: str, other_category: str, value_to_exclude: str) -> bool:
        """Applies a confirmed negative link. Returns False on contradiction."""
        if primary_elem not in self.primary_elements or other_category not in self.elements or value_to_exclude not in self.elements.get(other_category,[]):
            return True

        current_possibilities = self.grid[primary_elem][other_category]
        if value_to_exclude in current_possibilities:
            current_possibilities.remove(value_to_exclude)
            if not current_possibilities: return False # Contradiction
        return True

    def _propagate_constraints(self) -> bool:
        """Iteratively applies deductions until no further changes occur. Returns False on contradiction."""
        changed = True
        while changed:
            changed = False
            # Deduction 1: Unique Value Found
            for p_elem in self.primary_elements:
                for category, possibilities in self.grid[p_elem].items():
                    if len(possibilities) == 1:
                        confirmed_value = list(possibilities)[0]
                        for other_p_elem in self.primary_elements:
                            if other_p_elem != p_elem:
                                if confirmed_value in self.grid[other_p_elem][category]:
                                    self.grid[other_p_elem][category].remove(confirmed_value)
                                    if not self.grid[other_p_elem][category]: return False
                                    changed = True

            # Deduction 2: Unique Entity Found
            for category in self.categories[1:]:
                 for value in self.elements[category]:
                      possible_entities = [p for p in self.primary_elements if value in self.grid[p][category]]
                      if len(possible_entities) == 1:
                          unique_entity = possible_entities[0]
                          if len(self.grid[unique_entity][category]) > 1:
                              if not self._apply_direct_positive(unique_entity, category, value): return False
                              changed = True
                      elif not possible_entities: # Value has no possible entity
                          is_assigned = any(len(self.grid[p][category])==1 and list(self.grid[p][category])[0]==value for p in self.primary_elements)
                          if not is_assigned: return False # Contradiction

            # Deduction 3: Apply Relative Clues
            for type, e1, c1, e2, c2 in self.relative_clues_parsed:
                 primary_for_e1 = [p for p in self.primary_elements if c1==self.primary_category and p==e1 or c1!=self.primary_category and e1 in self.grid[p][c1]]
                 if len(primary_for_e1) == 1:
                      assoc_p = primary_for_e1[0]
                      if type == "relative_positive":
                           if not self._apply_direct_positive(assoc_p, c2, e2): return False
                      else: # relative_negative
                           if not self._apply_direct_negative(assoc_p, c2, e2): return False

                 primary_for_e2 = [p for p in self.primary_elements if c2==self.primary_category and p==e2 or c2!=self.primary_category and e2 in self.grid[p][c2]]
                 if len(primary_for_e2) == 1:
                      assoc_p = primary_for_e2[0]
                      if type == "relative_positive":
                           if not self._apply_direct_positive(assoc_p, c1, e1): return False
                      else: # relative_negative
                           if not self._apply_direct_negative(assoc_p, c1, e1): return False

        return True

    def _is_solved(self) -> bool:
        """Checks if the grid is completely and uniquely determined."""
        for p_elem in self.primary_elements:
            for category in self.categories[1:]:
                if len(self.grid[p_elem][category]) != 1: return False
        for category in self.categories[1:]:
            if len({list(self.grid[p][category])[0] for p in self.primary_elements}) != self.grid_size: return False
        return True

    def get_solution(self) -> Optional[Dict[str, Dict[str, str]]]:
        """Returns the solved grid if verification was successful and unique."""
        if not self._is_solved(): return None
        return {p: {cat: list(poss)[0] for cat, poss in data.items()} for p, data in self.grid.items()}

    def verify(self) -> Tuple[bool, Optional[Dict[str, Dict[str, str]]]]:
        """Attempts to solve the logic grid using the provided clues."""
        if not self._parse_and_apply_clues(): return False, None
        if not self._propagate_constraints(): return False, None
        if self._is_solved(): return True, self.get_solution()
        return False, None


class PuzzleVerifier:
    """Verifies either Symbol Cipher or Logic Grid puzzles for unique solvability."""
    MAX_PERMUTATION_ELEMENTS = 9 # Reduced limit for faster feedback

    def __init__(self, puzzle_type: str, **kwargs):
        self.puzzle_type = puzzle_type
        self.kwargs = kwargs
        if puzzle_type == 'symbol':
            self.symbols = kwargs.get('symbols')
            self.letters = kwargs.get('letters')
            self.clues = kwargs.get('clues')
            if not all([self.symbols, self.letters, self.clues is not None]): raise ValueError("Missing args for symbol verification.")
            self.num_elements = len(self.symbols)
            if len(self.letters) != self.num_elements: raise ValueError("Symbol/letter count mismatch.")
        elif puzzle_type == 'logic_grid':
            self.categories = kwargs.get('categories')
            self.elements = kwargs.get('elements')
            self.clues = kwargs.get('clues') # List[str]
            if not all([self.categories, self.elements, self.clues is not None]): raise ValueError("Missing args for logic grid verification.")
            self.logic_grid_verifier = _LogicGridInternalVerifier(self.categories, self.elements, self.clues)
        else: raise ValueError(f"Unsupported puzzle_type: {puzzle_type}")

    def verify(self) -> Tuple[bool, Union[List[Dict[str, str]], Optional[Dict[str, Dict[str, str]]]]]:
        """Verifies the puzzle based on its type."""
        if self.puzzle_type == 'symbol':
            return self._verify_symbol_puzzle()
        elif self.puzzle_type == 'logic_grid':
            return self.logic_grid_verifier.verify()
        return False, None # Should not be reached

    def _verify_symbol_puzzle(self) -> Tuple[bool, List[Dict[str, str]]]:
        """Finds all valid solutions for a symbol cipher puzzle."""
        if self.num_elements > self.MAX_PERMUTATION_ELEMENTS:
            logging.warning(f"Symbol puzzle size ({self.num_elements}) exceeds verification limit ({self.MAX_PERMUTATION_ELEMENTS}). Skipping.")
            return False, [] # Cannot verify uniqueness

        valid_solutions = []
        letter_permutations = itertools.permutations(self.letters)
        for p_letters in letter_permutations:
            potential_mapping = dict(zip(self.symbols, p_letters))
            if self._check_mapping_against_clues(potential_mapping):
                valid_solutions.append(potential_mapping)
                # Optimization: Stop early if > 1 found? Generator might need exact count.
                # if len(valid_solutions) > 1: return False, valid_solutions

        is_unique = (len(valid_solutions) == 1)
        return is_unique, valid_solutions

    def _check_mapping_against_clues(self, mapping: Dict[str, str]) -> bool:
        """Checks if a given mapping satisfies all clues."""
        return all(self._check_single_clue(mapping, clue_text, clue_type) for clue_text, clue_type in self.clues)

    def _check_single_clue(self, mapping: Dict[str, str], clue_text: str, clue_type: ClueType) -> bool:
        """Checks if a specific mapping satisfies a single clue."""
        try:
            if clue_type == ClueType.DIRECT:
                match = re.search(r"'(.+)' directly represents the letter '([A-Z])'", clue_text)
                return match and mapping.get(match.group(1)) == match.group(2)
            elif clue_type == ClueType.EXCLUSION:
                 match = re.search(r"'(.+)' does not represent the letter '([A-Z])'", clue_text)
                 return match and mapping.get(match.group(1)) != match.group(2)
            elif clue_type == ClueType.POSITIONAL:
                 match = re.search(r"the (\w+) symbol represents (a vowel|a consonant)", clue_text)
                 if not match: return False
                 pos_word, cat = match.groups()
                 positions = {"first": 0, "second": 1, "third": 2, "fourth": 3, "fifth": 4, "sixth": 5, "seventh": 6, "eighth": 7, "ninth": 8, "tenth": 9}
                 idx = positions.get(pos_word)
                 if idx is None or idx >= len(self.symbols): return False
                 letter = mapping.get(self.symbols[idx])
                 if not letter: return False
                 is_vowel = letter in VOWELS
                 return (cat == "a vowel" and is_vowel) or (cat == "a consonant" and not is_vowel)
            elif clue_type == ClueType.RELATIONAL:
                 match = re.search(r"letter for '(.+)' comes (earlier|later) .* than the letter for '(.+)'", clue_text)
                 if not match: return False
                 s1, comp, s2 = match.groups()
                 l1, l2 = mapping.get(s1), mapping.get(s2)
                 if not l1 or not l2: return False
                 return (comp == "earlier" and ord(l1) < ord(l2)) or (comp == "later" and ord(l1) > ord(l2))
            elif clue_type == ClueType.CATEGORY:
                 match = re.search(r"'(.+)' represents (a vowel|a consonant)", clue_text)
                 if not match: return False
                 symbol, cat = match.groups()
                 letter = mapping.get(symbol)
                 if not letter: return False
                 is_vowel = letter in VOWELS
                 return (cat == "a vowel" and is_vowel) or (cat == "a consonant" and not is_vowel)
            elif clue_type == ClueType.LOGICAL:
                match = re.search(r"If '(.+)' represents (a vowel|a consonant), then '(.+)' represents (a vowel|a consonant)", clue_text)
                if not match: return False
                s1, prem_cat, s2, conc_cat = match.groups()
                l1, l2 = mapping.get(s1), mapping.get(s2)
                if not l1 or not l2: return False
                premise_true = (l1 in VOWELS if prem_cat == "a vowel" else l1 not in VOWELS)
                if not premise_true: return True # False premise implies true
                conclusion_true = (l2 in VOWELS if conc_cat == "a vowel" else l2 not in VOWELS)
                return conclusion_true # If premise true, result is conclusion
            else:
                logging.warning(f"Unknown clue type '{clue_type}' during verification.")
                return False
        except Exception as e:
            logging.error(f"Error verifying clue '{clue_text}' (Type: {clue_type}): {e}", exc_info=True)
            return False


# --- Helper Class for Scheduling Solver (Simple Backtracking Example) ---
class _SchedulingSolver:
    """Simple backtracking solver to find *a* valid schedule."""
    def __init__(self, people, slots, constraints):
        self.people = people
        self.slots = slots
        self.constraints = constraints
        self.slot_indices = {slot: i for i, slot in enumerate(slots)}

    def find_solution(self):
        assignment = {person: None for person in self.people} # slot assigned to person
        return self._solve(assignment, 0)

    def _solve(self, assignment, person_idx):
        if person_idx == len(self.people):
            # Found a complete assignment, double check constraints involving relationships
            return assignment if self._is_fully_valid(assignment) else None

        person = self.people[person_idx]
        available_slots = list(self.slots) # Start with all slots
        random.shuffle(available_slots)

        for slot in available_slots:
            assignment[person] = slot
            if self._is_partially_valid(assignment, person_idx + 1):
                result = self._solve(assignment, person_idx + 1)
                if result:
                    return result # Solution found down this path
            assignment[person] = None # Backtrack

        return None # No solution found from this state

    def _is_partially_valid(self, assignment, num_assigned):
        """Check constraints only involving the first 'num_assigned' people."""
        assigned_people = self.people[:num_assigned]
        booked_slots = set() # Track slots booked by assigned people

        # Check basic assignment validity and unavailability/must_be for assigned people
        for i in range(num_assigned):
            person = assigned_people[i]
            slot = assignment[person]
            if slot is None: continue # Should not happen if called correctly

            # Check for double booking the same slot among assigned people
            if slot in booked_slots: return False
            booked_slots.add(slot)

            for constraint in self.constraints:
                ctype = constraint[0]
                if ctype == 'unavailable' and constraint[1] == person and constraint[2] == slot: return False
                if ctype == 'must_be' and constraint[1] == person and constraint[2] != slot: return False

        # Check relational constraints involving only assigned people
        for constraint in self.constraints:
            ctype = constraint[0]
            if ctype in ['before', 'together', 'apart']:
                p1, p2 = constraint[1], constraint[2]
                # Only check if both involved people are already assigned
                if p1 in assigned_people and p2 in assigned_people:
                    slot1, slot2 = assignment[p1], assignment[p2]
                    if slot1 is None or slot2 is None: continue # Skip if one isn't assigned yet

                    idx1, idx2 = self.slot_indices.get(slot1, -1), self.slot_indices.get(slot2, -1)

                    if ctype == 'before' and idx1 >= idx2: return False
                    if ctype == 'together' and slot1 != slot2: return False
                    if ctype == 'apart' and slot1 == slot2: return False
        return True

    def _is_fully_valid(self, assignment):
         """Check all constraints for a complete assignment."""
         # Reformat solution to match the expected output format
         final_schedule = {p: {s: "Available" for s in self.slots} for p in self.people}
         booked_map = {}
         for person, slot in assignment.items():
             if slot is None: return False # Incomplete assignment
             for s in self.slots: final_schedule[person][s] = "Unavailable"
             final_schedule[person][slot] = "Booked"
             booked_map[person] = slot

         # Now validate this final_schedule against all constraints
         for constraint in self.constraints:
             ctype = constraint[0]
             if ctype == 'unavailable':
                 if final_schedule[constraint[1]][constraint[2]] == "Booked": return False
             elif ctype == 'must_be':
                  if final_schedule[constraint[1]][constraint[2]] != "Booked": return False
             elif ctype == 'before':
                  p1, p2 = constraint[1], constraint[2]
                  slot1, slot2 = booked_map.get(p1), booked_map.get(p2)
                  if slot1 is None or slot2 is None: return False # Assignment error
                  if self.slot_indices.get(slot1, -1) >= self.slot_indices.get(slot2, -1): return False
             elif ctype == 'together':
                  p1, p2 = constraint[1], constraint[2]
                  slot1, slot2 = booked_map.get(p1), booked_map.get(p2)
                  if slot1 is None or slot2 is None: return False
                  if slot1 != slot2: return False
             elif ctype == 'apart':
                  p1, p2 = constraint[1], constraint[2]
                  slot1, slot2 = booked_map.get(p1), booked_map.get(p2)
                  if slot1 is None or slot2 is None: return False
                  if slot1 == slot2: return False

         # Return the schedule in the desired format if valid
         return final_schedule