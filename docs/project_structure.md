# Project Structure

```
.
├── .git/                     # Git repository data
├── .gitignore                # Files ignored by Git
├── README.md                 # Project overview and user guide
├── requirements.txt          # Python dependencies
├── alchemist_cipher_save.json # Example save file (or actual save location)
├── docs/                     # Developer documentation
│   ├── index.md              # Main documentation page
│   ├── project_structure.md  # This file
│   ├── modules.md            # Core module descriptions
│   ├── ui.md                 # UI component details
│   ├── puzzle_logic.md       # Puzzle implementation details
│   ├── data_management.md    # Save/load and data handling
│   └── contribution_guide.md # How to contribute
└── alchemist_cipher/         # Main application package
    ├── __init__.py           # Package marker
    ├── __main__.py           # Allows running with `python -m alchemist_cipher`
    ├── main.py               # Main application logic, UI setup (PyQt6)
    ├── puzzle.py             # Classes and logic for all puzzle types
    ├── game_state.py         # Handles saving and loading game state
    ├── ai_solvers.py         # AI logic for solving puzzles step-by-step
    ├── change_tracker.py     # Utility for tracking changes
    ├── ui.py                 # UI specific helpers or classes
    ├── themes.py             # Theme management
    ├── tutorial.py           # Tutorial system logic
    ├── tutorial_content.html # Content for the tutorial display
    ├── icons/                # Directory for UI icons
    │   └── ...               # Icon files
    ├── game_data/            # Data files for puzzles (if any)
    │   └── ...               # Data files
    └── __pycache__/          # Python bytecode cache (auto-generated)
```

## Key Directories & Files

*   `alchemist_cipher/`: Contains all the source code for the game.
*   `docs/`: Holds the developer documentation.
*   `alchemist_cipher/main.py`: The main entry point and primary UI controller.
*   `alchemist_cipher/puzzle.py`: Central hub for all puzzle generation and interaction logic.
*   `alchemist_cipher/game_state.py`: Manages persistence (saving/loading).
*   `README.md`: High-level overview for users.
*   `requirements.txt`: Lists necessary Python libraries. 