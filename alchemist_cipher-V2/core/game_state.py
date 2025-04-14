import json
import os
import sys # Import sys
from typing import Dict, Optional, Set, Union, Any, Tuple, List
from enum import Enum
import logging
import random
import time

# Corrected relative imports based on the new structure
from puzzle.puzzle_types import Puzzle, ScenarioPuzzle
from puzzle.generator import PuzzleGenerator
from puzzle.common import HumanScenarioType, ClueType
# from utils import resource_path # Removed import

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define SAVE_FILE_PATH directly using sys._MEIPASS check
SAVE_FILE_NAME = "alchemist_cipher_save.json"
try:
    # Running frozen (PyInstaller)
    base_path = sys._MEIPASS
except AttributeError:
    # Running not frozen (dev environment)
    base_path = os.path.abspath(".")
SAVE_FILE_PATH = os.path.join(base_path, SAVE_FILE_NAME)

class GameState:
    # SAVE_FILE = "alchemist_cipher_save.json" # Removed old constant
    SAVE_VERSION = 3 # Increment version due to adding solver name

    def __init__(self):
        self.current_level = 0
        self.user_mapping: Dict[str, str] = {} # For symbol puzzles
        self.scenario_user_state: Optional[Dict[str, Any]] = None # For scenario puzzles
        self.hints_used_this_level = 0
        self.max_hints_per_level = 2
        self.puzzles_solved = 0
        self.current_theme = "Default"
        self.unlocked_themes: Set[str] = {"Default"}
        self.current_puzzle: Optional[Union[Puzzle, ScenarioPuzzle]] = None
        # Instantiate PuzzleGenerator here
        try:
             self.puzzle_generator = PuzzleGenerator()
        except (FileNotFoundError, ValueError, RuntimeError) as e:
            logging.critical(f"CRITICAL: Failed to initialize PuzzleGenerator: {e}. Game may not function.")
            # Decide how to handle this - maybe raise, or set generator to None and check later?
            self.puzzle_generator = None # Indicate failure
            # raise RuntimeError("Failed to load critical puzzle generation data.") from e # Or raise

        self.save_version = self.SAVE_VERSION
        # --- AI Solver Config ---
        self.selected_solver_name = "Internal (Perfect)" # Default solver
        self.solver_configs: Dict[str, Dict[str, Any]] = {} # Store API keys etc. {solver_name: {config_key: value}}
        # ---

    def save_game(self) -> None:
        """Saves the current game state, handling both puzzle types and potential errors."""
        puzzle_data = None
        puzzle_type_name = None
        user_state = None
        state = {} # Initialize state dict

        try:
            # Ensure current_puzzle is valid before accessing attributes
            if not self.current_puzzle:
                logging.info("Attempted to save game with no active puzzle. Saving core state only.")
                # Puzzle state will remain None

            elif isinstance(self.current_puzzle, Puzzle) and not self.current_puzzle.is_scenario:
                puzzle_type_name = "SymbolCipher"
                try:
                    serializable_clues = [(text, c_type.name) for text, c_type in self.current_puzzle.clues]
                    puzzle_data = {
                        "level": self.current_puzzle.level,
                        "symbols": self.current_puzzle.symbols,
                        "letters": self.current_puzzle.letters,
                        "solution_mapping": self.current_puzzle.solution_mapping,
                        "clues": serializable_clues,
                        "is_verified": getattr(self.current_puzzle, 'is_verified', False) # Use getattr for safety
                    }
                    user_state = self.user_mapping
                except AttributeError as e:
                     logging.error(f"Error accessing attributes of Symbol Puzzle during save: {e}")
                     puzzle_data = None # Don't save corrupted data
                     puzzle_type_name = None
            elif isinstance(self.current_puzzle, ScenarioPuzzle):
                puzzle_type_name = "Scenario"
                try:
                    puzzle_data = {
                        "level": self.current_puzzle.level,
                        "puzzle_type": self.current_puzzle.puzzle_type.name,
                        "description": self.current_puzzle.description,
                        "characters": self.current_puzzle.characters,
                        "setting": self.current_puzzle.setting,
                        "goal": self.current_puzzle.goal,
                        "information": self.current_puzzle.information,
                        "solution": self.current_puzzle.solution,
                        "rules": getattr(self.current_puzzle, 'rules', None),
                        "options": getattr(self.current_puzzle, 'options', None), # Save options for Dilemma
                        "is_verified": getattr(self.current_puzzle, 'is_verified', False), # Save verification status
                        # Save elements specifically for LogicGrid reconstruction (if exists)
                        "elements": getattr(self.current_puzzle, 'elements', None)
                    }
                    user_state = self.scenario_user_state
                except AttributeError as e:
                    logging.error(f"Error accessing attributes of Scenario Puzzle during save: {e}")
                    puzzle_data = None # Don't save corrupted data
                    puzzle_type_name = None
            else:
                 logging.warning(f"Attempted to save an unknown puzzle type: {type(self.current_puzzle)}")
                 puzzle_type_name = None
                 puzzle_data = None

            # Base state dictionary
            state = {
                "save_version": self.save_version,
                "current_level": self.current_level,
                "hints_used_this_level": self.hints_used_this_level,
                "puzzles_solved": self.puzzles_solved,
                "current_theme": self.current_theme,
                "unlocked_themes": list(self.unlocked_themes),
                # --- Save AI Solver State ---
                "selected_solver_name": self.selected_solver_name,
                "solver_configs": self.solver_configs, # Note: Saves potentially sensitive info if keys stored here!
                # ---
                # Puzzle state (might be None if no puzzle active or error occurred)
                "current_puzzle_type": puzzle_type_name,
                "current_puzzle_data": puzzle_data,
                "user_state": user_state
            }

            # Use the calculated SAVE_FILE_PATH
            with open(SAVE_FILE_PATH, 'w') as f:
                json.dump(state, f, indent=4)
            logging.info(f"Game state saved successfully to {SAVE_FILE_PATH}")

        except IOError as e:
            logging.error(f"Could not save game state to {SAVE_FILE_PATH}: {e}")
            raise IOError(f"Could not save game state: {e}")
        except TypeError as e:
            # Attempt to serialize state even on error for debugging
            safe_state = {}
            for k, v in state.items():
                try:
                    json.dumps({k: v}) # Test serialization
                    safe_state[k] = v
                except TypeError:
                    safe_state[k] = f"!!UNSERIALIZABLE ({type(v)})!!"
            logging.error(f"Could not serialize game state: {e}. Partially Serializable State details: {safe_state}")
            raise TypeError(f"Could not serialize game state: {e}")
        except Exception as e:
            logging.exception(f"An unexpected error occurred during game save.")
            raise

    def load_game(self) -> None:
        """Loads game state with improved error handling, validation, and defaults."""
        # Use the calculated SAVE_FILE_PATH
        if not os.path.exists(SAVE_FILE_PATH):
            logging.info(f"Save file '{SAVE_FILE_PATH}' not found. Starting new game state.")
            # Ensure generator is initialized if not already done (or if it failed before)
            if self.puzzle_generator is None:
                try:
                    self.puzzle_generator = PuzzleGenerator()
                except Exception as e:
                    logging.critical(f"CRITICAL: Failed to initialize PuzzleGenerator during load: {e}.")
                    # Handle this critical error appropriately
            return

        state = None
        try:
            # Use the calculated SAVE_FILE_PATH
            with open(SAVE_FILE_PATH, 'r') as f:
                state = json.load(f)
            logging.info(f"Loaded game state from {SAVE_FILE_PATH}")

            loaded_version = state.get("save_version", 0)
            # --- Version Migration Logic ---
            if loaded_version < self.SAVE_VERSION:
                 logging.warning(f"Loading older save file version ({loaded_version} vs current {self.SAVE_VERSION}). Migrating...")
                 # Example: Migration for V3 (adding solver fields)
                 if loaded_version < 3:
                     state["selected_solver_name"] = self.selected_solver_name # Default from __init__
                     state["solver_configs"] = self.solver_configs # Default from __init__
                 # Add more migration steps here if needed for future versions
                 state["save_version"] = self.SAVE_VERSION # Update version after migration
                 logging.info("Save file migrated to current version.")
            elif loaded_version > self.SAVE_VERSION:
                 logging.error(f"Save file version ({loaded_version}) is newer than game version ({self.SAVE_VERSION}). Cannot load safely.")
                 raise RuntimeError("Save file is from a newer version of the game.")

            # --- Load core state with robust defaults ---
            self.current_level = state.get("current_level", 0)
            self.hints_used_this_level = state.get("hints_used_this_level", 0)
            self.puzzles_solved = state.get("puzzles_solved", 0)
            self.current_theme = state.get("current_theme", "Default")
            loaded_themes = state.get("unlocked_themes", ["Default"])
            self.unlocked_themes = set(loaded_themes) if isinstance(loaded_themes, list) else {"Default"}
            self.save_version = state.get("save_version", self.SAVE_VERSION) # Use loaded version if present and valid

            # --- Load AI Solver State ---
            self.selected_solver_name = state.get("selected_solver_name", "Internal (Perfect)") # Apply default if missing
            loaded_configs = state.get("solver_configs", {})
            self.solver_configs = loaded_configs if isinstance(loaded_configs, dict) else {}
            # ---

            # Reset puzzle/user state before loading
            self.current_puzzle = None
            self.user_mapping = {}
            self.scenario_user_state = None

            puzzle_type_name = state.get("current_puzzle_type")
            puzzle_data = state.get("current_puzzle_data")
            user_state = state.get("user_state")

            if not puzzle_type_name or not puzzle_data:
                logging.warning("Save file missing puzzle type or data. No puzzle loaded.")
                return

            # --- Reconstruct Puzzle (Symbol or Scenario) ---
            if puzzle_type_name == "SymbolCipher":
                try:
                    self._reconstruct_symbol_puzzle(puzzle_data, user_state)
                    logging.info("Successfully loaded SymbolCipher puzzle.")
                except (KeyError, TypeError, ValueError) as e:
                    logging.error(f"Failed to reconstruct SymbolCipher puzzle from data: {e}. Data: {puzzle_data}")
                    self.current_puzzle = None # Ensure puzzle is None on failure

            elif puzzle_type_name == "Scenario":
                try:
                    self._reconstruct_scenario_puzzle(puzzle_data, user_state)
                    if self.current_puzzle: # Check if reconstruction was successful
                        logging.info(f"Successfully loaded Scenario puzzle: {self.current_puzzle.puzzle_type.name}")
                except (KeyError, TypeError, ValueError) as e:
                    logging.error(f"Failed to reconstruct Scenario puzzle from data: {e}. Data: {puzzle_data}")
                    self.current_puzzle = None # Ensure puzzle is None on failure
            else:
                 logging.warning(f"Unknown puzzle type '{puzzle_type_name}' found in save file.")
                 self.current_puzzle = None

        except FileNotFoundError:
             logging.info(f"Save file '{SAVE_FILE_PATH}' not found.")
             self.__init__() # Re-initialize to get defaults
        except (IOError, json.JSONDecodeError) as e:
            logging.error(f"Error reading or parsing save file '{SAVE_FILE_PATH}': {e}")
            self.__init__() # Reset to defaults
            logging.info("Game state reset to default due to load error.")
        except Exception as e:
             logging.exception(f"Unexpected error loading game state.")
             self.__init__() # Reset to defaults
             logging.info("Game state reset to default due to unexpected load error.")

    def _reconstruct_clues(self, raw_clues: Any) -> List[Tuple[str, ClueType]]:
        """Helper to safely reconstruct clues list from loaded data."""
        reconstructed_clues = []
        if not isinstance(raw_clues, list):
            logging.warning(f"Clues data is not a list: {raw_clues}. Skipping clues.")
            return []

        for item in raw_clues:
            if isinstance(item, list) and len(item) == 2 and isinstance(item[0], str) and isinstance(item[1], str):
                try:
                    clue_type = ClueType[item[1]]
                    reconstructed_clues.append((item[0], clue_type))
                except KeyError:
                    logging.warning(f"Unknown ClueType '{item[1]}' in save file. Skipping clue: {item[0]}")
            else:
                logging.warning(f"Malformed clue data in save file: {item}. Skipping.")
        return reconstructed_clues

    def _reconstruct_symbol_puzzle(self, puzzle_data: Dict, user_state: Any) -> None:
        """Helper to reconstruct a Symbol Puzzle object."""
        required_fields = ["level", "symbols", "letters", "solution_mapping", "clues"]
        if not all(field in puzzle_data for field in required_fields):
             raise ValueError("Missing required fields in saved SymbolCipher puzzle data.")

        reconstructed_clues = self._reconstruct_clues(puzzle_data["clues"])
        self.current_puzzle = Puzzle(
            level=puzzle_data["level"],
            symbols=puzzle_data["symbols"],
            letters=puzzle_data["letters"],
            solution_mapping=puzzle_data["solution_mapping"],
            clues=reconstructed_clues,
            is_verified=puzzle_data.get("is_verified", False) # Load verification status
        )
        if isinstance(user_state, dict):
             # Validate keys and values for user_mapping
             valid_user_mapping = {k: v for k, v in user_state.items()
                                    if isinstance(k, str) and k in self.current_puzzle.symbols and
                                       isinstance(v, str) and (v == "" or v in self.current_puzzle.letters)}
             if len(valid_user_mapping) != len(user_state):
                logging.warning("Invalid keys/values found in loaded user_mapping for SymbolCipher, resetting partially.")
             self.user_mapping = valid_user_mapping
        else:
             logging.warning("Invalid user_state for SymbolCipher, resetting.")
             self.user_mapping = {}

    def _reconstruct_scenario_puzzle(self, puzzle_data: Dict, user_state: Any) -> None:
        """Helper to reconstruct a Scenario Puzzle object."""
        puzzle_type_str = puzzle_data.get("puzzle_type")
        if not isinstance(puzzle_type_str, str):
            raise ValueError("Missing or invalid 'puzzle_type' string in scenario data.")
        try:
            puzzle_type_enum = HumanScenarioType[puzzle_type_str]
        except KeyError:
            raise ValueError(f"Unknown ScenarioPuzzleType '{puzzle_type_str}' in save file.")

        # Validate required fields common to all scenarios
        required_fields = ["level", "description", "characters", "setting", "goal", "information", "solution"]
        if not all(field in puzzle_data for field in required_fields):
             raise ValueError(f"Missing required fields in saved Scenario puzzle data. Found: {list(puzzle_data.keys())}")

        # Handle 'elements' which might be None if not a logic grid or saved before V.X
        elements_data = puzzle_data.get("elements")

        # Create ScenarioPuzzle instance
        self.current_puzzle = ScenarioPuzzle(
             level=puzzle_data["level"],
             puzzle_type=puzzle_type_enum,
             description=puzzle_data["description"],
             characters=puzzle_data.get("characters", []), # Default to empty list
             setting=puzzle_data.get("setting", {}), # Default to empty dict
             goal=puzzle_data["goal"],
             information=puzzle_data.get("information", []), # Default to empty list
             solution=puzzle_data["solution"],
             rules=puzzle_data.get("rules"), # None if not present
             options=puzzle_data.get("options"), # None if not present
             elements=elements_data, # Pass loaded elements data
             is_verified=puzzle_data.get("is_verified", False) # Default to False
         )

        # Restore user state safely
        if isinstance(user_state, dict):
             # Add validation if specific structures are expected for user_state per scenario type
             self.scenario_user_state = user_state
        else:
             logging.warning(f"Invalid user_state for Scenario, resetting.")
             self.scenario_user_state = None


    def start_new_puzzle(self, puzzle_type: Optional[Union[str, HumanScenarioType]] = None) -> None:
        """Generates and starts a new puzzle, ensuring it's verified if possible."""
        if self.puzzle_generator is None:
             logging.critical("Puzzle generator is not available. Cannot start new puzzle.")
             raise RuntimeError("Cannot generate puzzle: Puzzle Generator failed to initialize.")

        try:
            # Delegate the actual generation logic to the puzzle generator
            logging.info(f"Requesting puzzle generation for level {self.current_level}, type: {puzzle_type}")
            self.current_puzzle = self.puzzle_generator.generate_puzzle(
                level=self.current_level,
                force_type=puzzle_type # Pass the specific type if requested
            )

            # Check if a puzzle was successfully generated
            if not self.current_puzzle:
                 # This case should ideally be handled by puzzle_generator raising an error,
                 # but we add a check here for robustness.
                 logging.error("Puzzle generator returned None unexpectedly.")
                 raise ValueError("Puzzle generator failed to return a puzzle.")

            # Optionally, add a check here for self.current_puzzle.is_verified if applicable to all types
            # 'is_verified' might not be relevant for all types (e.g., Dilemma)
            if not getattr(self.current_puzzle, 'is_verified', True): # Default to True if attr missing
                 logging.warning(f"Generated puzzle (Type: {type(self.current_puzzle).__name__}) could not be internally verified for uniqueness/solvability.")

            # Reset state for the new puzzle
            self.user_mapping = {}
            self.scenario_user_state = None # Reset specific state for scenarios
            self.hints_used_this_level = 0

            puzzle_class_name = type(self.current_puzzle).__name__
            scenario_detail = ""
            if isinstance(self.current_puzzle, ScenarioPuzzle):
                 scenario_detail = f" ({getattr(self.current_puzzle, 'puzzle_type', 'N/A').name})"

            logging.info(f"Started new puzzle (Level {self.current_level + 1}, Type: {puzzle_class_name}{scenario_detail})")
            self.save_game() # Save immediately after starting a new puzzle

        except (ValueError, RuntimeError) as e:
            # Errors during generation (e.g., failed verification, missing data)
            logging.error(f"Could not generate puzzle: {e}", exc_info=True)
            # Handle error gracefully, maybe retry or inform user via re-raising
            raise ValueError(f"Failed to generate the requested puzzle: {e}") from e # Re-raise for UI
        except Exception as e:
            # Catch unexpected errors during generation
            logging.exception("An unexpected error occurred during puzzle generation.")
            raise RuntimeError(f"An unexpected error occurred generating the puzzle: {e}") from e

    def check_solution(self, user_solution: Optional[Dict[str, Any]] = None) -> bool:
        """
        Checks the solution for the current puzzle type using its method.

        Args:
            user_solution: The user's proposed solution, primarily used for ScenarioPuzzles.
                           For Symbol Puzzles, the internal self.user_mapping is used.

        Returns:
            True if the solution is correct, False otherwise.
        """
        if not self.current_puzzle:
            logging.warning("Checked solution when no puzzle was active.")
            return False

        try:
            # Symbol puzzle uses internal state (user_mapping)
            if isinstance(self.current_puzzle, Puzzle) and not self.current_puzzle.is_scenario:
                # The check_solution method for Puzzle expects the user mapping
                return self.current_puzzle.check_solution(self.user_mapping)
            # Scenario puzzle uses the provided user_solution
            elif isinstance(self.current_puzzle, ScenarioPuzzle):
                if user_solution is None:
                     logging.warning("Scenario puzzle check called with user_solution=None.")
                     return False
                # The check_solution method for ScenarioPuzzle expects the user solution dict
                # We might store the user's attempt for hints, but the check uses the provided arg
                # self.scenario_user_state = user_solution # Store the attempt
                return self.current_puzzle.check_solution(user_solution)
            else:
                logging.error(f"check_solution called on unexpected puzzle type: {type(self.current_puzzle)}")
                return False
        except Exception as e:
            logging.exception(f"Error during check_solution for puzzle type {type(self.current_puzzle)}.")
            return False


    def get_hint(self) -> Optional[Union[Tuple[str, str, str], str]]:
        """
        Gets a hint appropriate for the current puzzle type.

        Returns:
            - For Symbol Puzzles: A tuple (symbol, letter, reason) or None if no hint possible.
            - For Scenario Puzzles: A string hint or None.
            - A string error message if no puzzle loaded, max hints reached, or error occurs.
        """
        if not self.current_puzzle:
            return "No puzzle loaded to get a hint for."
        if self.hints_used_this_level >= self.max_hints_per_level:
            return "No hints left for this level!"

        hint = None
        try:
            if isinstance(self.current_puzzle, Puzzle) and not self.current_puzzle.is_scenario:
                # Symbol puzzle hint logic might use the current user mapping
                hint = self.current_puzzle.get_hint(self.user_mapping)
            elif isinstance(self.current_puzzle, ScenarioPuzzle):
                # Pass current user state if available and potentially useful for hint logic
                # The ScenarioPuzzle's get_hint method takes the user state dict
                hint = self.current_puzzle.get_hint(self.scenario_user_state)
            else:
                logging.error(f"get_hint called on unexpected puzzle type: {type(self.current_puzzle)}")
                return "Cannot provide hint for this puzzle type."

        except Exception as e:
             logging.exception("Error occurred while getting hint.")
             return f"Error getting hint: {e}"


        if hint is not None: # Check explicitly for None, as empty string might be a valid (bad) hint
            self.hints_used_this_level += 1
            logging.info(f"Hint used for level {self.current_level+1}. Hints remaining: {self.max_hints_per_level - self.hints_used_this_level}")
            # Consider saving game after using a hint? Optional.
            # self.save_game()
            return hint
        else:
            # Puzzle's get_hint method returned None (e.g., no more hints possible, or puzzle solved)
            logging.info(f"No further hints could be generated for level {self.current_level+1}.")
            return "No further hints could be generated for this puzzle."

    def unlock_theme(self, theme_name: str) -> bool:
        """Unlocks a new theme if conditions are met."""
        # Potential future enhancement: Add checks here (e.g., based on puzzles_solved)
        # For now, it just adds the theme if not present.
        if theme_name not in self.unlocked_themes:
            self.unlocked_themes.add(theme_name)
            logging.info(f"Theme unlocked: {theme_name}")
            try:
                self.save_game()
            except Exception as e:
                 logging.error(f"Failed to save game after unlocking theme {theme_name}: {e}")
                 # Decide if unlock should be rolled back or just log the error
            return True
        return False # Theme was already unlocked

    def check_unlockables(self) -> Optional[str]:
        """Checks if any content (like themes) should be unlocked based on progress."""
        # Define unlock conditions clearly (maps number of puzzles solved to theme name)
        unlock_map = {
            3: "Arcane Library",
            7: "Midnight Lab",
            # Add more unlocks here:
            # 12: "Celestial Observatory",
            # 20: "Forgotten Temple",
        }

        newly_unlocked = None
        for solved_count_threshold, theme_name in unlock_map.items():
            if self.puzzles_solved >= solved_count_threshold and theme_name not in self.unlocked_themes:
                # Found a theme that meets the criteria and isn't unlocked yet
                newly_unlocked = theme_name
                break # Stop checking once the first unlockable is found for this check

        return newly_unlocked

    # --- AI Solver Method (Example - if needed directly in GameState) ---
    # Usually, AI interaction is handled in the UI or a dedicated controller,
    # but if GameState needed to manage AI state directly, methods would go here.
    # Example:
    # def set_selected_ai_solver(self, solver_name: str):
    #     # Validate solver_name against available solvers?
    #     self.selected_solver_name = solver_name
    #     logging.info(f"Selected AI Solver set to: {solver_name}")
    #     self.save_game() # Save change

    # def get_solver_configuration(self, solver_name: str) -> Dict[str, Any]:
    #     return self.solver_configs.get(solver_name, {})

    # def update_solver_configuration(self, solver_name: str, config: Dict[str, Any]):
    #     self.solver_configs[solver_name] = config
    #     logging.info(f"Configuration updated for solver: {solver_name}")
    #     self.save_game() # Save updated config