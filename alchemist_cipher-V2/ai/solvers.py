from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, List
import logging
import time # For potential dummy delays
import re
import json # For parsing LLM responses

# Corrected relative imports
from ..puzzle.puzzle_types import Puzzle, ScenarioPuzzle
from ..puzzle.common import HumanScenarioType

# --- Abstract Base Class ---

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
            by the puzzle's check_solution method (e.g., symbol mapping, scenario answer dict),
            or None if unable to solve or an error occurs.
        """
        pass

    def get_configuration_widgets(self) -> Optional[Dict[str, Any]]:
        """
        Optionally return widgets needed for configuration (e.g., API key input).
        Returns a dictionary mapping label: widget, or None.
        Widgets should be created here and stored as instance variables if their
        state needs to be accessed later by set_configuration.
        """
        return None # Default: no configuration needed

    def set_configuration(self, config: Dict[str, Any]):
        """
        Apply configuration settings obtained from the widgets.
        Example: Reads the text from an API key input widget stored in __init__ or get_configuration_widgets.
        """
        pass # Default: nothing to configure

# --- Concrete Solver Implementations ---

class InternalSolver(AbstractPuzzleSolver):
    """Uses the known internal solution - for perfect play and visualization."""

    @property
    def name(self) -> str:
        return "Internal (Perfect)"

    def solve(self, puzzle: Union[Puzzle, ScenarioPuzzle]) -> Optional[Dict[str, Any]]:
        logger = logging.getLogger(__name__)
        logger.info(f"InternalSolver solving Level {puzzle.level+1} ({type(puzzle).__name__})")
        try:
            if isinstance(puzzle, Puzzle) and not puzzle.is_scenario:
                # Return the direct mapping
                if not hasattr(puzzle, 'solution_mapping'):
                     logger.error("InternalSolver: Symbol puzzle missing 'solution_mapping' attribute.")
                     return None
                logger.debug(f"InternalSolver returning symbol solution: {puzzle.solution_mapping}")
                return puzzle.solution_mapping.copy() # Return a copy
            elif isinstance(puzzle, ScenarioPuzzle):
                # Return the scenario solution dictionary
                if not hasattr(puzzle, 'solution'):
                    logger.error("InternalSolver: Scenario puzzle missing 'solution' attribute.")
                    return None
                logger.debug(f"InternalSolver returning scenario solution ({puzzle.puzzle_type.name}): {puzzle.solution}")
                return puzzle.solution.copy() # Return a copy
            else:
                logger.error(f"InternalSolver cannot handle puzzle type: {type(puzzle)}")
                return None
        except Exception as e:
            logger.exception(f"InternalSolver failed: {e}")
            return None

class RandomGuessSolver(AbstractPuzzleSolver):
    """A simple baseline solver that makes random guesses."""

    @property
    def name(self) -> str:
        return "Random Guesser"

    def solve(self, puzzle: Union[Puzzle, ScenarioPuzzle]) -> Optional[Dict[str, Any]]:
        logger = logging.getLogger(__name__)
        logger.info(f"RandomGuessSolver attempting Level {puzzle.level+1}")
        time.sleep(0.1) # Simulate some thought
        try:
            if isinstance(puzzle, Puzzle) and not puzzle.is_scenario:
                # Assign random letters to symbols
                import random
                if not puzzle.letters or not puzzle.symbols:
                     logger.warning("RandomGuessSolver: Puzzle has empty letters or symbols.")
                     return {}
                letters_copy = list(puzzle.letters)
                symbols_copy = list(puzzle.symbols)
                random.shuffle(letters_copy)
                # Ensure we have a letter for each symbol, pad with '?' if necessary (shouldn't happen with valid puzzle)
                guess = {symbol: letters_copy[i % len(letters_copy)] for i, symbol in enumerate(symbols_copy)}
                logger.debug(f"Random Guess (Symbol): {guess}")
                return guess

            elif isinstance(puzzle, ScenarioPuzzle):
                # Random guessing for scenarios is very difficult to make meaningful.
                # Let's return a guess structure based on the expected solution format.
                logger.debug(f"Random Guess (Scenario {puzzle.puzzle_type.name})")
                if puzzle.puzzle_type == HumanScenarioType.LOGIC_GRID:
                     # Return an empty grid or random assignments? Empty is safer.
                     return {"grid": {}}
                elif puzzle.puzzle_type == HumanScenarioType.RELATIONSHIP_MAP:
                    # Pair randomly - might violate constraints
                    import random
                    chars = [c['name'] for c in puzzle.characters]
                    random.shuffle(chars)
                    guess_map = {}
                    for i in range(0, len(chars) - 1, 2):
                        guess_map[chars[i]] = chars[i+1]
                    return {"map": guess_map}
                elif puzzle.puzzle_type == HumanScenarioType.ORDERING:
                     # Shuffle the expected items
                     import random
                     items = puzzle.solution.get('order', []) # Requires solution to exist!
                     if not items: return {"order": []} # Cannot guess if no items known
                     random.shuffle(items)
                     return {"order": list(items)} # Return shuffled list
                elif puzzle.puzzle_type == HumanScenarioType.SCHEDULING:
                     # Randomly book some slots
                     import random
                     guess_sched = {}
                     sol_sched = puzzle.solution.get('schedule', {})
                     if not sol_sched: return {"schedule": {}}
                     people = list(sol_sched.keys())
                     slots = list(sol_sched.get(people[0], {}).keys()) if people else []
                     if not people or not slots: return {"schedule": {}}
                     for p in people:
                         guess_sched[p] = {}
                         for s in slots:
                             guess_sched[p][s] = random.choice(["Booked", "Available"])
                     return {"schedule": guess_sched}
                elif puzzle.puzzle_type == HumanScenarioType.DILEMMA:
                     # Pick a random option
                     import random
                     options = getattr(puzzle, 'options', [])
                     if not options: return {"choice": ""}
                     return {"choice": random.choice(options)}
                elif puzzle.puzzle_type in [HumanScenarioType.SOCIAL_DEDUCTION, HumanScenarioType.COMMON_SENSE_GAP, HumanScenarioType.AGENT_SIMULATION]:
                     # Guess a random character name or a common word? Very unlikely to be correct.
                     import random
                     potential_answers = [c['name'] for c in puzzle.characters] if puzzle.characters else ["object", "rule"]
                     return {"answer": random.choice(potential_answers)}
                else:
                    # Fallback: Return empty dict, likely failing the check
                    logger.debug(f"Random Guess for unknown scenario type: Returning empty solution.")
                    return {}

            else: # Unknown puzzle type
                logger.error(f"RandomGuessSolver cannot handle puzzle type: {type(puzzle)}")
                return None
        except Exception as e:
            logger.exception(f"RandomGuessSolver failed: {e}")
            return None


# --- Placeholder for External API Solvers ---

class OpenAISolver(AbstractPuzzleSolver):
    """Placeholder for an OpenAI GPT-based solver."""
    def __init__(self):
        self.api_key: Optional[str] = None
        self.api_key_input: Optional[Any] = None # Placeholder for the widget
        # Add other necessary clients or setup here (e.g., openai client)
        # try:
        #     import openai
        #     self.openai_client = None # Initialize later when key is set
        # except ImportError:
        #      logging.warning("OpenAI library not installed. pip install openai")
        #      self.openai_client = None

    @property
    def name(self) -> str:
        return "OpenAI (GPT - Placeholder)"

    def get_configuration_widgets(self) -> Optional[Dict[str, Any]]:
        # Example: Add an API key input field using PyQt6
        try:
            from PyQt6.QtWidgets import QLineEdit
            self.api_key_input = QLineEdit()
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.api_key_input.setPlaceholderText("Enter OpenAI API Key")
            return {"OpenAI API Key": self.api_key_input}
        except ImportError:
             logging.error("PyQt6 not available, cannot create config widget for OpenAI.")
             return None
        except Exception as e:
             logging.exception(f"Error creating OpenAI config widget: {e}")
             return None


    def set_configuration(self, config: Dict[str, Any]):
        # Assumes config comes from a source that provides the key name used in get_configuration_widgets
        # In a real app, you might read directly from self.api_key_input.text() here if called after widget interaction
        logger = logging.getLogger(__name__)
        self.api_key = config.get("OpenAI API Key") # Get value from passed config dict
        logger.info(f"OpenAI Solver configured. Key {'set' if self.api_key else 'not set'}.")
        # Initialize OpenAI client here if key is present and library installed
        # if self.api_key and self.openai_client is None:
        #     try:
        #         import openai
        #         self.openai_client = openai.OpenAI(api_key=self.api_key)
        #         logger.info("OpenAI client initialized.")
        #     except Exception as e:
        #         logger.error(f"Failed to initialize OpenAI client: {e}")
        #         self.openai_client = None

    def _create_prompt(self, puzzle: Union[Puzzle, ScenarioPuzzle]) -> str:
        """Creates a detailed prompt for the LLM based on the puzzle."""
        prompt = "You are an expert logic puzzle solver. Solve the following puzzle and provide the answer *only* as a JSON dictionary in the specified format, with no extra text before or after the JSON block.\n\n"
        prompt += f"--- Puzzle Details ---\n"
        prompt += f"Level: {puzzle.level + 1}\n"

        if isinstance(puzzle, Puzzle) and not puzzle.is_scenario:
            prompt += "Type: Symbol Cipher\n"
            symbols_str = ", ".join(f'"{s}"' for s in puzzle.symbols) # Quote symbols for clarity
            letters_str = ", ".join(f'"{l}"' for l in puzzle.letters)
            prompt += f"Symbols to map: [{symbols_str}]\n"
            prompt += f"Available Letters: [{letters_str}]\n"
            prompt += "Clues:\n"
            for i, (clue_text, clue_type) in enumerate(puzzle.clues):
                prompt += f"{i+1}. ({clue_type.name}) {clue_text}\n"
            prompt += "\n--- Required Output Format ---\n"
            prompt += "Output the solution as a single JSON dictionary mapping each symbol string to its corresponding letter string.\n"
            prompt += "Example: {\"α\": \"A\", \"β\": \"B\", ...}"

        elif isinstance(puzzle, ScenarioPuzzle):
            puzzle_type_name = puzzle.puzzle_type.name.replace('_', ' ').title()
            prompt += f"Type: Scenario - {puzzle_type_name}\n"
            prompt += f"Description: {puzzle.description}\n"
            if puzzle.characters:
                char_list = [f"{c.get('name', 'Unknown')} ({c.get('trait', 'N/A')}, {c.get('occupation', 'N/A')})" for c in puzzle.characters]
                prompt += f"Characters/Entities: {'; '.join(char_list)}\n"
            if puzzle.setting and puzzle.setting.get('name') != "N/A":
                 setting_name = puzzle.setting.get('name', '')
                 setting_details = puzzle.setting.get('details', [])
                 details_str = f" ({', '.join(setting_details)})" if isinstance(setting_details, list) and setting_details else ""
                 prompt += f"Setting: {setting_name}{details_str}\n"
            if puzzle.rules:
                 prompt += f"Rules:\n"
                 for i, rule in enumerate(puzzle.rules): prompt += f"- {rule}\n"
            prompt += f"Goal: {puzzle.goal}\n"
            prompt += "Information/Clues:\n"
            if puzzle.information:
                for i, info in enumerate(puzzle.information): prompt += f"{i+1}. {info}\n"
            else: prompt += "- None provided.\n"

            if puzzle.puzzle_type == HumanScenarioType.DILEMMA and puzzle.options:
                prompt += f"Options:\n"
                for i, opt in enumerate(puzzle.options): prompt += f"- {opt}\n"
            if puzzle.puzzle_type == HumanScenarioType.LOGIC_GRID and puzzle.elements:
                prompt += f"Elements to map:\n"
                for cat, elems in puzzle.elements.items():
                    prompt += f"- {cat}: {', '.join(elems)}\n"

            prompt += "\n--- Required Output Format ---\n"
            prompt += "Output the solution as a single JSON dictionary. The required keys and value structures are:\n"
            if puzzle.puzzle_type == HumanScenarioType.LOGIC_GRID:
                prompt += '- Key: "grid", Value: A dictionary where keys are primary entities (e.g., from first category in elements) and values are dictionaries mapping other category names to their assigned element value for that entity.\n'
                prompt += '  Example: {"grid": { "Alice": { "HouseColor": "Red", "Pet": "Cat" }, ... } }'
            elif puzzle.puzzle_type == HumanScenarioType.RELATIONSHIP_MAP:
                prompt += '- Key: "map", Value: A dictionary mapping each person involved to their single partner. Ensure every person appears exactly once as a key.\n'
                prompt += '  Example: {"map": { "Alice": "Bob", "Charlie": "David", ... } }'
            elif puzzle.puzzle_type == HumanScenarioType.ORDERING:
                prompt += '- Key: "order", Value: A list of strings representing the items in their correct sequence from first to last.\n'
                prompt += '  Example: {"order": ["Action A", "Action C", "Action B"] }'
            elif puzzle.puzzle_type == HumanScenarioType.SCHEDULING:
                prompt += '- Key: "schedule", Value: A dictionary where keys are people\'s names. Each person\'s value is another dictionary mapping time slots (strings) to their status ("Booked" or "Available").\n'
                prompt += '  Example: {"schedule": { "Alice": { "9:00 AM": "Booked", "10:00 AM": "Available" }, ... } }'
            elif puzzle.puzzle_type == HumanScenarioType.DILEMMA:
                 prompt += f'- Key: "choice", Value: A string containing the exact text of the selected option from the provided list.\n'
                 prompt += f'  Example: {{"choice": "{puzzle.options[0] if puzzle.options else "Selected option text"}"}}'
            elif puzzle.puzzle_type in [HumanScenarioType.SOCIAL_DEDUCTION, HumanScenarioType.COMMON_SENSE_GAP, HumanScenarioType.AGENT_SIMULATION]:
                 prompt += '- Key: "answer", Value: A single string containing the deduced answer (e.g., name, item, rule text).\n'
                 prompt += '  Example: {"answer": "Culprit Name" or "Missing Item" or "Rule Text"}'
            else: prompt += "- For other types: Use the most logical key (e.g., 'result') and provide the solution structure as clearly as possible."
            prompt += "\nEnsure the output is ONLY the JSON dictionary."
        else:
            return "Error: Unknown puzzle type encountered."

        return prompt

    def _parse_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Attempts to parse the LLM's JSON response, handling potential markdown code blocks."""
        logger = logging.getLogger(__name__)
        logger.debug(f"Attempting to parse OpenAI response: {response_text[:200]}...") # Log beginning of response
        try:
            # Handle potential ```json ... ``` markdown block
            json_match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL | re.IGNORECASE)
            if json_match:
                json_str = json_match.group(1)
                logger.debug("Found JSON within markdown code block.")
            else:
                 # Look for the first '{' and last '}' assuming it might be just JSON
                 start = response_text.find('{')
                 end = response_text.rfind('}')
                 if start != -1 and end != -1 and end > start:
                      json_str = response_text[start:end+1]
                      logger.debug("Assuming raw JSON response (found '{' and '}').")
                 else:
                     logger.warning(f"Could not find JSON block or raw JSON object in OpenAI response: {response_text}")
                     return None # Cannot find JSON

            # Parse the extracted JSON string
            parsed = json.loads(json_str)
            if isinstance(parsed, dict):
                 logger.debug(f"Successfully parsed OpenAI response: {parsed}")
                 return parsed
            else:
                 logger.warning(f"Parsed JSON is not a dictionary: {type(parsed)}")
                 return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response from OpenAI: {e}. String was: '{json_str if 'json_str' in locals() else response_text[:100]}' ")
            return None
        except Exception as e:
            logger.exception(f"Error parsing OpenAI response: {e}")
            return None


    def solve(self, puzzle: Union[Puzzle, ScenarioPuzzle]) -> Optional[Dict[str, Any]]:
        logger = logging.getLogger(__name__)
        logger.info(f"OpenAISolver attempting Level {puzzle.level+1} ({type(puzzle).__name__})")
        if not self.api_key:
            logger.error("OpenAI API Key not set.")
            # In a real app, you might raise an exception or return a specific error object
            # that the UI can catch and display a message.
            # from PyQt6.QtWidgets import QMessageBox
            # QMessageBox.warning(None, "API Key Error", "OpenAI API Key is missing. Please set it via Options menu.")
            return None # Indicate failure due to missing config

        # --- Placeholder for API Call ---
        # In a real implementation, this section would use the 'openai' library
        # or 'requests' to call the API.

        # 1. Create the prompt
        prompt = self._create_prompt(puzzle)
        logger.debug(f"--- OpenAI Prompt ---\n{prompt}\n--------------------")
        if "Error:" in prompt:
             logger.error(f"Failed to create prompt: {prompt}")
             return None

        # 2. Make the API call
        response_text = ""
        try:
            # --- Replace with actual API call ---
            # Example using hypothetical openai client:
            # if not self.openai_client:
            #     logger.error("OpenAI client not initialized (API key missing or import failed?).")
            #     return None
            # response = self.openai_client.chat.completions.create(
            #      model="gpt-4", # Or desired model
            #      messages=[{"role": "user", "content": prompt}],
            #      temperature=0.2, # Lower temperature for more deterministic output
            #      response_format={"type": "json_object"} # Request JSON output if model supports
            # )
            # response_text = response.choices[0].message.content
            # logger.info(f"Received response from OpenAI API.")
            # ------------------------------------

            # Dummy response for placeholder:
            logger.warning("OpenAI API call is not implemented. Using dummy response.")
            # Select a dummy based on puzzle type for basic testing
            if isinstance(puzzle, Puzzle) and not puzzle.is_scenario:
                 dummy_sol = puzzle.solution_mapping.copy() # Use internal solution for dummy
                 response_text = json.dumps(dummy_sol)
            elif isinstance(puzzle, ScenarioPuzzle):
                 dummy_sol = puzzle.solution.copy() # Use internal solution for dummy
                 response_text = json.dumps(dummy_sol)
            else:
                 response_text = '{"error": "Dummy response for unknown type"}'
            # Add artificial delay
            time.sleep(0.5)

        except Exception as api_error:
            logger.exception(f"Error during OpenAI API call: {api_error}")
            return None
        # --- End Placeholder ---

        # 3. Parse the response
        solution = self._parse_response(response_text)

        # 4. Basic Validation of parsed structure (Optional but recommended)
        if solution:
            ptype = puzzle.puzzle_type if isinstance(puzzle, ScenarioPuzzle) else None
            required_key = None
            if isinstance(puzzle, Puzzle) and not puzzle.is_scenario:
                # Check if all symbols are present as keys
                if not all(s in solution for s in puzzle.symbols):
                    logger.warning(f"OpenAI Symbol response missing keys. Expected: {puzzle.symbols}, Got keys: {list(solution.keys())}")
                    return None # Solution structure is wrong
            elif isinstance(puzzle, ScenarioPuzzle):
                 if ptype == HumanScenarioType.LOGIC_GRID: required_key = 'grid'
                 elif ptype == HumanScenarioType.RELATIONSHIP_MAP: required_key = 'map'
                 elif ptype == HumanScenarioType.ORDERING: required_key = 'order'
                 elif ptype == HumanScenarioType.SCHEDULING: required_key = 'schedule'
                 elif ptype == HumanScenarioType.DILEMMA: required_key = 'choice'
                 elif ptype in [HumanScenarioType.SOCIAL_DEDUCTION, HumanScenarioType.COMMON_SENSE_GAP, HumanScenarioType.AGENT_SIMULATION]: required_key = 'answer'

                 if required_key and required_key not in solution:
                      logger.warning(f"OpenAI response missing required key '{required_key}' for {ptype.name if ptype else 'N/A'}. Solution: {solution}")
                      return None # Structure is wrong
                 # TODO: Could add more detailed validation here (e.g., check types of values)
        else:
             logger.warning("OpenAI response parsing failed or returned None.")
             return None

        return solution


# --- Add other placeholder classes similarly ---
# class ClaudeSolver(AbstractPuzzleSolver): ...
# class LocalModelSolver(AbstractPuzzleSolver): ...


# --- Solver Registry ---

# List of available solver classes (add more as implemented)
AVAILABLE_SOLVERS: List[type[AbstractPuzzleSolver]] = [
    InternalSolver,
    RandomGuessSolver,
    OpenAISolver,
    # ClaudeSolver,
    # LocalModelSolver,
]

# Function to get instantiated solvers
def get_solver_instances() -> Dict[str, AbstractPuzzleSolver]:
    """Creates instances of all available solvers."""
    instances = {}
    logger = logging.getLogger(__name__)
    for solver_class in AVAILABLE_SOLVERS:
        try:
            instance = solver_class()
            if instance.name in instances:
                 logger.warning(f"Duplicate solver name '{instance.name}' found from class {solver_class.__name__}. Overwriting.")
            instances[instance.name] = instance
            logger.info(f"Successfully instantiated solver: {instance.name}")
        except Exception as e:
            logger.error(f"Failed to instantiate solver {solver_class.__name__}: {e}", exc_info=True)
    return instances