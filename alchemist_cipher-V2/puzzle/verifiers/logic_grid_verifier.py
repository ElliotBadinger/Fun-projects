import re
import logging
from typing import Dict, List, Tuple, Optional, Any, Union
from constraint import Problem, AllDifferentConstraint, FunctionConstraint

logger = logging.getLogger(__name__)

class _LogicGridInternalVerifier:
    """
    (Internal Use) Verifies logic grid puzzles using a CSP solver (python-constraint).
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

        # --- Store Puzzle Data ---
        self.categories = list(categories)
        self.elements = {cat: list(elem_list) for cat, elem_list in zip(categories, elements)}
        self.clues = clues
        self.primary_category = self.categories[0]
        self.primary_elements = self.elements[self.primary_category]
        self.secondary_categories = self.categories[1:]

        # --- CSP Solver Initialization ---
        self.problem = Problem()
        self.variables: Dict[str, List[str]] = {} # Stores var names for each category: {cat: [var1, var2...]}
        self.solution: Optional[Dict[str, Any]] = None # Store the single solution if found

        # --- Variable Setup ---
        # Each cell in the logic grid is a variable.
        # Variable name format: f"{primary_elem}__{secondary_cat}"
        # Domain: Elements of the secondary category
        for p_elem in self.primary_elements:
            for s_cat in self.secondary_categories:
                var_name = f"{p_elem}__{s_cat}" # Use double underscore to avoid conflicts
                self.variables.setdefault(s_cat, []).append(var_name)
                self.problem.addVariable(var_name, self.elements[s_cat])

        # --- Core Logic Grid Constraint ---
        # For each secondary category, the values assigned across all primary elements must be unique.
        for s_cat in self.secondary_categories:
            self.problem.addConstraint(AllDifferentConstraint(), self.variables[s_cat])

        logger.debug(f"CSP LogicGridVerifier initialized: {self.grid_size}x{len(self.categories)} grid.")
        # Note: Clue parsing and application happens in verify()

    def _find_category(self, element: str) -> Optional[str]:
        """Finds the category of a single element."""
        for cat, elems in self.elements.items():
            if element in elems:
                return cat
        logger.warning(f"Element '{element}' not found in any category pool during clue parsing.")
        return None

    def _parse_and_apply_clues(self) -> bool:
        """
        Parses clues and adds them as constraints to the CSP problem.
        Returns True (parsing failure doesn't stop solving attempt).
        """
        logger.debug("Parsing clues and adding constraints...")

        # --- Regex Patterns (Adjusted slightly for clarity) ---
        pattern_positive = re.compile(r"^([\w\s]+?)\s+(?:is associated with|is)\s+([\w\s]+?)\.?$", re.IGNORECASE)
        pattern_negative = re.compile(r"^([\w\s]+?)\s+(?:is not associated with|is not)\s+([\w\s]+?)\.?$", re.IGNORECASE)
        pattern_relative_base = r"The\s+[\w\s]+?\s+associated with\s+([\w\s]+?)(?:\s+\(([\w\s]+?)\))?"
        pattern_relative_positive = re.compile(pattern_relative_base + r"\s+is also associated with\s+([\w\s]+?)(?:\s+\(([\w\s]+?)\))?\s*\.?$", re.IGNORECASE)
        pattern_relative_negative = re.compile(pattern_relative_base + r"\s+is NOT associated with\s+([\w\s]+?)(?:\s+\(([\w\s]+?)\))?\s*\.?$", re.IGNORECASE)

        for clue_num, clue in enumerate(self.clues):
            clue = clue.strip()
            if not clue: continue
            constraint_added = False

            # --- Try Positive Clue (Element A IS Element B) ---
            match_pos = pattern_positive.match(clue)
            if match_pos:
                e1_raw, e2_raw = match_pos.groups()
                e1, e2 = e1_raw.strip(), e2_raw.strip()
                cat1 = self._find_category(e1)
                cat2 = self._find_category(e2)

                if cat1 == self.primary_category and cat2 and cat2 in self.secondary_categories:
                    var_name = f"{e1}__{cat2}"
                    if var_name in self.problem._variables:
                        self.problem.addConstraint(lambda val, expected=e2: val == expected, [var_name])
                        constraint_added = True
                        logger.debug(f"  Clue {clue_num+1} (Pos): Added constraint {var_name} == {e2}")
                elif cat2 == self.primary_category and cat1 and cat1 in self.secondary_categories:
                    var_name = f"{e2}__{cat1}"
                    if var_name in self.problem._variables:
                        self.problem.addConstraint(lambda val, expected=e1: val == expected, [var_name])
                        constraint_added = True
                        logger.debug(f"  Clue {clue_num+1} (Pos): Added constraint {var_name} == {e1}")

            # --- Try Negative Clue (Element A IS NOT Element B) ---
            match_neg = pattern_negative.match(clue)
            if not constraint_added and match_neg:
                e1_raw, e2_raw = match_neg.groups()
                e1, e2 = e1_raw.strip(), e2_raw.strip()
                cat1 = self._find_category(e1)
                cat2 = self._find_category(e2)

                if cat1 == self.primary_category and cat2 and cat2 in self.secondary_categories:
                     var_name = f"{e1}__{cat2}"
                     if var_name in self.problem._variables:
                         self.problem.addConstraint(lambda val, unexpected=e2: val != unexpected, [var_name])
                         constraint_added = True
                         logger.debug(f"  Clue {clue_num+1} (Neg): Added constraint {var_name} != {e2}")
                elif cat2 == self.primary_category and cat1 and cat1 in self.secondary_categories:
                     var_name = f"{e2}__{cat1}"
                     if var_name in self.problem._variables:
                         self.problem.addConstraint(lambda val, unexpected=e1: val != unexpected, [var_name])
                         constraint_added = True
                         logger.debug(f"  Clue {clue_num+1} (Neg): Added constraint {var_name} != {e1}")

            # --- Try Relative Positive Clue (Primary element linked to E1(C1) is also linked to E2(C2)) ---
            match_rel_pos = pattern_relative_positive.match(clue)
            if not constraint_added and match_rel_pos:
                e1_raw, c1_raw, e2_raw, c2_raw = match_rel_pos.groups()
                e1, e2 = e1_raw.strip(), e2_raw.strip()
                c1 = c1_raw.strip() if c1_raw else self._find_category(e1)
                c2 = c2_raw.strip() if c2_raw else self._find_category(e2)

                if c1 and c2 and c1 in self.secondary_categories and c2 in self.secondary_categories and c1 != c2 and \
                   e1 in self.elements.get(c1, []) and e2 in self.elements.get(c2, []):

                    vars_c1 = [f"{p_elem}__{c1}" for p_elem in self.primary_elements]
                    vars_c2 = [f"{p_elem}__{c2}" for p_elem in self.primary_elements]

                    def rel_pos_constraint(p_elem_val_c1, p_elem_val_c2, target_val_c1=e1, target_val_c2=e2):
                        return not (p_elem_val_c1 == target_val_c1) or (p_elem_val_c2 == target_val_c2)

                    for i in range(self.grid_size):
                        if vars_c1[i] in self.problem._variables and vars_c2[i] in self.problem._variables:
                            self.problem.addConstraint(FunctionConstraint(rel_pos_constraint), [vars_c1[i], vars_c2[i]])
                        else:
                            logger.error(f"Missing variable in rel_pos_constraint: {vars_c1[i]} or {vars_c2[i]}")

                    constraint_added = True
                    logger.debug(f"  Clue {clue_num+1} (RelPos): Added constraint linking {e1}({c1}) and {e2}({c2})")

            # --- Try Relative Negative Clue (Primary element linked to E1(C1) is NOT linked to E2(C2)) ---
            match_rel_neg = pattern_relative_negative.match(clue)
            if not constraint_added and match_rel_neg:
                e1_raw, c1_raw, e2_raw, c2_raw = match_rel_neg.groups()
                e1, e2 = e1_raw.strip(), e2_raw.strip()
                c1 = c1_raw.strip() if c1_raw else self._find_category(e1)
                c2 = c2_raw.strip() if c2_raw else self._find_category(e2)

                if c1 and c2 and c1 in self.secondary_categories and c2 in self.secondary_categories and c1 != c2 and \
                   e1 in self.elements.get(c1, []) and e2 in self.elements.get(c2, []):

                    vars_c1 = [f"{p_elem}__{c1}" for p_elem in self.primary_elements]
                    vars_c2 = [f"{p_elem}__{c2}" for p_elem in self.primary_elements]

                    def rel_neg_constraint(p_elem_val_c1, p_elem_val_c2, target_val_c1=e1, target_val_c2=e2):
                        return not (p_elem_val_c1 == target_val_c1) or (p_elem_val_c2 != target_val_c2)

                    for i in range(self.grid_size):
                        if vars_c1[i] in self.problem._variables and vars_c2[i] in self.problem._variables:
                            self.problem.addConstraint(FunctionConstraint(rel_neg_constraint), [vars_c1[i], vars_c2[i]])
                        else:
                            logger.error(f"Missing variable in rel_neg_constraint: {vars_c1[i]} or {vars_c2[i]}")

                    constraint_added = True
                    logger.debug(f"  Clue {clue_num+1} (RelNeg): Added anti-link constraint between {e1}({c1}) and {e2}({c2})")

            if not constraint_added and clue:
                 logger.warning(f"Verifier could not parse or apply clue {clue_num+1}: '{clue}'")

        logger.debug("Finished adding constraints based on clues.")
        return True # Indicate parsing finished (even if some clues failed)

    def _is_solved(self, solutions: List[Dict[str, Any]]) -> bool:
        """Checks if the CSP solver found exactly one solution."""
        return len(solutions) == 1

    def _format_solution(self, solution_dict: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        """Formats the CSP solution into the desired nested dictionary structure."""
        formatted: Dict[str, Dict[str, str]] = {p_elem: {} for p_elem in self.primary_elements}
        for var_name, value in solution_dict.items():
            try:
                p_elem, s_cat = var_name.split("__", 1) # Split only on first double underscore
                if p_elem in formatted:
                    formatted[p_elem][s_cat] = value
                else:
                    logger.error(f"Error formatting solution: Primary element '{p_elem}' from variable '{var_name}' not recognized.")
            except ValueError:
                logger.error(f"Error splitting variable name during formatting: '{var_name}'")
        return formatted

    def verify(self) -> Tuple[bool, Optional[Dict[str, Dict[str, str]]]]:
        """
        Attempts to solve the logic grid using the CSP problem defined from clues.

        Returns:
            Tuple[bool, Optional[Dict]]:
                - bool: True if a unique solution exists, False otherwise.
                - Optional[Dict]: The unique solution grid if found, else None.
        """
        logger.info("Verifying logic grid puzzle using CSP solver...")

        # Parse clues and add constraints to the initialized problem
        self._parse_and_apply_clues()

        # Find solutions using the CSP solver
        try:
            solutions = self.problem.getSolutions()
        except Exception as e:
            logger.error(f"CSP solver encountered an error: {e}", exc_info=True)
            return False, None # Indicate failure due to solver error

        num_solutions = len(solutions)
        logger.info(f"CSP solver found {num_solutions} solution(s).")

        is_unique = self._is_solved(solutions)

        if is_unique:
            self.solution = solutions[0] # Store the unique solution raw
            formatted_solution = self._format_solution(self.solution)
            logger.info("Verification successful: Unique solution found.")
            return True, formatted_solution
        elif num_solutions == 0:
            logger.info("Verification failed: No solution found (contradiction).")
            return False, None
        else: # Multiple solutions
            logger.info(f"Verification failed: Multiple ({num_solutions}) solutions found (ambiguous).")
            # Optionally log first few solutions if needed for debugging
            # logger.debug(f"Example solutions: {solutions[:2]}")\
            return False, None