from typing import Dict, List, Tuple, Optional, Any
import random
import re
import logging

# Import necessary components from the puzzle package
from puzzle.common import ClueType, VOWELS, CONSONANTS
from puzzle.puzzle_types import Puzzle
from puzzle.verifier import PuzzleVerifier # To check generated puzzle

logger = logging.getLogger(__name__)

def generate_symbol_puzzle_internal(level: int, min_elements: int, max_elements: int,
                                     symbols_pool: List[str], letters_pool: List[str],
                                     vowels: str, consonants: str,
                                     max_verification_tries: int, **kwargs) -> Puzzle:
    """Generates a verified symbol cipher puzzle."""
    logger.debug(f"Attempting Symbol Puzzle generation for level {level}")
    for attempt in range(max_verification_tries):
        # Determine number of elements based on level and clamped max
        num_elements = min(min_elements + level // 2, max_elements)
        num_elements = max(min_elements, num_elements) # Ensure at least min

        if num_elements > len(symbols_pool) or num_elements > len(letters_pool):
            logger.error(f"Cannot generate puzzle: Not enough symbols ({len(symbols_pool)}) or letters ({len(letters_pool)}) for {num_elements} elements.")
            raise ValueError("Insufficient pool size for requested number of elements.")

        # Select symbols and letters
        symbols = random.sample(symbols_pool, num_elements)
        letters = random.sample(letters_pool, num_elements)
        random.shuffle(letters) # Ensure random mapping
        intended_solution = dict(zip(symbols, letters))

        # Generate clues for this potential solution
        clues = _generate_symbol_clues(symbols, letters, intended_solution, level, vowels, consonants)

        # Basic check: Ensure a reasonable number of clues were generated
        if not clues or len(clues) < num_elements // 2: # Need at least some clues
            logger.debug(f"Attempt {attempt+1}: Not enough clues generated ({len(clues)}). Retrying.")
            continue

        # Verify the generated puzzle (clues + symbols/letters)
        try:
            # Use the PuzzleVerifier (which might be slow for large puzzles)
            verifier = PuzzleVerifier(puzzle_type='symbol', symbols=symbols, letters=letters, clues=clues)
            is_unique, solutions = verifier.verify()

            if is_unique and len(solutions) == 1:
                actual_solution = solutions[0]
                # Double-check if the *verifier's* unique solution matches *our* intended one
                if actual_solution == intended_solution:
                     logger.info(f"Successfully generated verified Symbol Puzzle (Level {level}, {num_elements} elements).")
                     return Puzzle(level, symbols, letters, intended_solution, clues, is_verified=True)
                else:
                     # This indicates a potential issue in clue generation or verification logic
                     logger.warning(f"Verifier found a unique solution, but it differs from intended one. Intended: {intended_solution}, Found: {actual_solution}. Retrying generation.")
            elif not is_unique:
                logger.debug(f"Attempt {attempt+1}: Puzzle not unique ({len(solutions)} solutions found). Retrying.")
            else: # is_unique is False, but solutions might be empty (contradiction)
                logger.debug(f"Attempt {attempt+1}: Puzzle verification failed (likely contradiction). Retrying.")

        except Exception as e:
            # Catch errors during verification (e.g., regex issues, logic errors)
            logger.error(f"Error during puzzle verification (Attempt {attempt+1}): {e}", exc_info=True)
            # Continue to next generation attempt

    # If loop finishes without returning, generation failed
    raise ValueError(f"Failed to generate a verifiable symbol puzzle after {max_verification_tries} attempts for level {level}.")


def _generate_symbol_clues(symbols: List[str], letters: List[str],
                           solution_mapping: Dict[str, str], level: int,
                           vowels: str, consonants: str) -> List[Tuple[str, ClueType]]:
    """Generates clues for symbol cipher puzzles."""
    clues = []
    if not symbols or not letters or not solution_mapping:
         logger.warning("Cannot generate symbol clues with empty symbols, letters, or solution.")
         return []

    symbol_list = list(solution_mapping.keys())
    random.shuffle(symbol_list)

    num_elements = len(symbols)
    # Adjust clue count based on level and size - aim for slightly more clues than elements
    num_clues_target = min(num_elements + level // 2 + 1, int(num_elements * 1.5)) # Example: 1.5x elements + level boost
    num_clues_target = max(num_elements // 2 + 1, num_clues_target) # Ensure a minimum number
    logger.debug(f"Targeting {num_clues_target} clues for {num_elements} elements at level {level}.")

    # Define available clue generation functions
    possible_clue_generators = {
        ClueType.DIRECT: lambda: _generate_direct_clue(symbols, letters, solution_mapping, symbol_list),
        ClueType.EXCLUSION: lambda: _generate_exclusion_clue(symbols, letters, solution_mapping, symbol_list),
        ClueType.POSITIONAL: lambda: _generate_positional_clue(symbols, letters, solution_mapping, symbol_list, vowels, consonants), # Pass symbols list for original order
        ClueType.RELATIONAL: lambda: _generate_relational_clue(symbols, letters, solution_mapping, symbol_list),
        ClueType.CATEGORY: lambda: _generate_category_clue(symbols, letters, solution_mapping, symbol_list, vowels, consonants),
        ClueType.LOGICAL: lambda: _generate_logical_clue(symbols, letters, solution_mapping, symbol_list, vowels, consonants),
    }

    # Determine which clue types are available based on level and puzzle size
    available_clue_types = [ClueType.DIRECT, ClueType.EXCLUSION] # Always available
    if level >= 1 and num_elements >= 2: available_clue_types.append(ClueType.CATEGORY)
    if level >= 2 and num_elements >= 3: available_clue_types.extend([ClueType.POSITIONAL, ClueType.RELATIONAL])
    if level >= 3 and num_elements >= 4: available_clue_types.append(ClueType.LOGICAL)

    generated_clue_texts = set() # Track generated text to avoid duplicates

    # Generate clues until target is met or possibilities exhausted
    attempts = 0
    max_total_attempts = num_clues_target * 5 # Give up after excessive attempts

    while len(clues) < num_clues_target and attempts < max_total_attempts:
         attempts += 1
         if not available_clue_types: break # Should not happen if basic types exist

         clue_type = random.choice(available_clue_types)
         generator_func = possible_clue_generators[clue_type]

         # Try generating a specific clue type a few times
         clue_text = None
         for retry in range(3): # Max 3 retries per type selection
             try:
                 clue_text = generator_func()
                 if clue_text and clue_text not in generated_clue_texts:
                     break # Found a new, valid clue
                 else:
                     clue_text = None # Reset if duplicate or None
             except Exception as e:
                 # Log minor errors during clue generation, but don't stop the process
                 logger.debug(f"Minor error generating {clue_type.name} clue (attempt {retry+1}): {e}")
                 clue_text = None

         if clue_text:
             clues.append((clue_text, clue_type))
             generated_clue_texts.add(clue_text)
             logger.debug(f"Generated clue #{len(clues)} ({clue_type.name}): {clue_text}")
         # else: logger.debug(f"Failed to generate a unique {clue_type.name} clue this cycle.")


    logger.info(f"Generated {len(clues)} clues for Symbol Puzzle.")
    return clues

# --- Symbol Cipher Clue Generation Helper Functions ---
# These now take the necessary pools (vowels, consonants) as arguments

def _generate_direct_clue(symbols: List[str], letters: List[str],
                          solution: Dict[str, str], symbol_pool: List[str]) -> Optional[str]:
    if not symbol_pool: return None
    symbol = random.choice(symbol_pool)
    letter = solution[symbol]
    return f"'{symbol}' directly represents the letter '{letter}'."

def _generate_exclusion_clue(symbols: List[str], letters: List[str],
                             solution: Dict[str, str], symbol_pool: List[str]) -> Optional[str]:
    if not symbol_pool or len(letters) < 2: return None
    symbol = random.choice(symbol_pool)
    actual_letter = solution[symbol]
    possible_wrong_letters = [l for l in letters if l != actual_letter]
    if not possible_wrong_letters: return None
    wrong_letter = random.choice(possible_wrong_letters)
    return f"The symbol '{symbol}' does not represent the letter '{wrong_letter}'."

def _generate_positional_clue(symbols_ordered: List[str], letters: List[str], # Takes original ordered list
                              solution: Dict[str, str], symbol_pool: List[str],
                              vowels: str, consonants: str) -> Optional[str]:
    # Relies on the original `symbols_ordered` list order passed to the generator
    if len(symbols_ordered) < 2: return None
    idx = random.randrange(len(symbols_ordered))
    symbol = symbols_ordered[idx] # Get symbol based on original index
    if symbol not in symbol_pool: return None # Ensure the selected symbol is actually in the current puzzle if pool shrinks

    position_word = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth"] # Extend as needed
    if idx < len(position_word):
         pos_str = position_word[idx]
         letter = solution[symbol]
         prop = "a vowel" if letter in vowels else "a consonant"
         # Randomly negate sometimes for variety?
         # if random.random() < 0.3:
         #     neg_prop = "a consonant" if letter in vowels else "a vowel"
         #     return f"In the sequence shown, the {pos_str} symbol does NOT represent {neg_prop}."
         # else:
         return f"In the sequence shown, the {pos_str} symbol represents {prop}."
    return None # Index out of range for position words

def _generate_relational_clue(symbols: List[str], letters: List[str],
                              solution: Dict[str, str], symbol_pool: List[str]) -> Optional[str]:
    if len(symbol_pool) < 2: return None
    s1, s2 = random.sample(symbol_pool, 2)
    l1, l2 = solution[s1], solution[s2]
    # Avoid clues for adjacent letters as they are less informative unless combined with other clues
    if abs(ord(l1) - ord(l2)) <= 1 and random.random() < 0.5: return None

    if ord(l1) < ord(l2):
        return f"The letter for '{s1}' comes earlier in the alphabet than the letter for '{s2}'."
    elif ord(l1) > ord(l2):
         return f"The letter for '{s1}' comes later in the alphabet than the letter for '{s2}'."
    else: return None # Should not happen if s1 != s2

def _generate_category_clue(symbols: List[str], letters: List[str],
                            solution: Dict[str, str], symbol_pool: List[str],
                            vowels: str, consonants: str) -> Optional[str]:
    if not symbol_pool: return None
    symbol = random.choice(symbol_pool)
    letter = solution[symbol]
    category = "a vowel" if letter in vowels else "a consonant"
    # Randomly negate?
    # if random.random() < 0.3:
    #      neg_category = "a consonant" if letter in vowels else "a vowel"
    #      return f"The symbol '{symbol}' does NOT represent {neg_category}."
    # else:
    return f"The symbol '{symbol}' represents {category}."

def _generate_logical_clue(symbols: List[str], letters: List[str],
                           solution: Dict[str, str], symbol_pool: List[str],
                           vowels: str, consonants: str) -> Optional[str]:
    # Simple If-Then based on categories
    if len(symbol_pool) < 2: return None
    s1, s2 = random.sample(symbol_pool, 2)
    l1, l2 = solution[s1], solution[s2]
    l1_prop_is_vowel = l1 in vowels
    l2_prop_is_vowel = l2 in vowels
    l1_prop_text = "a vowel" if l1_prop_is_vowel else "a consonant"
    l2_prop_text = "a vowel" if l2_prop_is_vowel else "a consonant"

    # Ensure the clue is logically sound based on the actual solution
    # Format: If P then Q. This is true if P is false, or if P is true and Q is true.
    # We can generate a true statement by:
    # 1. Making P true and Q true according to the solution.
    # 2. Making P false according to the solution (Q can be anything).

    make_premise_false = random.choice([True, False])

    if make_premise_false:
        premise_prop_text = "a consonant" if l1_prop_is_vowel else "a vowel" # Opposite of l1's actual type
        # Conclusion can be anything, let's make it random but potentially true/false
        concl_prop_text = random.choice(["a vowel", "a consonant"])
        return f"If '{s1}' represents {premise_prop_text}, then '{s2}' represents {concl_prop_text}."
    else:
        # Premise matches l1's actual type, conclusion must match l2's actual type
        return f"If '{s1}' represents {l1_prop_text}, then '{s2}' represents {l2_prop_text}."