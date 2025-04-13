from typing import Dict, List, Tuple, Optional, Any
import random
import logging
import itertools # For combinations in clue generation

# Import necessary components from the puzzle package
from ..common import HumanScenarioType
from ..puzzle_types import ScenarioPuzzle
# Import the internal verifier to check solvability
from ..verifiers.logic_grid_verifier import _LogicGridInternalVerifier

logger = logging.getLogger(__name__)

def generate_logic_grid_puzzle_internal(level: int, puzzle_type: HumanScenarioType,
                                        generator_instance, # Instance of PuzzleGenerator for data access
                                        **kwargs) -> ScenarioPuzzle:
    """Generates a classic logic grid puzzle, returned as a ScenarioPuzzle."""
    logger.debug(f"Attempting Logic Grid generation for level {level}")

    themes_data = generator_instance.LOGIC_GRID_THEMES
    if not themes_data:
        raise ValueError("Logic grid themes data not loaded or empty.")

    # --- Theme and Size Selection ---
    # Select theme based on level? For now, random.
    theme_name = random.choice(list(themes_data.keys()))
    theme = themes_data[theme_name]
    categories = list(theme["categories"]) # Ensure it's a mutable list
    element_pool_lists = [list(pool) for pool in theme["elements"]] # Ensure mutable lists

    if not categories or not element_pool_lists or len(categories) != len(element_pool_lists):
         raise ValueError(f"Invalid theme format for '{theme_name}': Mismatched categories/elements.")
    if len(set(len(p) for p in element_pool_lists)) != 1:
         raise ValueError(f"Inconsistent element pool sizes for theme '{theme_name}'.")

    grid_size = len(element_pool_lists[0])
    num_categories = len(categories)
    if grid_size < 2 or num_categories < 2:
         raise ValueError(f"Logic grid size/categories must be at least 2 for theme '{theme_name}'.")
    logger.debug(f"Selected theme: {theme_name}, Size: {grid_size}x{num_categories}")

    # --- Create the Ground Truth Solution Grid ---
    # Shuffle categories and element assignments for variety
    primary_category_index = 0 # Assume first category is the primary one (rows)
    other_category_indices = list(range(1, num_categories))
    random.shuffle(other_category_indices) # Shuffle order of other categories

    # Create mapping based on shuffled indices
    primary_elements = element_pool_lists[primary_category_index]
    shuffled_elements_for_mapping = [list(element_pool_lists[idx]) for idx in other_category_indices]
    for elem_list in shuffled_elements_for_mapping:
        random.shuffle(elem_list) # Shuffle elements within each secondary category

    solution_grid: Dict[str, Dict[str, str]] = {}
    for i in range(grid_size):
        entity_name = primary_elements[i]
        solution_grid[entity_name] = {}
        for list_idx, cat_idx in enumerate(other_category_indices):
            category_name = categories[cat_idx]
            element_value = shuffled_elements_for_mapping[list_idx][i]
            solution_grid[entity_name][category_name] = element_value
    logger.debug(f"Generated ground truth solution grid: {solution_grid}")

    # --- Generate Clues (Crucial Step) ---
    # We need enough clues to make the puzzle uniquely solvable.
    # This ideally involves using a solver/verifier iteratively.

    max_clue_generation_attempts = 50 # Max attempts to find a good clue set
    final_clues = None
    generated_solution = None

    for clue_attempt in range(max_clue_generation_attempts):
        potential_clues = _generate_potential_logic_grid_clues(
            categories, element_pool_lists, solution_grid, level, primary_elements
        )
        # Select a subset of clues - crucial for difficulty and solvability
        # Start with more clues, then potentially reduce if needed
        num_clues_target = int(grid_size * num_categories * 0.6 + level + 1) # Heuristic target
        num_clues_target = min(len(potential_clues), num_clues_target) # Can't exceed available
        num_clues_target = max(num_clues_target, grid_size * (num_categories - 1)) # Ensure a minimum baseline?

        current_clue_set = random.sample(potential_clues, k=num_clues_target)

        # --- Verify the clue set ---
        try:
            verifier = _LogicGridInternalVerifier(
                categories=categories,
                elements=element_pool_lists, # Pass original pools
                clues=current_clue_set
            )
            is_unique, verified_solution_dict = verifier.verify()

            if is_unique and verified_solution_dict == solution_grid:
                logger.info(f"Found verifiable clue set (Attempt {clue_attempt+1}) with {len(current_clue_set)} clues.")
                final_clues = current_clue_set
                generated_solution = solution_grid # Confirm solution matches intended
                break # Success!
            else:
                 logger.debug(f"Clue set attempt {clue_attempt+1} failed verification (Unique: {is_unique}, Match: {verified_solution_dict == solution_grid}).")

        except Exception as e:
            logger.error(f"Error during logic grid verification (Attempt {clue_attempt+1}): {e}", exc_info=True)
            # Continue trying with a different clue set

    if final_clues is None or generated_solution is None:
        logger.error(f"Failed to generate a verifiable logic grid clue set after {max_clue_generation_attempts} attempts.")
        raise ValueError("Could not generate a verifiable logic grid puzzle.")

    # --- Construct Puzzle Object ---
    primary_cat_name = categories[primary_category_index]
    secondary_cat_names = [categories[idx] for idx in other_category_indices]
    joined_secondary_categories = ", ".join(secondary_cat_names)

    # Create description dynamically
    description = f"Logic Puzzle ({theme_name} - {grid_size}x{len(secondary_cat_names)+1}): Deduce the correct pairings using the clues.\n"
    description += f"\nCategories Involved:\n"
    description += f"- {primary_cat_name} (e.g., {primary_elements[0]}): {', '.join(primary_elements)}\n"
    for i, cat_idx in enumerate(other_category_indices):
         cat_name = categories[cat_idx]
         elements_str = ", ".join(element_pool_lists[cat_idx])
         description += f"- {cat_name} (e.g., {element_pool_lists[cat_idx][0]}): {elements_str}\n"

    # Structure characters/setting based on puzzle elements
    puzzle_characters = [{"name": name, "details": f"{primary_cat_name}"} for name in primary_elements]
    puzzle_setting = {"name": f"Logic Grid Context: {theme_name}", "details": secondary_cat_names}
    puzzle_goal = f"Complete the grid to show how each {primary_cat_name} is uniquely associated with elements from the other categories ({joined_secondary_categories})."

    # The final structure expected by the ScenarioPuzzle class
    puzzle_elements_dict = {cat: elem_list for cat, elem_list in zip(categories, element_pool_lists)}
    puzzle_solution_dict = {"grid": generated_solution}

    return ScenarioPuzzle(
        level=level, puzzle_type=HumanScenarioType.LOGIC_GRID, description=description,
        characters=puzzle_characters, setting=puzzle_setting, goal=puzzle_goal,
        information=final_clues, solution=puzzle_solution_dict,
        elements=puzzle_elements_dict, # Pass elements for UI reconstruction
        is_verified=True # Mark as verified by the internal process
    )


def _generate_potential_logic_grid_clues(categories: List[str], element_lists: List[List[str]],
                                         solution: Dict[str, Dict[str, str]], level: int,
                                         primary_elements: List[str]) -> List[str]:
    """Generates a pool of possible clues based on the solution grid."""
    potential_clues = []
    primary_cat_name = categories[0]
    other_categories = categories[1:]
    grid_size = len(primary_elements)

    # 1. Direct Positive Clues
    for entity, assignments in solution.items():
        for category, value in assignments.items():
            potential_clues.append(f"{entity} is associated with {value}.") # Simple form

    # 2. Direct Negative Clues (more numerous)
    all_elements_flat = {elem for sublist in element_lists for elem in sublist}
    elements_by_cat = {cat: set(elems) for cat, elems in zip(categories, element_lists)}

    for entity, assignments in solution.items():
         # Negative associations within the same category
         for category, correct_value in assignments.items():
             for possible_value in elements_by_cat[category]:
                 if possible_value != correct_value:
                     potential_clues.append(f"{entity} is not associated with {possible_value}.")
         # Negative associations across different entities for the same value
         for category, correct_value in assignments.items():
              for other_entity in primary_elements:
                  if other_entity != entity:
                      potential_clues.append(f"{other_entity} is not associated with {correct_value}.")

    # 3. Relative Clues (linking two secondary categories for a primary entity)
    if len(other_categories) >= 2:
         for entity, assignments in solution.items():
              # Positive relative
              cat_pairs = list(itertools.combinations(other_categories, 2))
              for cat1, cat2 in cat_pairs:
                   val1, val2 = assignments[cat1], assignments[cat2]
                   potential_clues.append(f"The {primary_cat_name} associated with {val1} (category {cat1}) is also associated with {val2} (category {cat2}).")

              # Negative relative (more complex to generate meaningfully)
              for cat1, cat2 in cat_pairs:
                   val1 = assignments[cat1]
                   correct_val2 = assignments[cat2]
                   incorrect_val2_options = [v for v in elements_by_cat[cat2] if v != correct_val2]
                   if incorrect_val2_options:
                        incorrect_val2 = random.choice(incorrect_val2_options)
                        potential_clues.append(f"The {primary_cat_name} associated with {val1} ({cat1}) is NOT associated with {incorrect_val2} ({cat2}).")

    # 4. More Complex Clues (placeholder for future expansion)
    # e.g., "Either A is X or B is Y", "C is Z if and only if D is W"

    random.shuffle(potential_clues)
    return potential_clues