import json
import os
from typing import Dict, Optional, Set, Union, Any, Tuple, List
from .puzzle import Puzzle, PuzzleGenerator, ScenarioPuzzle, HumanScenarioType, ClueType
from enum import Enum
import logging
import random
import time

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GameState:
    SAVE_FILE = "alchemist_cipher_save.json"
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
        self.puzzle_generator = PuzzleGenerator()
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

        try:
            if isinstance(self.current_puzzle, Puzzle) and not self.current_puzzle.is_scenario:
                puzzle_type_name = "SymbolCipher"
                serializable_clues = [(text, c_type.name) for text, c_type in self.current_puzzle.clues]
                puzzle_data = {
                    "level": self.current_puzzle.level,
                    "symbols": self.current_puzzle.symbols,
                    "letters": self.current_puzzle.letters,
                    "solution_mapping": self.current_puzzle.solution_mapping,
                    "clues": serializable_clues,
                    "is_verified": self.current_puzzle.is_verified
                }
                user_state = self.user_mapping
            elif isinstance(self.current_puzzle, ScenarioPuzzle):
                puzzle_type_name = "Scenario"
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
                }
                # Add elements specifically for LogicGrid reconstruction
                if self.current_puzzle.puzzle_type == HumanScenarioType.LOGIC_GRID and hasattr(self.current_puzzle, 'elements'):
                     puzzle_data["elements"] = self.current_puzzle.elements

                user_state = self.scenario_user_state

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
                # Puzzle state (might be None if no puzzle active)
                "current_puzzle_type": puzzle_type_name,
                "current_puzzle_data": puzzle_data,
                "user_state": user_state
            }

            with open(self.SAVE_FILE, 'w') as f:
                json.dump(state, f, indent=4)
            logging.info(f"Game state saved successfully to {self.SAVE_FILE}")

        except IOError as e:
            logging.error(f"Could not save game state to {self.SAVE_FILE}: {e}")
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
        if not os.path.exists(self.SAVE_FILE):
            logging.info(f"Save file '{self.SAVE_FILE}' not found. Starting new game.")
            # Keep default __init__ values including AI solver config
            return

        state = None
        try:
            with open(self.SAVE_FILE, 'r') as f:
                state = json.load(f)
            logging.info(f"Loaded game state from {self.SAVE_FILE}")

            loaded_version = state.get("save_version", 0)
            if loaded_version < self.save_version:
                 logging.warning(f"Loading an older save file version ({loaded_version} vs current {self.save_version}). Applying defaults for missing fields.")
                 # Example: Migration for V3 - If solver fields don't exist, keep defaults
                 if "selected_solver_name" not in state:
                     state["selected_solver_name"] = self.selected_solver_name # Default from __init__
                 if "solver_configs" not in state:
                     state["solver_configs"] = self.solver_configs # Default from __init__
            elif loaded_version > self.save_version:
                 logging.error(f"Save file version ({loaded_version}) is newer than game version ({self.save_version}). Cannot load.")
                 raise RuntimeError("Save file is from a newer version of the game.")


            # Load core state with robust defaults
            self.current_level = state.get("current_level", 0)
            self.hints_used_this_level = state.get("hints_used_this_level", 0)
            self.puzzles_solved = state.get("puzzles_solved", 0)
            self.current_theme = state.get("current_theme", "Default")
            loaded_themes = state.get("unlocked_themes", ["Default"])
            self.unlocked_themes = set(loaded_themes) if isinstance(loaded_themes, list) else {"Default"}

            # --- Load AI Solver State ---
            self.selected_solver_name = state.get("selected_solver_name", "Internal (Perfect)") # Apply default if missing even after migration logic
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

            # --- Reconstruct Puzzle (Symbol or Scenario - existing logic follows) ---
            if puzzle_type_name == "SymbolCipher":
                try:
                    raw_clues = puzzle_data.get("clues", [])
                    reconstructed_clues = self._reconstruct_clues(raw_clues)

                    required_fields = ["level", "symbols", "letters", "solution_mapping"]
                    if not all(field in puzzle_data for field in required_fields):
                         raise ValueError("Missing required fields in saved SymbolCipher puzzle data.")

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
                         valid_user_mapping = {k: v for k, v in user_state.items() if isinstance(k, str) and isinstance(v, str)}
                         if len(valid_user_mapping) != len(user_state):
                            logging.warning("Invalid keys/values found in loaded user_mapping for SymbolCipher, resetting partially.")
                         self.user_mapping = valid_user_mapping
                    else:
                         logging.warning("Invalid user_state for SymbolCipher, resetting.")
                         self.user_mapping = {}
                    logging.info("Successfully loaded SymbolCipher puzzle.")
                except (KeyError, TypeError, ValueError) as e:
                    logging.error(f"Failed to reconstruct SymbolCipher puzzle from data: {e}. Data: {puzzle_data}")
                    self.current_puzzle = None

            # --- Reconstruct Scenario Puzzle ---
            elif puzzle_type_name == "Scenario":
                try:
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

                    # Use specific class for LogicGrid if type matches
                    if puzzle_type_enum == HumanScenarioType.LOGIC_GRID:
                        # Logic grids need 'elements' data
                        required_fields.append("elements")
                        if not all(field in puzzle_data for field in required_fields):
                            raise ValueError("Missing 'elements' field required for saved Logic Grid puzzle.")

                        self.current_puzzle = ScenarioPuzzle(
                             level=puzzle_data["level"],
                             puzzle_type=puzzle_type_enum,
                             description=puzzle_data["description"],
                             characters=puzzle_data["characters"],
                             setting=puzzle_data["setting"],
                             goal=puzzle_data["goal"],
                             information=puzzle_data["information"],
                             solution=puzzle_data["solution"],
                             elements=puzzle_data["elements"],
                             is_verified=puzzle_data.get("is_verified", False)
                        )
                    else:
                         # Generic ScenarioPuzzle for other types
                         self.current_puzzle = ScenarioPuzzle(
                             level=puzzle_data["level"],
                             puzzle_type=puzzle_type_enum,
                             description=puzzle_data["description"],
                             characters=puzzle_data["characters"],
                             setting=puzzle_data["setting"],
                             goal=puzzle_data["goal"],
                             information=puzzle_data["information"],
                             solution=puzzle_data["solution"],
                             rules=puzzle_data.get("rules"),
                             options=puzzle_data.get("options"),
                             is_verified=puzzle_data.get("is_verified", False)
                         )

                    # Restore user state safely
                    if isinstance(user_state, dict):
                         self.scenario_user_state = user_state
                    else:
                         logging.warning(f"Invalid user_state for Scenario, resetting.")
                         self.scenario_user_state = None
                    logging.info(f"Successfully loaded Scenario puzzle: {puzzle_type_enum.name}")
                except (KeyError, TypeError, ValueError) as e:
                    logging.error(f"Failed to reconstruct Scenario puzzle from data: {e}. Data: {puzzle_data}")
                    self.current_puzzle = None
            else:
                 logging.warning(f"Unknown puzzle type '{puzzle_type_name}' found in save file.")

        except FileNotFoundError:
             logging.info(f"Save file '{self.SAVE_FILE}' not found.")
             self.__init__() # Re-initialize to get defaults including AI solver config
        except (IOError, json.JSONDecodeError) as e:
            logging.error(f"Error reading or parsing save file '{self.SAVE_FILE}': {e}")
            self.__init__()
            logging.info("Game state reset to default due to load error.")
        except Exception as e:
             logging.exception(f"Unexpected error loading game state.")
             self.__init__()
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

    def start_new_puzzle(self, puzzle_type: Optional[Union[str, HumanScenarioType]] = None) -> None:
        """Generates and starts a new puzzle, ensuring it's verified if possible."""
        try:
            # Delegate the actual generation logic to the puzzle generator
            self.current_puzzle = self.puzzle_generator.generate_puzzle(
                level=self.current_level,
                force_type=puzzle_type # Pass the specific type if requested
            )

            # Check if a puzzle was successfully generated
            if not self.current_puzzle:
                 raise ValueError("Puzzle generator failed to return a puzzle.")
            # Optionally, add a check here for self.current_puzzle.is_verified if applicable to all types?
            # if not getattr(self.current_puzzle, 'is_verified', True): # Default to True if attr missing
            #     logging.warning("Generated puzzle could not be verified for uniqueness/solvability.")

            self.user_mapping = {}
            self.scenario_user_state = None
            self.hints_used_this_level = 0
            puzzle_type_name = type(self.current_puzzle).__name__
            scenario_detail = f"({getattr(self.current_puzzle, 'puzzle_type', 'N/A').name})" if getattr(self.current_puzzle, 'is_scenario', False) else ""
            logging.info(f"Started new puzzle (Level {self.current_level + 1}, Type: {puzzle_type_name}{scenario_detail})")
            self.save_game() # Save immediately after starting a new puzzle
        except ValueError as e:
            logging.error(f"Could not generate puzzle: {e}")
            # Handle error gracefully, maybe retry or inform user
            raise ValueError(f"Failed to generate the requested puzzle: {e}") # Re-raise for UI
        except Exception as e:
            logging.exception("An unexpected error occurred during puzzle generation.")
            raise RuntimeError(f"An unexpected error occurred generating the puzzle: {e}")

    def check_solution(self, user_solution: Optional[Dict[str, Any]] = None) -> bool:
        """Checks the solution for the current puzzle type using its method."""
        if not self.current_puzzle:
            logging.warning("Checked solution when no puzzle was active.")
            return False

        # Symbol puzzle uses internal state (user_mapping)
        if isinstance(self.current_puzzle, Puzzle) and not self.current_puzzle.is_scenario:
            return self.current_puzzle.check_solution(self.user_mapping)
        # Scenario puzzle uses the provided user_solution
        elif isinstance(self.current_puzzle, ScenarioPuzzle):
            if user_solution is None:
                 logging.warning("Scenario puzzle check called with user_solution=None.")
                 return False
            # Store the user's current attempt for potential hint generation later
            # We might not want the AI's perfect solution stored here?
            # self.scenario_user_state = user_solution
            return self.current_puzzle.check_solution(user_solution)
        else:
            logging.error(f"check_solution called on unexpected puzzle type: {type(self.current_puzzle)}")
            return False

    def get_hint(self) -> Optional[Union[Tuple[str, str, str], str]]:
        """Gets a hint appropriate for the current puzzle type."""
        if not self.current_puzzle:
            return "No puzzle loaded to get a hint for."
        if self.hints_used_this_level >= self.max_hints_per_level:
            return "No hints left for this level!"

        hint = None
        try:
            if isinstance(self.current_puzzle, Puzzle) and not self.current_puzzle.is_scenario:
                hint = self.current_puzzle.get_hint(self.user_mapping)
            elif isinstance(self.current_puzzle, ScenarioPuzzle):
                # Pass current user state if available and potentially useful for hint logic
                hint = self.current_puzzle.get_hint(self.scenario_user_state)
            else:
                logging.error(f"get_hint called on unexpected puzzle type: {type(self.current_puzzle)}")
                return "Cannot provide hint for this puzzle type."

        except Exception as e:
             logging.exception("Error occurred while getting hint.")
             return f"Error getting hint: {e}"


        if hint:
            self.hints_used_this_level += 1
            # Maybe save game after using a hint?
            # self.save_game()
            return hint
        else:
            # Puzzle's get_hint method returned None (e.g., no more hints possible)
            return "No further hints could be generated for this puzzle."

    def unlock_theme(self, theme_name: str) -> bool:
        """Unlocks a new theme if conditions are met."""
        if theme_name not in self.unlocked_themes:
            self.unlocked_themes.add(theme_name)
            logging.info(f"Theme unlocked: {theme_name}")
            self.save_game()
            return True
        return False

    def check_unlockables(self) -> Optional[str]:
        """Checks and returns newly unlocked content based on progress."""
        # Define unlock conditions clearly
        unlock_map = {
            3: "Arcane Library",
            7: "Midnight Lab",
            # Add more unlocks here:
            # 12: "Celestial Observatory",
            # 20: "Forgotten Temple",
        }

        for solved_count, theme_name in unlock_map.items():
            if self.puzzles_solved >= solved_count and theme_name not in self.unlocked_themes:
                return theme_name
        return None

    # --- AI Solver Method ---
