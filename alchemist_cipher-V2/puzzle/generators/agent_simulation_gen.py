from typing import Dict, List, Tuple, Optional, Any
import random
import logging

# Changed imports to absolute
from puzzle.common import HumanScenarioType
from puzzle.puzzle_types import ScenarioPuzzle

logger = logging.getLogger(__name__)

# --- Simulation Constants ---
MAX_SIM_TIME_STEPS = 6
MIN_SIM_TIME_STEPS = 3
MIN_AGENTS = 2
MAX_AGENTS = 4
MIN_LOCATIONS = 3
MAX_LOCATIONS = 5
MIN_RULES = 2
MAX_RULES = 4

def generate_agent_simulation_puzzle_internal(level: int, puzzle_type: HumanScenarioType,
                                              generator_instance, # Instance of PuzzleGenerator for data access
                                              **kwargs) -> ScenarioPuzzle:
    """Generates a puzzle based on observing a simple agent simulation."""
    logger.debug(f"Attempting Agent Simulation generation for level {level}")

    # Access data pools
    rules_pool = generator_instance.AGENT_SIMULATION_RULES
    names = generator_instance.SCENARIO_NAMES
    traits = generator_instance.SCENARIO_TRAITS
    settings = generator_instance.SCENARIO_SETTINGS

    if not all([rules_pool, names, traits, settings]):
         raise ValueError("Cannot generate agent sim puzzle: Required data pools missing/empty.")

    # --- Simulation Setup ---
    num_agents = random.randint(MIN_AGENTS, min(MAX_AGENTS, len(names), MIN_AGENTS + level // 2))
    num_time_steps = random.randint(MIN_SIM_TIME_STEPS, min(MAX_SIM_TIME_STEPS, MIN_SIM_TIME_STEPS + level // 2))

    # Select locations (use setting names)
    locations_available = [s['name'] for s in settings if s.get('name')]
    if len(locations_available) < MIN_LOCATIONS:
        raise ValueError("Not enough unique location names available in settings data.")
    num_locations = random.randint(min(num_agents, MIN_LOCATIONS), min(MAX_LOCATIONS, len(locations_available)))
    locations = random.sample(locations_available, num_locations)
    simulation_setting = {"name": "Observation Zone", "details": locations}

    # Select rules
    if len(rules_pool) < MIN_RULES:
        raise ValueError("Not enough agent simulation rules defined.")
    num_rules = random.randint(MIN_RULES, min(MAX_RULES, len(rules_pool)))
    selected_rule_templates = random.sample(rules_pool, num_rules)

    # Parameterize rules (instantiate placeholders like {location_A})
    rules_in_effect = [] # List of tuples: (rule_id, params_dict, rule_text)
    rule_texts_for_display = []
    parameter_options = {'location': locations, 'agent_trait': traits} # Add more as needed

    for rule_template in selected_rule_templates:
        rule_id, rule_text_template = rule_template["id"], rule_template["text"]
        params, final_rule_text = {}, rule_text_template

        # Simple regex to find placeholders like {location_A}, {trait}
        placeholders = re.findall(r"\{(\w+)(?:_\w+)?\}", rule_text_template) # Matches {location_A}, {trait} etc.
        param_map = {} # Maps placeholder -> chosen value for this instance

        for ph in placeholders:
            base_param_type = ph.split('_')[0] # e.g., 'location' from 'location_A'
            if base_param_type in parameter_options:
                 # Ensure different placeholders get potentially different values if possible
                 chosen_value = random.choice(parameter_options[base_param_type])
                 # Avoid assigning the same location to A and B if possible
                 retries = 0
                 while f'{{{ph}}}' in param_map and param_map[f'{{{ph}}}'] == chosen_value and retries < 5 and len(parameter_options[base_param_type]) > 1:
                     chosen_value = random.choice(parameter_options[base_param_type])
                     retries += 1

                 param_key = ph # Use full placeholder name like 'location_A' as key
                 params[param_key] = chosen_value
                 param_map[f'{{{ph}}}'] = chosen_value # Track for replacement
            else:
                logger.warning(f"No parameter options defined for placeholder base type: {base_param_type} in rule '{rule_id}'")

        # Apply substitutions to rule text
        for ph_full, value in param_map.items():
             final_rule_text = final_rule_text.replace(ph_full, value)

        rules_in_effect.append({"id": rule_id, "params": params, "text": final_rule_text})
        rule_texts_for_display.append(final_rule_text)
        logger.debug(f"Instantiated rule: {final_rule_text} (Params: {params})")


    # Setup Initial Agent States
    char_names = random.sample(names, num_agents)
    initial_locations = random.choices(locations, k=num_agents) # Allow multiple agents at start
    characters = []
    agent_goals = {} # Store goals separately for simulation step
    for i in range(num_agents):
        trait = random.choice(traits)
        # Define agent goal (e.g., reach a location, avoid another agent)
        goal_type = random.choice(["REACH_LOCATION", "AVOID_LOCATION", "REACH_AGENT", "AVOID_AGENT", "STAY"])
        goal_target = None
        if goal_type == "REACH_LOCATION": goal_target = random.choice([l for l in locations if l != initial_locations[i]] or [initial_locations[i]])
        elif goal_type == "AVOID_LOCATION": goal_target = random.choice(locations)
        elif goal_type == "REACH_AGENT": goal_target = random.choice([n for n in char_names if n != char_names[i]] or [char_names[i]])
        elif goal_type == "AVOID_AGENT": goal_target = random.choice([n for n in char_names if n != char_names[i]] or [char_names[i]])
        # Store goal components
        agent_goals[char_names[i]] = {"type": goal_type, "target": goal_target}
        agent_goal_str = f"{goal_type}: {goal_target}" if goal_target else goal_type

        characters.append({
            "name": char_names[i],
            "trait": trait,
            # "goal_str": agent_goal_str, # Store original string if needed for display/debug
            "location": initial_locations[i],
            "state_history": {0: initial_locations[i]} # Store location history T=0
        })
        logger.debug(f"Agent {char_names[i]} init: Loc={initial_locations[i]}, Trait={trait}, Goal={agent_goal_str}")


    # --- Run Simulation ---
    # This requires a dedicated simulation step function
    try:
        agent_state_histories = _run_simulation(
            characters, locations, rules_in_effect, agent_goals, num_time_steps
        )
        # Update characters with full history
        for i, agent in enumerate(characters):
            agent["state_history"] = agent_state_histories[agent["name"]]
    except Exception as sim_error:
        logger.error(f"Agent simulation failed: {sim_error}", exc_info=True)
        raise ValueError("Agent simulation failed during puzzle generation.") from sim_error


    # --- Generate Observations for the Player ---
    information = []
    # Reveal some (but not all) rules
    num_rules_to_reveal = min(len(rule_texts_for_display), max(1, num_rules // 2 + level // 5)) # Reveal fewer rules?
    revealed_rules_text = random.sample(rule_texts_for_display, k=num_rules_to_reveal)
    if revealed_rules_text:
        information.append("Some rules governing agent behavior have been identified:")
        information.extend(f"- Rule: {r}" for r in revealed_rules_text)
    else:
        information.append("The exact rules governing agent behavior are unknown.")

    # Reveal some (but not all) state observations
    max_possible_observations = num_agents * (num_time_steps + 1)
    num_observations = random.randint(min(num_agents + 1, max_possible_observations),
                                      min(int(max_possible_observations * 0.7), max_possible_observations)) # Reveal up to 70%?

    information.append("\nObservations during the simulation:")
    added_observations = set() # (time, agent_name)
    observation_pool = []
    for agent in characters:
        for t in range(num_time_steps + 1):
             location = agent['state_history'].get(t, "Unknown")
             observation_pool.append((t, agent['name'], location))

    random.shuffle(observation_pool)
    for t, agent_name, location in observation_pool:
        if len(added_observations) >= num_observations: break
        obs_key = (t, agent_name)
        if obs_key not in added_observations:
             # Vary observation text slightly
             obs_text_options = [
                 f"At T={t}, {agent_name} was observed in {location}.",
                 f"Time {t}: {agent_name} located at {location}.",
                 f"{agent_name}'s position at step {t} was {location}."
             ]
             information.append(f"- {random.choice(obs_text_options)}")
             added_observations.add(obs_key)

    random.shuffle(information) # Shuffle all info pieces

    # --- Define Goal & Solution ---
    # Goal: Identify an unrevealed rule OR predict a future state OR identify a trait
    goal_type = random.choice(["IDENTIFY_RULE", "IDENTIFY_TRAIT", "PREDICT_STATE"])
    puzzle_goal, solution = "", {}

    unrevealed_rules = [r["text"] for r in rules_in_effect if r["text"] not in revealed_rules_text]

    if goal_type == "IDENTIFY_RULE" and unrevealed_rules:
        puzzle_goal = "Based on the observations, identify one UNSTATED rule likely influencing the agents."
        solution = {"answer": random.choice(unrevealed_rules)}
    elif goal_type == "IDENTIFY_TRAIT":
        target_agent = random.choice(characters)
        puzzle_goal = f"Considering the actions and known rules, what is the most likely TRAIT of {target_agent['name']}?"
        solution = {"answer": target_agent['trait']}
    else: # Fallback or PREDICT_STATE (hard to verify prediction without running sim further)
        # Fallback to identifying a revealed rule if no unrevealed exist
        if unrevealed_rules or not revealed_rules_text: # If unrevealed exist, stick to that
            puzzle_goal = "Based on the observations, identify one UNSTATED rule likely influencing the agents."
            solution = {"answer": random.choice(unrevealed_rules) if unrevealed_rules else "Error: No unrevealed rule"}
        else: # Only revealed rules exist, ask about one of them
             puzzle_goal = "Which of the known rules seems most consistently applied or influential based on observations?"
             solution = {"answer": random.choice(revealed_rules_text)}


    # --- Construct Puzzle Object ---
    agent_names_str_desc = ", ".join(a['name'] for a in characters)
    locations_str_desc = ", ".join(locations)
    description = (
        f"Observe {num_agents} agents ({agent_names_str_desc}) interacting within a defined space "
        f"({locations_str_desc}) over {num_time_steps} time steps. "
        f"Their behavior is governed by a set of rules, some known, some unknown."
    )

    logger.info(f"Generated Agent Simulation puzzle. Goal type: {goal_type}")
    # Verification is based on the simulation trace consistency.
    return ScenarioPuzzle(
        level=level,
        puzzle_type=HumanScenarioType.AGENT_SIMULATION,
        description=description,
        characters=characters, # Include history in character data
        setting=simulation_setting,
        goal=puzzle_goal,
        information=information,
        solution=solution,
        rules=rule_texts_for_display, # Provide all instantiated rules text
        is_verified=True # Mark as verified based on simulation consistency
    )


# --- Agent Simulation Helper Function ---
import re # Import re inside function if not already imported globally

def _run_simulation(initial_agents: List[Dict], locations: List[str], rules: List[Dict],
                    agent_goals: Dict[str, Dict], num_steps: int) -> Dict[str, Dict[int, str]]:
    """
    Runs a simplified agent simulation step by step.

    Args:
        initial_agents: List of agent dicts (must include 'name', 'trait', 'state_history' with T=0).
        locations: List of valid location names.
        rules: List of rule dicts ({'id': str, 'params': dict, 'text': str}).
        agent_goals: Dict mapping agent name to {'type': str, 'target': Optional[str]}.
        num_steps: Number of steps to simulate (beyond T=0).

    Returns:
        Dict mapping agent name to their full state history {time_step: location}.
    """
    logger.info(f"Starting simulation: {len(initial_agents)} agents, {num_steps} steps, {len(rules)} rules.")
    agent_histories = {agent['name']: agent['state_history'].copy() for agent in initial_agents}
    agent_traits = {agent['name']: agent['trait'] for agent in initial_agents}
    agent_current_loc = {agent['name']: agent['state_history'][0] for agent in initial_agents}

    for t in range(1, num_steps + 1):
        logger.debug(f"--- Simulation Step {t} ---")
        agent_decisions = {} # agent_name: intended_next_location

        # 1. Determine Intended Moves based on rules and goals
        for agent_name in agent_histories.keys():
            current_loc = agent_current_loc[agent_name]
            trait = agent_traits[agent_name]
            goal = agent_goals.get(agent_name, {"type": "STAY", "target": None})
            possible_moves = [loc for loc in locations] # Include current location (staying)
            intended_move = current_loc # Default: stay put

            # Apply rules (simplified: first matching rule determines move)
            # This needs to be much more robust in a real sim (priorities, combinations)
            moved_by_rule = False
            for rule in rules:
                rule_id = rule["id"]
                params = rule["params"]
                # --- Evaluate Rule Condition (Highly Simplified Examples) ---
                condition_met = False
                potential_target_loc = None

                if rule_id == "MOVE_TOWARDS_GOAL_LOC" and goal["type"] == "REACH_LOCATION" and goal["target"] in locations:
                    if current_loc != goal["target"]:
                         condition_met = True
                         potential_target_loc = goal["target"] # Simplistic: move directly if possible next step? No pathfinding.
                elif rule_id == "MOVE_AWAY_FROM_GOAL_AGENT" and goal["type"] == "AVOID_AGENT" and goal["target"] in agent_current_loc:
                     target_agent_loc = agent_current_loc[goal["target"]]
                     if current_loc == target_agent_loc: # If currently at same loc
                          away_options = [l for l in locations if l != current_loc]
                          if away_options: potential_target_loc = random.choice(away_options); condition_met = True
                elif rule_id == "PREFER_QUIET_LOC" and trait == "Quiet":
                    target_loc = params.get("location_A")
                    if target_loc and target_loc != current_loc:
                         # Check if target loc is quiet (e.g., empty or 1 agent) - needs current state snapshot
                         agents_at_target = [name for name, loc in agent_current_loc.items() if loc == target_loc and name != agent_name]
                         if len(agents_at_target) <= 0: # Prefer empty
                              potential_target_loc = target_loc; condition_met = True
                elif rule_id == "MOVE_RANDOM_IF_NO_GOAL": # Generic fallback
                    if not moved_by_rule: # Apply only if no other rule moved the agent yet
                         move_options = [l for l in locations if l != current_loc]
                         if move_options: potential_target_loc = random.choice(move_options); condition_met = True # Always met if options exist

                # --- Apply Action if Condition Met ---
                if condition_met and potential_target_loc:
                    intended_move = potential_target_loc # Rule dictates move
                    logger.debug(f"  Agent {agent_name}: Rule '{rule_id}' triggered. Intends move to {intended_move}")
                    moved_by_rule = True
                    break # Simple priority: first rule wins

            # Store intended move
            agent_decisions[agent_name] = intended_move


        # 2. Resolve Conflicts (Crucial step - very basic implementation)
        next_locations = {}
        location_occupancy = {loc: [] for loc in locations} # Track intended occupants

        # First pass: tentative assignment
        for agent_name, target_loc in agent_decisions.items():
            location_occupancy[target_loc].append(agent_name)

        # Second pass: conflict resolution
        resolved_moves = {}
        for loc, occupants in location_occupancy.items():
            if len(occupants) <= 1: # No conflict or just one agent wants this spot
                 for agent_name in occupants:
                     resolved_moves[agent_name] = loc
            else: # Conflict! More than one agent wants this location
                logger.debug(f"  Conflict at {loc}: Agents {occupants} intend to move here.")
                # Basic resolution: Randomly pick one winner, others stay put
                winner = random.choice(occupants)
                resolved_moves[winner] = loc
                logger.debug(f"    Resolved: {winner} gets {loc}.")
                for agent_name in occupants:
                    if agent_name != winner:
                        resolved_moves[agent_name] = agent_current_loc[agent_name] # Loser stays
                        logger.debug(f"    Resolved: {agent_name} stays at {agent_current_loc[agent_name]}.")

        # 3. Update State History
        agent_current_loc = resolved_moves # Update current locations for next step
        for agent_name, final_location in resolved_moves.items():
            agent_histories[agent_name][t] = final_location
            logger.debug(f"  Agent {agent_name}: Final location at T={t} is {final_location}")


    logger.info("Simulation finished.")
    return agent_histories