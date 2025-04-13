from typing import Dict, List, Tuple, Optional, Any, Union, Set
import random
from collections import defaultdict
from enum import Enum, auto
import itertools # Needed for solver permutation check
import re # Needed for clue parsing in verifier
import math
import logging

# Define constants at the module level
LETTERS_POOL = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
VOWELS = "AEIOU"

# --- Constants ---
LOGIC_GRID_YES = '✔️'
LOGIC_GRID_NO = '❌'
LOGIC_GRID_UNKNOWN = '?'

# --- Main Classes ---

class ClueType(Enum):
    DIRECT = auto()          # Direct symbol-to-letter mapping
    EXCLUSION = auto()       # Symbol cannot map to letter
    POSITIONAL = auto()      # Symbol's position in sequence
    RELATIONAL = auto()      # Relationship between symbols/letters
    CATEGORY = auto()        # Category-based clues (vowels, consonants, etc.)
    LOGICAL = auto()         # More complex logical relationships

class Puzzle:
    """Represents a single Symbol Cipher puzzle with educational elements."""
    def __init__(self, level: int, symbols: List[str], letters: List[str],
                 solution_mapping: Dict[str, str], clues: List[Tuple[str, ClueType]],
                 is_verified: bool = False): # Added verification flag
        self.level = level
        self.symbols = symbols
        self.letters = letters
        self.solution_mapping = solution_mapping # The intended solution
        self.clues = clues
        self.num_elements = len(symbols)
        self.clue_types_used = {clue_type for _, clue_type in clues}
        self.is_verified = is_verified
        self.is_scenario = False # Differentiate from ScenarioPuzzles

    def check_solution(self, user_mapping: Dict[str, str]) -> bool:
        """Checks if the user's mapping matches the solution."""
        if len(user_mapping) != self.num_elements:
            return False
        # In a verified puzzle, comparing against the stored solution is sufficient
        return user_mapping == self.solution_mapping

    def get_hint(self, user_mapping: Dict[str, str]) -> Optional[Tuple[str, str, str]]:
        """Provides a hint with explanation of the logical reasoning."""
        unrevealed = {s: l for s, l in self.solution_mapping.items() 
                     if user_mapping.get(s) != l}
        if not unrevealed:
            return None
        
        if not self.clues:
            # Handle case where there might be unrevealed symbols but no clues left
            unrevealed_keys = list(unrevealed.keys())
            if not unrevealed_keys: return None # Should not happen if unrevealed is not empty, but safety check
            symbol_to_reveal = random.choice(unrevealed_keys)
            return (symbol_to_reveal, self.solution_mapping[symbol_to_reveal],
                    "No specific clues available for this hint.")

        # Iterate through unrevealed symbols first to ensure 'symbol' is defined
        shuffled_unrevealed = list(unrevealed.keys())
        random.shuffle(shuffled_unrevealed)
        
        for symbol in shuffled_unrevealed:
            # Now iterate through clues to find one related to the current 'symbol'
            shuffled_clues = list(self.clues)
            random.shuffle(shuffled_clues)
            for clue_text, clue_type in shuffled_clues:
                # Check if the current symbol is relevant to this clue
                # Basic relevance check (can be improved with more robust parsing)
                if f"'{symbol}'" in clue_text or clue_text.startswith(f"{symbol} "):
                    # Provide hint based on clue type using the defined 'symbol'
                    hint_reason = f"Consider the clue: {clue_text}"
                    # Could add more specific reasoning per type here if needed
                    return (symbol, self.solution_mapping[symbol], hint_reason)

        # Fallback hint if *no* relevant clue was found for *any* unrevealed symbol after checking all
        symbol_to_reveal = random.choice(shuffled_unrevealed) # Use the already shuffled list
        return (symbol_to_reveal, self.solution_mapping[symbol_to_reveal],
                "No specific clue directly helps with the remaining symbols. Try making an educated guess.")


class HumanScenarioType(Enum):
    LOGIC_GRID = auto()      # Classic logic grid (people, objects, attributes)
    SCHEDULING = auto()        # E.g., Who is available when? (More structured)
    RELATIONSHIP_MAP = auto()  # E.g., Mapping relationships in a group
    ORDERING = auto()        # E.g., Sequence of events, ranking
    SOCIAL_DEDUCTION = auto()  # E.g., Identifying lies, motives based on statements
    COMMON_SENSE_GAP = auto()  # E.g., Finding missing steps/items in a process
    DILEMMA = auto()           # E.g., Choosing best action in a social/ethical situation
    AGENT_SIMULATION = auto()  # Deducing state/rules from agent interactions


class ScenarioPuzzle:
    """Represents a logic puzzle based on a human-centric scenario."""
    def __init__(self, level: int, puzzle_type: HumanScenarioType,
                 description: str, # Narrative description of the scenario
                 characters: List[Dict[str, Any]], # List of involved characters/entities and their traits
                 setting: Dict[str, Any], # Details about the location/context
                 goal: str, # What the player needs to figure out
                 information: List[str], # Clues, statements, observations (can be narrative)
                 solution: Dict[str, Any], # Solution format depends heavily on puzzle type
                 rules: Optional[List[str]] = None,
                 options: Optional[List[str]] = None, # Added for DILEMMA
                 elements: Optional[Dict[str, List[str]]] = None, # Added for LOGIC_GRID UI
                 **kwargs): # Accept extra kwargs
        # Pop or ignore 'is_verified' and other unexpected args from kwargs if needed
        kwargs.pop('is_verified', None) # Example: explicitly ignore is_verified
        if kwargs:
            print(f"Warning: Ignoring unexpected arguments when creating ScenarioPuzzle: {list(kwargs.keys())}")

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
                 # Expecting user_solution to contain {"grid": {... solved grid ...}}
                 # And self.solution to also contain {"grid": {... correct grid ...}}
                 if 'grid' not in self.solution or 'grid' not in user_solution:
                      print("Warning: Missing 'grid' key in solution check for LOGIC_GRID.")
                      return False
                 # Direct comparison of the grid dictionaries
                 # TODO: This might need a more robust check depending on grid format
                 return self.solution['grid'] == user_solution['grid']
            
            # --- Simple Answer Check (Social Deduction, Common Sense Gap, AGENT_SIMULATION) --- 
            elif self.puzzle_type in [HumanScenarioType.SOCIAL_DEDUCTION, HumanScenarioType.COMMON_SENSE_GAP, HumanScenarioType.AGENT_SIMULATION]:
                 # Expecting {"answer": "..."} format for both self.solution and user_solution
                 if 'answer' not in self.solution or 'answer' not in user_solution:
                     print(f"Warning: Missing 'answer' key in solution check for {self.puzzle_type.name}.")
                     return False
                 
                 correct_answer = str(self.solution['answer']).strip().lower()
                 user_answer = str(user_solution['answer']).strip().lower()
                 
                 return user_answer == correct_answer
                 
            # --- Add checks for other types as needed --- 
            elif self.puzzle_type == HumanScenarioType.ORDERING:
                 # Assuming solution format: {"order": ["item1", "item2", ...]}
                 if 'order' not in self.solution or 'order' not in user_solution:
                      print(f"Warning: Missing 'order' key in solution check for {self.puzzle_type.name}.")
                      return False
                 # Ensure both are lists before comparing
                 sol_order = self.solution.get('order', [])
                 user_order = user_solution.get('order', [])
                 if not isinstance(sol_order, list) or not isinstance(user_order, list):
                      print(f"Warning: Invalid 'order' format in solution check for {self.puzzle_type.name}.")
                      return False
                 return sol_order == user_order
            elif self.puzzle_type == HumanScenarioType.RELATIONSHIP_MAP:
                # Check if the user's map represents the same pairs as the solution map.
                if 'map' not in self.solution or 'map' not in user_solution:
                    print(f"Warning: Missing 'map' key in solution check for {self.puzzle_type.name}.")
                    return False

                sol_map = self.solution.get('map', {})
                user_map = user_solution.get('map', {})

                if not isinstance(sol_map, dict) or not isinstance(user_map, dict):
                    print(f"Warning: Invalid 'map' format in solution check for {self.puzzle_type.name}.")
                    return False

                # Helper to normalize map to a set of frozensets (pairs)
                def normalize_map(relationship_map: Dict[str, str]) -> Set[frozenset]:
                    normalized_pairs = set()
                    processed_keys = set()
                    for key, value in relationship_map.items():
                        # Avoid processing the reverse pair if already handled
                        if key not in processed_keys and value not in processed_keys:
                            normalized_pairs.add(frozenset({key, value}))
                            processed_keys.add(key)
                            processed_keys.add(value)
                    return normalized_pairs

                try:
                    normalized_solution_pairs = normalize_map(sol_map)
                    normalized_user_pairs = normalize_map(user_map)
                    
                    # Compare the sets of pairs
                    return normalized_solution_pairs == normalized_user_pairs
                except Exception as e:
                    # Catch potential errors during normalization (e.g., unexpected map format)
                    print(f"Error normalizing relationship maps for comparison: {e}")
                    return False
            elif self.puzzle_type == HumanScenarioType.SCHEDULING:
                print(f"Warning: Solution check for {self.puzzle_type.name} not implemented.")
                # TODO: Implement SCHEDULING solution check (e.g., compare schedule grids/dictionaries)
                # Assuming solution format like: {"schedule": {person1: {time1: status, ...}, ...}}
                if 'schedule' not in self.solution or 'schedule' not in user_solution:
                    print(f"Warning: Missing 'schedule' key in solution check for {self.puzzle_type.name}.")
                    return False
                # Basic dict comparison for now
                return self.solution.get('schedule', {}) == user_solution.get('schedule', {})
            elif self.puzzle_type == HumanScenarioType.DILEMMA:
                print(f"Warning: Solution check for {self.puzzle_type.name} not implemented.")
                # TODO: Implement DILEMMA solution check (might involve checking selected choice/justification)
                # Assuming solution format like: {"choice": "option_a", "justification": "..."}
                # For now, just compare choice if available
                if 'choice' not in self.solution or 'choice' not in user_solution:
                     print(f"Warning: Missing 'choice' key in solution check for {self.puzzle_type.name}.")
                     return False
                return self.solution.get('choice') == user_solution.get('choice')
            else:
                 # Fallback for unimplemented types: basic dictionary comparison
                 print(f"Warning: Using basic dictionary comparison for unhandled type: {self.puzzle_type.name}")
                 return self.solution == user_solution

        except Exception as e:
             # Handle potential errors during comparison (e.g., type mismatches)
             print(f"Error during solution check for type {self.puzzle_type.name}: {e}")
             return False

    def get_hint(self, user_state: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Provides a scenario-based hint."""
        # Hint logic will be very specific to the scenario type
        # Could reveal a subtle aspect of a statement, focus attention on a character, etc.
        if not self.information:
             return "Try re-reading the scenario description and goal carefully. (No specific hints available)"

        # Simple hint: point to a random piece of information
        hint_info = random.choice(self.information)
        # Make hint less direct than just showing the clue
        if self.puzzle_type == HumanScenarioType.LOGIC_GRID:
             return f"Consider this clue: '{hint_info}'" # Logic grids often use direct clues
        else:
            # For narrative types, make it more interpretive
            return f"Pay close attention to this detail: '{hint_info}' What might it imply in this situation?"


class PuzzleGenerator:
    """Generates verified Symbol Cipher OR human-centric Scenario puzzles."""
    SYMBOLS_POOL = ["α", "β", "γ", "δ", "ε", "ζ", "η", "θ", "ι", "κ", "λ", "μ", "ν", "ξ", "ο", "π", "ρ", "σ", "τ", "υ", "φ", "χ", "ψ", "ω"] # Expanded pool
    LETTERS_POOL = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" # Keep for symbol puzzles
    VOWELS = "AEIOU"
    CONSONANTS = "".join(c for c in LETTERS_POOL if c not in VOWELS)

    # --- Scenario Data Pools (Examples - to be expanded significantly) ---
    SCENARIO_NAMES = [
        "Aisha", "Alex", "Alicia", "Ben", "Brandon", "Brenda", "Carlos", "Chloe", "Chen",
        "David", "Deepa", "Eva", "Ethan", "Finn", "Fatima", "Grace", "Gabriel", "Hugo", "Hannah",
        "Isla", "Isaac", "Javier", "Jack", "Jamal", "Kate", "Kenji", "Liam", "Lin",
        "Maya", "Marco", "Mei", "Noah", "Nadia", "Omar", "Olivia", "Priya", "Pedro",
        "Quinn", "Raj", "Ricardo", "Sofia", "Samira", "Tariq", "Tasha", "Uma", "Vikram",
        "Wei", "Willow", "Xavier", "Yara", "Yusuf", "Zainab", "Zoe"
    ]
    SCENARIO_TRAITS = [
        # Positive/Neutral
        "Honest", "Helpful", "Calm", "Creative", "Organized", "Optimistic", "Practical", "Patient",
        "Punctual", "Resourceful", "Logical", "Detail-oriented", "Cooperative", "Diplomatic", "Generous",
        "Curious", "Methodical", "Observant", "Humorous", "Adaptable",
        # Negative/Challenging
        "Forgetful", "Busy", "Secretive", "Anxious", "Distracted", "Quiet", "Talkative", "Skeptical",
        "Pessimistic", "Impatient", "Impulsive", "Stubborn", "Argumentative", "Evasive", "Messy",
        "Procrastinating", "Cynical", "Nitpicky", "Overly-competitive"
    ]
    SCENARIO_OCCUPATIONS = [
        "Accountant", "Artist", "Baker", "Barista", "Biologist", "Chef", "Carpenter", "Cashier",
        "Data Analyst", "Dentist", "Doctor", "Electrician", "Engineer", "Event Planner", "Florist",
        "Graphic Designer", "Hair Stylist", "Historian", "IT Support", "Journalist", "Librarian",
        "Mechanic", "Musician", "Nurse", "Office Manager", "Pharmacist", "Photographer", "Plumber",
        "Professor", "Project Manager", "Receptionist", "Researcher", "Salesperson", "Scientist",
        "Software Developer", "Teacher", "Translator", "Urban Planner", "Veterinarian", "Waiter/Waitress",
        "Web Developer", "Writer", "Yoga Instructor", "Zoologist"
    ]
    SCENARIO_RELATIONSHIPS = [
        "Colleagues", "Friends", "Siblings", "Neighbors", "Classmates", "Team Members",
        "Manager and Employee", "Teacher and Student", "Client and Service Provider",
        "Business Partners", "Old Rivals", "Mentor and Mentee", "Club Members", "Family Friends",
        "Acquaintances", "Former Partners", "Housemates", "Competitors"
    ]
    SCENARIO_SETTINGS = [
        {"name": "Office Meeting Room", "details": ["Whiteboard with diagrams", "Half-empty coffee cups", "Laptop chargers plugged in"]},
        {"name": "Local Cafe", "details": ["Background chatter", "Coffee machine hiss", "Pastries under glass", "Quiet background music"]},
        {"name": "Family Dinner", "details": ["Dining table set for four", "Home-cooked food smell", "Overlapping conversations", "Kids' drawings on the fridge"]},
        {"name": "Park Bench", "details": ["Birds chirping", "Distant traffic sounds", "People walking dogs", "Children playing nearby"]},
        {"name": "Online Chat Group", "details": ["Typing indicators flickering", "Use of emojis and GIFs", "Time stamps on messages", "Pinned announcement"]},
        {"name": "University Library", "details": ["Whispering voices", "Sound of pages turning", "Rows of bookshelves", "Study carrels with lamps"]},
        {"name": "Community Workshop", "details": ["Tools hanging on pegboard", "Sawdust on the floor", "Partially finished projects", "Smell of wood or paint"]},
    ]
    SCENARIO_GOALS = [
        "Figure out who accidentally deleted the shared document.",
        "Determine the correct order of arrivals at the party based on conflicting statements.",
        "Identify the person who secretly agrees with the unpopular proposal.",
        "Find the missing tool needed to assemble the furniture.",
        "Decide the fairest way to divide the remaining project tasks.",
        "Uncover the reason why someone missed the crucial meeting.",
        "Determine who left the confusing note on the fridge.",
        "Identify which statement contains the logical flaw.",
        "Figure out the correct sequence for watering the office plants.",
        "Find the discrepancy in the budget report.",
        "Discover who borrowed the missing stapler without asking.",
        "Piece together the timeline of events during the power outage.",
        "Identify the source of the misleading information.",
        "Resolve the scheduling conflict for the team meeting.",
        "Deduce the motive behind a surprising decision.",
        "Find the appropriate gift for a colleague based on subtle hints."
    ]
    COMMON_SENSE_ITEMS = {
        "baking a cake": {"present": ["flour", "sugar", "eggs", "mixing bowl", "oven"], "missing": ["oven mitts", "baking pan", "whisk"]},
        "making tea": {"present": ["kettle", "water", "mug"], "missing": ["tea bag", "milk", "sugar"]},
        "going camping": {"present": ["tent", "sleeping bag"], "missing": ["flashlight", "water bottle", "insect repellent"]},
        "planting a seed": {"present": ["seed", "pot", "sunlight"], "missing": ["soil", "water"]},
        "writing a letter": {"present": ["paper", "pen"], "missing": ["envelope", "stamp", "address"]},
        "making coffee (drip)": {"present": ["coffee maker", "water", "mug"], "missing": ["coffee grounds", "filter"]},
        "preparing for rain": {"present": ["shoes", "jacket"], "missing": ["umbrella", "rain boots"]},
        "setting a table": {"present": ["plate", "fork", "knife"], "missing": ["glass", "napkin", "spoon"]},
        "wrapping a gift": {"present": ["gift", "box"], "missing": ["wrapping paper", "tape", "scissors"]},
        "attending online meeting": {"present": ["computer", "internet"], "missing": ["webcam", "microphone", "meeting link"]}
    }
    # --- (End Scenario Data Pools) ---

    # --- Agent Simulation Rule Pool (Initial Draft) ---
    AGENT_SIMULATION_RULES = [
        # Movement Rules
        {"id": "MOVE_TOWARDS_GOAL_LOC", "text": "Agents move towards their target location if their goal is REACH."}, 
        {"id": "MOVE_AWAY_FROM_GOAL_AGENT", "text": "Agents move away from their target agent if their goal is AVOID."}, 
        {"id": "MOVE_RANDOM_IF_NO_GOAL", "text": "Agents without a clear goal-based move tend to move randomly."}, 
        # Trait-Based Movement/Preference
        {"id": "PREFER_QUIET_LOC", "text": "Agents with trait 'Quiet' prefer to move towards {location_A}."}, # Param: location_A
        {"id": "AVOID_CROWD_ANXIOUS", "text": "Agents with trait 'Anxious' move away from locations with more than one other agent."}, 
        {"id": "MOVE_TOWARDS_OTHERS_TALKATIVE", "text": "Agents with trait 'Talkative' prefer locations with other agents."}, 
        # Location Rules
        {"id": "LOCATION_CAPACITY_1", "text": "Only one agent can be in {location_B} at a time."}, # Param: location_B
        {"id": "LOCATION_STICKY", "text": "Agents who enter {location_C} tend to stay there for an extra turn."}, # Param: location_C
        # Interaction Rules (Simplified)
        {"id": "YIELD_ON_CONFLICT_CALM", "text": "If two agents try to enter the same empty location, the 'Calm' one yields (doesn't move)."},
        {"id": "SWAP_ON_INTERACT", "text": "If an agent's goal is INTERACT_WITH Agent X, and they reach Agent X, they swap locations on the next step."}
    ]

    SCENARIO_START_LEVEL = 3 # Lower level to introduce scenarios earlier
    HUMAN_SCENARIO_CHANCE_INCREASE = 0.15 # Faster increase in chance per level
    MAX_HUMAN_SCENARIO_CHANCE = 0.80 # Cap the chance

    # --- (Keep Logic Grid themes for now, might be used by specific type) ---\
    LOGIC_GRID_THEMES = {
        "Neighbors": {
            "categories": ["Name", "HouseColor", "Pet"],
            "elements": [
                ["Alice", "Bob", "Charlie"],
                ["Red", "Blue", "Green"],
                ["Cat", "Dog", "Fish"]
            ]
        },
        "Office Lunch": {
            "categories": ["Employee", "Sandwich", "Drink"],
            "elements": [
                ["David", "Eve", "Frank"],
                ["Ham", "Cheese", "Tuna"],
                ["Coffee", "Tea", "Water"]
            ]
        },
         "Party Guests": {
            "categories": ["Guest", "Costume", "Gift"],
            "elements": [
                 ["Grace", "Heidi", "Ivan", "Judy"], # Example 4x4
                 ["Pirate", "Robot", "Wizard", "Alien"],
                 ["Book", "Game", "Music", "Plant"]
            ]
        }
    }
    # --- (End Logic Grid Data) ---\

    def __init__(self, min_elements: int = 4, max_elements: int = 8, max_tries: int = 300): # Increased max_tries further
        # Basic validation
        if not (isinstance(min_elements, int) and min_elements > 0):
            raise ValueError("min_elements must be a positive integer")
        if not (isinstance(max_elements, int) and max_elements > 0):
            raise ValueError("max_elements must be a positive integer")
        if not (isinstance(max_tries, int) and max_tries > 0):
            raise ValueError("max_tries must be a positive integer")
        if min_elements > max_elements:
            raise ValueError("min_elements cannot be greater than max_elements")

        # Ensure pools are large enough for max_elements
        if max_elements > len(self.SYMBOLS_POOL):
             print(f"Warning: max_elements ({max_elements}) exceeds SYMBOLS_POOL size ({len(self.SYMBOLS_POOL)}). Clamping.")
             max_elements = len(self.SYMBOLS_POOL)
        if max_elements > len(LETTERS_POOL):
             print(f"Warning: max_elements ({max_elements}) exceeds LETTERS_POOL size ({len(LETTERS_POOL)}). Clamping.")
             max_elements = len(LETTERS_POOL)
        if min_elements > max_elements: # Re-check after clamping
             raise ValueError(f"min_elements ({min_elements}) cannot be greater than clamped max_elements ({max_elements}) due to pool size limits.")


        self.min_symbol_elements = min_elements # For symbol puzzles
        self.max_symbol_elements = max_elements # For symbol puzzles
        self.max_verification_tries = max_tries

    def generate_puzzle(self, level: int, **kwargs) -> Union[Puzzle, ScenarioPuzzle]: # Added **kwargs
        """Generates either a symbol cipher or a human scenario puzzle based on level.
           Can be forced to generate a specific type using kwargs."""
        force_type = kwargs.get('force_type') # Get the requested type

        # Handle forced types first
        if force_type == "Symbol":
            try:
                return self._generate_symbol_puzzle(level)
            except Exception as e:
                logging.error(f"Error explicitly generating symbol puzzle: {e}. Trying fallback.")
                # Fallback to scenario if symbol generation fails explicitly
                return self._generate_human_scenario_puzzle(level, specific_type=None) # Random scenario

        elif isinstance(force_type, HumanScenarioType):
            try:
                return self._generate_human_scenario_puzzle(level, specific_type=force_type)
            except Exception as e:
                logging.error(f"Error explicitly generating scenario {force_type.name}: {e}. Trying fallback.")
                # Fallback to symbol if specific scenario fails
                return self._generate_symbol_puzzle(level)
        elif force_type == "Scenario": # Force random scenario
             try:
                 return self._generate_human_scenario_puzzle(level, specific_type=None)
             except Exception as e:
                 logging.error(f"Error explicitly generating random scenario: {e}. Trying fallback.")
                 # Fallback to symbol if random scenario fails
                 return self._generate_symbol_puzzle(level)

        # If no specific type is forced (force_type is None), use level-based probability
        scenario_chance = 0.0
        if level >= self.SCENARIO_START_LEVEL:
             scenario_chance = min(0.2 + (level - self.SCENARIO_START_LEVEL) * self.HUMAN_SCENARIO_CHANCE_INCREASE, self.MAX_HUMAN_SCENARIO_CHANCE)

        puzzle_type_choice = random.random()

        if puzzle_type_choice < scenario_chance:
            try:
                # Try generating a random human-centric scenario puzzle
                return self._generate_human_scenario_puzzle(level, specific_type=None)
            except Exception as e:
                logging.error(f"Error generating random human scenario puzzle: {e}. Falling back to symbol puzzle.")
                # Fallback to symbol puzzle if scenario generation fails
                return self._generate_symbol_puzzle(level)
        else:
             # Generate symbol puzzle
             try:
                  return self._generate_symbol_puzzle(level)
             except Exception as e:
                  logging.error(f"Error generating symbol puzzle (level {level}): {e}. Trying random scenario as fallback.")
                  # Fallback to scenario if symbol generation fails
                  return self._generate_human_scenario_puzzle(level, specific_type=None)


    def _generate_symbol_puzzle(self, level: int) -> Puzzle:
        """Generates a verified symbol cipher puzzle."""
        for attempt in range(self.max_verification_tries):
            # Use specific min/max for symbol puzzles, adjusted by level
            num_elements = min(self.min_symbol_elements + level // 2, self.max_symbol_elements) # Slower increase per level
            num_elements = max(self.min_symbol_elements, num_elements) # Ensure minimum

            # Check against available pools for symbols/letters (already clamped in __init__)
            if num_elements > len(self.SYMBOLS_POOL) or num_elements > len(LETTERS_POOL):
                 # This should theoretically not be reached if __init__ clamping works
                 raise ValueError(f"Internal Error: num_elements ({num_elements}) exceeds pool sizes despite clamping.")

            symbols = random.sample(self.SYMBOLS_POOL, num_elements)
            letters = random.sample(LETTERS_POOL, num_elements)
            random.shuffle(letters) # Shuffle to make mapping non-trivial
            intended_solution = dict(zip(symbols, letters))

            clues = self._generate_educational_clues(symbols, letters, intended_solution, level)

            # Skip verification if no clues were generated (e.g., invalid input to clue gen)
            # Also add a basic check: need enough clues to potentially solve
            if not clues or len(clues) < num_elements // 3:
                # print(f"Warning: Insufficient or no clues generated for symbol puzzle attempt {attempt+1}, level {level}. Retrying.")
                continue # Retry generation

            # Verification step
            verifier = PuzzleVerifier(puzzle_type='symbol', symbols=symbols, letters=letters, clues=clues)
            is_unique, solutions = verifier.verify()

            if is_unique and len(solutions) == 1:
                # Check if the single solution matches the intended one
                # Note: zip order matters, ensure consistency if re-checking
                if solutions[0] == intended_solution:
                     # print(f"Symbol Verification successful (Attempt {attempt+1})")
                     return Puzzle(level, symbols, letters, intended_solution, clues, is_verified=True)
                # else:
                     # This case means the clues lead to a *different* unique solution
                     # This implies an issue in clue generation or verification logic.
                     # print(f"Warning: Unique solution found, but differs from intended! Attempt {attempt+1}, Level {level}")
                     # Consider this a failure and retry

            # If verification fails (0 or >1 solutions), loop continues to retry

        raise ValueError(f"Failed to generate a verifiable symbol puzzle after {self.max_verification_tries} attempts for level {level}.")

    def _generate_educational_clues(self, symbols: List[str], letters: List[str],
                                  solution_mapping: Dict[str, str], level: int) -> List[Tuple[str, ClueType]]:
        """Generates clues for symbol cipher puzzles."""
        clues = []
        if not symbols or not letters or not solution_mapping:
             print("Warning: Cannot generate symbol clues with empty symbols, letters, or solution.")
             return [] # Return empty list if inputs are invalid

        symbol_list = list(solution_mapping.keys())
        random.shuffle(symbol_list) # Use this shuffled list for selecting symbols for clues

        num_elements = len(symbols)
        # Adjust number of clues based on level and number of elements
        # Aim for slightly more clues than elements at higher levels for redundancy/guidance
        # Increase upper bound slightly, maybe num_elements * 2
        num_clues = min(num_elements + level // 2, num_elements * 2)
        num_clues = max(num_elements // 2 + 1, num_clues) # Ensure at least half + 1 (min 1)

        possible_clue_generators = {
            ClueType.DIRECT: self._generate_direct_clue,
            ClueType.EXCLUSION: self._generate_exclusion_clue,
            ClueType.POSITIONAL: self._generate_positional_clue,
            ClueType.RELATIONAL: self._generate_relational_clue,
            ClueType.CATEGORY: self._generate_category_clue,
            ClueType.LOGICAL: self._generate_logical_clue,
        }

        # Determine available clue types based on level and puzzle size
        available_clue_types = [ClueType.DIRECT, ClueType.EXCLUSION] # Always available
        if level >= 1 and num_elements >= 2:
            available_clue_types.append(ClueType.CATEGORY)
        if level >= 2 and num_elements >= 3: # Need enough elements for relations/positions
             available_clue_types.extend([ClueType.POSITIONAL, ClueType.RELATIONAL])
        if level >= 4 and num_elements >= 4: # Logical clues need more complexity
            available_clue_types.append(ClueType.LOGICAL)

        generated_clue_texts = set() # Track generated text to avoid duplicates

        # Ensure symbol_list is passed correctly
        current_symbol_pool = list(symbol_list) # Make a copy to potentially modify

        for i in range(num_clues):
             if not current_symbol_pool: # Ensure we have symbols to base clues on
                 break # Stop if we run out of symbols to reference

             clue_type = random.choice(available_clue_types)
             generator_func = possible_clue_generators[clue_type]

             # Try generating a clue up to 5 times to avoid rare infinite loops
             for _ in range(5):
                 try:
                     # Pass the *original* full symbols list for positional,
                     # but the shuffled subset (current_symbol_pool) for selection
                     # Note: symbol_pool argument is not consistently used across all generators, some use symbols directly. Refactor needed for consistency if required.
                     clue_text = generator_func(symbols, letters, solution_mapping, current_symbol_pool)
                     if clue_text and clue_text not in generated_clue_texts:
                         clues.append((clue_text, clue_type))
                         generated_clue_texts.add(clue_text)
                         # Optional: remove used symbol from current_symbol_pool if clue reveals it?
                         # Requires more complex handling. For now, just avoid text duplicates.
                         break # Success, move to next clue attempt
                 except Exception as e:
                     # Catch potential errors in individual clue generators
                     # print(f"Warning: Error generating {clue_type.name} clue: {e}. Retrying generator.")
                     pass # Allow retry within the 5 attempts

        # Basic check: Ensure enough clues were generated relative to elements
        # if len(clues) < num_elements // 2 and num_elements > 1:
        #      print(f"Warning: Generated fewer clues ({len(clues)}) than expected minimum for {num_elements} elements at level {level}.")

        return clues

    # Placeholder for the new human-centric puzzle generator
    def _generate_human_scenario_puzzle(self, level: int, specific_type: Optional[HumanScenarioType] = None) -> ScenarioPuzzle:
        """Generates a human-centric scenario puzzle. If specific_type is None, chooses randomly."""
        # --- Basic Setup ---
        # Define the pool of types we can currently generate reasonably well
        generatable_types = [
            HumanScenarioType.SOCIAL_DEDUCTION,
            HumanScenarioType.COMMON_SENSE_GAP,
            HumanScenarioType.AGENT_SIMULATION,
            HumanScenarioType.RELATIONSHIP_MAP, # Added
            HumanScenarioType.ORDERING, # Added - Placeholder
            HumanScenarioType.SCHEDULING, # Added - Placeholder
            # HumanScenarioType.DILEMMA, # Added - Placeholder (Consider complexity)
            # HumanScenarioType.LOGIC_GRID # Enable this if _generate_logic_grid_puzzle is robust
        ]

        if specific_type:
             if specific_type in generatable_types:
                 chosen_type = specific_type
             else:
                 logging.warning(f"Requested scenario type {specific_type.name} is not currently generatable. Choosing random.")
                 chosen_type = random.choice(generatable_types)
        else: # No specific type requested, choose randomly
             chosen_type = random.choice(generatable_types)

        print(f"Attempting to generate puzzle type: {chosen_type.name}") # Debugging

        # --- Use Specific Generator based on Type ---
        generation_function_map = {
            HumanScenarioType.LOGIC_GRID: self._generate_logic_grid_puzzle,
            HumanScenarioType.AGENT_SIMULATION: self._generate_agent_simulation_puzzle,
            HumanScenarioType.SOCIAL_DEDUCTION: self._generate_social_deduction_puzzle, # Needs its own func
            HumanScenarioType.COMMON_SENSE_GAP: self._generate_common_sense_gap_puzzle, # Needs its own func
            HumanScenarioType.RELATIONSHIP_MAP: self._generate_relationship_map_puzzle, # Needs its own func
            HumanScenarioType.ORDERING: self._generate_ordering_puzzle, # New placeholder func
            HumanScenarioType.SCHEDULING: self._generate_scheduling_puzzle, # New placeholder func
            HumanScenarioType.DILEMMA: self._generate_dilemma_puzzle, # New placeholder func
        }

        if chosen_type in generation_function_map:
            generator_func = generation_function_map[chosen_type]
            try:
                return generator_func(level)
            except NotImplementedError:
                 print(f"Generation function for {chosen_type.name} is not implemented. Falling back.")
            except Exception as e:
                print(f"Failed to generate {chosen_type.name}, falling back: {e}")
        else:
             print(f"Warning: No generation function mapped for type {chosen_type.name}. Falling back.")

        # --- Fallback Logic (Ensure this block is correctly indented within the method) --- #
        # This fallback logic should ideally only be reached if the chosen type's
        # dedicated generator fails OR if there was no function mapped initially.
        fallback_types = [
            HumanScenarioType.SOCIAL_DEDUCTION,
            HumanScenarioType.COMMON_SENSE_GAP,
        ]
        fallback_types = [t for t in fallback_types if t != chosen_type]
        if not fallback_types:
            fallback_types.append(HumanScenarioType.SOCIAL_DEDUCTION)

        fallback_choice = random.choice(fallback_types)
        print(f"Falling back to generate type: {fallback_choice.name}")
        
        # The fallback_choice is guaranteed to be in the map based on current fallback_types
        generator_func = generation_function_map[fallback_choice]
        try:
            # Call the dedicated generator for the fallback
            return generator_func(level) 
        except Exception as fallback_e:
            # If fallback also fails, raise a specific error
            raise ValueError(f"Failed to generate primary type {chosen_type.name} and fallback type {fallback_choice.name}.") from fallback_e
        # No code should follow the raise in the except block within this fallback path.

    def _generate_social_deduction_puzzle(self, level: int) -> ScenarioPuzzle:
         """Generates a SOCIAL_DEDUCTION scenario puzzle."""
         # --- Component Selection ---
         # (Select characters, setting, goal etc. - moved from main generator)
         setting = random.choice(self.SCENARIO_SETTINGS)
         num_chars = min(3 + level // 3, len(self.SCENARIO_NAMES))
         num_chars = max(2, num_chars)
         if num_chars > len(self.SCENARIO_NAMES):
             raise ValueError(f"Not enough unique names ({len(self.SCENARIO_NAMES)})")
         char_names = random.sample(self.SCENARIO_NAMES, num_chars)
         occupations = random.sample(self.SCENARIO_OCCUPATIONS, min(num_chars, len(self.SCENARIO_OCCUPATIONS)))
         assigned_occupations = [occupations[i % len(occupations)] for i in range(num_chars)]
         characters = []
         for i, name in enumerate(char_names):
             trait = random.choice(self.SCENARIO_TRAITS)
             occupation = assigned_occupations[i]
             characters.append({"name": name, "trait": trait, "occupation": occupation})
         relationship = random.choice(self.SCENARIO_RELATIONSHIPS)

         # --- Generate Specifics ---
         goal = random.choice([g for g in self.SCENARIO_GOALS if "who" in g or "identify" in g or "reason" in g or "source" in g or "motive" in g or "discrepancy" in g])
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
        # --- Component Selection ---
        setting = random.choice(self.SCENARIO_SETTINGS)
        num_chars = 1 # Only need one person for this usually
        char_names = random.sample(self.SCENARIO_NAMES, num_chars)
        characters = [{"name": name, "trait": random.choice(self.SCENARIO_TRAITS)} for name in char_names] # Occupation less relevant here

        # --- Generate Specifics ---
        scenario_key = random.choice(list(self.COMMON_SENSE_ITEMS.keys()))
        scenario_data = self.COMMON_SENSE_ITEMS[scenario_key]
        process_desc = scenario_key
        k_present = random.randint(2, min(len(scenario_data["present"]), 4))
        items_present = random.sample(scenario_data["present"], k=k_present)
        missing_item = random.choice(scenario_data["missing"])
        solution = {"answer": missing_item}
        goal = f"Identify the essential missing item/tool needed to complete the task: {process_desc}."

        description = f"Task Context: In a {setting['name']}, {char_names[0]} is preparing to '{process_desc}'. They have gathered the following: {', '.join(items_present)}."

        information = [f"They seem ready to proceed but something feels incomplete."]
        distractor_items = [i for i in scenario_data["present"] if i not in items_present]
        if distractor_items:
             information.append(f"Nearby, one can also see a {random.choice(distractor_items)}.")
        if setting['details']:
             information.append(f"Relevant context: {random.choice(setting['details'])}.")

        # Add hint based on missing item purpose
        if missing_item in ["oven mitts", "rain boots", "umbrella"]: hint = "Protection from heat/weather is needed."
        elif missing_item in ["baking pan", "envelope", "filter", "pot", "wrapping paper"]: hint = "A container or specific medium is required."
        elif missing_item in ["whisk", "stamp", "tea bag", "soil", "tape", "scissors", "webcam", "microphone"]: hint = "A specific tool or consumable is necessary."
        elif missing_item in ["address", "meeting link"]: hint = "Crucial information is missing to proceed."
        else: hint = "Think about the next logical step in the process."
        information.append(f"Hint: {hint}")
        random.shuffle(information)

        return ScenarioPuzzle(level=level, puzzle_type=HumanScenarioType.COMMON_SENSE_GAP, description=description, characters=characters, setting=setting, goal=goal, information=information, solution=solution)

    def _generate_relationship_map_puzzle(self, level: int) -> ScenarioPuzzle:
         """Generates a RELATIONSHIP_MAP scenario puzzle."""
         # --- Component Selection ---
         setting = random.choice(self.SCENARIO_SETTINGS)
         num_chars = min(4 + (level // 2) * 2, len(self.SCENARIO_NAMES)) # Need even number, 4, 6, 8...
         num_chars = max(4, num_chars) # Ensure at least 4 for pairs
         if num_chars > len(self.SCENARIO_NAMES):
             raise ValueError(f"Not enough unique names ({len(self.SCENARIO_NAMES)}) for {num_chars} chars")
         if num_chars % 2 != 0: # Ensure even number if sample size allowed odd
             num_chars -=1

         char_names = random.sample(self.SCENARIO_NAMES, num_chars)
         occupations = random.sample(self.SCENARIO_OCCUPATIONS, min(num_chars, len(self.SCENARIO_OCCUPATIONS)))
         assigned_occupations = [occupations[i % len(occupations)] for i in range(num_chars)]
         characters = []
         for i, name in enumerate(char_names):
             trait = random.choice(self.SCENARIO_TRAITS)
             occupation = assigned_occupations[i]
             characters.append({"name": name, "trait": trait, "occupation": occupation})
         relationship = random.choice(self.SCENARIO_RELATIONSHIPS)

         # --- Generate Specifics ---
         goal = random.choice([
             "Determine who is partnered with whom.",
             "Map out the reporting structure (direct pairs only).", # Simplified goal
             "Identify the mentor for each trainee (1-to-1 pairing)."
         ])
         num_pairs = num_chars // 2
         shuffled_chars = list(characters)
         random.shuffle(shuffled_chars)

         solution_map = {}
         for i in range(num_pairs):
             char1_info = shuffled_chars[2*i]
             char2_info = shuffled_chars[2*i + 1]
             char1_name = char1_info['name']
             char2_name = char2_info['name']
             solution_map[char1_name] = char2_name
             solution_map[char2_name] = char1_name # Assume bidirectional for now

         solution = {"map": solution_map}

         involved_people_str = ", ".join([f"{c['name']} ({c['occupation']})" for c in characters])
         description = f"Context: A group of {relationship} are involved in a task at {setting['name']}. Details: {', '.join(setting['details'])}. Goal: {goal}. The individuals are: {involved_people_str}."

         clues = []
         potential_clue_pairs = list(itertools.combinations(characters, 2))
         random.shuffle(potential_clue_pairs)
         num_clues_target = num_chars # Target roughly one clue per person
         clues_generated = 0

         for char_a_info, char_b_info in potential_clue_pairs:
             if clues_generated >= num_clues_target: break
             char_a_name = char_a_info['name']
             char_b_name = char_b_info['name']
             are_paired = solution_map.get(char_a_name) == char_b_name

             if are_paired:
                 # Positive clue
                 if char_a_info['trait'] == "Cooperative" or char_b_info['trait'] == "Helpful":
                     clues.append(f"{char_a_name} was seen working closely with {char_b_name}.")
                 elif char_a_info['trait'] == "Organized":
                     clues.append(f"{char_a_name}'s notes mention frequent meetings with {char_b_name}.")
                 else:
                     clues.append(f"There's evidence linking {char_a_name} and {char_b_name} on this task.")
                 clues_generated += 1
             else:
                 # Negative clue (generate less frequently)
                 if random.random() < 0.6:
                     if char_a_info['trait'] == "Skeptical" or char_b_info['trait'] == "Independent":
                         clues.append(f"{char_a_name} explicitly stated they prefer not to work with {char_b_name}.")
                     elif char_a_info['trait'] == "Busy":
                          clues.append(f"{char_a_name} mentioned having conflicting schedules with {char_b_name}.")
                     else:
                         clues.append(f"It is known that {char_a_name} and {char_b_name} are in different project groups.")
                     clues_generated += 1

         # Ensure enough clues
         while clues_generated < num_pairs: # Need at least enough clues to define pairs
              clues.append("Further investigation is needed to confirm all relationships.")
              clues_generated+=1

         information = clues
         random.shuffle(information)

         return ScenarioPuzzle(level=level, puzzle_type=HumanScenarioType.RELATIONSHIP_MAP, description=description, characters=characters, setting=setting, goal=goal, information=information, solution=solution)

    def _generate_ordering_puzzle(self, level: int) -> ScenarioPuzzle:
        """Generates an ORDERING scenario puzzle. [PLACEHOLDER]"""
        print("Warning: _generate_ordering_puzzle is a placeholder.")
        # TODO: Implement actual generation logic for ORDERING puzzles
        # - Select items/events to order (3-6 based on level?)
        # - Create a correct sequence (solution)
        # - Generate clues (e.g., "A happened before B", "C was last", "B and D were adjacent")
        # - Ensure clues lead to a unique solution (tricky part!)
        items_to_order = random.sample(["Event Alpha", "Task Beta", "Step Gamma", "Process Delta", "Action Epsilon"], k=min(3 + level // 2, 5))
        solution_order = list(items_to_order)
        random.shuffle(solution_order)
        solution = {"order": solution_order}
        goal = f"Determine the correct sequence of the following: {', '.join(items_to_order)}."
        description = f"A series of events occurred, but the exact order is unclear. Use the information provided to reconstruct the sequence."
        # Placeholder Clues
        information = [
            f"{solution_order[0]} happened first.",
            f"{solution_order[-1]} was the last one.",
            f"{solution_order[1]} occurred immediately after {solution_order[0]}."
        ]
        if len(solution_order) > 3:
             information.append(f"{solution_order[-2]} happened sometime before {solution_order[-1]}.")
        random.shuffle(information)

        return ScenarioPuzzle(level=level, puzzle_type=HumanScenarioType.ORDERING, description=description, characters=[], setting={}, goal=goal, information=information, solution=solution)


    def _generate_scheduling_puzzle(self, level: int) -> ScenarioPuzzle:
        """Generates a SCHEDULING scenario puzzle."""
        print("Generating SCHEDULING puzzle...") # Debugging

        # --- Parameters based on Level ---
        num_people = random.randint(min(3 + level // 3, 4), min(4 + level // 2, 5))
        num_slots = random.randint(min(3 + level // 3, 4), min(4 + level // 2, 5))
        num_constraints = int(num_people * num_slots * 0.4 + level) # ~40% constraints + level bonus

        if num_people > len(self.SCENARIO_NAMES):
            raise ValueError(f"Cannot generate scheduling puzzle: Not enough names ({len(self.SCENARIO_NAMES)}) for {num_people} people.")

        people = random.sample(self.SCENARIO_NAMES, k=num_people)
        # Generate time slots like "9 AM", "10 AM", "11 AM", "1 PM", "2 PM"
        start_hour = random.choice([8, 9])
        time_slots = []
        for i in range(num_slots):
            hour = start_hour + i
            if hour == 12:
                time_slots.append(f"12 PM") # Handle noon
            elif hour > 12:
                 time_slots.append(f"{hour - 12} PM")
            else:
                 time_slots.append(f"{hour} AM")

        # --- Generate Constraints and Solution ---
        # Represent schedule as {person: {time_slot: "Available"/"Booked"}}
        # Represent constraints as list of functions or tuples:
        # ('unavailable', person, time_slot)
        # ('must_be', person, time_slot)
        # ('before', person1, person2) -> p1's booked slot must be earlier than p2's
        # ('together', person1, person2) -> must have the same booked slot
        # ('apart', person1, person2) -> must have different booked slots

        max_attempts = 100
        for attempt in range(max_attempts):
            constraints = []
            potential_solution = {p: {t: "Available" for t in time_slots} for p in people}
            num_booked_slots = 0 # Track booked slots to ensure puzzle isn't trivial

            # 1. Generate basic availability/unavailability constraints
            for _ in range(num_constraints // 2):
                person = random.choice(people)
                slot = random.choice(time_slots)
                if random.random() < 0.4: # ~40% chance of 'must_be' (rare)
                    constraints.append(('must_be', person, slot))
                else:
                    constraints.append(('unavailable', person, slot))

            # 2. Generate relational constraints
            for _ in range(num_constraints // 2):
                p1, p2 = random.sample(people, 2)
                constraint_type = random.choice(['before', 'together', 'apart'])
                if constraint_type == 'before':
                    constraints.append(('before', p1, p2))
                elif constraint_type == 'together':
                     constraints.append(('together', p1, p2))
                elif constraint_type == 'apart':
                     constraints.append(('apart', p1, p2))

            # 3. Try to build a solution satisfying constraints
            # This is the complex part - a simple backtracking or constraint satisfaction solver needed
            # Basic iterative approach (might not find complex solutions or be efficient):
            possible = True
            temp_solution = {p: {t: "Unknown" for t in time_slots} for p in people} # Start fresh

            # Apply must_be first
            for constraint in constraints:
                 if constraint[0] == 'must_be':
                     person, slot = constraint[1], constraint[2]
                     if temp_solution[person][slot] == "Booked": # Conflict
                          pass # Ignore, maybe another must_be set it
                     elif temp_solution[person][slot] == "Unavailable":
                         possible = False; break
                     else:
                         # Make this slot booked, others unavailable for this person
                         for s in time_slots: temp_solution[person][s] = "Unavailable"
                         temp_solution[person][slot] = "Booked"
                         num_booked_slots+=1
            if not possible: continue # Retry generation

            # Apply unavailable
            for constraint in constraints:
                 if constraint[0] == 'unavailable':
                     person, slot = constraint[1], constraint[2]
                     if temp_solution[person][slot] == "Booked":
                         possible = False; break
                     temp_solution[person][slot] = "Unavailable"
            if not possible: continue

            # Fill remaining 'Unknown' with available/booked somewhat randomly, respecting constraints
            # Simplified fill: Randomly book some available slots
            num_targets_to_book = max(1, num_people // 2) # Ensure at least one booking if possible
            booked_count_target = num_booked_slots + num_targets_to_book

            fill_attempts = 0
            while num_booked_slots < booked_count_target and fill_attempts < num_people * num_slots * 2:
                person = random.choice(people)
                slot = random.choice(time_slots)
                if temp_solution[person][slot] == "Unknown":
                     temp_solution[person][slot] = "Booked"
                     # Check if this new booking violates relational constraints - VERY hard without solver
                     # Simple check: If 'apart' constraint exists, ensure partner isn't booked here
                     valid_booking = True
                     for const in constraints:
                         if const[0] == 'apart' and const[1] == person:
                              p2 = const[2]
                              if temp_solution[p2][slot] == "Booked": valid_booking=False; break
                         elif const[0] == 'apart' and const[2] == person:
                              p1 = const[1]
                              if temp_solution[p1][slot] == "Booked": valid_booking=False; break
                     if valid_booking:
                          num_booked_slots += 1
                          # Make other slots unavailable for this person to simplify
                          for s in time_slots:
                               if s != slot and temp_solution[person][s] == "Unknown":
                                   temp_solution[person][s] = "Unavailable"
                     else:
                          temp_solution[person][slot] = "Unavailable" # Mark as unavailable if conflict found
                fill_attempts += 1

            # Final pass: set remaining Unknown to Available
            for p in people:
                for s in time_slots:
                    if temp_solution[p][s] == "Unknown":
                        temp_solution[p][s] = "Available"

            # 4. Verify the generated solution against ALL constraints (Crucial!)
            verified = True
            booked_slots_map = {p: None for p in people} # Find the single booked slot per person (if any)
            for p in people:
                 for s in time_slots:
                      if temp_solution[p][s] == "Booked":
                           if booked_slots_map[p] is not None: verified=False; break # Multiple bookings
                           booked_slots_map[p] = s
                 if not verified: break # Break outer loop
                
            for constraint in constraints:
                if constraint[0] == 'unavailable':
                    if temp_solution[constraint[1]][constraint[2]] == "Booked": verified = False; break
                elif constraint[0] == 'must_be':
                     if temp_solution[constraint[1]][constraint[2]] != "Booked": verified = False; break
                elif constraint[0] == 'before':
                     p1, p2 = constraint[1], constraint[2]
                     slot1, slot2 = booked_slots_map[p1], booked_slots_map[p2]
                     if slot1 is None or slot2 is None: continue # Skip if one isn't booked
                     if time_slots.index(slot1) >= time_slots.index(slot2): verified = False; break
                elif constraint[0] == 'together':
                     p1, p2 = constraint[1], constraint[2]
                     slot1, slot2 = booked_slots_map[p1], booked_slots_map[p2]
                     if slot1 is None or slot2 is None: continue # Skip if one isn't booked
                     if slot1 != slot2: verified = False; break
                elif constraint[0] == 'apart':
                     p1, p2 = constraint[1], constraint[2]
                     slot1, slot2 = booked_slots_map[p1], booked_slots_map[p2]
                     if slot1 is None or slot2 is None: continue # Skip if one isn't booked
                     if slot1 == slot2: verified = False; break
                if not verified: break
            if not verified: continue # Constraint failed

            # TODO: Add uniqueness check (requires a solver) - Skipped for now

            # If verified (and ideally unique), use this solution
            final_solution = temp_solution
            break # Exit generation loop
        else:
            # If loop finishes without break
            raise ValueError(f"Failed to generate a valid scheduling puzzle solution after {max_attempts} attempts.")

        # --- Generate Clue Text from Constraints ---
        information = []
        constraint_texts = {
            'unavailable': "{p} is unavailable at {s}.",
            'must_be': "{p} must have their appointment at {s}.",
            'before': "{p1}'s appointment must be scheduled before {p2}'s.",
            'together': "{p1} and {p2} must have their appointments at the same time.",
            'apart': "{p1} and {p2} must have their appointments at different times."
        }
        for constraint in constraints:
            ctype = constraint[0]
            if ctype in ['unavailable', 'must_be']:
                info = constraint_texts[ctype].format(p=constraint[1], s=constraint[2])
            elif ctype in ['before', 'together', 'apart']:
                 info = constraint_texts[ctype].format(p1=constraint[1], p2=constraint[2])
            else: continue
            information.append(info)

        random.shuffle(information)

        # --- Construct Puzzle Object ---
        goal = f"Determine the schedule for {', '.join(people)} across these time slots: {', '.join(time_slots)}. Mark each slot as 'Available' or 'Booked'."
        description = f"You need to coordinate the schedules for {len(people)} individuals. Use the provided constraints to figure out everyone's availability."
        characters_list = [{"name": p, "trait": random.choice(self.SCENARIO_TRAITS)} for p in people] # Add dummy traits
        setting_dict = {"name": "Scheduling Coordination", "details": time_slots}

        return ScenarioPuzzle(
            level=level,
            puzzle_type=HumanScenarioType.SCHEDULING,
            description=description,
            characters=characters_list,
            setting=setting_dict,
            goal=goal,
            information=information, # The constraints as text clues
            solution={"schedule": final_solution}, # Store the verified schedule
            rules=None
        )

    def _generate_dilemma_puzzle(self, level: int) -> ScenarioPuzzle:
        """Generates a DILEMMA scenario puzzle."""
        print("Generating DILEMMA puzzle...") # Debugging

        # --- Dilemma Pool ---
        # Define dilemmas with description, options, and a rationale/solution
        # Solution can be the 'best' choice or just the intended answer for the puzzle
        dilemmas = [
            {
                "id": "deadline_help",
                "desc": "You see a colleague, Alex, struggling significantly with their part of a team project shortly before the deadline. Offering to help Alex might jeopardize your own remaining tasks and risk your part being late. Not helping ensures your work is done, but might cause Alex's part to be incomplete, potentially harming the overall team result.",
                "options": ["Offer significant help to Alex", "Offer limited advice but focus on your tasks", "Focus completely on your own tasks", "Inform the manager about Alex's struggle"],
                "solution": "Offer limited advice but focus on your tasks", # Often seen as balancing responsibility
                "info": [
                    "Team success often requires mutual support.",
                    "Meeting individual responsibilities is crucial for project timelines.",
                    "Open communication with management about potential risks is sometimes necessary.",
                    "Alex has occasionally missed deadlines before."
                ]
            },
            {
                "id": "minor_error",
                "desc": "You discover a minor, non-critical calculation error in a report that your team, led by Ben, has already submitted to another department. Pointing out the error now might cause slight embarrassment for the team and Ben. Ignoring it has a very small chance of causing minor confusion later if someone scrutinizes the figures closely, but it will likely go unnoticed.",
                "options": ["Inform Ben privately about the error", "Send a correction email to the receiving department", "Ignore the error", "Ask a trusted colleague for advice first"],
                "solution": "Inform Ben privately about the error", # Allows team lead to handle it
                "info": [
                    "Maintaining accuracy and integrity in reports is important.",
                    "Team cohesion and avoiding unnecessary alarms are also valuable.",
                    "Ben is generally receptive to constructive feedback.",
                    "The other department relies on this report for high-level summaries."
                ]
            },
            {
                "id": "confidential_info",
                "desc": "During a casual conversation in the break room, your friend and colleague, Chloe, accidentally mentions confidential information about an upcoming, unannounced company restructuring that could affect several jobs. You realize you weren't supposed to know this yet.",
                "options": ["Pretend you didn't hear/understand", "Tell Chloe she shouldn't share that", "Report the leak to HR/your manager", "Keep quiet but feel conflicted"],
                "solution": "Tell Chloe she shouldn't share that", # Addresses the immediate issue without escalating prematurely
                "info": [
                    "Maintaining confidentiality is a professional responsibility.",
                    "Friendship loyalty can create difficult conflicts of interest.",
                    "Information leaks can cause significant disruption and anxiety.",
                    "Company policy requires reporting breaches, but the context might matter."
                ]
            },
             {
                "id": "credit_taking",
                "desc": "You notice during a team meeting that your manager, David, presents an idea you shared with him privately last week as entirely his own, receiving praise from senior leadership. David didn't acknowledge your contribution at all.",
                "options": ["Speak to David privately after the meeting", "Raise the issue publicly in the meeting", "Talk to HR or David's manager", "Let it go, avoid confrontation"],
                "solution": "Speak to David privately after the meeting", # Direct, less confrontational initial step
                "info": [
                    "Receiving credit for your work is important for career progression.",
                    "Direct confrontation with a manager can be risky.",
                    "Documenting your contributions can be helpful.",
                    "Company culture influences how such conflicts are typically resolved."
                 ]
            }
        ]

        # --- Select and Construct Puzzle ---
        # Increase complexity/nuance slightly with level?
        # For now, just random selection
        chosen_dilemma = random.choice(dilemmas)

        # The puzzle expects the user to select the 'solution' option
        solution = {"choice": chosen_dilemma["solution"]}
        goal = "Analyze the situation and choose the most appropriate course of action from the options provided."
        description = chosen_dilemma["desc"]
        information = chosen_dilemma["info"]
        random.shuffle(information)

        # Add a general hint
        hint = "Consider the immediate and long-term consequences of each option, as well as professional ethics and relationships."
        information.append(f"Hint: {hint}")

        # The ScenarioPuzzle object itself doesn't need complex character/setting data for dilemmas
        return ScenarioPuzzle(
            level=level,
            puzzle_type=HumanScenarioType.DILEMMA,
            description=description,
            characters=[], # Not the focus
            setting={"name": "Workplace Scenario", "details": []}, # Generic setting
            goal=goal,
            information=information, # Context and arguments
            solution=solution, # The intended choice
            rules=None,
            # Add options directly to the puzzle object for the UI to use
            options=chosen_dilemma["options"]
        )


    # Keep the old scenario generator for logic grids, refactored to fit new ScenarioPuzzle structure
    def _generate_logic_grid_puzzle(self, level: int) -> ScenarioPuzzle:
        """Generates a classic logic grid puzzle, returned as a ScenarioPuzzle."""
        # Select a theme
        available_themes = list(self.LOGIC_GRID_THEMES.keys())
        if not available_themes:
             raise ValueError("No logic grid themes defined in PuzzleGenerator.")
        theme_name = random.choice(available_themes)
        theme_data = self.LOGIC_GRID_THEMES[theme_name]
        categories = theme_data["categories"]
        element_pool = theme_data["elements"] # List of lists of elements for each category

        # Determine grid size (e.g., 3x3, 4x4) - use the size defined in the theme
        if not element_pool or not all(isinstance(p, list) for p in element_pool):
             raise ValueError(f"Invalid element pool format for theme '{theme_name}'.")
        if len(set(len(p) for p in element_pool)) != 1:
             raise ValueError(f"Inconsistent element pool sizes for theme '{theme_name}'. All lists must have the same length.")
        grid_size = len(element_pool[0])
        if grid_size < 2:
             raise ValueError(f"Logic grid size must be at least 2 for theme '{theme_name}'.")

        # --- Create the ground truth solution grid ---
        solution_elements = {} # Stores the final pairings {PrimaryElement: {Cat2: Val2, Cat3: Val3}}
        primary_category = categories[0]
        primary_elements = element_pool[0]

        # Generate permutations for matching other categories
        other_category_indices = list(range(1, len(categories)))
        shuffled_elements = [list(element_pool[cat_idx]) for cat_idx in other_category_indices]
        for elem_list in shuffled_elements:
            random.shuffle(elem_list) # Shuffle each list independently

        # Build the solution dictionary based on these shuffled lists
        for i in range(grid_size):
            entity_name = primary_elements[i]
            solution_elements[entity_name] = {}
            for list_idx, cat_idx in enumerate(other_category_indices):
                category_name = categories[cat_idx]
                element_value = shuffled_elements[list_idx][i] # Assign based on shuffled order
                solution_elements[entity_name][category_name] = element_value

        # --- Generate Clues ---
        potential_clues = []
        # Generate direct positive and negative clues
        for entity, assignments in solution_elements.items():
            for category, value in assignments.items():
                potential_clues.append((f"{entity} is associated with {value}.", "positive", entity, category, value))
                for other_val in element_pool[categories.index(category)]:
                    if other_val != value:
                        potential_clues.append((f"{entity} is not associated with {other_val}.", "negative_entity", entity, category, other_val))
                for other_entity in primary_elements:
                    if other_entity != entity:
                        potential_clues.append((f"{other_entity} is not associated with {value}.", "negative_value", other_entity, category, value))

        # Generate relative clues (more complex logic)
        if len(categories) >= 3 and grid_size >= 2:
            for _ in range(grid_size * (len(categories) - 2)): # Generate a few relative clues
                # Pick two different non-primary categories
                cat1_idx, cat2_idx = random.sample(range(1, len(categories)), 2)
                cat1_name = categories[cat1_idx]
                cat2_name = categories[cat2_idx]

                # Pick a specific element from the first category
                elem1 = random.choice(element_pool[cat1_idx])

                # Find the entity associated with elem1
                assoc_entity = None
                for entity, assignments in solution_elements.items():
                    if assignments.get(cat1_name) == elem1:
                        assoc_entity = entity
                        break

                if assoc_entity:
                    # Find the corresponding element in the second category for that entity
                    assoc_elem2 = solution_elements[assoc_entity].get(cat2_name)
                    if assoc_elem2:
                        # Positive relative clue
                        clue_text = f"The {primary_category} associated with {elem1} ({cat1_name}) is also associated with {assoc_elem2} ({cat2_name})."
                        potential_clues.append((clue_text, "relative_positive", None, None, None))

                        # Negative relative clue (more variety)
                        other_elem2_pool = [e for e in element_pool[cat2_idx] if e != assoc_elem2]
                        if other_elem2_pool:
                             other_elem2 = random.choice(other_elem2_pool)
                             clue_text_neg = f"The {primary_category} associated with {elem1} ({cat1_name}) is NOT associated with {other_elem2} ({cat2_name})."
                             potential_clues.append((clue_text_neg, "relative_negative", None, None, None))

        # --- Select Clues --- 
        # Difficulty: Select a subset of clues ensuring unique solvability.
        # This requires a solver/verifier. Without one, we rely on heuristics.
        # Heuristic: Start with essential clues and add some redundancy.
        
        # 1. Ensure each pairing is mentioned positively at least once?
        # This is hard to guarantee without backtracking or complex selection.
        # Alternative: Prioritize positive clues during selection.

        # 2. Select a target number of clues (adjust based on level/size)
        # Target more clues than theoretically minimal to aid solvability without verifier.
        num_categories = len(categories)
        min_theoretical_clues = (grid_size - 1) * (num_categories -1) * grid_size # Complex formula, approx
        # Simpler target:
        num_clues_target = int(grid_size * num_categories * 0.6 + level) # ~60% density + level bonus
        num_clues_target = max(num_clues_target, grid_size * (num_categories -1 )) # Ensure reasonable minimum

        # 3. Select clues, potentially prioritizing types
        random.shuffle(potential_clues)
        selected_clues_data = []
        clue_texts_added = set()

        # Prioritize positive clues first?
        positive_clues = [c for c in potential_clues if c[1] == 'positive']
        relative_pos_clues = [c for c in potential_clues if c[1] == 'relative_positive']
        negative_clues = [c for c in potential_clues if c[1].startswith('negative')] # negative_entity, negative_value
        relative_neg_clues = [c for c in potential_clues if c[1] == 'relative_negative']
        
        # Ensure some core info (maybe one positive per entity?)
        core_clues_count = 0
        added_entities = set()
        for clue_data in positive_clues:
            if clue_data[2] not in added_entities:
                 if clue_data[0] not in clue_texts_added:
                     selected_clues_data.append(clue_data)
                     clue_texts_added.add(clue_data[0])
                     added_entities.add(clue_data[2])
                     core_clues_count += 1
            if core_clues_count >= grid_size: break # Got one positive for each entity
            
        # Fill remaining slots with a mix, avoiding duplicates
        remaining_clues_pool = (relative_pos_clues + negative_clues + relative_neg_clues +
                                [c for c in positive_clues if c[0] not in clue_texts_added])
        random.shuffle(remaining_clues_pool)
        
        slots_to_fill = num_clues_target - len(selected_clues_data)
        
        for clue_data in remaining_clues_pool:
             if slots_to_fill <= 0: break
             if clue_data[0] not in clue_texts_added:
                  selected_clues_data.append(clue_data)
                  clue_texts_added.add(clue_data[0])
                  slots_to_fill -= 1

        # If still not enough clues (e.g., pool exhausted), add generic hint
        if len(selected_clues_data) < num_clues_target // 2:
            selected_clues_data.append(("Use the process of elimination carefully.", "hint", None, None, None))

        final_clues = [c[0] for c in selected_clues_data] # Extract text
        random.shuffle(final_clues) # Shuffle final list

        # --- Construct Description ---
        joined_secondary_categories = ", ".join(categories[1:]) # Evaluate join separately
        description = f"Logic Puzzle ({theme_name} - {grid_size}x{grid_size}): Deduce the correct pairings.\n"
        description += f"Categories: {primary_category} (Rows) vs {joined_secondary_categories} (Columns).\n"
        # List elements for clarity
        for i, cat_name in enumerate(categories):
            elements_str = ", ".join(element_pool[i]) # Evaluate join separately
            description += f"  {cat_name}: {elements_str}\n"

        # --- Verification Placeholder ---
        # WARNING: Without a solver, the puzzle might be unsolvable or have multiple solutions.
        # print("Warning: Logic Grid puzzle uniqueness not verified.")

        # --- Adapt to ScenarioPuzzle structure ---
        # Create character dicts only for the primary category
        puzzle_characters = []
        for name in primary_elements:
            # Try to find associated data from the solution to make characters richer
            char_details = solution_elements.get(name, {})
            # Select one or two details for the character dict, avoid just 'name'
            trait_info = next((f"{k}:{v}" for k, v in char_details.items()), "N/A")
            puzzle_characters.append({"name": name, "details": trait_info}) 
            
        puzzle_setting = {"name": f"Logic Grid Context: {theme_name}", "details": categories[1:]}
        puzzle_goal = f"Complete the grid to show how the categories match for each {primary_category}. Mark cells with ✔️ (Yes) or ❌ (No)."
        # Store the solution grid itself under the 'grid' key
        puzzle_solution = {"grid": solution_elements}

        return ScenarioPuzzle(
            level=level,
            puzzle_type=HumanScenarioType.LOGIC_GRID,
            description=description,
            characters=puzzle_characters,
            setting=puzzle_setting,
            goal=puzzle_goal,
            information=final_clues,
            solution=puzzle_solution,
            # Pass elements separately for UI generation
            elements={cat: elem_list for cat, elem_list in zip(categories, element_pool)}
        )


    # --- Symbol Cipher Clue Generation Methods ---

    def _generate_direct_clue(self, symbols: List[str], letters: List[str],
                              solution: Dict[str, str], symbol_pool: List[str]) -> Optional[str]:
        """Generates a direct mapping clue (Symbol X is Letter Y)."""
        if not symbol_pool: return None
        symbol = random.choice(symbol_pool)
        letter = solution[symbol]
        return f"'{symbol}' directly represents the letter '{letter}'."

    def _generate_exclusion_clue(self, symbols: List[str], letters: List[str],
                                 solution: Dict[str, str], symbol_pool: List[str]) -> Optional[str]:
        """Generates an exclusion clue (Symbol X is NOT Letter Y)."""
        if not symbol_pool or len(letters) < 2: return None
        symbol = random.choice(symbol_pool)
        actual_letter = solution[symbol]
        # Find a letter that the symbol *doesn't* map to from the pool used in *this* puzzle
        possible_wrong_letters = [l for l in letters if l != actual_letter]
        if not possible_wrong_letters: return None # Should only happen if letters has only 1 unique element
        wrong_letter = random.choice(possible_wrong_letters)
        return f"The symbol '{symbol}' does not represent the letter '{wrong_letter}'."

    def _generate_positional_clue(self, symbols: List[str], letters: List[str],
                                  solution: Dict[str, str], symbol_pool: List[str]) -> Optional[str]:
        """Generates a clue based on position in the original `symbols` list."""
        # This relies on the original `symbols` list order passed to the generator
        if len(symbols) < 2: return None
        idx = random.randrange(len(symbols))
        symbol = symbols[idx] # Get symbol at this index from the original ordered list
        position_word = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth",
                         "eleventh", "twelfth", "thirteenth", "fourteenth", "fifteenth"] # Extend as needed
        if idx < len(position_word):
             pos_str = position_word[idx]
             # Relate it to a property of its corresponding letter
             letter = solution[symbol]
             prop = "a vowel" if letter in self.VOWELS else "a consonant"
             # Frame relative to the sequence shown to the player (which is based on `symbols`)
             return f"In the sequence shown, the {pos_str} symbol represents {prop}."
        return None # Or handle higher indices if max_elements is large

    def _generate_relational_clue(self, symbols: List[str], letters: List[str],
                                  solution: Dict[str, str], symbol_pool: List[str]) -> Optional[str]:
        """Generates a clue comparing two symbols based on their letters."""
        if len(symbol_pool) < 2: return None
        # Sample from the pool available for clues, not necessarily adjacent in original list
        s1, s2 = random.sample(symbol_pool, 2)
        l1, l2 = solution[s1], solution[s2]

        # Compare letter positions in the standard alphabet
        if ord(l1) < ord(l2):
            return f"The letter for '{s1}' comes earlier in the alphabet than the letter for '{s2}'."
        elif ord(l1) > ord(l2):
             return f"The letter for '{s1}' comes later in the alphabet than the letter for '{s2}'."
        else: # Should not happen with unique letters guaranteed by sampling
            return None

    def _generate_category_clue(self, symbols: List[str], letters: List[str],
                                solution: Dict[str, str], symbol_pool: List[str]) -> Optional[str]:
        """Generates a clue based on letter category (vowel/consonant)."""
        if not symbol_pool: return None
        symbol = random.choice(symbol_pool)
        letter = solution[symbol]
        category = "a vowel" if letter in self.VOWELS else "a consonant"
        return f"The symbol '{symbol}' represents {category}."

    def _generate_logical_clue(self, symbols: List[str], letters: List[str],
                               solution: Dict[str, str], symbol_pool: List[str]) -> Optional[str]:
        """Generates a conditional logical clue involving two symbols."""
        if len(symbol_pool) < 3: return None # Need >= 3 for interesting logical clues usually

        # Example: "If '{s1}' is {prop1}, then '{s2}' is {prop2}."
        s1, s2 = random.sample(symbol_pool, 2) # Pick two distinct symbols
        l1, l2 = solution[s1], solution[s2]

        # Determine properties (vowel/consonant)
        l1_prop_is_vowel = l1 in self.VOWELS
        l2_prop_is_vowel = l2 in self.VOWELS
        l1_prop_text = "a vowel" if l1_prop_is_vowel else "a consonant"
        l2_prop_text = "a vowel" if l2_prop_is_vowel else "a consonant"

        # Randomly decide if the premise of the clue should match the actual solution state
        premise_matches_solution = random.choice([True, False])

        if premise_matches_solution:
            # Premise is TRUE for the actual solution. Conclusion must also be TRUE.
            # Clue form: "If '{s1}' represents {actual prop of l1}, then '{s2}' represents {actual prop of l2}."
             return f"If '{s1}' represents {l1_prop_text}, then '{s2}' represents {l2_prop_text}."
        else:
            # Premise is FALSE for the actual solution. Conclusion can be anything (True or False).
            # Clue form: "If '{s1}' represents {opposite prop of l1}, then '{s2}' represents {random prop}."
            l1_opposite_prop_text = "a consonant" if l1_prop_is_vowel else "a vowel"
            # Make the conclusion potentially misleading or simply random
            l2_random_prop_text = random.choice(["a vowel", "a consonant"])
            return f"If '{s1}' represents {l1_opposite_prop_text}, then '{s2}' represents {l2_random_prop_text}."

        # TODO: Could add other logical forms (e.g., involving 3 symbols, OR, XOR conditions)

    # --- Helper function for Social Deduction Statements (Moved and Indented) ---
    def _generate_social_deduction_statement(self, character: Dict, target_person_name: str, all_characters: List[Dict], is_target: bool, setting: Dict) -> str:
        name = character['name']
        trait = character['trait']
        others = [c for c in all_characters if c['name'] != name]
        other_person = random.choice(others)['name'] if others else "someone else"

        if is_target:
            # Statements for the target person, reflecting their trait
            if trait == "Secretive": return f"{name} claims they were focused on their own work and didn't notice anything unusual."
            if trait == "Evasive": return f"{name} vaguely mentions being \"around\" but can't recall specific times when asked about the incident."
            if trait == "Anxious": return f"{name} seems flustered and says, 'I... I don't think I saw anything important.'"
            if trait == "Forgetful": return f"{name} frowns, saying, 'I might have seen something, but the details are fuzzy right now.'"
            if trait == "Argumentative": return f"{name} deflects by questioning why everyone is focused on them."
            if trait == "Honest": return f"{name} states, 'I was involved, but there's a misunderstanding about what happened.'" # Misleadingly honest?
            return f"{name} provides a simple denial, saying they weren't near the location at the time."
        else:
            # Statements from others, potentially hinting or misleading based on their trait
            if trait == "Honest": return f"{name} states clearly they observed {target_person_name} acting suspiciously near the relevant area."
            if trait == "Observant": return f"{name} mentions noticing a small detail, like {target_person_name} hastily putting something in their bag."
            if trait == "Talkative": return f"{name} heard {other_person} gossiping about {target_person_name}'s recent strange behavior."
            if trait == "Skeptical": return f"{name} expresses doubt about {target_person_name}'s usual routine, suggesting they had opportunity."
            if trait == "Distracted": return f"{name} thinks they saw {other_person} near the scene, but admits they weren't paying close attention."
            if trait == "Quiet": return f"{name} hesitates, then quietly suggests asking {target_person_name} directly."
            if trait == "Helpful": return f"{name} tries to piece together the timeline but inadvertently gives {target_person_name} an alibi."
            if trait == "Nitpicky": return f"{name} focuses on an irrelevant inconsistency in {other_person}'s account."
            return f"{name} says they didn't see {target_person_name}, but did notice {other_person} nearby."

    # --- Helper function for Social Deduction Observations (Moved and Indented) ---
    def _generate_social_deduction_observation(self, target_person_name: str, all_characters: List[Dict], setting: Dict, goal: str) -> str:
        # Provides a piece of contextual evidence, possibly pointing towards the target
        # Safely get a setting detail
        setting_detail = random.choice(setting['details']) if setting.get('details') else "a nearby object"

        if "document" in goal or "report" in goal:
             return f"A crumpled draft related to the issue was found near {target_person_name}'s workspace."
        if "email" in goal or "message" in goal:
             return f"The system logs show {target_person_name} was logged in around the time the message should have been sent."
        if "meeting" in goal or "schedule" in goal:
             return f"{target_person_name}'s calendar had a conflicting, private appointment during the meeting time."
        if "tool" in goal or "item" in goal or "stapler" in goal:
             return f"An item similar to the missing one, but slightly different, was seen at {target_person_name}'s desk earlier."
        return f"Regarding the {setting_detail}, witnesses recall {target_person_name} being the last person near it."

    # --- Helper function for Red Herrings (Moved and Indented) ---
    def _generate_red_herring(self, all_characters: List[Dict], setting: Dict) -> str:
        others = [c['name'] for c in all_characters]
        if not others: return "An unrelated discussion about the weather occurred."
        person1 = random.choice(others)
        person2 = random.choice([p for p in others if p != person1]) if len(others) > 1 else person1

        # Safely get details options
        details_options = setting.get('details')
        if not details_options: # If details list is empty or None
             details_options = ["the nearby window", "a poster on the wall", "a potted plant"]

        irrelevant_detail = random.choice([
            f"{person1} was complaining about the office coffee machine again.",
            f"There was a brief, unrelated discussion about {person2}'s upcoming vacation.",
            f"Someone mentioned the {random.choice(details_options)} needs maintenance.", # Use details_options
            f"{person1} and {person2} had a short, amicable chat about weekend plans.",
            f"An announcement was made about an upcoming company event."
        ])
        return irrelevant_detail

    # --- Agent-Based Simulation Puzzle Generator --- 
    def _generate_agent_simulation_puzzle(self, level: int) -> ScenarioPuzzle:
        """Generates a puzzle based on observing a simple agent simulation."""
        print("Generating AGENT_SIMULATION puzzle...") # Debugging
        # --- Define Simulation Parameters --- 
        num_agents = random.randint(2, min(3 + level // 2, 4)) # Keep it small, increase slowly
        num_locations = random.randint(min(3 + level // 2, 4), min(4 + level // 2, 5))
        num_time_steps = random.randint(min(3 + level // 3, 4), min(4 + level // 2, 5))

        # --- Setup Initial State --- 
        # 1. Define Locations
        locations = [f"Area {chr(65+i)}" for i in range(num_locations)] 
        setting = {"name": "Interaction Zone", "details": locations}

        # 2. Create Agents (with unique initial locations)
        characters = []
        char_names = random.sample(self.SCENARIO_NAMES, min(num_agents, len(self.SCENARIO_NAMES)))
        if len(char_names) < num_agents:
            char_names.extend([f"Agent {i+1}" for i in range(num_agents - len(char_names))])
        
        initial_locations = random.sample(locations, k=num_agents) # Assign unique start spots
        
        for i in range(num_agents):
            trait = random.choice(self.SCENARIO_TRAITS)
            # Select a target that is NOT the agent's own start location
            possible_targets = locations + [c['name'] for c in characters if c['name'] != char_names[i]]
            target = random.choice([t for t in possible_targets if t != initial_locations[i]])
            goal_type = random.choice(["REACH", "AVOID"])
            agent_goal = f"{goal_type} {target}"
            
            characters.append({
                "name": char_names[i],
                "trait": trait,
                "goal": agent_goal,
                "location": initial_locations[i],
                "state_history": {0: initial_locations[i]}
            })

        # 3. Select Rules and Parameterize them
        num_rules = random.randint(2, min(len(self.AGENT_SIMULATION_RULES), 4))
        selected_rule_dicts = random.sample(self.AGENT_SIMULATION_RULES, num_rules)
        
        rules_in_effect = [] # Store tuples: (rule_id, params_dict)
        rule_texts_for_display = []

        for rule_template in selected_rule_dicts:
            rule_id = rule_template["id"]
            rule_text_template = rule_template["text"]
            params = {}
            final_rule_text = rule_text_template
            
            # Substitute parameters based on rule ID
            if "{location_A}" in rule_text_template:
                param_loc = random.choice(locations)
                params["location_A"] = param_loc
                final_rule_text = final_rule_text.replace("{location_A}", param_loc)
            if "{location_B}" in rule_text_template:
                param_loc = random.choice(locations)
                params["location_B"] = param_loc
                final_rule_text = final_rule_text.replace("{location_B}", param_loc)
            if "{location_C}" in rule_text_template:
                 param_loc = random.choice(locations)
                 params["location_C"] = param_loc
                 final_rule_text = final_rule_text.replace("{location_C}", param_loc)
            
            # Add other parameter substitutions if needed
            
            rules_in_effect.append((rule_id, params))
            rule_texts_for_display.append(final_rule_text)

        # --- Run Simulation (Improved Conflict Resolution) --- 
        for t in range(1, num_time_steps + 1):
            current_locations = {agent["name"]: agent["state_history"][t-1] for agent in characters}
            intended_moves = {} # {agent_name: new_location} - Calculate intended move first

            # --- Determine Intended Moves Based on Rules --- 
            for agent in characters:
                current_loc = agent['state_history'][t-1]
                intended_loc = current_loc # Default: stay put
                agent_action_taken = False # Track if a rule dictated a move

                # Iterate through active rules (consider priority implicitly by order?)
                for rule_id, params in rules_in_effect:
                    if agent_action_taken: break # Only one primary move rule per agent per turn

                    # --- Apply Movement Rules --- 
                    if rule_id == "MOVE_TOWARDS_GOAL_LOC":
                        goal_parts = agent['goal'].split(" ", 1)
                        if goal_parts[0] == "REACH" and goal_parts[1] in locations:
                            target_loc = goal_parts[1]
                            if current_loc != target_loc:
                                # Simple adjacent move simulation (find best neighbor)
                                # This is still basic; a pathfinding algorithm would be better.
                                # For simplicity: if target is different, pick any different location.
                                possible_moves = [loc for loc in locations if loc != current_loc]
                                if possible_moves:
                                     intended_loc = random.choice(possible_moves) # TODO: Improve movement logic
                                     agent_action_taken = True

                    elif rule_id == "MOVE_AWAY_FROM_GOAL_AGENT":
                        goal_parts = agent['goal'].split(" ", 1)
                        if goal_parts[0] == "AVOID":
                            target_agent_name = goal_parts[1]
                            target_agent_loc = current_locations.get(target_agent_name)
                            if target_agent_loc == current_loc:
                                possible_moves = [loc for loc in locations if loc != current_loc]
                                if possible_moves:
                                    intended_loc = random.choice(possible_moves)
                                    agent_action_taken = True
                    
                    # --- Apply Trait/Location Based Rules --- 
                    elif rule_id == "PREFER_QUIET_LOC":
                         if agent['trait'] == "Quiet":
                             target_loc = params.get("location_A")
                             if target_loc and current_loc != target_loc:
                                 possible_moves = [loc for loc in locations if loc != current_loc]
                                 if possible_moves:
                                     intended_loc = random.choice(possible_moves) # TODO: Move towards target
                                     agent_action_taken = True
                                     
                    elif rule_id == "AVOID_CROWD_ANXIOUS":
                        if agent['trait'] == "Anxious":
                            agents_at_current_loc = [name for name, loc in current_locations.items() if loc == current_loc]
                            if len(agents_at_current_loc) > 1:
                                # Find less crowded location (count agents aiming for each location)
                                agent_counts_per_loc = defaultdict(int)
                                for loc in locations: agent_counts_per_loc[loc] = 0
                                for name, loc in current_locations.items(): agent_counts_per_loc[loc]+=1
                                
                                less_crowded_options = [loc for loc in locations if loc != current_loc and agent_counts_per_loc[loc] <= 1]
                                if less_crowded_options:
                                     intended_loc = random.choice(less_crowded_options)
                                     agent_action_taken = True
                                elif len(locations) > 1: # If all others are crowded, pick any different one
                                     possible_moves = [loc for loc in locations if loc != current_loc]
                                     if possible_moves:
                                          intended_loc = random.choice(possible_moves)
                                          agent_action_taken = True
                                          
                    # --- Fallback: MOVE_RANDOM_IF_NO_GOAL --- 
                    # This rule should have lower priority or be applied if no other action taken
                    elif rule_id == "MOVE_RANDOM_IF_NO_GOAL" and not agent_action_taken:
                        possible_moves = [loc for loc in locations if loc != current_loc]
                        if possible_moves:
                            intended_loc = random.choice(possible_moves)
                            agent_action_taken = True # Mark action taken for fallback
                
                intended_moves[agent["name"]] = intended_loc

            # --- Conflict Resolution --- 
            resolved_locations = intended_moves.copy() # Start with intended moves
            destination_counts = defaultdict(list)
            for agent_name, dest_loc in intended_moves.items():
                 destination_counts[dest_loc].append(agent_name)
                 
            conflict_resolved_agents = set() # Track agents whose conflicts are handled

            for dest_loc, agent_names in destination_counts.items():
                 if len(agent_names) <= 1: continue # No conflict
                 
                 # Check for Capacity Limit Conflict FIRST
                 capacity_limited = False
                 limit_rule_params = None
                 for rule_id, params in rules_in_effect:
                      if rule_id == "LOCATION_CAPACITY_1" and params.get("location_B") == dest_loc:
                           capacity_limited = True
                           break # Found capacity limit rule for this location
                 
                 if capacity_limited:
                      agent_names_str = ", ".join(agent_names) # Evaluate join separately
                      print(f"  [T={t}] Conflict at Capacity-1 location {dest_loc} involving: {agent_names_str}. Reverting ALL involved moves.") # Use the variable
                      for agent_name in agent_names:
                           # Only revert if agent hasn't been handled by another conflict rule
                           if agent_name not in conflict_resolved_agents:
                                resolved_locations[agent_name] = current_locations[agent_name]
                                conflict_resolved_agents.add(agent_name)
                      continue # Move to next potential conflict location

                 # Check for Yielding Conflict Rule (if capacity not limited)
                 yield_rule_active = any(rule_id == "YIELD_ON_CONFLICT_CALM" for rule_id, _ in rules_in_effect)
                 if yield_rule_active and len(agent_names) == 2: # Specific rule for 2 agents
                      agent1_name, agent2_name = agent_names[0], agent_names[1]
                      # Check if these agents have already had their move determined by another conflict
                      if agent1_name in conflict_resolved_agents or agent2_name in conflict_resolved_agents:
                           continue # Skip yield check if one was already handled (e.g., reverted)
                           
                      agent1_trait = next((a['trait'] for a in characters if a['name'] == agent1_name), None)
                      agent2_trait = next((a['trait'] for a in characters if a['name'] == agent2_name), None)
                      
                      calm_agent_reverted = False
                      if agent1_trait == "Calm" and agent2_trait != "Calm":
                           print(f"  [T={t}] Conflict at {dest_loc}: {agent1_name} (Calm) yields to {agent2_name}. {agent1_name} reverts.")
                           resolved_locations[agent1_name] = current_locations[agent1_name]
                           conflict_resolved_agents.add(agent1_name) # Mark as handled
                           # agent2 keeps the move
                           calm_agent_reverted = True
                      elif agent2_trait == "Calm" and agent1_trait != "Calm":
                           print(f"  [T={t}] Conflict at {dest_loc}: {agent2_name} (Calm) yields to {agent1_name}. {agent2_name} reverts.")
                           resolved_locations[agent2_name] = current_locations[agent2_name]
                           conflict_resolved_agents.add(agent2_name) # Mark as handled
                           # agent1 keeps the move
                           calm_agent_reverted = True
                           
                      if calm_agent_reverted:
                           continue # Conflict for these two resolved, move to next location
                           
                 # Default Conflict Resolution (if not Capacity 1 and not Yield)
                 # Revert all agents involved in *this specific destination conflict* who haven't been handled yet
                 default_conflict_agent_names_str = ", ".join(agent_names) # Evaluate join separately
                 print(f"  [T={t}] Default Conflict at {dest_loc} involving: {default_conflict_agent_names_str}. Reverting non-resolved involved moves.")
                 for agent_name in agent_names:
                      if agent_name not in conflict_resolved_agents:
                           resolved_locations[agent_name] = current_locations[agent_name]
                           conflict_resolved_agents.add(agent_name)
            
            # --- Update Histories with Resolved Locations --- 
            for agent in characters:
                 agent['state_history'][t] = resolved_locations[agent['name']] # Use resolved locations

        # --- Generate Observations (Information) --- 
        information = []
        # Reveal *some* parameterized rules (adjust k based on level?)
        num_rules_to_reveal = min(len(rule_texts_for_display), max(1, num_rules // 2 + level // 4))
        revealed_rules_text = random.sample(rule_texts_for_display, k=num_rules_to_reveal)
        information.extend(f"Rule Observed: {r}" for r in revealed_rules_text)
        
        # Observations of states
        num_observations = random.randint(num_agents + 1, int(num_agents * num_time_steps * 0.6))
        for _ in range(num_observations):
            t = random.randint(0, num_time_steps) # Include T=0 observations
            agent = random.choice(characters)
            location = agent['state_history'][t]
            # Avoid revealing final state if goal is prediction?
            if goal_type == "PREDICT_STATE" and t == num_time_steps and agent["name"] == predict_agent["name"]: 
                continue
            information.append(f"At T={t}, {agent['name']} was observed in {location}.")
        random.shuffle(information)

        # --- Define Puzzle Goal & Solution (Improved Logic) --- 
        # Helper function removed, logic integrated or simplified

        # Goal examples: Predict state at T+1, Identify hidden trait/goal, Identify rule
        goal_type = random.choice(["PREDICT_STATE", "IDENTIFY_TRAIT", "IDENTIFY_RULE"])
        puzzle_goal = ""
        solution = {}
        predict_agent = None # Define predict_agent outside the if block

        if goal_type == "PREDICT_STATE" and num_time_steps > 0:
            predict_agent = random.choice(characters)
            puzzle_goal = f"Based on the rules and observations, where will {predict_agent['name']} likely be at T={num_time_steps + 1}?"
            
            # Simulate one more step for the prediction
            final_state_map = {agent["name"]: agent["state_history"][num_time_steps] for agent in characters}
            # Need to run the *same* rule logic and conflict resolution for T+1
            # Re-run the intention and conflict resolution logic for one step:
            next_intended_moves = {}
            for agent in characters:
                 current_loc = final_state_map[agent["name"]]
                 intended_loc = current_loc
                 agent_action_taken=False
                 # ... (Copy/refactor agent movement logic from main loop) ...
                 # Simplified prediction: Use the intended move without conflict resolution?
                 # Let's try that first for simplicity:
                 for rule_id, params in rules_in_effect:
                      if agent_action_taken: break
                      # Apply relevant rules based on final_state_map
                      if rule_id == "MOVE_TOWARDS_GOAL_LOC":
                          goal_parts = agent['goal'].split(" ", 1)
                          if goal_parts[0] == "REACH" and goal_parts[1] in locations:
                              target_loc = goal_parts[1]
                              if current_loc != target_loc:
                                   possible_moves = [loc for loc in locations if loc != current_loc]
                                   if possible_moves: intended_loc = random.choice(possible_moves); agent_action_taken = True
                      # ... (Add other relevant rule checks similarly) ...
                 next_intended_moves[agent["name"]] = intended_loc
                 
            predicted_loc = next_intended_moves[predict_agent["name"]]
            solution = {"answer": predicted_loc}
            
        elif goal_type == "IDENTIFY_TRAIT":
            target_agent = random.choice(characters)
            puzzle_goal = f"Based on their actions ({target_agent['name']}'s movement pattern) and the observed rules, what is the most likely trait of {target_agent['name']}?"
            solution = {"answer": target_agent['trait']} 
            
        else: # IDENTIFY_RULE
            unrevealed_rules = [r for r in rule_texts_for_display if r not in revealed_rules_text]
            if not unrevealed_rules and rule_texts_for_display: 
                unrevealed_rules = rule_texts_for_display # Fallback if all were revealed
                puzzle_goal = "Which revealed rule was most influential in the observed behavior?"
            elif not rule_texts_for_display:
                raise ValueError("Cannot generate IDENTIFY_RULE goal with no rules.")
            else:
                 puzzle_goal = "Identify an unstated rule that was likely governing the agents' interactions."
            
            solution = {"answer": random.choice(unrevealed_rules)}

        # --- Construct Description --- 
        agent_names_str_desc = ", ".join(a['name'] for a in characters) # Evaluate join separately
        locations_str_desc = ", ".join(locations) # Evaluate join separately
        description = f"Observe the interactions of {num_agents} agents ({agent_names_str_desc}) in an environment with {num_locations} areas ({locations_str_desc}) over {num_time_steps} time steps. Deduce the underlying logic based on the provided observations and partial rules."

        return ScenarioPuzzle(
            level=level,
            puzzle_type=HumanScenarioType.AGENT_SIMULATION,
            description=description,
            characters=characters, 
            setting=setting,      
            goal=puzzle_goal,
            information=information,
            solution=solution,
            rules=rule_texts_for_display # Pass the *parameterized* rules
        )


class _LogicGridInternalVerifier: # Renamed from LogicGridVerifier
    """
    Verifies if the clues provided for a logic grid puzzle lead to a unique
    and consistent solution using constraint propagation.
    """
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

        # Grid state: grid[primary_elem][other_category] = set(possible_values)
        self.grid = {
            p_elem: {
                cat: set(self.elements[cat]) for cat in self.categories[1:]
            }
            for p_elem in self.primary_elements
        }
        # Store relative clues separately for iterative application
        self.relative_clues_parsed = []

    def _initialize_grid(self):
        """Resets the grid to the initial state with all possibilities."""
        self.grid = {
            p_elem: {
                cat: set(self.elements[cat]) for cat in self.categories[1:]
            }
            for p_elem in self.primary_elements
        }
        self.relative_clues_parsed = [] # Clear parsed relative clues too

    def _parse_and_apply_clues(self) -> bool:
        """Parses all clues and applies initial constraints. Returns False on immediate contradiction."""
        self._initialize_grid() # Start fresh

        # Simple regex patterns (can be improved for robustness)
        # "Entity is associated with Value." / "Entity is Value." (assuming Value implies category)
        pattern_positive = re.compile(r"(\w+)\s+(?:is associated with|is)\s+(\w+)\.?$", re.IGNORECASE)
        # "Entity is not associated with Value." / "Entity is not Value."
        pattern_negative_entity = re.compile(r"(\w+)\s+(?:is not associated with|is not)\s+(\w+)\.?$", re.IGNORECASE)
        # "OtherEntity is not associated with Value." (Implied negative) - Harder to parse directly without context
        # "The Cat1 associated with Elem1 (Cat1) is also associated with Elem2 (Cat2)."
        pattern_relative_positive = re.compile(
            r"The\s+\w+\s+associated with\s+(\w+)\s+\((\w+)\)\s+is also associated with\s+(\w+)\s+\((\w+)\)\.?$", re.IGNORECASE)
         # "The Cat1 associated with Elem1 (Cat1) is NOT associated with Elem2 (Cat2)."
        pattern_relative_negative = re.compile(
            r"The\s+\w+\s+associated with\s+(\w+)\s+\((\w+)\)\s+is NOT associated with\s+(\w+)\s+\((\w+)\)\.?$", re.IGNORECASE)


        for clue in self.clues:
            applied = False
            # Try positive match
            match_pos = pattern_positive.match(clue)
            if match_pos:
                entity, value = match_pos.groups()
                cat1, cat2 = self._find_categories(entity, value)
                if cat1 == self.primary_category and cat2:
                    if not self._apply_direct_positive(entity, cat2, value): return False
                    applied = True
                elif cat2 == self.primary_category and cat1:
                    # Handle case where value is primary category element
                    if not self._apply_direct_positive(value, cat1, entity): return False
                    applied = True

            # Try negative match
            match_neg = pattern_negative_entity.match(clue)
            if not applied and match_neg:
                entity, value = match_neg.groups()
                cat1, cat2 = self._find_categories(entity, value)
                if cat1 == self.primary_category and cat2:
                    if not self._apply_direct_negative(entity, cat2, value): return False
                    applied = True
                elif cat2 == self.primary_category and cat1:
                     if not self._apply_direct_negative(value, cat1, entity): return False
                     applied = True

            # Try relative positive match
            match_rel_pos = pattern_relative_positive.match(clue)
            if not applied and match_rel_pos:
                elem1, cat1, elem2, cat2 = match_rel_pos.groups()
                if cat1 in self.elements and cat2 in self.elements and elem1 in self.elements[cat1] and elem2 in self.elements[cat2]:
                    # Store parsed relative clue for later processing
                    self.relative_clues_parsed.append(("relative_positive", elem1, cat1, elem2, cat2))
                    applied = True # Mark as handled for now

            # Try relative negative match
            match_rel_neg = pattern_relative_negative.match(clue)
            if not applied and match_rel_neg:
                 elem1, cat1, elem2, cat2 = match_rel_neg.groups()
                 if cat1 in self.elements and cat2 in self.elements and elem1 in self.elements[cat1] and elem2 in self.elements[cat2]:
                     # Store parsed relative clue for later processing
                     self.relative_clues_parsed.append(("relative_negative", elem1, cat1, elem2, cat2))
                     applied = True

            # if not applied:
            #     print(f"Warning: Could not parse or apply clue: '{clue}'") # Debugging

        return True # No immediate contradictions found

    def _find_categories(self, item1: str, item2: str) -> Tuple[Optional[str], Optional[str]]:
        """Find which categories item1 and item2 belong to."""
        cat1 = None
        cat2 = None
        for cat, elems in self.elements.items():
            if item1 in elems:
                cat1 = cat
            if item2 in elems:
                cat2 = cat
        return cat1, cat2

    def _apply_direct_positive(self, primary_elem: str, other_category: str, value: str) -> bool:
        """Applies a confirmed positive link. Returns False on contradiction."""
        if primary_elem not in self.primary_elements or other_category not in self.elements or value not in self.elements[other_category]:
            # print(f"Debug: Invalid positive clue data: {primary_elem}, {other_category}, {value}")
            return True # Ignore invalid data for now

        current_possibilities = self.grid[primary_elem][other_category]

        # If value is already impossible, it's a contradiction
        if value not in current_possibilities:
             # print(f"Contradiction: Trying to set {primary_elem}-{other_category} to {value}, but it was already excluded.")
             return False

        # Set this as the only possibility
        self.grid[primary_elem][other_category] = {value}

        # Eliminate this value from all other primary elements in this category
        for other_p_elem in self.primary_elements:
            if other_p_elem != primary_elem:
                if not self._apply_direct_negative(other_p_elem, other_category, value):
                    return False # Propagated contradiction
        return True

    def _apply_direct_negative(self, primary_elem: str, other_category: str, value_to_exclude: str) -> bool:
        """Applies a confirmed negative link. Returns False on contradiction."""
        if primary_elem not in self.primary_elements or other_category not in self.elements or value_to_exclude not in self.elements[other_category]:
             # print(f"Debug: Invalid negative clue data: {primary_elem}, {other_category}, {value_to_exclude}")
             return True # Ignore invalid data

        current_possibilities = self.grid[primary_elem][other_category]

        if value_to_exclude in current_possibilities:
            current_possibilities.remove(value_to_exclude)
            if not current_possibilities:
                # print(f"Contradiction: Removing {value_to_exclude} left no options for {primary_elem}-{other_category}.")
                return False # Contradiction: removed the last possibility
        return True

    def _propagate_constraints(self) -> bool:
        """Iteratively applies deductions until no further changes occur. Returns False on contradiction."""
        changed = True
        while changed:
            changed = False

            # --- Deduction 1: Unique Value Found ---
            # If a cell (p_elem, category) has only one possible value, eliminate that value
            # from all other p_elements in that same category.
            for p_elem in self.primary_elements:
                for category, possibilities in self.grid[p_elem].items():
                    if len(possibilities) == 1:
                        confirmed_value = list(possibilities)[0]
                        for other_p_elem in self.primary_elements:
                            if other_p_elem != p_elem:
                                # Check if the value exists before trying to remove
                                if confirmed_value in self.grid[other_p_elem][category]:
                                    self.grid[other_p_elem][category].remove(confirmed_value)
                                    if not self.grid[other_p_elem][category]: return False # Contradiction
                                    changed = True # Mark change

            # --- Deduction 2: Unique Entity Found ---
            # If a value V in a category C is only possible for a single primary element P,
            # then P must be associated with V. Set (P, C) to {V}.
            for category in self.categories[1:]:
                 for value in self.elements[category]:
                      possible_entities = []
                      for p_elem in self.primary_elements:
                          if value in self.grid[p_elem][category]:
                              possible_entities.append(p_elem)

                      if len(possible_entities) == 1:
                          unique_entity = possible_entities[0]
                          # Check if grid already reflects this, avoid infinite loop
                          if len(self.grid[unique_entity][category]) > 1:
                              # print(f"Deduction 2: {value} ({category}) only possible for {unique_entity}. Setting.")
                              self.grid[unique_entity][category] = {value}
                              if not self.grid[unique_entity][category]: return False # Contradiction (shouldn't happen here)
                              changed = True # Mark change (will trigger Deduction 1)
                      elif len(possible_entities) == 0:
                          # If a value is not possible for *any* entity, it's a contradiction
                          # (unless it was correctly eliminated everywhere)
                          # Check if this value *should* exist based on the grid state
                          is_value_assigned = any(len(self.grid[p][category]) == 1 and list(self.grid[p][category])[0] == value for p in self.primary_elements)
                          if not is_value_assigned:
                              # print(f"Contradiction: Value {value} ({category}) has no possible entity.")
                              return False


            # --- Deduction 3: Apply Relative Clues ---
            # Re-evaluate stored relative clues based on current grid state
            for clue_data in self.relative_clues_parsed:
                 type, elem1, cat1, elem2, cat2 = clue_data

                 # Find the primary entity associated with elem1 in cat1
                 possible_primary_for_elem1 = []
                 if cat1 == self.primary_category: # If elem1 is primary, the link is direct
                      possible_primary_for_elem1 = [elem1]
                 else:
                      for p_elem in self.primary_elements:
                           if elem1 in self.grid[p_elem][cat1]:
                                possible_primary_for_elem1.append(p_elem)

                 # If we've narrowed down the primary element for elem1 to one possibility:
                 if len(possible_primary_for_elem1) == 1:
                      assoc_primary = possible_primary_for_elem1[0]

                      if type == "relative_positive":
                           # Apply: assoc_primary MUST be linked to elem2 in cat2
                           if elem2 not in self.grid[assoc_primary][cat2]:
                                # print(f"Contradiction from relative clue: {assoc_primary} linked to {elem1} ({cat1}), implies link to {elem2} ({cat2}), but {elem2} already excluded.")
                                return False
                           if len(self.grid[assoc_primary][cat2]) > 1:
                               # print(f"Relative Deduction: {assoc_primary} -> {elem1} ({cat1}), so {assoc_primary} -> {elem2} ({cat2})")
                               self.grid[assoc_primary][cat2] = {elem2}
                               changed = True
                               # Trigger propagation for Deduction 1
                      elif type == "relative_negative":
                           # Apply: assoc_primary CANNOT be linked to elem2 in cat2
                           if elem2 in self.grid[assoc_primary][cat2]:
                                if len(self.grid[assoc_primary][cat2]) == 1:
                                     # print(f"Contradiction from relative clue: {assoc_primary} linked to {elem1} ({cat1}), implies NOT linked to {elem2} ({cat2}), but it's the only option.")
                                     return False
                                # print(f"Relative Deduction: {assoc_primary} -> {elem1} ({cat1}), so {assoc_primary} NOT -> {elem2} ({cat2})")
                                self.grid[assoc_primary][cat2].remove(elem2)
                                changed = True
                                # Trigger propagation

                 # --- Also consider the reverse logic for relative clues ---
                 # Find primary entity associated with elem2 in cat2
                 possible_primary_for_elem2 = []
                 if cat2 == self.primary_category:
                      possible_primary_for_elem2 = [elem2]
                 else:
                      for p_elem in self.primary_elements:
                           if elem2 in self.grid[p_elem][cat2]:
                                possible_primary_for_elem2.append(p_elem)

                 if len(possible_primary_for_elem2) == 1:
                      assoc_primary = possible_primary_for_elem2[0]

                      if type == "relative_positive":
                            # If P is linked to Elem2 (Cat2), it must also be linked to Elem1 (Cat1)
                            if elem1 not in self.grid[assoc_primary][cat1]: return False # Contradiction
                            if len(self.grid[assoc_primary][cat1]) > 1:
                                 self.grid[assoc_primary][cat1] = {elem1}; changed = True
                      # Negative relative logic also applies in reverse (A->B => not(A->not B))
                      # If P->E2(C2) then P not-> E1(C1). Yes.
                      elif type == "relative_negative":
                           # If P -> E2(C2), then P cannot be linked to E1(C1)
                            if elem1 in self.grid[assoc_primary][cat1]:
                                 if len(self.grid[assoc_primary][cat1]) == 1: return False # Contradiction
                                 self.grid[assoc_primary][cat1].remove(elem1); changed = True


        return True # No contradictions found during this pass

    def _is_solved(self) -> bool:
        """Checks if the grid is completely and uniquely determined."""
        for p_elem in self.primary_elements:
            for category in self.categories[1:]:
                if len(self.grid[p_elem][category]) != 1:
                    return False # Not fully solved
        # Additionally, check if all values are used exactly once per category
        for category in self.categories[1:]:
            assigned_values = set()
            for p_elem in self.primary_elements:
                 val = list(self.grid[p_elem][category])[0] # Gets the single value
                 assigned_values.add(val)
            if len(assigned_values) != self.grid_size:
                 return False # Values missing or duplicated
        return True

    def get_solution(self) -> Optional[Dict[str, Dict[str, str]]]:
        """Returns the solved grid if verification was successful and unique, otherwise None."""
        if not self._is_solved():
            return None

        solution = {}
        for p_elem in self.primary_elements:
            solution[p_elem] = {}
            for category in self.categories[1:]:
                 # Since it's solved, the set contains exactly one element
                 solution[p_elem][category] = list(self.grid[p_elem][category])[0]
        return solution


    def verify(self) -> Tuple[bool, Optional[Dict[str, Dict[str, str]]]]:
        """
        Attempts to solve the logic grid using the provided clues.

        Returns:
            Tuple[bool, Optional[Dict]]:
                - bool: True if a unique solution is found, False otherwise.
                - Optional[Dict]: The solution grid if unique, otherwise None.
        """
        # 1. Parse clues and apply initial direct constraints
        if not self._parse_and_apply_clues():
             print("Verification Failed: Contradiction found during initial clue application.")
             return False, None # Contradiction

        # 2. Propagate constraints iteratively
        if not self._propagate_constraints():
            print("Verification Failed: Contradiction found during constraint propagation.")
            return False, None # Contradiction

        # 3. Check if solved
        if self._is_solved():
            # print("Verification Successful: Unique solution found.")
            return True, self.get_solution()
        else:
            # If not solved after propagation, constraint solver isn't sufficient (or clues are ambiguous)
            # For now, we don't implement backtracking search for multiple solutions.
            # We assume the puzzles generated should be solvable by deduction alone.
            print("Verification Failed: Grid not fully solved after propagation (ambiguous clues or requires backtracking).")

            # --- Optional: Print current state for debugging ---
            # print("Current Grid State:")
            # for p_elem in self.primary_elements:
            #      print(f"  {p_elem}:")
            #      for cat in self.categories[1:]:
            #           print(f"    {cat}: {self.grid[p_elem][cat]}")
            # --- End Debug Print ---

            return False, None # Not uniquely solved


class PuzzleVerifier:
    """
    Verifies either Symbol Cipher or Logic Grid puzzles for unique solvability.
    """
    def __init__(self, puzzle_type: str, **kwargs):
        """
        Initializes the verifier based on puzzle type.

        Args:
            puzzle_type (str): 'symbol' or 'logic_grid'.
            **kwargs: Arguments specific to the puzzle type:
                - For 'symbol': symbols (List[str]), letters (List[str]), clues (List[Tuple[str, ClueType]])
                - For 'logic_grid': categories (List[str]), elements (List[List[str]]), clues (List[str])
        """
        self.puzzle_type = puzzle_type
        self.kwargs = kwargs

        if puzzle_type == 'symbol':
            self.symbols = kwargs.get('symbols')
            self.letters = kwargs.get('letters')
            self.clues = kwargs.get('clues')
            if not all([self.symbols, self.letters, self.clues is not None]):
                 raise ValueError("Missing required arguments for symbol puzzle verification: symbols, letters, clues")
            self.num_elements = len(self.symbols)
            if len(self.letters) != self.num_elements:
                raise ValueError("Mismatch between number of symbols and letters for symbol puzzle.")

        elif puzzle_type == 'logic_grid':
            self.categories = kwargs.get('categories')
            self.elements = kwargs.get('elements')
            self.clues = kwargs.get('clues') # Clues are List[str] here
            if not all([self.categories, self.elements, self.clues is not None]):
                raise ValueError("Missing required arguments for logic grid verification: categories, elements, clues")
            # Instantiate the internal logic grid verifier immediately
            self.logic_grid_verifier = _LogicGridInternalVerifier(self.categories, self.elements, self.clues)

        else:
            raise ValueError(f"Unsupported puzzle_type for verification: {puzzle_type}")

    def verify(self) -> Tuple[bool, Union[List[Dict[str, str]], Optional[Dict[str, Dict[str, str]]]]]:
        """
        Verifies the puzzle based on its type.

        Returns:
            Tuple[bool, Union[List[Dict[str, str]], Optional[Dict[str, Dict[str, str]]]]]:
                - bool: True if a unique solution exists, False otherwise.
                - Union:
                    - For symbol puzzles: A list containing the single valid mapping dict if unique, otherwise an empty list or list with multiple solutions.
                    - For logic grid puzzles: The solution grid dict if unique, otherwise None.
        """
        if self.puzzle_type == 'symbol':
            return self._verify_symbol_puzzle()
        elif self.puzzle_type == 'logic_grid':
            # Delegate to the internal verifier's verify method
            is_unique, solution_grid = self.logic_grid_verifier.verify()
            return is_unique, solution_grid
        else:
             # Should not be reached due to __init__ check
             return False, None


    # --- Symbol Cipher Verification Logic ---

    def _verify_symbol_puzzle(self) -> Tuple[bool, List[Dict[str, str]]]:
        """Finds all valid solutions for a symbol cipher puzzle."""
        valid_solutions = []
        
        # Check if number of elements is manageable for permutation check
        # Factorial grows very fast! 10! is 3.6 million, 12! is ~479 million.
        # Set a reasonable limit. 
        MAX_PERMUTATION_ELEMENTS = 10 
        if self.num_elements > MAX_PERMUTATION_ELEMENTS:
            print(f"Warning: Symbol puzzle size ({self.num_elements}) exceeds verification limit ({MAX_PERMUTATION_ELEMENTS}). Skipping exhaustive check.")
            # Cannot reliably verify uniqueness. Assume not unique for safety? Or trust generator?
            # Returning False, [] indicates verification couldn't confirm uniqueness.
            return False, [] 
            
        # Generate all possible mappings (permutations of letters assigned to symbols)
        letter_permutations = itertools.permutations(self.letters)

        for p_letters in letter_permutations:
            potential_mapping = dict(zip(self.symbols, p_letters))
            if self._check_mapping_against_clues(potential_mapping):
                valid_solutions.append(potential_mapping)
                # Optimization: If we find more than one, we know it's not unique.
                # However, the generator needs the exact count (0, 1, or >1)
                # if len(valid_solutions) > 1:
                #    return False, valid_solutions # Not unique

        # After checking all permutations:
        is_unique = (len(valid_solutions) == 1)
        return is_unique, valid_solutions

    def _check_mapping_against_clues(self, mapping: Dict[str, str]) -> bool:
        """Checks if a given symbol->letter mapping satisfies all clues."""
        for clue_text, clue_type in self.clues:
            if not self._check_single_clue(mapping, clue_text, clue_type):
                return False # This mapping fails this clue
        return True # This mapping satisfies all clues

    def _check_single_clue(self, mapping: Dict[str, str], clue_text: str, clue_type: ClueType) -> bool:
        """Checks if a specific mapping satisfies a single clue."""
        try:
            # --- DIRECT ---
            if clue_type == ClueType.DIRECT:
                # Example: "'α' directly represents the letter 'P'."
                match = re.search(r"'(.+)' directly represents the letter '([A-Z])'", clue_text)
                if match:
                    symbol, expected_letter = match.groups()
                    return mapping.get(symbol) == expected_letter
                else: return False # Malformed clue

            # --- EXCLUSION ---
            elif clue_type == ClueType.EXCLUSION:
                # Example: "The symbol 'β' does not represent the letter 'Q'."
                 match = re.search(r"'(.+)' does not represent the letter '([A-Z])'", clue_text)
                 if match:
                     symbol, excluded_letter = match.groups()
                     actual_letter = mapping.get(symbol)
                     return actual_letter is not None and actual_letter != excluded_letter
                 else: return False # Malformed clue

            # --- POSITIONAL ---
            elif clue_type == ClueType.POSITIONAL:
                 # Example: "In the sequence shown, the first symbol represents a vowel."
                 # Requires the original symbol order used for generation! Stored in self.symbols
                 match = re.search(r"the (\w+) symbol represents (a vowel|a consonant)", clue_text)
                 if match:
                     position_word, category = match.groups()
                     positions = {"first": 0, "second": 1, "third": 2, "fourth": 3, "fifth": 4,
                                  "sixth": 5, "seventh": 6, "eighth": 7, "ninth": 8, "tenth": 9} # Extend if needed
                     if position_word not in positions: return False # Unknown position word
                     idx = positions[position_word]
                     if idx >= len(self.symbols): return False # Index out of bounds

                     symbol_at_pos = self.symbols[idx]
                     letter = mapping.get(symbol_at_pos)
                     if not letter: return False # Symbol not in mapping? Should not happen

                     is_vowel = letter in VOWELS
                     if category == "a vowel":
                         return is_vowel
                     else: # category == "a consonant"
                         return not is_vowel
                 else: return False

            # --- RELATIONAL ---
            elif clue_type == ClueType.RELATIONAL:
                 # Example: "The letter for 'γ' comes earlier in the alphabet than the letter for 'δ'."
                 match = re.search(r"letter for '(.+)' comes (earlier|later) .* than the letter for '(.+)'", clue_text)
                 if match:
                     s1, comparison, s2 = match.groups()
                     l1 = mapping.get(s1)
                     l2 = mapping.get(s2)
                     if not l1 or not l2: return False # Symbols not in mapping

                     if comparison == "earlier":
                         return ord(l1) < ord(l2)
                     else: # comparison == "later"
                         return ord(l1) > ord(l2)
                 else: return False

            # --- CATEGORY ---
            elif clue_type == ClueType.CATEGORY:
                 # Example: "The symbol 'ε' represents a vowel."
                 match = re.search(r"'(.+)' represents (a vowel|a consonant)", clue_text)
                 if match:
                      symbol, category = match.groups()
                      letter = mapping.get(symbol)
                      if not letter: return False
                      is_vowel = letter in VOWELS
                      if category == "a vowel":
                          return is_vowel
                      else: # category == "a consonant"
                          return not is_vowel
                 else: return False

            # --- LOGICAL ---
            elif clue_type == ClueType.LOGICAL:
                # Example: "If 'α' represents a vowel, then 'β' represents a consonant."
                match = re.search(r"If '(.+)' represents (a vowel|a consonant), then '(.+)' represents (a vowel|a consonant)", clue_text)
                if match:
                     s1, premise_cat, s2, conclusion_cat = match.groups()
                     l1 = mapping.get(s1)
                     l2 = mapping.get(s2)
                     if not l1 or not l2: return False

                     # Check premise
                     premise_true = (l1 in VOWELS) if premise_cat == "a vowel" else (l1 not in VOWELS)

                     # If premise is false, the implication is always true
                     if not premise_true:
                         return True

                     # If premise is true, check conclusion
                     conclusion_true = (l2 in VOWELS) if conclusion_cat == "a vowel" else (l2 not in VOWELS)
                     return conclusion_true # If premise is true, result is true iff conclusion is true
                else: return False # Malformed clue

            # --- Unknown Clue Type ---
            else:
                print(f"Warning: Unknown clue type '{clue_type}' encountered during verification.")
                return False # Treat unknown types as failure for safety

        except Exception as e:
            # Catch potential errors during regex parsing or logic
            # print(f"Error verifying clue '{clue_text}' (Type: {clue_type}): {e}")
            return False # Treat errors as failure

# ... (Keep Example Usage comment block if desired) ...

# --- Fix Linter Error in Puzzle Docstring ---
# The error `Invalid character "\u5c"` often happens with backslashes in docstrings.
# Ensure the docstring for the Puzzle class is properly formatted.
# Re-paste the Puzzle class definition with a corrected docstring if needed.
# Assuming the original docstring was meant to be standard:



