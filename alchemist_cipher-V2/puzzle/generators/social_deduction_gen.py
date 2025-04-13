from typing import Dict, List, Tuple, Optional, Any
import random
import logging

# Import necessary components from the puzzle package
from ..common import HumanScenarioType
from ..puzzle_types import ScenarioPuzzle

logger = logging.getLogger(__name__)

def generate_social_deduction_puzzle_internal(level: int, puzzle_type: HumanScenarioType,
                                              generator_instance, # Instance of PuzzleGenerator for data access
                                              **kwargs) -> ScenarioPuzzle:
    """Generates a SOCIAL_DEDUCTION scenario puzzle."""
    logger.debug(f"Attempting Social Deduction generation for level {level}")

    # Access data pools from the generator instance
    settings = generator_instance.SCENARIO_SETTINGS
    names = generator_instance.SCENARIO_NAMES
    occupations_pool = generator_instance.SCENARIO_OCCUPATIONS
    traits = generator_instance.SCENARIO_TRAITS
    relationships = generator_instance.SCENARIO_RELATIONSHIPS
    goals = generator_instance.SCENARIO_GOALS

    if not all([settings, names, occupations_pool, traits, relationships, goals]):
         logger.error("Cannot generate social deduction puzzle: Required data pools missing/empty in generator instance.")
         raise ValueError("Missing required data for social deduction puzzle generation.")

    setting = random.choice(settings)
    # Determine number of characters based on level and available names
    max_possible_chars = len(names)
    num_chars = min(3 + level // 3, max_possible_chars)
    num_chars = max(2, num_chars) # Ensure at least 2 characters

    char_names = random.sample(names, num_chars)
    # Assign occupations, reusing if necessary but preferring unique
    occupations = random.sample(occupations_pool, min(num_chars, len(occupations_pool)))
    assigned_occupations = [occupations[i % len(occupations)] for i in range(num_chars)]

    characters = []
    for i, name in enumerate(char_names):
        trait = random.choice(traits)
        occupation = assigned_occupations[i]
        characters.append({"name": name, "trait": trait, "occupation": occupation})

    relationship = random.choice(relationships)

    # Select a goal suitable for social deduction
    possible_goals = [g for g in goals if any(k in g.lower() for k in ["who", "identify", "reason", "source", "motive", "discrepancy", "borrowed", "missing"])]
    if not possible_goals: possible_goals = ["Identify the person responsible."] # Fallback goal
    goal = random.choice(possible_goals)

    # Select the target person and define the solution
    target_person_info = random.choice(characters)
    target_person_name = target_person_info['name']
    solution = {"answer": target_person_name}

    # Create description
    involved_people_str = ", ".join([f"{c['name']} (a {c['occupation']}, described as {c['trait']})" for c in characters])
    setting_details_str = ", ".join(setting.get('details', ["various items"]))
    description = (
        f"Context: A group of {num_chars} {relationship} find themselves involved in a situation "
        f"at/in a {setting['name']} (containing {setting_details_str}). "
        f"An issue needs resolving: {goal}. The individuals involved are: {involved_people_str}."
    )

    # Generate statements from each character
    statements = []
    for char in characters:
        is_target = (char['name'] == target_person_name)
        stmt = _generate_social_deduction_statement(char, target_person_name, characters, is_target, setting)
        statements.append(stmt)

    # Generate a key observation pointing towards the target
    observation = _generate_social_deduction_observation(target_person_name, characters, setting, goal)

    # Generate a red herring distraction
    red_herring = _generate_red_herring(characters, setting)

    # Combine information pieces
    information = [observation] + statements + [f"Also noted: {red_herring}"]
    random.shuffle(information) # Shuffle clues for the player

    # Construct the ScenarioPuzzle object
    logger.info(f"Generated Social Deduction puzzle. Target: {target_person_name}")
    # Note: Verification for this type is complex and currently relies on generation logic quality.
    return ScenarioPuzzle(
        level=level,
        puzzle_type=HumanScenarioType.SOCIAL_DEDUCTION,
        description=description,
        characters=characters,
        setting=setting,
        goal=goal,
        information=information,
        solution=solution,
        is_verified=False # Mark as not formally verified
    )


# --- Social Deduction Helper Methods ---

def _generate_social_deduction_statement(character: Dict, target_person_name: str, all_characters: List[Dict], is_target: bool, setting: Dict) -> str:
    """Generates a statement for a character based on their trait and if they are the target."""
    name = character['name']
    trait = character.get('trait', '_default') # Use trait, fallback to default
    others = [c for c in all_characters if c['name'] != name]
    other_person_info = random.choice(others) if others else None
    other_person_name = other_person_info['name'] if other_person_info else "someone else"

    # Define statement templates based on trait and target status
    if is_target:
        # Statements for the target person (often denials or deflections)
        statements = {
            "Secretive": f"{name} claims, 'I was focused on my own work and didn't notice anything unusual.'",
            "Evasive": f"{name} vaguely mentions being 'around the area' but avoids giving specific details.",
            "Anxious": f"{name} seems flustered, saying, 'I... I don't think I saw anything that could help.'",
            "Forgetful": f"{name} frowns, 'Things were busy. I might have seen something, but the details escape me.'",
            "Argumentative": f"{name} deflects, 'Why is everyone asking me? Maybe ask {other_person_name}?'",
            "Honest": f"{name} states firmly, 'I understand why you might ask, but I assure you, I wasn't involved in that.'",
            "Stubborn": f"{name} simply repeats, 'I have nothing to add.'",
            "Calm": f"{name} calmly explains their actions during the relevant time, offering an alibi.",
            "_default": f"{name} provides a simple denial, stating 'It wasn't me.'"
        }
        return statements.get(trait, statements["_default"])
    else:
        # Statements for non-target characters (observations, accusations, misdirections)
        statements = {
            "Honest": f"{name} states plainly, 'I observed {target_person_name} acting a bit suspiciously near the time it happened.'",
            "Observant": f"{name} mentions, 'I noticed {target_person_name} seemed rushed and put something away quickly.'",
            "Talkative": f"{name} heard from {other_person_name} that {target_person_name} was the last one seen near the {random.choice(setting.get('details',['area'])):.15s}...", # Truncate detail if long
            "Skeptical": f"{name} expresses doubt, 'Are we sure? {target_person_name}'s explanation doesn't quite add up.'",
            "Distracted": f"{name} thinks they saw {other_person_name} nearby, saying 'Maybe check with them? I wasn't paying full attention.'",
            "Quiet": f"{name} hesitates, then suggests, 'Perhaps we should ask {target_person_name} directly about this?'",
            "Helpful": f"{name} tries to reconstruct the timeline, accidentally mentioning {target_person_name} was definitely present.",
            "Nitpicky": f"{name} focuses on a minor inconsistency in {other_person_name}'s statement about the time.",
            "Cooperative": f"{name} offers, 'I saw {target_person_name} heading towards that direction around then.'",
            "Pessimistic": f"{name} sighs, 'Knowing {target_person_name}, it wouldn't surprise me.'", # Subtle accusation
             "_default": f"{name} says they didn't see {target_person_name} directly involved, but did notice {other_person_name} acting nervous." # Point away
        }
        return statements.get(trait, statements["_default"])


def _generate_social_deduction_observation(target_person_name: str, all_characters: List[Dict], setting: Dict, goal: str) -> str:
    """Generates a piece of 'objective' information pointing towards the target."""
    setting_detail = random.choice(setting.get('details', ["a nearby object"]))
    goal_lower = goal.lower()

    # Tailor observation based on common goal keywords
    if any(k in goal_lower for k in ["document", "report", "note", "file"]):
         return f"Observation: A key document related to the issue was last seen on {target_person_name}'s desk."
    if any(k in goal_lower for k in ["email", "message", "log", "system", "computer"]):
         return f"Observation: Access logs show {target_person_name} was the last person to modify the relevant file/system."
    if any(k in goal_lower for k in ["meeting", "schedule", "appointment", "time"]):
         return f"Observation: {target_person_name}'s calendar seems to be the only one with an unexplained gap during the crucial time."
    if any(k in goal_lower for k in ["tool", "item", "stapler", "borrowed", "missing"]):
         return f"Observation: An item identical to the missing one was seen in {target_person_name}'s possession earlier."
    if "discrepancy" in goal_lower or "budget" in goal_lower:
         return f"Observation: The section of the report with the discrepancy was primarily handled by {target_person_name}."

    # Generic fallback observation
    return f"Observation: Regarding the {setting_detail}, several people recall {target_person_name} being the last person physically near it."


def _generate_red_herring(all_characters: List[Dict], setting: Dict) -> str:
    """Generates a distracting, unrelated piece of information."""
    others = [c['name'] for c in all_characters]
    if not others: return "An unrelated discussion about the weather occurred earlier."

    p1 = random.choice(others)
    # Ensure p2 is different if possible
    possible_p2 = [p for p in others if p != p1]
    p2 = random.choice(possible_p2) if possible_p2 else p1 # Use p1 if only one character

    details_options = setting.get('details', ["the nearby window", "a poster", "a plant", "office supplies"])
    options = [
        f"{p1} was complaining about the temperature in the {setting['name']}.",
        f"There was a brief, unrelated discussion about {p2}'s weekend plans.",
        f"Someone mentioned the {random.choice(details_options)} needs attention.",
        f"{p1} and {p2} had a short, unrelated chat near the coffee machine.",
        f"An announcement was made about an upcoming, unrelated company event.",
        f"A phone rang unanswered for a while.",
        f"Someone spilled a drink earlier, causing a minor distraction."
    ]
    return random.choice(options)