from typing import Dict, List, Tuple, Optional, Any
import random
import logging
import itertools

# Import necessary components from the puzzle package
from ..common import HumanScenarioType
from ..puzzle_types import ScenarioPuzzle

logger = logging.getLogger(__name__)

def generate_relationship_map_puzzle_internal(level: int, puzzle_type: HumanScenarioType,
                                              generator_instance, # Instance of PuzzleGenerator for data access
                                              **kwargs) -> ScenarioPuzzle:
    """Generates a RELATIONSHIP_MAP scenario puzzle."""
    logger.debug(f"Attempting Relationship Map generation for level {level}")

    # Access data pools
    settings = generator_instance.SCENARIO_SETTINGS
    names = generator_instance.SCENARIO_NAMES
    occupations_pool = generator_instance.SCENARIO_OCCUPATIONS
    traits = generator_instance.SCENARIO_TRAITS
    relationships = generator_instance.SCENARIO_RELATIONSHIPS

    if not all([settings, names, occupations_pool, traits, relationships]):
         logger.error("Cannot generate relationship map puzzle: Required data pools missing/empty.")
         raise ValueError("Missing required data for relationship map puzzle generation.")

    # Determine puzzle size
    setting = random.choice(settings)
    # Ensure even number of characters, scaling with level
    min_chars = 4
    max_chars = min(len(names), 8) # Cap maximum size
    num_chars = min(min_chars + (level // 2) * 2, max_chars)
    num_chars = max(min_chars, num_chars if num_chars % 2 == 0 else num_chars - 1) # Ensure even, min 4

    if num_chars > len(names):
        logger.error(f"Not enough unique names ({len(names)}) for {num_chars} characters.")
        raise ValueError(f"Not enough unique names for {num_chars} characters.")

    # Select characters
    char_names = random.sample(names, num_chars)
    occupations = random.sample(occupations_pool, min(num_chars, len(occupations_pool)))
    assigned_occupations = [occupations[i % len(occupations)] for i in range(num_chars)]
    characters = []
    for i, name in enumerate(char_names):
        trait = random.choice(traits)
        occupation = assigned_occupations[i]
        characters.append({"name": name, "trait": trait, "occupation": occupation})

    relationship_context = random.choice(relationships) # e.g., "Colleagues", "Team Members"

    # Define goal
    goal = random.choice([
        f"Determine who is partnered with whom among these {num_chars} {relationship_context}.",
        f"Map out the direct reporting pairs (1-to-1) within this group.",
        f"Identify the mentor for each trainee (1-to-1 pairing)."
    ])
    num_pairs = num_chars // 2

    # Create the solution mapping
    shuffled_chars = list(characters)
    random.shuffle(shuffled_chars)
    solution_map = {}
    for i in range(num_pairs):
        char1_info, char2_info = shuffled_chars[2*i], shuffled_chars[2*i + 1]
        char1_name, char2_name = char1_info['name'], char2_info['name']
        # Store both directions for easier checking later, though only one needed for solution structure usually
        solution_map[char1_name] = char2_name
        solution_map[char2_name] = char1_name

    solution = {"map": solution_map} # The final solution structure

    # Create description
    involved_people_str = ", ".join([f"{c['name']} ({c['occupation']})" for c in characters])
    setting_details_str = ", ".join(setting.get('details',[]))
    description = (
        f"Context: A group of {num_chars} {relationship_context} are involved in a collaborative task "
        f"at/in {setting['name']} (Details: {setting_details_str}). Goal: {goal}. "
        f"The individuals are: {involved_people_str}."
    )

    # --- Generate Clues ---
    clues = []
    potential_clue_pairs = list(itertools.combinations(characters, 2))
    random.shuffle(potential_clue_pairs)
    num_clues_target = max(num_chars, int(num_pairs * 1.5) + level // 2) # Target more clues than pairs
    clues_generated_count = 0
    added_clue_pairs = set() # Track pairs (positive/negative) to avoid direct redundancy

    clue_generation_attempts = 0
    max_clue_generation_attempts = len(potential_clue_pairs) * 3 # Try combinations multiple times

    while clues_generated_count < num_clues_target and clue_generation_attempts < max_clue_generation_attempts:
        clue_generation_attempts += 1
        if not potential_clue_pairs: break # Exhausted all pairs

        # Pick a pair to generate a clue about
        char_a_info, char_b_info = random.choice(potential_clue_pairs)
        char_a_name, char_b_name = char_a_info['name'], char_b_info['name']
        pair_key = frozenset({char_a_name, char_b_name})

        # Check if this pair is the actual solution pair
        are_paired = solution_map.get(char_a_name) == char_b_name

        clue_text = None
        clue_type = None # 'positive' or 'negative'

        # Try generating a positive clue if they ARE paired
        if are_paired and random.random() < 0.6: # Higher chance for positive clues for actual pairs
            clue_text = _generate_positive_relationship_clue(char_a_info, char_b_info)
            clue_type = 'positive'

        # Try generating a negative clue if they are NOT paired (or sometimes even if they are, as misdirection)
        elif not are_paired and random.random() < 0.6: # Chance for negative clues
             clue_text = _generate_negative_relationship_clue(char_a_info, char_b_info, characters, solution_map)
             clue_type = 'negative'

        # If a clue was generated, check if it's redundant for this specific pair
        if clue_text:
            if pair_key not in added_clue_pairs:
                 clues.append(clue_text)
                 added_clue_pairs.add(pair_key) # Mark this pair as having a clue generated
                 clues_generated_count += 1
            # else: logger.debug(f"Skipping redundant clue for pair: {pair_key}")


    # Ensure enough clues (rough heuristic) - add generic if needed
    if clues_generated_count < num_pairs + 1: # Need at least N+1 clues?
         needed = num_pairs + 1 - clues_generated_count
         logger.warning(f"Generated only {clues_generated_count} specific clues, adding {needed} generic ones.")
         for _ in range(needed):
              p1_info, p2_info = random.sample(characters, 2)
              clues.append(f"The relationship between {p1_info['name']} and {p2_info['name']} requires careful consideration.")


    information = clues
    random.shuffle(information)

    logger.info(f"Generated Relationship Map puzzle with {num_chars} characters and {len(clues)} clues.")
    # Note: Verification for this type relies on clue generation quality.
    return ScenarioPuzzle(
        level=level,
        puzzle_type=HumanScenarioType.RELATIONSHIP_MAP,
        description=description,
        characters=characters,
        setting=setting,
        goal=goal,
        information=information,
        solution=solution,
        is_verified=False # Mark as not formally verified
    )

def _generate_positive_relationship_clue(char_a_info, char_b_info) -> Optional[str]:
    """Generates a clue suggesting two people ARE paired."""
    a_name, b_name = char_a_info['name'], char_b_info['name']
    a_trait, b_trait = char_a_info['trait'], char_b_info['trait']

    options = [
        f"{a_name} was seen working closely with {b_name} on the main task.",
        f"Notes indicate frequent collaboration between {a_name} and {b_name}.",
        f"Both {a_name} and {b_name} submitted a joint component of the project.",
        f"{a_name} mentioned relying on {b_name}'s input.",
        f"If {a_trait} == 'Organized', '{a_name} scheduled several meetings specifically with {b_name}'.",
        f"If {b_trait} == 'Helpful', '{b_name} spent significant time assisting {a_name}'.",
        f"If {a_trait} == 'Talkative', '{a_name} often discusses work matters with {b_name}'.",
    ]
    # Filter out options based on traits (simple conditional logic)
    valid_options = [opt for opt in options if not opt.startswith("If ") or eval(opt[3:opt.find("',")])]
    # Clean up the chosen option by removing the "If ..., '" prefix/suffix
    chosen_option = random.choice(valid_options)
    if chosen_option.startswith("If "):
        chosen_option = chosen_option[chosen_option.find("', '")+4:-2]

    return chosen_option if chosen_option else None


def _generate_negative_relationship_clue(char_a_info, char_b_info, all_chars, solution_map) -> Optional[str]:
    """Generates a clue suggesting two people are NOT paired."""
    a_name, b_name = char_a_info['name'], char_b_info['name']
    a_trait, b_trait = char_a_info['trait'], char_b_info['trait']

    # Find the actual partners if needed for more complex clues
    a_partner = solution_map.get(a_name)
    b_partner = solution_map.get(b_name)

    options = [
        f"{a_name} explicitly stated they work in a different sub-group than {b_name}.",
        f"Schedules show {a_name} and {b_name} have conflicting meeting times.",
        f"{a_name} is known to be paired with someone else.", # Vague
        f"If {a_trait} == 'Independent', '{a_name} mentioned preferring to handle their tasks separately from {b_name}'.",
        f"If {b_trait} == 'Busy', '{b_name} indicated having no time to coordinate with {a_name}'.",
        f"If {a_partner} and random.random() < 0.5, '{a_name} works directly with {a_partner}, not {b_name}'.", # More direct negative using solution
        f"If {b_partner} and random.random() < 0.5, '{b_name} is partnered with {b_partner}, ruling out {a_name}'.", # More direct negative
    ]
    # Filter and clean up options
    valid_options = []
    for opt in options:
        is_valid = True
        if opt.startswith("If "):
            condition_str = opt[3:opt.find("',")]
            try:
                 # Be careful with eval - ensure condition_str is safe or use safer evaluation
                 if not eval(condition_str):
                     is_valid = False
            except: is_valid = False # Condition failed
        if is_valid: valid_options.append(opt)

    if not valid_options: return None

    chosen_option = random.choice(valid_options)
    if chosen_option.startswith("If "):
        chosen_option = chosen_option[chosen_option.find("', '")+4:-2]

    return chosen_option if chosen_option else None