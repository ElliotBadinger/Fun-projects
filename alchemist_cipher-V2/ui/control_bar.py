from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QSpacerItem, QSizePolicy
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSize, Qt
import logging
import os # Import os
import sys # Import sys

# from utils import resource_path # Removed import

logger = logging.getLogger(__name__)

# Calculate base path once for icons
try:
    base_path = sys._MEIPASS
except AttributeError:
    base_path = os.path.abspath(".")

def populate_control_bar_layout(parent_layout, main_window):
    """Creates the control bar buttons and adds them to the parent layout.
       Connects signals and stores references on main_window.
    """
    logger.debug("Populating control bar layout...")
    control_layout = QHBoxLayout()
    # Optional: Add a frame for visual grouping?
    # control_frame = QFrame(); control_frame.setFrameShape(QFrame.Shape.StyledPanel)
    # control_frame_layout = QHBoxLayout(control_frame)

    icon_size = QSize(24, 24) # Standard icon size

    # --- Hint Button ---
    main_window.hint_button = QPushButton(" Hint")
    hint_icon_path = os.path.join(base_path, "icons/hint.png")
    hint_icon = QIcon.fromTheme("help-contextual", QIcon(hint_icon_path))
    if not hint_icon.isNull(): main_window.hint_button.setIcon(hint_icon)
    main_window.hint_button.setIconSize(icon_size)
    main_window.hint_button.setToolTip("Use a hint for the current puzzle (Ctrl+H)")
    main_window.hint_button.setShortcut("Ctrl+H")
    main_window.hint_button.clicked.connect(main_window._use_hint) # Connect to main window method
    main_window.hint_button.setEnabled(False) # Initially disabled until puzzle loaded
    control_layout.addWidget(main_window.hint_button)

    # --- Check Button ---
    main_window.check_button = QPushButton(" Check")
    check_icon_path = os.path.join(base_path, "icons/check.png")
    check_icon = QIcon.fromTheme("dialog-ok-apply", QIcon(check_icon_path))
    if not check_icon.isNull(): main_window.check_button.setIcon(check_icon)
    main_window.check_button.setIconSize(icon_size)
    main_window.check_button.setToolTip("Check if your current solution is correct (Enter)")
    main_window.check_button.setShortcut(Qt.Key.Key_Return) # Use Enter key as shortcut? Or Ctrl+Enter?
    main_window.check_button.setDefault(True) # Make check the default button? Careful with focus.
    main_window.check_button.clicked.connect(main_window._check_solution) # Connect to main window method
    main_window.check_button.setEnabled(False) # Initially disabled
    control_layout.addWidget(main_window.check_button)

    # --- Reset Button ---
    main_window.reset_button = QPushButton(" Reset")
    reset_icon_path = os.path.join(base_path, "icons/reset.png")
    reset_icon = QIcon.fromTheme("edit-undo", QIcon(reset_icon_path))
    if not reset_icon.isNull(): main_window.reset_button.setIcon(reset_icon)
    main_window.reset_button.setIconSize(icon_size)
    main_window.reset_button.setToolTip("Reset the current puzzle inputs and hints used (Ctrl+R)")
    main_window.reset_button.setShortcut("Ctrl+R")
    main_window.reset_button.clicked.connect(main_window._reset_puzzle) # Connect to main window method
    main_window.reset_button.setEnabled(False) # Initially disabled
    control_layout.addWidget(main_window.reset_button)

    # Add Spacer to push buttons left/right or center them
    # control_layout.addStretch(1) # Example: push buttons left

    # Add the control layout to the main window's layout
    parent_layout.addLayout(control_layout)
    logger.debug("Control bar layout populated.")