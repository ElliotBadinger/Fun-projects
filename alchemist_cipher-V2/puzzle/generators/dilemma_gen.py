from typing import Dict, List, Tuple, Optional, Any
import random
import logging

# Import necessary components from the puzzle package
from ..common import HumanScenarioType
from ..puzzle_types import ScenarioPuzzle

logger = logging.getLogger(__name__)

def generate_dilemma_puzzle_internal(level: int, puzzle_type: HumanScenarioType,
                                     generator_instance, # Instance of PuzzleGenerator for data access
                                     **kwargs) -> ScenarioPuzzle:
    """Generates a DILEMMA scenario puzzle."""
    logger.debug(f"Attempting Dilemma generation for level {level}")

    dilemma_data = generator_instance.DILEMMA_SCENARIOS
    settings = generator_instance.SCENARIO_SETTINGS # Get settings for context

    if not dilemma_data:
         raise ValueError("Cannot generate dilemma puzzle: Dilemma scenarios data not loaded or empty.")
    if not settings:
         raise ValueError("Cannot generate dilemma puzzle: Settings data not loaded or empty.")

    # Select a dilemma scenario (potentially filter by level/complexity later)
    chosen_dilemma = random.choice(dilemma_data)

    # Validate chosen dilemma structure
    required_keys = ["id", "desc", "options", "solution", "info"]
    if not all(key in chosen_dilemma for key in required_keys):
        logger.error(f"Invalid dilemma format: Missing keys in '{chosen_dilemma.get('id', 'UNKNOWN')}'. Found: {list(chosen_dilemma.keys())}")
        raise ValueError(f"Invalid dilemma data structure for id '{chosen_dilemma.get('id', 'UNKNOWN')}'.")
    if not isinstance(chosen_dilemma["options"], list) or len(chosen_dilemma["options"]) < 2:
        raise ValueError(f"Dilemma '{chosen_dilemma['id']}' needs at least 2 options.")
    if not isinstance(chosen_dilemma["info"], list):
         raise ValueError(f"Dilemma '{chosen_dilemma['id']}' info must be a list.")

    # Prepare puzzle components
    solution = {"choice": chosen_dilemma["solution"]}
    goal = "Analyze the ethical or practical dilemma presented and choose the most appropriate course of action from the given options."
    description = chosen_dilemma["desc"]

    # Combine info and add a generic hint
    information = list(chosen_dilemma["info"]) # Make a copy
    hint = "Consider the potential consequences of each option, relevant ethical principles (fairness, honesty, responsibility), and the impact on relationships or objectives."
    information.append(f"Hint: {hint}")
    random.shuffle(information)

    # Select a relevant setting (optional, could be generic)
    setting = random.choice(settings)

    logger.info(f"Generated Dilemma puzzle: {chosen_dilemma['id']}")
    return ScenarioPuzzle(
        level=level,
        puzzle_type=HumanScenarioType.DILEMMA,
        description=description,
        characters=[], # Dilemmas often don't focus on specific character deduction
        setting=setting, # Use a random setting for context
        goal=goal,
        information=information,
        solution=solution,
        rules=None, # No separate rules list
        options=chosen_dilemma["options"], # Pass options to the puzzle object
        is_verified=True # Dilemmas are typically 'solved' by choosing, not strict verification
    )