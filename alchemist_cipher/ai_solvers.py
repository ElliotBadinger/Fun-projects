from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
import logging
import time # For potential dummy delays
import re

# Import necessary game components (adjust path if needed)
from .puzzle import Puzzle, ScenarioPuzzle, HumanScenarioType

class AbstractPuzzleSolver(ABC):
    """Abstract base class for AI puzzle solvers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the display name of the solver."""
        pass

    @abstractmethod
    def solve(self, puzzle: Union[Puzzle, ScenarioPuzzle]) -> Optional[Dict[str, Any]]:
        """
        Attempts to solve the given puzzle.

        Args:
            puzzle: The Puzzle or ScenarioPuzzle instance.

        Returns:
            A dictionary representing the proposed solution in the format expected
            by GameState.check_solution (e.g., symbol mapping, scenario answer dict),
            or None if unable to solve or an error occurs.
        """
        pass

    def get_configuration_widgets(self) -> Optional[Dict[str, Any]]:
        """
        Optionally return widgets needed for configuration (e.g., API key input).
        Returns a dictionary mapping label: widget, or None.
        """
        return None # Default: no configuration needed

    def set_configuration(self, config: Dict[str, Any]):
        """
        Apply configuration settings (e.g., API key).
        """
        pass # Default: nothing to configure

# --- Concrete Solver Implementations ---

class InternalSolver(AbstractPuzzleSolver):
    """Uses the known internal solution - for perfect play and visualization."""

    @property
    def name(self) -> str:
        return "Internal (Perfect)"

    def solve(self, puzzle: Union[Puzzle, ScenarioPuzzle]) -> Optional[Dict[str, Any]]:
        logging.info(f"InternalSolver solving Level {puzzle.level+1} ({type(puzzle).__name__})")
        try:
            if isinstance(puzzle, Puzzle) and not puzzle.is_scenario:
                # Return the direct mapping
                return puzzle.solution_mapping.copy() # Return a copy
            elif isinstance(puzzle, ScenarioPuzzle):
                # Return the scenario solution dictionary
                return puzzle.solution.copy() # Return a copy
            else:
                logging.error(f"InternalSolver cannot handle puzzle type: {type(puzzle)}")
                return None
        except Exception as e:
            logging.exception(f"InternalSolver failed: {e}")
            return None

class RandomGuessSolver(AbstractPuzzleSolver):
    """A simple baseline solver that makes random guesses."""

    @property
    def name(self) -> str:
        return "Random Guesser"

    def solve(self, puzzle: Union[Puzzle, ScenarioPuzzle]) -> Optional[Dict[str, Any]]:
        logging.info(f"RandomGuessSolver attempting Level {puzzle.level+1}")
        time.sleep(0.1) # Simulate some thought
        try:
            if isinstance(puzzle, Puzzle) and not puzzle.is_scenario:
                # Assign random letters to symbols
                import random
                letters_copy = list(puzzle.letters)
                random.shuffle(letters_copy)
                if len(letters_copy) < len(puzzle.symbols): # Should not happen
                     letters_copy.extend(['?'] * (len(puzzle.symbols) - len(letters_copy)))
                guess = {symbol: letters_copy[i] for i, symbol in enumerate(puzzle.symbols)}
                logging.debug(f"Random Guess (Symbol): {guess}")
                return guess

            elif isinstance(puzzle, ScenarioPuzzle):
                # This is much harder to guess randomly in a structured way
                # Placeholder: Return an empty dict, likely failing the check
                logging.debug(f"Random Guess (Scenario {puzzle.puzzle_type.name}): Returning empty solution.")
                return {} # Return empty dict, will fail most checks

            else:
                return None
        except Exception as e:
            logging.exception(f"RandomGuessSolver failed: {e}")
            return None


# --- Placeholder for External API Solvers ---

class OpenAISolver(AbstractPuzzleSolver):
    """Placeholder for an OpenAI GPT-based solver."""
    def __init__(self):
        self.api_key = None
        # Add other necessary clients or setup here

    @property
    def name(self) -> str:
        return "OpenAI (GPT - Placeholder)"

    def get_configuration_widgets(self) -> Optional[Dict[str, Any]]:
        # Example: Add an API key input field
        from PyQt6.QtWidgets import QLineEdit
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Enter OpenAI API Key")
        return {"OpenAI API Key": self.api_key_input}

    def set_configuration(self, config: Dict[str, Any]):
        self.api_key = config.get("OpenAI API Key")
        logging.info(f"OpenAI Solver configured. Key {'set' if self.api_key else 'not set'}.")
        # Initialize OpenAI client here if key is present

    def _create_prompt(self, puzzle: Union[Puzzle, ScenarioPuzzle]) -> str:
        """Creates a detailed prompt for the LLM based on the puzzle."""
        # THIS IS THE MOST COMPLEX PART - Requires careful engineering per puzzle type
        prompt = "You are a logic puzzle solver. Solve the following puzzle and provide the answer in the specified format.\n\n"
        prompt += f"Puzzle Level: {puzzle.level + 1}\n"

        if isinstance(puzzle, Puzzle) and not puzzle.is_scenario:
            prompt += "Type: Symbol Cipher\n"
            prompt += f"Symbols: {', '.join(puzzle.symbols)}\n"
            prompt += f"Possible Letters: {', '.join(puzzle.letters)}\n"
            prompt += "Clues:\n"
            for clue_text, clue_type in puzzle.clues:
                prompt += f"- ({clue_type.name}) {clue_text}\n"
            prompt += "\nOutput the solution as a JSON dictionary mapping each symbol string to its corresponding letter string (e.g., {\"α\": \"A\", \"β\": \"B\"})."

        elif isinstance(puzzle, ScenarioPuzzle):
            prompt += f"Type: Scenario - {puzzle.puzzle_type.name.replace('_', ' ').title()}\n"
            prompt += f"Description: {puzzle.description}\n"
            if puzzle.characters: prompt += f"Characters/Entities: {puzzle.characters}\n" # Maybe format this better
            if puzzle.setting: prompt += f"Setting: {puzzle.setting}\n"
            if puzzle.rules: prompt += f"Rules: {puzzle.rules}\n"
            prompt += f"Goal: {puzzle.goal}\n"
            prompt += "Information/Clues:\n"
            for info in puzzle.information: prompt += f"- {info}\n"
            if puzzle.options: prompt += f"Options (for Dilemma): {puzzle.options}\n"
            if puzzle.elements: prompt += f"Elements (for Logic Grid): {puzzle.elements}\n"

            # Specify output format based on type
            prompt += "\nOutput the solution as a JSON dictionary. The required keys depend on the puzzle type:\n"
            if puzzle.puzzle_type == HumanScenarioType.LOGIC_GRID: prompt += "- For Logic Grid: {\"grid\": { \"entity_name\": { \"category_name\": \"value\", ... }, ... } }"
            elif puzzle.puzzle_type == HumanScenarioType.RELATIONSHIP_MAP: prompt += "- For Relationship Map: {\"map\": { \"person1\": \"person2\", ... } } (Include each person once as key)"
            elif puzzle.puzzle_type == HumanScenarioType.ORDERING: prompt += "- For Ordering: {\"order\": [\"item1\", \"item2\", ...] }"
            elif puzzle.puzzle_type == HumanScenarioType.SCHEDULING: prompt += "- For Scheduling: {\"schedule\": { \"person\": { \"slot\": \"Booked/Available\", ... }, ... } }"
            elif puzzle.puzzle_type == HumanScenarioType.DILEMMA: prompt += f"- For Dilemma: {{\"choice\": \"Selected option text from {puzzle.options}\" }}"
            elif puzzle.puzzle_type in [HumanScenarioType.SOCIAL_DEDUCTION, HumanScenarioType.COMMON_SENSE_GAP, HumanScenarioType.AGENT_SIMULATION]: prompt += "- For Deduction/Gap/Simulation: {\"answer\": \"Your single deduced answer string\"}"
            else: prompt += "- For other types: Provide the most relevant solution structure."

        else:
            return "Error: Unknown puzzle type."

        return prompt

    def _parse_response(self, response_text: str, puzzle_type: Optional[type] = None) -> Optional[Dict[str, Any]]:
        """Attempts to parse the LLM's JSON response."""
        import json
        try:
            # LLMs often wrap JSON in ```json ... ``` or just output the JSON directly
            json_match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                 # Look for the first '{' and last '}' assuming it's just JSON
                 start = response_text.find('{')
                 end = response_text.rfind('}')
                 if start != -1 and end != -1 and end > start:
                      json_str = response_text[start:end+1]
                 else:
                     logging.warning(f"Could not find JSON block in OpenAI response: {response_text}")
                     return None # Cannot find JSON

            parsed = json.loads(json_str)
            if isinstance(parsed, dict):
                 logging.debug(f"Successfully parsed OpenAI response: {parsed}")
                 return parsed
            else:
                 logging.warning(f"Parsed JSON is not a dictionary: {parsed}")
                 return None
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON response from OpenAI: {e}\nResponse was: {response_text}")
            return None
        except Exception as e:
            logging.exception(f"Error parsing OpenAI response: {e}")
            return None


    def solve(self, puzzle: Union[Puzzle, ScenarioPuzzle]) -> Optional[Dict[str, Any]]:
        logging.info(f"OpenAISolver attempting Level {puzzle.level+1}")
        if not self.api_key:
            logging.error("OpenAI API Key not set.")
            # Maybe show a message box to the user? For now, just log and fail.
            # from PyQt6.QtWidgets import QMessageBox
            # QMessageBox.warning(None, "API Key Error", "OpenAI API Key is missing. Please set it in Options -> Select AI Solver.")
            return None

        # --- Placeholder for API Call ---
        logging.warning("OpenAI API call is not implemented. Returning None.")
        # 1. Create the prompt
        prompt = self._create_prompt(puzzle)
        logging.debug(f"--- OpenAI Prompt ---\n{prompt}\n--------------------")

        # 2. Make the API call (using openai library, requests, etc.)
        # response_text = call_openai_api(self.api_key, prompt) # Replace with actual call
        response_text = '{"error": "API call not implemented"}' # Dummy response

        # 3. Parse the response
        solution = self._parse_response(response_text, type(puzzle))

        # 4. Validate structure based on puzzle type (basic check)
        if solution:
            if isinstance(puzzle, Puzzle) and not isinstance(solution, dict): return None # Symbol needs dict
            if isinstance(puzzle, ScenarioPuzzle):
                 ptype = puzzle.puzzle_type
                 required_key = None
                 if ptype == HumanScenarioType.LOGIC_GRID: required_key = 'grid'
                 elif ptype == HumanScenarioType.RELATIONSHIP_MAP: required_key = 'map'
                 elif ptype == HumanScenarioType.ORDERING: required_key = 'order'
                 elif ptype == HumanScenarioType.SCHEDULING: required_key = 'schedule'
                 elif ptype == HumanScenarioType.DILEMMA: required_key = 'choice'
                 elif ptype in [HumanScenarioType.SOCIAL_DEDUCTION, HumanScenarioType.COMMON_SENSE_GAP, HumanScenarioType.AGENT_SIMULATION]: required_key = 'answer'

                 if required_key and required_key not in solution:
                      logging.warning(f"OpenAI response missing required key '{required_key}' for {ptype.name}. Solution: {solution}")
                      # return None # Be strict: if key missing, fail
                      pass # Be lenient: allow check even if key missing? Let's be strict. return None.
        # --- End Placeholder ---

        return solution


# Add other placeholder classes similarly
# class ClaudeSolver(AbstractPuzzleSolver): ...
# class LocalModelSolver(AbstractPuzzleSolver): ...


# List of available solver classes (add more as implemented)
AVAILABLE_SOLVERS = [
    InternalSolver,
    RandomGuessSolver,
    OpenAISolver,
    # ClaudeSolver,
]

# Function to get instantiated solvers
def get_solver_instances() -> Dict[str, AbstractPuzzleSolver]:
    instances = {}
    for solver_class in AVAILABLE_SOLVERS:
        try:
            instance = solver_class()
            instances[instance.name] = instance
        except Exception as e:
            logging.error(f"Failed to instantiate solver {solver_class.__name__}: {e}")
    return instances