from typing import Dict, List, Tuple, Optional, Any, Union, Set, Callable
import random
import logging
import json
import os
import sys # Import sys

# Relative imports for components within the puzzle package
from .common import HumanScenarioType, ClueType, SYMBOLS_POOL, LETTERS_POOL, VOWELS, CONSONANTS
from .puzzle_types import Puzzle, ScenarioPuzzle
from .verifier import PuzzleVerifier # Needed for symbol puzzle verification call
# from utils import resource_path # Removed import

# Import specific generator functions
from .generators import (
    symbol_cipher_gen,
    logic_grid_gen,
    social_deduction_gen,
    common_sense_gen,
    relationship_map_gen,
    ordering_gen,
    scheduling_gen,
    dilemma_gen,
    agent_simulation_gen
)

# Setup logging
logger = logging.getLogger(__name__)

# Define DATA_DIR directly using sys._MEIPASS check
try:
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    base_path = sys._MEIPASS
except AttributeError:
    # Not frozen, assume running from dev environment (resolve relative to project root)
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(base_path, "game_data")

# Validate DATA_DIR exists
if not os.path.isdir(DATA_DIR):
    logger.error(f"FATAL: Could not find game_data directory at resolved path: {DATA_DIR} (Base: {base_path})")
    raise FileNotFoundError(f"Could not locate the game_data directory at: {DATA_DIR}")

class PuzzleGenerator:
    """Generates verified Symbol Cipher OR human-centric Scenario puzzles."""

    # Scenario settings
    SCENARIO_START_LEVEL = 3
    HUMAN_SCENARIO_CHANCE_INCREASE = 0.15
    MAX_HUMAN_SCENARIO_CHANCE = 0.80
    MAX_GENERATION_ATTEMPTS = 10 # For specific scenario types when one fails

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
        self.symbols_pool = SYMBOLS_POOL
        self.letters_pool = LETTERS_POOL
        clamped_max = min(max_elements, len(self.symbols_pool), len(self.letters_pool))
        if clamped_max < max_elements:
            logger.warning(f"max_elements ({max_elements}) exceeds symbol/letter pool size. Clamping to {clamped_max}.")
            max_elements = clamped_max
        if min_elements > max_elements:
            # This should only happen if min_elements was initially > clamped_max
            min_elements = clamped_max
            logger.warning(f"min_elements was greater than clamped max_elements. Setting min_elements to {min_elements}.")
            # Original check: raise ValueError(f"min_elements ({min_elements}) exceeds clamped max_elements ({max_elements}).")

        self.min_symbol_elements = min_elements
        self.max_symbol_elements = max_elements
        self.max_verification_tries = max_tries # Used by symbol gen

        # Load scenario data pools from JSON files
        self._load_scenario_data()

        # Map Scenario Types to their generation functions
        self._generation_function_map: Dict[HumanScenarioType, Callable] = {
            HumanScenarioType.LOGIC_GRID: logic_grid_gen.generate_logic_grid_puzzle_internal,
            HumanScenarioType.AGENT_SIMULATION: agent_simulation_gen.generate_agent_simulation_puzzle_internal,
            HumanScenarioType.SOCIAL_DEDUCTION: social_deduction_gen.generate_social_deduction_puzzle_internal,
            HumanScenarioType.COMMON_SENSE_GAP: common_sense_gen.generate_common_sense_gap_puzzle_internal,
            HumanScenarioType.RELATIONSHIP_MAP: relationship_map_gen.generate_relationship_map_puzzle_internal,
            HumanScenarioType.ORDERING: ordering_gen.generate_ordering_puzzle_internal,
            HumanScenarioType.SCHEDULING: scheduling_gen.generate_scheduling_puzzle_internal,
            HumanScenarioType.DILEMMA: dilemma_gen.generate_dilemma_puzzle_internal,
        }
        self._generatable_scenario_types = list(self._generation_function_map.keys())

    def _load_data_from_json(self, filename: str) -> Union[Dict, List]:
        """Helper to load data from a JSON file in the DATA_DIR."""
        filepath = os.path.join(DATA_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Data file not found: {filepath}")
            # Propagate error upwards, as data is critical
            raise FileNotFoundError(f"Required data file missing: {filepath}")
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {filepath}: {e}")
            raise ValueError(f"Invalid JSON format in {filepath}")
        except Exception as e:
            logger.error(f"Unexpected error loading data from {filepath}: {e}")
            raise # Re-raise other unexpected errors

    def _load_scenario_data(self):
        """Loads all necessary scenario data pools from JSON files."""
        # Make pools instance variables for access by generators
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
                 logger.warning("One or more essential common data pools (Names, Traits, Settings) are empty after loading.")
            if not self.LOGIC_GRID_THEMES: logger.warning("Logic Grid themes data pool is empty.")
            if not self.DILEMMA_SCENARIOS: logger.warning("Dilemma scenarios data pool is empty.")
            if not self.COMMON_SENSE_ITEMS: logger.warning("Common Sense scenarios data pool is empty.")
            if not self.AGENT_SIMULATION_RULES: logger.warning("Agent Simulation rules data pool is empty.")
            # Add more checks as needed

        except (FileNotFoundError, ValueError) as e:
            logger.critical(f"Fatal error loading critical game data: {e}", exc_info=True)
            # Application cannot proceed without data
            raise RuntimeError("Failed to load essential game data. Cannot continue.") from e

    def generate_puzzle(self, level: int, force_type: Optional[Union[str, HumanScenarioType]] = None) -> Union[Puzzle, ScenarioPuzzle]:
        """Generates either a symbol cipher or a human scenario puzzle based on level and forced type."""
        logger.info(f"Generating puzzle for Level {level}. Forced type: {force_type}")

        # --- Handle Forced Type ---
        if force_type == "Symbol":
            return self._attempt_generation(self._generate_symbol_puzzle, level, "Symbol")
        elif isinstance(force_type, HumanScenarioType):
            if force_type not in self._generation_function_map:
                 logger.error(f"Forced scenario type {force_type.name} has no generation function mapped.")
                 raise ValueError(f"Cannot generate unsupported scenario type: {force_type.name}")
            gen_func = self._generation_function_map[force_type]
            # Pass data pools to the specific generator function
            return self._attempt_generation(gen_func, level, f"Scenario ({force_type.name})",
                                            puzzle_type=force_type, generator_instance=self) # Pass self for data access
        elif force_type == "Scenario": # Random Scenario
            return self._attempt_generation(self._generate_human_scenario_puzzle, level, "Scenario (Random)", specific_type=None)

        # --- Level-Based Probability ---
        scenario_chance = 0.0
        if level >= self.SCENARIO_START_LEVEL:
             scenario_chance = min(0.2 + (level - self.SCENARIO_START_LEVEL) * self.HUMAN_SCENARIO_CHANCE_INCREASE, self.MAX_HUMAN_SCENARIO_CHANCE)
        logger.debug(f"Level {level}: Scenario chance = {scenario_chance:.2f}")

        if random.random() < scenario_chance:
            # Try Scenario first, fallback to Symbol
            logger.debug("Trying Scenario generation first.")
            try:
                return self._generate_human_scenario_puzzle(level, specific_type=None)
            except Exception as e:
                logger.warning(f"Scenario generation failed (Level {level}): {e}. Falling back to Symbol.", exc_info=True)
                return self._generate_symbol_puzzle(level) # Fallback guarantees a Puzzle or raises its own error
        else:
            # Try Symbol first, fallback to Scenario
            logger.debug("Trying Symbol generation first.")
            try:
                return self._generate_symbol_puzzle(level)
            except Exception as e:
                 logger.warning(f"Symbol generation failed (Level {level}): {e}. Falling back to Scenario.", exc_info=True)
                 # Ensure fallback scenario generation is attempted
                 return self._generate_human_scenario_puzzle(level, specific_type=None) # Fallback

    def _attempt_generation(self, generation_func: Callable, level: int, type_name: str, **gen_kwargs) -> Union[Puzzle, ScenarioPuzzle]:
        """Helper to attempt generation and handle errors."""
        try:
            # Pass necessary instance variables (like data pools) to the static methods if needed
            # Or pass 'self' if the generator methods need other instance state
            if 'generator_instance' in gen_kwargs: # Scenario generators might need 'self'
                 return generation_func(level=level, **gen_kwargs)
            else: # Symbol generator is simpler
                 return generation_func(level=level, generator_instance=self, **gen_kwargs)
        except Exception as e:
            logger.error(f"Error explicitly generating {type_name} puzzle (Level {level}): {e}", exc_info=True)
            # If forced generation fails, raise an error to indicate it couldn't fulfill the request
            raise ValueError(f"Failed to generate requested puzzle type '{type_name}'.") from e

    def _generate_symbol_puzzle(self, level: int, **kwargs) -> Puzzle:
        """Generates a verified symbol cipher puzzle by calling the specific generator."""
        # Passes necessary parameters from self to the static/external generation function
        return symbol_cipher_gen.generate_symbol_puzzle_internal(
            level=level,
            min_elements=self.min_symbol_elements,
            max_elements=self.max_symbol_elements,
            symbols_pool=self.symbols_pool,
            letters_pool=self.letters_pool,
            vowels=VOWELS,
            consonants=CONSONANTS,
            max_verification_tries=self.max_verification_tries
        )

    def _generate_human_scenario_puzzle(self, level: int, specific_type: Optional[HumanScenarioType] = None) -> ScenarioPuzzle:
        """Generates a human-centric scenario puzzle. If specific_type is None, chooses randomly."""
        if not self._generatable_scenario_types:
             logger.error("No scenario types available for generation.")
             raise ValueError("No scenario puzzle types are configured for generation.")

        chosen_type = specific_type
        if not chosen_type:
             chosen_type = random.choice(self._generatable_scenario_types)
        elif chosen_type not in self._generation_function_map:
            logger.warning(f"Requested scenario type {chosen_type.name} cannot be generated. Choosing random.")
            chosen_type = random.choice(self._generatable_scenario_types)

        logger.info(f"Attempting internal generation for puzzle type: {chosen_type.name}")
        generator_func = self._generation_function_map[chosen_type]

        for attempt in range(self.MAX_GENERATION_ATTEMPTS):
            try:
                # Pass 'self' to provide access to loaded data pools (SCENARIO_NAMES etc.)
                puzzle = generator_func(level=level, puzzle_type=chosen_type, generator_instance=self)
                # Optionally add verification step here if specific verifiers exist
                # puzzle.is_verified = self._verify_scenario(puzzle) # Example placeholder
                logger.info(f"Successfully generated {chosen_type.name} puzzle.")
                return puzzle
            except NotImplementedError:
                logger.error(f"Generation function for {chosen_type.name} is marked as not implemented.")
                raise # Re-raise if it's explicitly not implemented
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed to generate {chosen_type.name}: {e}", exc_info=True)
                if attempt < self.MAX_GENERATION_ATTEMPTS - 1:
                     # If not the last attempt, maybe try the same type again or switch?
                     # For now, let's stick to the chosen type until max attempts.
                     pass
                else: # Last attempt failed
                    # Fallback Logic - Choose a different type
                    fallback_types = [t for t in self._generatable_scenario_types if t != chosen_type]
                    if not fallback_types: # Should not happen if more than one type exists
                        logger.error(f"Generation failed for {chosen_type.name} and no fallback types exist.")
                        raise ValueError(f"Failed to generate primary type {chosen_type.name} and no fallback available.")

                    fallback_choice = random.choice(fallback_types)
                    logger.warning(f"Max attempts failed for {chosen_type.name}. Falling back to generate type: {fallback_choice.name}")
                    fallback_func = self._generation_function_map[fallback_choice]
                    try:
                        # Try fallback generation once
                        puzzle = fallback_func(level=level, puzzle_type=fallback_choice, generator_instance=self)
                        # puzzle.is_verified = self._verify_scenario(puzzle) # Placeholder verification
                        logger.info(f"Successfully generated fallback {fallback_choice.name} puzzle.")
                        return puzzle
                    except Exception as fallback_e:
                        logger.exception(f"Fallback generation for {fallback_choice.name} also failed.")
                        raise ValueError(f"Failed to generate primary type {chosen_type.name} and fallback type {fallback_choice.name}.") from fallback_e

        # This line should technically be unreachable if logic above is correct
        raise ValueError("Failed to generate any scenario puzzle after multiple attempts and fallbacks.")

    # Removed specific _generate_X_puzzle methods as they are now in puzzle/generators/