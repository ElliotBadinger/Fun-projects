from typing import Dict, List, Tuple, Optional, Any
import random
import logging

# Changed imports to absolute
from puzzle.common import HumanScenarioType
from puzzle.puzzle_types import ScenarioPuzzle

logger = logging.getLogger(__name__)

def generate_common_sense_gap_puzzle_internal(level: int, puzzle_type: HumanScenarioType,
                                              generator_instance, # Instance of PuzzleGenerator for data access
                                              **kwargs) -> ScenarioPuzzle:
    """Generates a COMMON_SENSE_GAP scenario puzzle."""
    logger.debug(f"Attempting Common Sense Gap generation for level {level}")

    # Access data pools
    common_sense_data = generator_instance.COMMON_SENSE_ITEMS
    settings = generator_instance.SCENARIO_SETTINGS
    names = generator_instance.SCENARIO_NAMES
    traits = generator_instance.SCENARIO_TRAITS

    if not all([common_sense_data, settings, names, traits]):
         logger.error("Cannot generate common sense puzzle: Required data pools missing/empty.")
         raise ValueError("Missing required data for common sense puzzle generation.")

    # Select scenario components
    setting = random.choice(settings)
    char_name = random.choice(names)
    characters = [{"name": char_name, "trait": random.choice(traits)}]

    # Select a common sense scenario
    scenario_key = random.choice(list(common_sense_data.keys()))
    scenario_details = common_sense_data[scenario_key]
    if not isinstance(scenario_details, dict) or "present" not in scenario_details or "missing" not in scenario_details:
         logger.error(f"Invalid data format for common sense scenario: {scenario_key}")
         raise ValueError(f"Invalid data format for common sense scenario: {scenario_key}")
    if not scenario_details["present"] or not scenario_details["missing"]:
         logger.error(f"Empty 'present' or 'missing' list for common sense scenario: {scenario_key}")
         raise ValueError(f"Missing items for common sense scenario: {scenario_key}")


    # Determine items present and the single missing item
    k_present = random.randint(max(1, len(scenario_details["present"]) // 2), len(scenario_details["present"]))
    items_present = random.sample(scenario_details["present"], k=k_present)
    missing_item = random.choice(scenario_details["missing"])
    solution = {"answer": missing_item}

    # Define goal and description
    goal = f"Identify the essential missing item/tool required by {char_name} to successfully '{scenario_key}'."
    present_items_str = ", ".join(items_present) if items_present else "nothing yet"
    description = (
        f"Task Context: In a {setting['name']}, {char_name} ({characters[0]['trait']}) is preparing to "
        f"'{scenario_key}'. They have gathered the following item(s): {present_items_str}."
    )

    # Generate supporting information/clues
    information = []
    information.append("They seem ready to proceed, but pause, realizing something essential is not there.")

    # Add distractor item if available
    distractor_items = [i for i in scenario_details["present"] if i not in items_present]
    if distractor_items:
        information.append(f"Nearby, not part of the gathered items, one can also see a {random.choice(distractor_items)}.")

    # Add setting detail
    if setting.get('details'):
        information.append(f"The {setting['name']} environment includes: {random.choice(setting['details'])}.")

    # Add hint based on missing item purpose/category
    hint = _get_common_sense_hint(missing_item)
    information.append(f"Hint: {hint}")
    random.shuffle(information)

    logger.info(f"Generated Common Sense Gap puzzle. Task: '{scenario_key}', Missing: '{missing_item}'")
    return ScenarioPuzzle(
        level=level,
        puzzle_type=HumanScenarioType.COMMON_SENSE_GAP,
        description=description,
        characters=characters,
        setting=setting,
        goal=goal,
        information=information,
        solution=solution,
        is_verified=False # Verification is implicit in the known missing item
    )

def _get_common_sense_hint(missing_item: str) -> str:
    """Provides a simple hint based on the type or purpose of the missing item."""
    hints = {
        # Protection
        "oven mitts": "Protection from heat is needed.", "rain boots": "Protection from weather is needed.", "umbrella": "Protection from weather is needed.", "insect repellent": "Protection from pests is needed.",
        # Container/Holder
        "baking pan": "A suitable container is required for the process.", "envelope": "A container is required for sending.", "pot": "A vessel is needed to hold the contents.", "water bottle": "A container for hydration is needed.", "glass": "A drinking vessel is missing.", "box": "A structure to contain the item is needed.",
        # Tool/Utensil
        "whisk": "A tool for mixing or blending is needed.", "tape": "An adhesive tool is required.", "scissors": "A cutting tool is needed.", "webcam": "A tool for visual input is required.", "microphone": "A tool for audio input is required.", "flashlight": "A light source is needed.", "spoon": "An eating utensil is missing.", "fork": "An eating utensil is missing.", "knife": "A utensil for cutting or spreading is needed.", "pen": "A writing instrument is required.",
        # Consumable/Medium
        "stamp": "A consumable for postage is needed.", "tea bag": "The core ingredient is missing.", "soil": "The growing medium is needed.", "coffee grounds": "The core ingredient is needed.", "water": "A vital liquid is needed.", "milk": "A common liquid addition is missing.", "sugar": "A common sweetener is missing.", "flour": "A key dry ingredient is missing.", "eggs": "A common binding/leavening ingredient is missing.", "seed": "The item to be grown is missing.",
        # Information/Access
        "address": "Crucial delivery information is missing.", "meeting link": "Crucial access information is missing.",
        # Covering/Cleaning
        "wrapping paper": "A decorative covering is required.", "napkin": "Something for cleaning up is needed.", "filter": "A specific medium to separate components is required.",
        # Default/Generic
        "_default": "Think about the very next logical step in the process and what is physically required for it."
    }
    # Find the first key that matches (or part of) the missing item
    for key, hint_text in hints.items():
        if key in missing_item.lower():
            return hint_text
    return hints["_default"] # Fallback hint