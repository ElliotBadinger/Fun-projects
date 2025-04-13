from typing import Dict, List, Tuple, Optional, Any, Union
import itertools
import re
import logging
import math

# Relative imports
from .common import ClueType, VOWELS, CONSONANTS
from .verifiers.logic_grid_verifier import _LogicGridInternalVerifier

logger = logging.getLogger(__name__)

class PuzzleVerifier:
    """Verifies either Symbol Cipher or Logic Grid puzzles for unique solvability."""
    MAX_SYMBOL_PERMUTATION_ELEMENTS = 9 # Max size for brute-force symbol check

    def __init__(self, puzzle_type: str, **kwargs):
        self.puzzle_type = puzzle_type.lower() # Normalize type string
        self.kwargs = kwargs
        self.logic_grid_verifier_instance = None # Initialize

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

            try:
                self.logic_grid_verifier_instance = _LogicGridInternalVerifier(categories, elements_list, clues)
            except ValueError as e:
                 logger.error(f"Failed to initialize internal logic grid verifier: {e}")
                 raise # Propagate initialization errors

        else:
            raise ValueError(f"Unsupported puzzle_type for verification: {puzzle_type}")

    def verify(self) -> Tuple[bool, Union[List[Dict[str, str]], Optional[Dict[str, Dict[str, str]]]]]:
        """
        Verifies the puzzle based on its type.

        Returns:
            Tuple containing:
            - bool: True if a unique solution exists, False otherwise.
            - Union[List[Dict], Optional[Dict]]:
                - For 'symbol': A list of all valid solution mappings found.
                - For 'logic_grid': The unique solution dict if found, else None.
        """
        logger.info(f"Starting verification for {self.puzzle_type} puzzle...")
        if self.puzzle_type == 'symbol':
            return self._verify_symbol_puzzle()
        elif self.puzzle_type == 'logic_grid':
            if self.logic_grid_verifier_instance:
                 return self.logic_grid_verifier_instance.verify()
            else:
                 logger.error("Logic grid verifier was not initialized.")
                 return False, None # Indicate failure
        else:
            # This case should be prevented by __init__
            logger.error(f"Verification called for unhandled type: {self.puzzle_type}")
            return False, None

    def _verify_symbol_puzzle(self) -> Tuple[bool, List[Dict[str, str]]]:
        """Finds all valid solutions for a symbol cipher puzzle via brute-force permutation."""
        if self.num_elements <= 0:
            logger.warning("Cannot verify symbol puzzle with zero elements.")
            return False, []
        if self.num_elements > self.MAX_SYMBOL_PERMUTATION_ELEMENTS:
            logger.warning(f"Symbol puzzle size ({self.num_elements}) exceeds verification limit ({self.MAX_SYMBOL_PERMUTATION_ELEMENTS}). Skipping brute-force verification.")
            # Cannot determine uniqueness, return False and empty list
            # Or potentially return True but indicate uncertainty? For now, return False.
            return False, []

        valid_solutions = []
        total_permutations = math.factorial(self.num_elements)
        logger.info(f"Verifying symbol puzzle by checking {total_permutations} permutations...")

        # Iterate through all possible assignments of letters to symbols
        letter_permutations = itertools.permutations(self.letters)
        checked_count = 0
        log_interval = max(1, total_permutations // 10) # Log progress roughly 10 times

        for p_letters in letter_permutations:
            checked_count += 1
            potential_mapping = dict(zip(self.symbols, p_letters))
            if self._check_mapping_against_clues(potential_mapping):
                valid_solutions.append(potential_mapping)
                # Optimization: Can stop early if we only care about uniqueness > 1
                # if len(valid_solutions) > 1:
                #     logger.info(f"Found >1 valid solutions after checking {checked_count} permutations. Puzzle not unique.")
                #     return False, valid_solutions

            if checked_count % log_interval == 0:
                 logger.debug(f"  ...checked {checked_count}/{total_permutations} permutations.")

        is_unique = (len(valid_solutions) == 1)
        logger.info(f"Symbol puzzle verification complete. Found {len(valid_solutions)} valid solution(s). Unique: {is_unique}")
        return is_unique, valid_solutions

    def _check_mapping_against_clues(self, mapping: Dict[str, str]) -> bool:
        """Checks if a given mapping satisfies all provided clues."""
        for clue_text, clue_type in self.clues:
            if not self._check_single_clue(mapping, clue_text, clue_type):
                # logger.debug(f"Mapping {mapping} failed clue: '{clue_text}' (Type: {clue_type})")
                return False # Mapping fails if any clue is violated
        return True # Mapping is valid if all clues are satisfied

    def _check_single_clue(self, mapping: Dict[str, str], clue_text: str, clue_type: ClueType) -> bool:
        """Checks if a specific mapping satisfies a single clue."""
        try:
            if clue_type == ClueType.DIRECT:
                # Example: "'α' directly represents the letter 'A'"
                match = re.search(r"'(.+?)'\s+directly represents the letter\s+'([A-Z])'", clue_text, re.IGNORECASE)
                return match and mapping.get(match.group(1)) == match.group(2)

            elif clue_type == ClueType.EXCLUSION:
                 # Example: "The symbol 'β' does not represent the letter 'C'."
                 match = re.search(r"symbol\s+'(.+?)'\s+does not represent the letter\s+'([A-Z])'", clue_text, re.IGNORECASE)
                 return match and mapping.get(match.group(1)) != match.group(2)

            elif clue_type == ClueType.POSITIONAL:
                 # Example: "In the sequence shown, the third symbol represents a consonant."
                 match = re.search(r"the\s+(\w+)\s+symbol represents\s+(a vowel|a consonant)", clue_text, re.IGNORECASE)
                 if not match: return False # Clue format error
                 pos_word, category_type = match.groups()
                 positions = {"first": 0, "second": 1, "third": 2, "fourth": 3, "fifth": 4, "sixth": 5, "seventh": 6, "eighth": 7, "ninth": 8, "tenth": 9} # Extend if needed
                 idx = positions.get(pos_word.lower())
                 if idx is None or idx >= len(self.symbols): # Check index validity
                     # logger.warning(f"Positional clue refers to invalid position '{pos_word}' or index {idx} for {len(self.symbols)} symbols.")
                     return False # Cannot evaluate if position is invalid
                 symbol_at_pos = self.symbols[idx]
                 letter = mapping.get(symbol_at_pos)
                 if not letter: return False # Should not happen if mapping is complete permutation
                 is_vowel = letter in VOWELS
                 return (category_type.lower() == "a vowel" and is_vowel) or \
                        (category_type.lower() == "a consonant" and not is_vowel)

            elif clue_type == ClueType.RELATIONAL:
                 # Example: "The letter for 'δ' comes earlier in the alphabet than the letter for 'γ'."
                 match = re.search(r"letter for\s+'(.+?)'\s+comes\s+(earlier|later)\s+.*than the letter for\s+'(.+?)'", clue_text, re.IGNORECASE)
                 if not match: return False
                 s1, comparison, s2 = match.groups()
                 l1, l2 = mapping.get(s1), mapping.get(s2)
                 if not l1 or not l2: return False # Symbols not in mapping? Should not happen.
                 return (comparison.lower() == "earlier" and ord(l1) < ord(l2)) or \
                        (comparison.lower() == "later" and ord(l1) > ord(l2))

            elif clue_type == ClueType.CATEGORY:
                 # Example: "The symbol 'ζ' represents a vowel."
                 match = re.search(r"symbol\s+'(.+?)'\s+represents\s+(a vowel|a consonant)", clue_text, re.IGNORECASE)
                 if not match: return False
                 symbol, category_type = match.groups()
                 letter = mapping.get(symbol)
                 if not letter: return False
                 is_vowel = letter in VOWELS
                 return (category_type.lower() == "a vowel" and is_vowel) or \
                        (category_type.lower() == "a consonant" and not is_vowel)

            elif clue_type == ClueType.LOGICAL:
                # Example: "If 'α' represents a vowel, then 'β' represents a consonant."
                match = re.search(r"If\s+'(.+?)'\s+represents\s+(a vowel|a consonant),\s*then\s+'(.+?)'\s+represents\s+(a vowel|a consonant)", clue_text, re.IGNORECASE)
                if not match: return False
                s1, premise_cat, s2, conclusion_cat = match.groups()
                l1, l2 = mapping.get(s1), mapping.get(s2)
                if not l1 or not l2: return False

                # Evaluate premise P
                premise_is_true = (l1 in VOWELS if premise_cat.lower() == "a vowel" else l1 not in VOWELS)

                # If P is false, the implication (P -> Q) is true
                if not premise_is_true:
                    return True

                # If P is true, the implication is true only if Q is true
                conclusion_is_true = (l2 in VOWELS if conclusion_cat.lower() == "a vowel" else l2 not in VOWELS)
                return conclusion_is_true
            else:
                # Should not happen if ClueType enum is used correctly
                logger.warning(f"Unknown clue type '{clue_type}' encountered during verification.")
                return False
        except Exception as e:
            # Catch potential errors in regex or logic for a specific clue
            logger.error(f"Error verifying clue '{clue_text}' (Type: {clue_type}) against mapping {mapping}: {e}", exc_info=False) # Keep log clean unless debugging
            return False # Treat errors as the clue not being satisfied