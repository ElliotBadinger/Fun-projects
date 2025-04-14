from typing import Dict, List, Tuple, Optional, Any
import random
import logging

# Changed imports to absolute
from puzzle.common import HumanScenarioType
from puzzle.puzzle_types import ScenarioPuzzle

logger = logging.getLogger(__name__)

def generate_ordering_puzzle_internal(level: int, puzzle_type: HumanScenarioType,
                                      generator_instance, # Instance of PuzzleGenerator for data access
                                      **kwargs) -> ScenarioPuzzle:
    """Generates an ORDERING scenario puzzle."""
    logger.debug(f"Attempting Ordering Puzzle generation for level {level}")

    settings = generator_instance.SCENARIO_SETTINGS
    if not settings:
        raise ValueError("Cannot generate ordering puzzle: Settings data missing.")

    # Determine puzzle size
    min_elements = 3
    max_elements = 6 # Keep relatively small
    num_elements = random.randint(min(min_elements + level // 3, min_elements + 1),
                                  min(min_elements + level // 2, max_elements))
    num_elements = max(min_elements, num_elements)

    # Use generic items or tasks for ordering
    items_to_order = [f"Action {chr(65+i)}" for i in range(num_elements)] # A, B, C...
    correct_order = list(items_to_order)
    random.shuffle(correct_order)
    solution = {"order": correct_order}
    indices = {item: i for i, item in enumerate(correct_order)} # Map item to its correct index

    # --- Generate Clues ---
    clues = []
    # Use a set to track generated constraints to avoid direct contradictions or trivial redundancies
    # Format: (type, item1, item2/index)
    added_constraints = set()

    # --- Clue Generation Strategy ---
    # Aim for a mix of clue types that constrain the order sufficiently.
    # Start with defining the ends, then add relative clues.

    # 1. First/Last Item Clues (with probability)
    first_item = correct_order[0]
    last_item = correct_order[-1]
    if random.random() < 0.4 + (level * 0.05): # Higher chance with level
        if ("pos", first_item, 0) not in added_constraints:
            clues.append(f"{first_item} happened first.")
            added_constraints.add(("pos", first_item, 0))
            # Add a negative for the last item if first is known
            if ("neg_pos", last_item, 0) not in added_constraints:
                 clues.append(f"{last_item} did not happen first.")
                 added_constraints.add(("neg_pos", last_item, 0))

    if random.random() < 0.4 + (level * 0.05):
        if ("pos", last_item, num_elements - 1) not in added_constraints:
            clues.append(f"{last_item} was the final action.")
            added_constraints.add(("pos", last_item, num_elements - 1))
             # Add a negative for the first item if last is known
            if ("neg_pos", first_item, num_elements - 1) not in added_constraints:
                 clues.append(f"{first_item} was not the final action.")
                 added_constraints.add(("neg_pos", first_item, num_elements - 1))


    # 2. Relative Position Clues (Before/After)
    num_relative_clues_target = max(1, num_elements - 1 + level // 3) # Need enough to link elements
    clues_generated_count = len(clues)
    attempts = 0
    max_clue_attempts = num_relative_clues_target * 5 # More attempts to find non-redundant clues

    while clues_generated_count < num_relative_clues_target and attempts < max_clue_attempts:
         attempts += 1
         # Select two distinct items
         idx1, idx2 = random.sample(range(num_elements), 2)
         item1, item2 = correct_order[idx1], correct_order[idx2]

         # Determine relationship and constraint key
         clue_text = None
         constraint_key = None
         constraint_key_opposite = None

         if idx1 < idx2: # item1 is before item2
              # Is it immediately before?
              if idx2 == idx1 + 1 and random.random() < 0.35: # Less chance for immediate
                   clue_text = f"{item1} occurred immediately before {item2}."
                   constraint_key = ("imm_before", item1, item2)
                   constraint_key_opposite = ("imm_after", item2, item1)
              elif random.random() < 0.6: # Standard before clue
                   clue_text = f"{item1} happened sometime before {item2}."
                   constraint_key = ("before", item1, item2)
                   constraint_key_opposite = ("after", item2, item1)
         else: # item1 is after item2 (idx1 > idx2)
              # Is it immediately after?
              if idx1 == idx2 + 1 and random.random() < 0.35:
                   clue_text = f"{item1} occurred immediately after {item2}."
                   constraint_key = ("imm_after", item1, item2)
                   constraint_key_opposite = ("imm_before", item2, item1)
              elif random.random() < 0.6: # Standard after clue
                   clue_text = f"{item1} happened sometime after {item2}."
                   constraint_key = ("after", item1, item2)
                   constraint_key_opposite = ("before", item2, item1)

         # Check if this constraint or its direct opposite already exists
         if clue_text and constraint_key not in added_constraints and constraint_key_opposite not in added_constraints:
             clues.append(clue_text)
             added_constraints.add(constraint_key)
             clues_generated_count += 1

    # 3. Add Negative Positional Clues if needed
    if clues_generated_count < num_relative_clues_target:
        logger.debug("Adding negative positional clues for Ordering puzzle.")
        neg_attempts = 0
        while clues_generated_count < num_relative_clues_target and neg_attempts < num_elements * 2:
             neg_attempts += 1
             item_idx = random.randrange(num_elements)
             item = correct_order[item_idx]
             wrong_pos_idx = random.choice([i for i in range(num_elements) if i != item_idx])
             position_word = ["first", "second", "third", "fourth", "fifth", "sixth"][wrong_pos_idx % 6] # Use mod for safety

             constraint_key = ("neg_pos", item, wrong_pos_idx)
             if constraint_key not in added_constraints and ("pos", item, wrong_pos_idx) not in added_constraints:
                  clues.append(f"It's known that {item} was not the {position_word} action.")
                  added_constraints.add(constraint_key)
                  clues_generated_count += 1


    if not clues: # Ensure at least one clue exists
        logger.warning("No clues generated for ordering puzzle, adding a basic one.")
        clues.append(f"{correct_order[0]} is one of the actions that occurred.")

    # --- Construct Puzzle Object ---
    items_str = ", ".join(items_to_order)
    goal = f"Determine the correct chronological sequence of the following actions: {items_str}."
    setting = random.choice(settings)
    description = f"A series of {num_elements} actions took place related to {setting['name']}, but the exact order is unclear. Use the information provided to reconstruct the sequence."
    information = clues
    random.shuffle(information)

    logger.info(f"Generated Ordering puzzle with {num_elements} items and {len(clues)} clues.")
    # Note: Verification for this type relies on careful clue generation.
    return ScenarioPuzzle(
        level=level,
        puzzle_type=HumanScenarioType.ORDERING,
        description=description,
        characters=[], # No specific characters needed usually
        setting=setting,
        goal=goal,
        information=information,
        solution=solution,
        is_verified=False # Mark as not formally verified by solver
    )