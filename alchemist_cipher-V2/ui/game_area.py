from PyQt6.QtWidgets import (QHBoxLayout, QVBoxLayout, QFrame, QLabel, QTextEdit,
                             QWidget, QScrollArea, QSizePolicy)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
import logging

logger = logging.getLogger(__name__)

def create_game_area_layout(parent_layout, main_window):
    """Creates the main game area layout (puzzle input + clues).
       Stores references to key widgets and layouts on main_window.
    """
    logger.debug("Creating game area layout...")
    main_window.game_area_layout = QHBoxLayout() # Store the main HBox layout ref

    # --- Puzzle Input Area (Left Side - Scrollable) ---
    main_window.puzzle_scroll_area = QScrollArea()
    main_window.puzzle_scroll_area.setWidgetResizable(True)
    main_window.puzzle_scroll_area.setFrameShape(QFrame.Shape.NoFrame) # Make it seamless

    # Widget inside scroll area that holds the actual puzzle content layout
    scroll_content_widget = QWidget(main_window.puzzle_scroll_area)
    main_window.puzzle_area_layout = QVBoxLayout(scroll_content_widget) # Store layout ref
    scroll_content_widget.setLayout(main_window.puzzle_area_layout)

    # Title for the puzzle area
    main_window.puzzle_title_label = QLabel("Puzzle Area")
    main_window.puzzle_title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
    main_window.puzzle_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    main_window.puzzle_area_layout.addWidget(main_window.puzzle_title_label)

    # Placeholder widget and layout where specific puzzle UI will be inserted
    main_window.puzzle_content_widget = QWidget()
    # Create the layout first, with the widget as parent
    temp_layout = QVBoxLayout(main_window.puzzle_content_widget)
    # The parent widget automatically takes ownership, no explicit setLayout needed

    # --- Start Debugging Block ---
    retrieved_layout = None
    widget_valid = main_window.puzzle_content_widget is not None
    logger.debug(f"game_area: Is puzzle_content_widget valid before getting layout? {widget_valid}")
    if widget_valid:
        try:
            retrieved_layout = main_window.puzzle_content_widget.layout()
            logger.debug(f"game_area: Result of widget.layout(): {retrieved_layout} (type: {type(retrieved_layout)}, id: {id(retrieved_layout) if retrieved_layout else 'N/A'})")
        except Exception as e:
            logger.exception(f"game_area: EXCEPTION calling widget.layout(): {e}")

    # Store the reference to the layout
    main_window.puzzle_content_layout = retrieved_layout # STORE THIS REF!
    logger.debug(f"game_area: Assigned main_window.puzzle_content_layout = {main_window.puzzle_content_layout} (id: {id(main_window.puzzle_content_layout) if main_window.puzzle_content_layout else 'N/A'})")

    # Check validity AFTER assignment and BEFORE use
    layout_valid_after_assign = main_window.puzzle_content_layout is not None and isinstance(main_window.puzzle_content_layout, QVBoxLayout)
    logger.debug(f"game_area: Is puzzle_content_layout valid after assignment? {layout_valid_after_assign}")

    if layout_valid_after_assign:
        try:
            main_window.puzzle_content_layout.setContentsMargins(5, 5, 5, 5) # Add some margin
            logger.debug("game_area: Successfully called setContentsMargins")
        except Exception as e:
            logger.exception(f"game_area: EXCEPTION calling setContentsMargins: {e}")
    else:
        logger.error("game_area: Skipping setContentsMargins because layout is invalid after assignment.")
    # --- End Debugging Block ---

    main_window.puzzle_area_layout.addWidget(main_window.puzzle_content_widget)

    main_window.puzzle_area_layout.addStretch(1) # Add stretch at the bottom

    # Add the scroll area (containing the puzzle layout) to the main game area layout
    main_window.puzzle_scroll_area.setWidget(scroll_content_widget)
    main_window.game_area_layout.addWidget(main_window.puzzle_scroll_area, stretch=3) # Puzzle area takes more space


    # --- Clues/Information Area (Right Side) ---
    clues_frame = QFrame()
    clues_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
    clues_layout = QVBoxLayout(clues_frame)

    main_window.clues_title = QLabel("Information")
    main_window.clues_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
    main_window.clues_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    clues_layout.addWidget(main_window.clues_title)

    main_window.clues_text = QTextEdit()
    main_window.clues_text.setReadOnly(True)
    main_window.clues_text.setFont(QFont("Arial", 11))
    main_window.clues_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth) # Wrap text
    clues_layout.addWidget(main_window.clues_text)

    main_window.game_area_layout.addWidget(clues_frame, stretch=2) # Clues area takes less space

    # Add the game area layout to the main window's layout
    parent_layout.addLayout(main_window.game_area_layout)
    logger.debug("Game area layout created.")