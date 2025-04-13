# The Alchemist's Cipher & Logic Puzzles

A Python-based desktop game featuring symbol cipher decoding and various scenario-based logic puzzles, built with PyQt6. Test your deductive reasoning across multiple challenging puzzle formats!

## Features

*   **Multiple Puzzle Types:**
    *   **Symbol Cipher:** Decode symbols based on logical clues about letter properties and relationships.
    *   **Scenario Puzzles:** Tackle diverse logic challenges:
        *   Logic Grid: Deduce pairings across categories using a grid.
        *   Social Deduction: Analyze statements to find the truth.
        *   Common Sense Gap: Identify missing items/steps in a process.
        *   Relationship Map: Map connections between individuals.
        *   Ordering: Determine the correct sequence of events/items.
        *   Scheduling: Resolve timing conflicts based on constraints.
        *   Dilemma: Choose the best action in complex situations.
        *   Agent Simulation: Infer rules or predict behavior by observing agents.
*   **Progressive Difficulty:** Puzzles increase in complexity as you level up.
*   **Hints:** Get help when you're stuck (limited per level).
*   **Themes:** Unlock and apply different visual themes as you progress.
*   **Save/Load:** Your progress (level, solved count, unlocked themes, current puzzle) is saved automatically and can be loaded.
*   **Educational Feedback:** Learn about the logical skills used after solving each puzzle.
*   **Tutorial & Practice:** Built-in guides and practice puzzles for logic grids.

## Getting Started

### Prerequisites

*   Python 3.x
*   PyQt6 library (`pip install PyQt6`)

### Running the Game

1.  Navigate to the root directory of the project in your terminal.
2.  Run the main module:
    ```bash
    python -m alchemist_cipher.main
    ```
    *(Alternatively, depending on your setup, you might run `python alchemist_cipher/main.py`)*

## Puzzle Types Overview

*   **Symbol Cipher:** Classic substitution cipher. Use clues about letter properties (vowels, consonants), positions, and relationships.
*   **Logic Grid:** Deduce relationships between elements across categories using a grid (mark with ✔️ or ❌).
*   **Social Deduction:** Analyze statements, identify inconsistencies, and deduce hidden information.
*   **Common Sense Gap:** Identify the missing essential item or step in a real-world task.
*   **Relationship Map:** Determine pairings or connections between individuals based on clues.
*   **Ordering:** Reconstruct the correct sequence of events or items.
*   **Scheduling:** Solve scheduling conflicts based on given constraints.
*   **Dilemma:** Choose the most appropriate action in a complex situation.
*   **Agent Simulation:** Observe simulated agent behavior to deduce rules, traits, or predict outcomes.

## Contributing

*(Contributions are welcome! Please refer to CONTRIBUTING.md - if available)*

## License

*(Specify license information here - if applicable)* 