import re
import logging
from typing import Dict, List, Tuple, Optional, Set, Union

logger = logging.getLogger(__name__)

class _LogicGridInternalVerifier:
    """
    (Internal Use) Verifies logic grid puzzles using constraint propagation.
    Assumes clues are provided as a list of strings.
    """
    def __init__(self, categories: List[str], elements: List[List[str]], clues: List[str]):
        # --- Input Validation ---
        if not categories or not elements or len(categories) != len(elements):
            raise ValueError("Invalid categories or elements provided: Mismatched lengths or empty.")
        if not elements or not elements[0]:
             raise ValueError("Element lists cannot be empty.")
        element_lengths = {len(e) for e in elements}
        if len(element_lengths) != 1:
             raise ValueError("Element lists must all have the same size.")
        self.grid_size = list(element_lengths)[0]
        if self.grid_size <= 0:
             raise ValueError("Grid size must be positive.")
        if not isinstance(clues, list):
             raise ValueError("Clues must be provided as a list of strings.")

        # --- Initialization ---
        self.categories = list(categories) # Ensure mutable copies
        self.elements = {cat: list(elem_list) for cat, elem_list in zip(categories, elements)}
        self.clues = clues
        self.primary_category = self.categories[0]
        self.primary_elements = self.elements[self.primary_category]
        self.secondary_categories = self.categories[1:]

        # The main grid state: maps primary element -> category -> set of possible values
        self.grid: Dict[str, Dict[str, Set[str]]] = {}
        # Store parsed relative clues for iterative application
        self.relative_clues_parsed: List[Tuple[str, str, str, str, str]] = []

        self._initialize_grid()
        logger.debug(f"LogicGridVerifier initialized: {self.grid_size}x{len(self.categories)} grid.")

    def _initialize_grid(self):
        """Resets the grid to the initial state with all possibilities."""
        self.grid = {
            p_elem: {
                cat: set(self.elements[cat]) for cat in self.secondary_categories
            }
            for p_elem in self.primary_elements
        }
        self.relative_clues_parsed = [] # Clear parsed clues too
        logger.debug("Verifier grid initialized.")

    def _find_category(self, element: str) -> Optional[str]:
        """Finds the category of a single element."""
        for cat, elems in self.elements.items():
            if element in elems:
                return cat
        logger.debug(f"Element '{element}' not found in any category pool.")
        return None

    def _find_categories(self, item1: str, item2: str) -> Tuple[Optional[str], Optional[str]]:
        """Find which categories item1 and item2 belong to."""
        return self._find_category(item1), self._find_category(item2)

    def _apply_direct_positive(self, primary_elem: str, other_category: str, value: str) -> bool:
        """
        Applies a confirmed positive link (primary_elem IS value in other_category).
        Returns False on immediate contradiction.
        """
        if primary_elem not in self.grid or other_category not in self.grid[primary_elem]:
            logger.warning(f"Apply Positive: Invalid primary element '{primary_elem}' or category '{other_category}'.")
            return True # Ignore invalid data rather than fail

        current_possibilities = self.grid[primary_elem][other_category]

        if value not in current_possibilities:
            logger.debug(f"CONTRADICTION: Trying to set '{primary_elem}' to '{value}' ({other_category}), but '{value}' is not possible ({current_possibilities}).")
            return False # Contradiction: Trying to assign a value that was already excluded

        if len(current_possibilities) == 1 and value in current_possibilities:
            return True # Already set, no change needed

        logger.debug(f"Apply Positive: Setting {primary_elem} -> {other_category} = {value}")
        # Set the possibility for this entity to only the confirmed value
        self.grid[primary_elem][other_category] = {value}

        # Apply the consequence: no other primary element can have this value in this category
        for other_p_elem in self.primary_elements:
            if other_p_elem != primary_elem:
                if not self._apply_direct_negative(other_p_elem, other_category, value):
                    # logger.debug(f"  -> Contradiction applying consequence to {other_p_elem}")
                    return False # Contradiction found while applying negative consequence
        return True

    def _apply_direct_negative(self, primary_elem: str, other_category: str, value_to_exclude: str) -> bool:
        """
        Applies a confirmed negative link (primary_elem IS NOT value_to_exclude in other_category).
        Returns False on immediate contradiction.
        """
        if primary_elem not in self.grid or other_category not in self.grid[primary_elem]:
            logger.warning(f"Apply Negative: Invalid primary element '{primary_elem}' or category '{other_category}'.")
            return True # Ignore invalid data

        current_possibilities = self.grid[primary_elem][other_category]

        if value_to_exclude in current_possibilities:
            # logger.debug(f"Apply Negative: Removing '{value_to_exclude}' from {primary_elem}/{other_category} possibilities {current_possibilities}")
            current_possibilities.remove(value_to_exclude)
            if not current_possibilities:
                logger.debug(f"CONTRADICTION: Removing '{value_to_exclude}' left no possibilities for {primary_elem}/{other_category}.")
                return False # Contradiction: Removing this leaves no options
            # If removal leaves only one possibility, apply that as a positive deduction
            if len(current_possibilities) == 1:
                 # logger.debug(f"  -> Deduction: {primary_elem} must be {list(current_possibilities)[0]} in {other_category}")
                 if not self._apply_direct_positive(primary_elem, other_category, list(current_possibilities)[0]):
                      # logger.debug(f"  -> Contradiction applying deduced positive link.")
                      return False
        # else: value was already excluded, no change needed

        return True

    def _parse_and_apply_clues(self) -> bool:
        """
        Parses clues and applies initial direct positive/negative constraints.
        Stores relative clues for later processing.
        Returns False on immediate contradiction during parsing.
        """
        logger.debug("Parsing and applying initial clues...")
        self.relative_clues_parsed = [] # Reset parsed relative clues

        # --- Regex Patterns (Simplified - more robust parsing might be needed) ---
        # Catches: "Alice is associated with Red.", "Bob is Cat."
        pattern_positive = re.compile(r"^([\w\s]+?)\s+(?:is associated with|is)\s+([\w\s]+?)\.?$", re.IGNORECASE)
        # Catches: "Charlie is not associated with Blue.", "David is not Dog."
        pattern_negative = re.compile(r"^([\w\s]+?)\s+(?:is not associated with|is not)\s+([\w\s]+?)\.?$", re.IGNORECASE)
        # Catches: "The Guest associated with Pirate (Costume) is also associated with Book (Gift)." - Categories optional
        pattern_relative_positive = re.compile(
            r"^The\s+([\w\s]+?)\s+associated with\s+([\w\s]+?)(?:\s+\(([\w\s]+?)\))?\s+is also associated with\s+([\w\s]+?)(?:\s+\(([\w\s]+?)\))?\s*\.?$",
            re.IGNORECASE)
        # Catches: "The Employee associated with Ham (Sandwich) is NOT associated with Tea (Drink)." - Categories optional
        pattern_relative_negative = re.compile(
            r"^The\s+([\w\s]+?)\s+associated with\s+([\w\s]+?)(?:\s+\(([\w\s]+?)\))?\s+is NOT associated with\s+([\w\s]+?)(?:\s+\(([\w\s]+?)\))?\s*\.?$",
            re.IGNORECASE)

        for clue_num, clue in enumerate(self.clues):
            clue = clue.strip()
            if not clue: continue
            applied = False

            # --- Try Positive Clue ---
            match_pos = pattern_positive.match(clue)
            if match_pos:
                e1_raw, e2_raw = match_pos.groups()
                e1, e2 = e1_raw.strip(), e2_raw.strip()
                cat1, cat2 = self._find_categories(e1, e2)
                if cat1 == self.primary_category and cat2 and cat2 in self.secondary_categories:
                    if not self._apply_direct_positive(e1, cat2, e2): return False # Contradiction
                    applied = True
                    logger.debug(f"  Clue {clue_num+1} (Pos): Applied {e1} -> {cat2} = {e2}")
                elif cat2 == self.primary_category and cat1 and cat1 in self.secondary_categories:
                    if not self._apply_direct_positive(e2, cat1, e1): return False # Contradiction
                    applied = True
                    logger.debug(f"  Clue {clue_num+1} (Pos): Applied {e2} -> {cat1} = {e1}")

            # --- Try Negative Clue ---
            match_neg = pattern_negative.match(clue)
            if not applied and match_neg:
                e1_raw, e2_raw = match_neg.groups()
                e1, e2 = e1_raw.strip(), e2_raw.strip()
                cat1, cat2 = self._find_categories(e1, e2)
                if cat1 == self.primary_category and cat2 and cat2 in self.secondary_categories:
                    if not self._apply_direct_negative(e1, cat2, e2): return False # Contradiction
                    applied = True
                    logger.debug(f"  Clue {clue_num+1} (Neg): Applied {e1} -> {cat2} != {e2}")
                elif cat2 == self.primary_category and cat1 and cat1 in self.secondary_categories:
                     if not self._apply_direct_negative(e2, cat1, e1): return False # Contradiction
                     applied = True
                     logger.debug(f"  Clue {clue_num+1} (Neg): Applied {e2} -> {cat1} != {e1}")

            # --- Try Relative Positive Clue ---
            match_rel_pos = pattern_relative_positive.match(clue)
            if not applied and match_rel_pos:
                # Group 1: Primary category (often implied, e.g., "The Guest") - We currently ignore this, assuming it's the primary.
                # Group 2: Element 1 value
                # Group 3: Element 1 category (optional)
                # Group 4: Element 2 value
                # Group 5: Element 2 category (optional)
                _, e1_raw, c1_raw, e2_raw, c2_raw = match_rel_pos.groups()
                e1, e2 = e1_raw.strip(), e2_raw.strip()
                # Infer categories if not explicitly provided in parens
                c1 = c1_raw.strip() if c1_raw else self._find_category(e1)
                c2 = c2_raw.strip() if c2_raw else self._find_category(e2)

                if c1 and c2 and c1 in self.secondary_categories and c2 in self.secondary_categories and c1 != c2 and \
                   e1 in self.elements.get(c1,[]) and e2 in self.elements.get(c2,[]):
                    # Store parsed relative clue: (type, value1, category1, value2, category2)
                    self.relative_clues_parsed.append(("relative_positive", e1, c1, e2, c2))
                    applied = True
                    logger.debug(f"  Clue {clue_num+1} (RelPos): Stored link between {e1}({c1}) and {e2}({c2})")
                # else: logger.warning(f"Could not parse relative positive clue: '{clue}' - Unknown elements/categories? ({e1},{c1}) ({e2},{c2})")


            # --- Try Relative Negative Clue ---
            match_rel_neg = pattern_relative_negative.match(clue)
            if not applied and match_rel_neg:
                _, e1_raw, c1_raw, e2_raw, c2_raw = match_rel_neg.groups()
                e1, e2 = e1_raw.strip(), e2_raw.strip()
                c1 = c1_raw.strip() if c1_raw else self._find_category(e1)
                c2 = c2_raw.strip() if c2_raw else self._find_category(e2)

                if c1 and c2 and c1 in self.secondary_categories and c2 in self.secondary_categories and c1 != c2 and \
                   e1 in self.elements.get(c1,[]) and e2 in self.elements.get(c2,[]):
                     # Store parsed relative clue: (type, value1, category1, value2, category2)
                     self.relative_clues_parsed.append(("relative_negative", e1, c1, e2, c2))
                     applied = True
                     logger.debug(f"  Clue {clue_num+1} (RelNeg): Stored anti-link between {e1}({c1}) and {e2}({c2})")
                # else: logger.warning(f"Could not parse relative negative clue: '{clue}' - Unknown elements/categories? ({e1},{c1}) ({e2},{c2})")


            # Log unparsed clues (optional)
            # if not applied and "hint" not in clue.lower():
            #     logger.debug(f"Verifier could not parse clue {clue_num+1}: '{clue}'")

        logger.debug(f"Initial clue parsing complete. {len(self.relative_clues_parsed)} relative clues stored.")
        return True # No immediate contradictions found during parsing

    def _propagate_constraints(self) -> bool:
        """
        Iteratively applies deductions based on grid state and relative clues until no further changes occur.
        Returns False on contradiction.
        """
        logger.debug("Starting constraint propagation...")
        iteration = 0
        max_iterations = self.grid_size * len(self.secondary_categories) * 5 # Heuristic limit

        while iteration < max_iterations:
            iteration += 1
            changed_this_iteration = False

            # --- Deduction 1: Unique Value Found for an Entity ---
            # If an entity has only one possible value left in a category,
            # eliminate that value from all other entities in that category.
            for p_elem in self.primary_elements:
                for category, possibilities in self.grid[p_elem].items():
                    if len(possibilities) == 1:
                        confirmed_value = list(possibilities)[0]
                        # Apply consequence to others
                        for other_p_elem in self.primary_elements:
                            if other_p_elem != p_elem:
                                if confirmed_value in self.grid[other_p_elem][category]:
                                    # Use apply_direct_negative to handle potential chain reactions
                                    if not self._apply_direct_negative(other_p_elem, category, confirmed_value):
                                         logger.debug(f"CONTRADICTION (Propagate D1): Removing '{confirmed_value}' from {other_p_elem}/{category} failed.")
                                         return False
                                    changed_this_iteration = True # Grid state changed

            # --- Deduction 2: Unique Entity Found for a Value ---
            # If a value in a category can only belong to one primary entity,
            # then that entity MUST have that value (set it positively).
            for category in self.secondary_categories:
                 for value in self.elements[category]:
                      possible_entities = [p for p in self.primary_elements if value in self.grid[p][category]]

                      if len(possible_entities) == 1:
                          unique_entity = possible_entities[0]
                          # If this entity doesn't already have this value confirmed, confirm it.
                          if len(self.grid[unique_entity][category]) > 1:
                              # Use apply_direct_positive for consistency and chain reactions
                              if not self._apply_direct_positive(unique_entity, category, value):
                                   logger.debug(f"CONTRADICTION (Propagate D2): Setting '{value}' for unique entity {unique_entity}/{category} failed.")
                                   return False
                              changed_this_iteration = True # Grid state changed
                      elif not possible_entities:
                           # If a value has no possible entities, it means it was eliminated for everyone.
                           # This is only valid if it *was* assigned previously (e.g. via a positive clue)
                           # Check if it IS assigned to someone already (should have len=1 possibility set)
                           is_assigned = any(len(self.grid[p][category])==1 and list(self.grid[p][category])[0]==value for p in self.primary_elements)
                           if not is_assigned:
                                logger.debug(f"CONTRADICTION (Propagate D2): Value '{value}' ({category}) has no possible entities and is not assigned.")
                                return False # Contradiction: value must belong somewhere

            # --- Deduction 3: Apply Relative Clues ---
            # If we know the primary entity associated with one part of a relative clue,
            # we can apply the consequence to the other part for that entity.
            for clue_data in self.relative_clues_parsed:
                 clue_type, e1, c1, e2, c2 = clue_data

                 # Find primary entities potentially associated with e1
                 possible_p_for_e1 = {p for p in self.primary_elements if e1 in self.grid[p][c1]}
                 # Find primary entities potentially associated with e2
                 possible_p_for_e2 = {p for p in self.primary_elements if e2 in self.grid[p][c2]}

                 if clue_type == "relative_positive":
                      # If only one entity could have e1, it must also have e2
                      if len(possible_p_for_e1) == 1:
                           p_elem = list(possible_p_for_e1)[0]
                           if len(self.grid[p_elem][c2]) > 1: # If not already confirmed
                               if not self._apply_direct_positive(p_elem, c2, e2): return False
                               changed_this_iteration = True
                      # If only one entity could have e2, it must also have e1
                      if len(possible_p_for_e2) == 1:
                           p_elem = list(possible_p_for_e2)[0]
                           if len(self.grid[p_elem][c1]) > 1:
                                if not self._apply_direct_positive(p_elem, c1, e1): return False
                                changed_this_iteration = True

                 elif clue_type == "relative_negative":
                      # If an entity MUST have e1, it CANNOT have e2
                      for p_elem in self.primary_elements:
                           if self.grid[p_elem][c1] == {e1}: # If e1 is confirmed for p_elem
                                if len(self.grid[p_elem][c2]) > 1: # If e2 isn't already excluded
                                     if not self._apply_direct_negative(p_elem, c2, e2): return False
                                     changed_this_iteration = True
                      # If an entity MUST have e2, it CANNOT have e1
                      for p_elem in self.primary_elements:
                          if self.grid[p_elem][c2] == {e2}: # If e2 is confirmed for p_elem
                               if len(self.grid[p_elem][c1]) > 1:
                                    if not self._apply_direct_negative(p_elem, c1, e1): return False
                                    changed_this_iteration = True

            # --- Check for Exit Condition ---
            if not changed_this_iteration:
                logger.debug(f"Constraint propagation finished after {iteration} iterations.")
                return True # Stable state reached

        # If loop finishes due to max_iterations, something might be wrong (or very complex puzzle)
        logger.warning(f"Constraint propagation reached max iterations ({max_iterations}). May not be fully resolved or might be cycling.")
        return True # Return True, but grid might not be fully solved


    def _is_solved(self) -> bool:
        """Checks if the grid is completely and uniquely determined."""
        # Check every cell has exactly one possibility
        for p_elem in self.primary_elements:
            for category in self.secondary_categories:
                if len(self.grid[p_elem][category]) != 1:
                    # logger.debug(f"Grid not solved: {p_elem}/{category} has possibilities {self.grid[p_elem][category]}")
                    return False

        # Check if every value in secondary categories is used exactly once
        for category in self.secondary_categories:
            assigned_values = {list(self.grid[p][category])[0] for p in self.primary_elements}
            if len(assigned_values) != self.grid_size:
                # logger.debug(f"Grid not solved: Category {category} assignment count mismatch ({len(assigned_values)} vs {self.grid_size}). Values: {assigned_values}")
                return False # Not all values used or duplicates found

        logger.debug("Grid state verified as solved.")
        return True

    def get_solution(self) -> Optional[Dict[str, Dict[str, str]]]:
        """Returns the solved grid if verification was successful and unique."""
        if not self._is_solved():
             logger.warning("Attempted to get solution from non-solved grid.")
             return None
        # Convert sets of size 1 to single values
        return {
            p_elem: {
                cat: list(poss_set)[0] for cat, poss_set in data.items()
            }
            for p_elem, data in self.grid.items()
        }

    def verify(self) -> Tuple[bool, Optional[Dict[str, Dict[str, str]]]]:
        """
        Attempts to solve the logic grid using the provided clues.

        Returns:
            Tuple[bool, Optional[Dict]]:
                - bool: True if a unique solution exists, False otherwise.
                - Optional[Dict]: The unique solution grid if found, else None.
        """
        logger.info("Verifying logic grid puzzle...")
        self._initialize_grid() # Reset grid before verification

        if not self._parse_and_apply_clues():
             logger.info("Verification failed: Contradiction found during initial clue parsing.")
             return False, None # Immediate contradiction from clues

        if not self._propagate_constraints():
             logger.info("Verification failed: Contradiction found during constraint propagation.")
             return False, None # Contradiction during solving

        # Check if the grid is fully solved after propagation
        if self._is_solved():
             logger.info("Verification successful: Unique solution found.")
             return True, self.get_solution()
        else:
             logger.info("Verification failed: Grid not fully resolved after propagation (ambiguous or no solution).")
             # Log current grid state for debugging?
             # logger.debug(f"Final grid state:\n{self.grid}")
             return False, None # Not uniquely solved