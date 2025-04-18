from typing import Dict, List, Tuple, Optional, Any
import random
import logging

# Changed imports to relative
from ..common import HumanScenarioType
from ..puzzle_types import ScenarioPuzzle
from ..solvers.scheduling_solver import _SchedulingSolver

logger = logging.getLogger(__name__)

def generate_scheduling_puzzle_internal(level: int, puzzle_type: HumanScenarioType,
                                        generator_instance, # Instance of PuzzleGenerator for data access
                                        **kwargs) -> ScenarioPuzzle:
    """Generates a SCHEDULING scenario puzzle."""
    logger.debug(f"Attempting Scheduling Puzzle generation for level {level}")

    # Access data pools
    names = generator_instance.SCENARIO_NAMES
    traits = generator_instance.SCENARIO_TRAITS
    if not names or not traits:
         raise ValueError("Cannot generate scheduling puzzle: Names/Traits data missing.")

    # Determine puzzle size (keep relatively small)
    min_people, max_people = 2, 4
    min_slots, max_slots = 3, 5
    num_people = random.randint(min(min_people + level // 3, min_people + 1),
                                min(min_people + level // 2, max_people))
    num_slots = random.randint(min(min_slots + level // 3, min_slots + 1),
                               min(min_slots + level // 2, max_slots))

    if num_people > len(names):
        raise ValueError(f"Not enough names for {num_people} people.")

    # Select people and time slots
    people = random.sample(names, k=num_people)
    start_hour = random.choice([8, 9, 10, 13, 14]) # Mix of AM/PM start times
    time_slots = []
    for i in range(num_slots):
        hour = start_hour + i
        am_pm = "AM" if hour < 12 else "PM"
        display_hour = hour % 12
        if display_hour == 0: display_hour = 12 # Handle 12 AM/PM correctly
        time_slots.append(f"{display_hour}:00 {am_pm}")

    # --- Generate Constraints and Find a Solution ---
    max_solver_attempts = 50 # Max attempts to find a solvable constraint set
    final_solution_schedule = None
    final_constraints = []
    final_constraint_texts = []

    for attempt in range(max_solver_attempts):
        constraints_logic = []
        constraint_texts_temp = []
        num_constraints_target = int(num_people * num_slots * 0.4 + level + 1) # Target density + level bonus
        num_constraints_target = max(num_constraints_target, num_people + 1) # Ensure minimum constraints

        # Generate potential constraints (logic tuples)
        potential_constraints_logic = _generate_scheduling_constraints_logic(people, time_slots, num_constraints_target)

        # Use the scheduling solver to find *one* valid schedule for these constraints
        solver = _SchedulingSolver(people, time_slots, potential_constraints_logic)
        solution_assignment = solver.find_solution() # Returns assignment dict {person: slot} or None

        if solution_assignment:
            # Convert assignment to the final schedule format {person: {slot: status}}
            valid_schedule = {p: {s: "Available" for s in time_slots} for p in people}
            for person, slot in solution_assignment.items():
                if slot in valid_schedule[person]:
                    valid_schedule[person][slot] = "Booked"
                else:
                    logger.error(f"Solver returned invalid slot '{slot}' for person '{person}'.")
                    valid_schedule = None # Mark as invalid
                    break
            if not valid_schedule: 
                continue # Try again if solver result was bad

            # TODO: Ideally, check for *uniqueness* here. This requires a more complex solver
            # that finds *all* solutions. For now, we accept the first solution found.
            logger.info(f"Found a valid schedule (Attempt {attempt+1}). Uniqueness not checked.")
            final_solution_schedule = valid_schedule
            final_constraints = potential_constraints_logic # Store the logic constraints
            # Convert logic constraints to text for the user
            final_constraint_texts = _convert_constraints_to_text(final_constraints, people, time_slots)
            break # Found a solvable set

    if not final_solution_schedule:
        logger.error(f"Failed to generate a solvable scheduling puzzle after {max_solver_attempts} attempts.")
        raise ValueError("Failed to generate a scheduling puzzle with a valid solution.")

    # --- Construct Puzzle Object ---
    goal = f"Determine the final schedule for {', '.join(people)} across these time slots: {', '.join(time_slots)}. Mark each slot as 'Available' or 'Booked'."
    description = f"Coordinate the schedules for {len(people)} individuals based on the provided constraints and information."
    characters_list = [{"name": p, "trait": random.choice(traits)} for p in people]
    setting_dict = {"name": "Appointment Scheduling System", "details": time_slots}
    information = final_constraint_texts
    random.shuffle(information)
    # Add a generic hint if needed
    information.append("Hint: Use a grid or table to keep track of possibilities and eliminate options based on the constraints.")

    logger.info(f"Generated Scheduling puzzle with {num_people} people, {num_slots} slots, {len(final_constraints)} constraints.")
    return ScenarioPuzzle(
        level=level,
        puzzle_type=HumanScenarioType.SCHEDULING,
        description=description,
        characters=characters_list,
        setting=setting_dict,
        goal=goal,
        information=information,
        solution={"schedule": final_solution_schedule},
        rules=None, # No separate rules list needed here, constraints are in 'information'
        is_verified=False # Mark as solvable for at least one solution, but not necessarily unique
    )


def _generate_scheduling_constraints_logic(people: List[str], slots: List[str], num_constraints_target: int) -> List[Tuple]:
    """Generates a list of logic constraints for the scheduling puzzle."""
    constraints = []
    added_constraints = set() # Avoid duplicates: (type, p1, p2/slot)

    max_attempts = num_constraints_target * 5

    while len(constraints) < num_constraints_target and len(added_constraints) < max_attempts:
        constraint_type_roll = random.random()
        constraint = None
        constraint_key = None

        # Availability/Unavailability (higher weight)
        if constraint_type_roll < 0.6:
            person = random.choice(people)
            slot = random.choice(slots)
            # Make 'must_be' rarer and dependent on level?
            if random.random() < 0.15 + (len(constraints) * 0.01): # Increasing chance for must_be?
                 constraint_type = 'must_be'
                 constraint = (constraint_type, person, slot)
                 constraint_key = (constraint_type, person, slot)
            else:
                 constraint_type = 'unavailable'
                 constraint = (constraint_type, person, slot)
                 constraint_key = (constraint_type, person, slot)

        # Relational (if enough people)
        elif constraint_type_roll < 0.9 and len(people) >= 2:
            p1, p2 = random.sample(people, 2)
            rel_type = random.choice(['before', 'together', 'apart'])
            constraint = (rel_type, p1, p2)
            # Key should be order-independent for 'together' and 'apart'
            pair_key = tuple(sorted((p1, p2)))
            if rel_type == 'before': constraint_key = (rel_type, p1, p2) # Order matters
            else: constraint_key = (rel_type,) + pair_key

        # Add constraint if it's new
        if constraint and constraint_key and constraint_key not in added_constraints:
            constraints.append(constraint)
            added_constraints.add(constraint_key)
            # Avoid adding direct opposites for relational? (e.g., p1 before p2 AND p2 before p1)
            # This is complex, solver handles contradictions, but generation could be smarter.

    return constraints


def _convert_constraints_to_text(constraints_logic: List[Tuple], people: List[str], slots: List[str]) -> List[str]:
    """Converts logic constraint tuples into human-readable text clues."""
    texts = []
    templates = {
        'unavailable': ["{p} is unavailable at {s}.", "{p} cannot make the {s} appointment.", "The {s} slot doesn't work for {p}."],
        'must_be': ["{p}'s appointment must be at {s}.", "{p} is only available at {s}.", "Schedule {p} for {s} specifically."],
        'before': ["{p1}'s appointment is scheduled sometime before {p2}'s.", "{p1} needs an earlier slot than {p2}.", "{p2}'s appointment must be after {p1}'s."],
        'together': ["{p1} and {p2} have appointments at the same time.", "{p1} and {p2} must be scheduled concurrently.", "Book {p1} and {p2} for the same slot."],
        'apart': ["{p1} and {p2} have appointments at different times.", "{p1} and {p2} cannot be scheduled for the same slot.", "Ensure {p1} and {p2} have separate appointment times."]
    }
    for const in constraints_logic:
        ctype = const[0]
        if ctype in templates:
            template = random.choice(templates[ctype])
            try:
                if ctype in ['unavailable', 'must_be']:
                    text = template.format(p=const[1], s=const[2])
                elif ctype in ['before', 'together', 'apart']:
                    text = template.format(p1=const[1], p2=const[2])
                else: continue # Should not happen
                texts.append(text)
            except IndexError:
                logger.warning(f"Index error formatting constraint text for: {const}")
            except Exception as e:
                logger.warning(f"Error formatting constraint text for {const}: {e}")
        else:
             logger.warning(f"Unknown constraint type encountered: {ctype}")

    return texts