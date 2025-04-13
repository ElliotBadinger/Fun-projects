from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy
from PyQt6.QtGui import QFont
import logging

logger = logging.getLogger(__name__)

def populate_info_bar_layout(parent_layout, main_window):
    """Creates the widgets for the info bar and adds them to the parent layout.
       Stores references to the widgets on the main_window object.
    """
    logger.debug("Populating info bar layout...")
    info_bar_layout = QHBoxLayout()

    # Level Label
    main_window.level_label = QLabel("Level: 1")
    main_window.level_label.setFont(QFont("Arial", 12))
    info_bar_layout.addWidget(main_window.level_label)

    info_bar_layout.addStretch(1) # Add stretch to push items apart

    # Puzzle Type Label
    main_window.puzzle_type_label = QLabel("Type: Unknown")
    main_window.puzzle_type_label.setFont(QFont("Arial", 12))
    # Allow type label to expand if needed
    # main_window.puzzle_type_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    info_bar_layout.addWidget(main_window.puzzle_type_label)

    info_bar_layout.addStretch(1) # Add stretch

    # Hints Label
    # Get initial max hints from game state if available
    initial_hints = "Hints Left: -"
    try:
        initial_hints = f"Hints Left: {main_window.game_state.max_hints_per_level}"
    except AttributeError:
         logger.warning("Could not get initial max hints from game state.")

    main_window.hints_label = QLabel(initial_hints)
    main_window.hints_label.setFont(QFont("Arial", 12))
    info_bar_layout.addWidget(main_window.hints_label)

    # Add the info bar layout to the main window's layout
    parent_layout.addLayout(info_bar_layout)
    logger.debug("Info bar layout populated.")