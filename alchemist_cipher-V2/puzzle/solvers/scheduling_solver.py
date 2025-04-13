import random
import logging
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger(__name__)

class _SchedulingSolver:
    """
    Simple backtracking solver to find *one* valid schedule assignment.
    Used internally by the scheduling puzzle generator.
    Does NOT guarantee finding a solution if one exists (due to random order).
    Does NOT check for uniqueness.
    """
    def __init__(self, people: List[str], slots: List[str], constraints: List[Tuple]):
        self.people = list(people) # Ensure mutable copy
        self.slots = list(slots)
        self.constraints = constraints
        # Precompute slot indices for 'before' constraint checking
        self.slot_indices = {slot: i for i, slot in enumerate(slots)}
        # Shuffle people order to avoid bias in backtracking search path
        random.shuffle(self.people)

    def find_solution(self) -> Optional[Dict[str, str]]:
        """
        Attempts to find one valid assignment using backtracking.

        Returns:
            A dictionary mapping {person: assigned_slot} if a solution is found,
            otherwise None.
        """
        logger.debug(f"Scheduling Solver: Trying to find assignment for {len(self.people)} people in {len(self.slots)} slots with {len(self.constraints)} constraints.")
        # Initial empty assignment
        assignment: Dict[str, Optional[str]] = {person: None for person in self.people}
        return self._solve(assignment, 0) # Start solving from the first person

    def _solve(self, current_assignment: Dict[str, Optional[str]], person_index: int) -> Optional[Dict[str, str]]:
        """Recursive backtracking function."""
        # Base Case: All people have been assigned a slot
        if person_index == len(self.people):
            # Double-check the complete assignment against all constraints (especially relational ones)
            if self._is_fully_valid(current_assignment):
                 logger.debug(f"  Solver found a valid complete assignment: {current_assignment}")
                 # Cast is safe here because _is_fully_valid checks for None
                 return {k: v for k, v in current_assignment.items() if v is not None}
            else:
                 # logger.debug(f"  Complete assignment failed final validation: {current_assignment}")
                 return None # Complete assignment violates some constraint

        # Recursive Step: Try assigning the current person to available slots
        person_to_assign = self.people[person_index]
        available_slots = list(self.slots) # Start with all slots
        random.shuffle(available_slots) # Try slots in random order

        for slot in available_slots:
            current_assignment[person_to_assign] = slot
            # logger.debug(f"  Trying {person_to_assign} = {slot} (Person {person_index+1}/{len(self.people)})")

            # Pruning: Check if the *partial* assignment is valid so far
            if self._is_partially_valid(current_assignment, person_index + 1):
                # Recurse for the next person
                result = self._solve(current_assignment, person_index + 1)
                if result:
                    return result # Solution found down this path!

            # Backtrack: Unassign the current person and try the next slot
            # logger.debug(f"  Backtracking: Resetting {person_to_assign} from {slot}")
            current_assignment[person_to_assign] = None

        # If no slot worked for the current person, backtrack further
        # logger.debug(f"  No valid slot found for {person_to_assign} at index {person_index}. Backtracking.")
        return None

    def _is_partially_valid(self, assignment: Dict[str, Optional[str]], num_assigned: int) -> bool:
        """
        Checks constraints that *can* be evaluated based on the first 'num_assigned' people.
        This includes single-person constraints (unavailable, must_be) for assigned people
        and relational constraints *only* if both involved people are within the first 'num_assigned'.
        Also checks for double-booking among the assigned people.
        """
        assigned_people = self.people[:num_assigned]
        booked_slots_partial: Dict[str, str] = {} # slot: person

        # Check basic assignment validity and single-person constraints
        for i in range(num_assigned):
            person = assigned_people[i]
            slot = assignment[person]
            if slot is None: continue # Skip if this person wasn't assigned yet (shouldn't happen in normal flow)

            # Check for double booking among the currently assigned people
            if slot in booked_slots_partial:
                 # logger.debug(f"    Partial Check Fail: Slot {slot} double booked by {person} and {booked_slots_partial[slot]}")
                 return False # Conflict: Slot already taken by another assigned person
            booked_slots_partial[slot] = person

            # Check single-person constraints (unavailable, must_be)
            for constraint in self.constraints:
                ctype = constraint[0]
                c_person = constraint[1]
                c_slot = constraint[2] # For unavailable/must_be

                if c_person == person: # Constraint applies to the currently checked person
                    if ctype == 'unavailable' and c_slot == slot:
                         # logger.debug(f"    Partial Check Fail: {person} is unavailable at assigned slot {slot}")
                         return False
                    if ctype == 'must_be' and c_slot != slot:
                         # logger.debug(f"    Partial Check Fail: {person} must be at {c_slot}, but assigned {slot}")
                         return False

        # Check relational constraints involving *only* the currently assigned people
        assigned_people_set = set(assigned_people)
        for constraint in self.constraints:
            ctype = constraint[0]
            if ctype in ['before', 'together', 'apart']:
                p1, p2 = constraint[1], constraint[2]
                # Check if *both* people involved are among those already assigned
                if p1 in assigned_people_set and p2 in assigned_people_set:
                    slot1, slot2 = assignment[p1], assignment[p2]
                    # We only care if both have non-None slots assigned
                    if slot1 is not None and slot2 is not None:
                        idx1 = self.slot_indices.get(slot1, -1)
                        idx2 = self.slot_indices.get(slot2, -1)
                        if idx1 == -1 or idx2 == -1: # Should not happen if slots are valid
                            logger.error(f"Invalid slot found in assignment during partial check: {slot1} or {slot2}")
                            return False

                        if ctype == 'before' and idx1 >= idx2:
                             # logger.debug(f"    Partial Check Fail (Before): {p1} ({slot1}/{idx1}) not before {p2} ({slot2}/{idx2})")
                             return False
                        if ctype == 'together' and slot1 != slot2:
                             # logger.debug(f"    Partial Check Fail (Together): {p1} ({slot1}) not with {p2} ({slot2})")
                             return False
                        if ctype == 'apart' and slot1 == slot2:
                             # logger.debug(f"    Partial Check Fail (Apart): {p1} and {p2} both in {slot1}")
                             return False
        # logger.debug(f"    Partial Check Pass for first {num_assigned} people.")
        return True # No constraint violations found among the partially assigned people

    def _is_fully_valid(self, assignment: Dict[str, Optional[str]]) -> bool:
        """Checks if a *complete* assignment satisfies *all* constraints."""
        # Check if assignment is actually complete
        if any(slot is None for slot in assignment.values()):
             logger.warning("Full validation called on incomplete assignment.")
             return False

        # Check for double booking (should be caught by partial, but double check)
        booked_slots_full = {}
        for person, slot in assignment.items():
            if slot in booked_slots_full: return False # Double booked
            booked_slots_full[slot] = person

        # Check all constraints
        for constraint in self.constraints:
            ctype = constraint[0]
            p1 = constraint[1]

            if ctype == 'unavailable':
                if assignment[p1] == constraint[2]: return False
            elif ctype == 'must_be':
                 if assignment[p1] != constraint[2]: return False
            elif ctype in ['before', 'together', 'apart']:
                 p2 = constraint[2]
                 slot1, slot2 = assignment[p1], assignment[p2]
                 idx1, idx2 = self.slot_indices.get(slot1, -1), self.slot_indices.get(slot2, -1)
                 if idx1 == -1 or idx2 == -1: return False # Invalid slot

                 if ctype == 'before' and idx1 >= idx2: return False
                 if ctype == 'together' and slot1 != slot2: return False
                 if ctype == 'apart' and slot1 == slot2: return False

        return True # All constraints satisfied