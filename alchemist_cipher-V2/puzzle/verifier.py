from typing import Dict, List, Tuple, Optional, Any, Union
import itertools
import re
import logging
import math

# Relative imports
from puzzle.common import ClueType, VOWELS, CONSONANTS
from puzzle.verifiers.logic_grid_verifier import _LogicGridInternalVerifier

logger = logging.getLogger(__name__)

class PuzzleVerifier:
    """Verifies either Symbol Cipher or Logic Grid puzzles for unique solvability."""
    MAX_SYMBOL_PERMUTATION_ELEMENTS = 9 # Max size for brute-force symbol check

    def __init__(self, puzzle_type: str, **kwargs):
        self.puzzle_type = puzzle_type.lower() # Normalize type string
        self.kwargs = kwargs
        self.logic_grid_verifier_instance: Optional[_LogicGridInternalVerifier] = None # Initialize with type hint
        self._initialization_error: Optional[str] = None # Store init error message

        try:
            if self.puzzle_type == 'symbol':
                self.symbols = kwargs.get('symbols')
                self.letters = kwargs.get('letters')
                self.clues = kwargs.get('clues') # List[Tuple[str, ClueType]]
                if not all([isinstance(self.symbols, list),
                            isinstance(self.letters, list),
                            isinstance(self.clues, list)]):
                    raise ValueError("Missing or invalid arguments for 'symbol' verification (symbols, letters, clues).")
                self.num_elements = len(self.symbols)
                if len(self.letters) != self.num_elements:
                    raise ValueError(f"Symbol/letter count mismatch: {len(self.symbols)} symbols vs {len(self.letters)} letters.")
            elif self.puzzle_type == 'logic_grid':
                categories = kwargs.get('categories')
                elements = kwargs.get('elements') # List[List[str]] or Dict[str, List[str]]
                clues = kwargs.get('clues') # List[str]

                if not all([isinstance(categories, list),
                            (isinstance(elements, list) or isinstance(elements, dict)),
                            isinstance(clues, list)]):
                    raise ValueError("Missing or invalid arguments for 'logic_grid' verification (categories, elements, clues).")

                # Handle if elements is passed as dict or list
                if isinstance(elements, dict):
                    # Ensure order matches categories if passed as dict
                    try:
                        elements_list = [elements[cat] for cat in categories]
                    except KeyError as e:
                        raise ValueError(f"Category '{e}' from categories list not found as key in elements dictionary.")
                else: # Assume it's a list of lists
                    elements_list = elements

                # Attempt to initialize the internal verifier
                try:
                    # Use the potentially refactored _LogicGridInternalVerifier
                    self.logic_grid_verifier_instance = _LogicGridInternalVerifier(categories, elements_list, clues)
                    logger.info("Successfully initialized internal logic grid verifier.")
                except Exception as e: # Catch any exception during internal init
                    logger.error(f"Failed to initialize internal logic grid verifier: {e}", exc_info=True) # Log with traceback
                    # Store error message but don't raise, allow verify to handle it
                    self._initialization_error = f"Internal verifier init failed: {e}"
                    self.logic_grid_verifier_instance = None # Ensure instance is None on error
            else:
                raise ValueError(f"Unsupported puzzle_type for verification: {puzzle_type}")
        except ValueError as e: # Catch errors from PuzzleVerifier's own validation
            logger.error(f"PuzzleVerifier initialization failed: {e}")
            self._initialization_error = str(e) # Store error message
            # Ensure relevant attributes are None if error occurs before assignment
            if self.puzzle_type == 'symbol':
                self.symbols = self.letters = self.clues = None
                self.num_elements = 0
            # logic_grid_verifier_instance is already handled for logic grid case

    def verify(self) -> Tuple[bool, Union[List[Dict[str, str]], Optional[Dict[str, Dict[str, str]]]]]:
        """
        Verifies the puzzle based on its type.

        Returns:
            Tuple containing:
            - bool: True if a unique solution exists, False otherwise.
            - Union[List[Dict], Optional[Dict]]:
                - For 'symbol': A list of all valid solution mappings found (empty if not unique/no solution/error).
                - For 'logic_grid': The unique solution dict if found, else None.
        """
        # Check for initialization errors first
        if self._initialization_error:
            logger.error(f"Verification aborted due to initialization error: {self._initialization_error}")
            return False, None # Cannot verify if init failed

        logger.info(f"Starting verification for {self.puzzle_type} puzzle...")
        if self.puzzle_type == 'symbol':
            # Ensure symbol attributes were initialized (check against None)
            if self.symbols is None or self.letters is None or self.clues is None:
                logger.error("Cannot verify symbol puzzle: missing required attributes due to init error.")
                return False, [] # Return empty list for symbol type on error
            return self._verify_symbol_puzzle()
        elif self.puzzle_type == 'logic_grid':
            # Check if the internal verifier instance exists
            if self.logic_grid_verifier_instance:
                try:
                    # Call the verify method of the (potentially refactored) internal verifier
                    return self.logic_grid_verifier_instance.verify()
                except Exception as e:
                    logger.error(f"Error during logic grid internal verification: {e}", exc_info=True)
                    return False, None # Internal verify error
            else:
                logger.error("Logic grid verifier was not initialized successfully. Cannot verify.")
                return False, None # Indicate failure due to non-initialization
        else:
            # This case should ideally be prevented by __init__ validation
            logger.error(f"Verification called for unhandled or uninitialized type: {self.puzzle_type}")
            return False, None

    def _verify_symbol_puzzle(self) -> Tuple[bool, List[Dict[str, str]]]:
        """Finds all valid solutions for a symbol cipher puzzle via brute-force permutation."""
        if self.num_elements <= 0:
            logger.warning("Cannot verify symbol puzzle with zero elements.")
            return False, []
        if self.num_elements > self.MAX_SYMBOL_PERMUTATION_ELEMENTS:
            logger.warning(f"Symbol puzzle size ({self.num_elements}) exceeds verification limit ({self.MAX_SYMBOL_PERMUTATION_ELEMENTS}). Skipping brute-force verification.")
            return False, []

        valid_solutions = []
        total_permutations = math.factorial(self.num_elements)
        logger.info(f"Verifying symbol puzzle by checking {total_permutations} permutations...")

        letter_permutations = itertools.permutations(self.letters)
        checked_count = 0
        log_interval = max(1, total_permutations // 10)

        for p_letters in letter_permutations:
            checked_count += 1
            potential_mapping = dict(zip(self.symbols, p_letters))
            if self._check_mapping_against_clues(potential_mapping):
                valid_solutions.append(potential_mapping)

            if checked_count % log_interval == 0:
                logger.debug(f"  ...checked {checked_count}/{total_permutations} permutations.")

        is_unique = (len(valid_solutions) == 1)
        logger.info(f"Symbol puzzle verification complete. Found {len(valid_solutions)} valid solution(s). Unique: {is_unique}")
        return is_unique, valid_solutions

    def _check_mapping_against_clues(self, mapping: Dict[str, str]) -> bool:
        """Checks if a given mapping satisfies all provided clues."""
        if self.clues is None: # Add check in case of init error
            logger.error("Cannot check clues, clues list is None.")
            return False
        for clue_text, clue_type in self.clues:
            if not self._check_single_clue(mapping, clue_text, clue_type):
                return False
        return True

    def _check_single_clue(self, mapping: Dict[str, str], clue_text: str, clue_type: ClueType) -> bool:
        """Checks if a specific mapping satisfies a single clue."""
        try:
            if clue_type == ClueType.DIRECT:
                match = re.search(r"'(.+?)'\s+directly represents the letter\s+'([A-Z])'", clue_text, re.IGNORECASE)
                return match and mapping.get(match.group(1)) == match.group(2)

            elif clue_type == ClueType.EXCLUSION:
                match = re.search(r"symbol\s+'(.+?)'\s+does not represent the letter\s+'([A-Z])'", clue_text, re.IGNORECASE)
                return match and mapping.get(match.group(1)) != match.group(2)

            elif clue_type == ClueType.POSITIONAL:
                match = re.search(r"the\s+(\w+)\s+symbol represents\s+(a vowel|a consonant)", clue_text, re.IGNORECASE)
                if not match: return False
                pos_word, category_type = match.groups()
                positions = {"first": 0, "second": 1, "third": 2, "fourth": 3, "fifth": 4, "sixth": 5, "seventh": 6, "eighth": 7, "ninth": 8, "tenth": 9}
                idx = positions.get(pos_word.lower())
                if idx is None or self.symbols is None or idx >= len(self.symbols): # Add check for self.symbols
                    return False
                symbol_at_pos = self.symbols[idx]
                letter = mapping.get(symbol_at_pos)
                if not letter: return False
                is_vowel = letter in VOWELS
                return (category_type.lower() == "a vowel" and is_vowel) or \
                       (category_type.lower() == "a consonant" and not is_vowel)

            elif clue_type == ClueType.RELATIONAL:
                match = re.search(r"letter for\s+'(.+?)'\s+comes\s+(earlier|later)\s+.*than the letter for\s+'(.+?)'", clue_text, re.IGNORECASE)
                if not match: return False
                s1, comparison, s2 = match.groups()
                l1, l2 = mapping.get(s1), mapping.get(s2)
                if not l1 or not l2: return False
                return (comparison.lower() == "earlier" and ord(l1) < ord(l2)) or \
                       (comparison.lower() == "later" and ord(l1) > ord(l2))

            elif clue_type == ClueType.CATEGORY:
                match = re.search(r"symbol\s+'(.+?)'\s+represents\s+(a vowel|a consonant)", clue_text, re.IGNORECASE)
                if not match: return False
                symbol, category_type = match.groups()
                letter = mapping.get(symbol)
                if not letter: return False
                is_vowel = letter in VOWELS
                return (category_type.lower() == "a vowel" and is_vowel) or \
                       (category_type.lower() == "a consonant" and not is_vowel)

            elif clue_type == ClueType.LOGICAL:
                match = re.search(r"If\s+'(.+?)'\s+represents\s+(a vowel|a consonant),\s*then\s+'(.+?)'\s+represents\s+(a vowel|a consonant)", clue_text, re.IGNORECASE)
                if not match: return False
                s1, premise_cat, s2, conclusion_cat = match.groups()
                l1, l2 = mapping.get(s1), mapping.get(s2)
                if not l1 or not l2: return False
                premise_is_true = (l1 in VOWELS if premise_cat.lower() == "a vowel" else l1 not in VOWELS)
                if not premise_is_true:
                    return True
                conclusion_is_true = (l2 in VOWELS if conclusion_cat.lower() == "a vowel" else l2 not in VOWELS)
                return conclusion_is_true
            else:
                logger.warning(f"Unknown clue type '{clue_type}' encountered during verification.")
                return False
        except Exception as e:
            logger.error(f"Error verifying clue '{clue_text}' (Type: {clue_type}) against mapping {mapping}: {e}", exc_info=False)
            return False