import sys
from typing import Optional, Dict, Any, Union, Tuple, List
import logging
import time
import os

# --- PyQt6 Imports ---
# Core application and window
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QMessageBox, QDialog
# Layouts
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout, QSpacerItem
# Widgets
from PyQt6.QtWidgets import QPushButton, QLabel, QComboBox, QTextEdit, QFrame, QTableWidget, QLineEdit, QRadioButton, QButtonGroup, QScrollArea
# Table related
from PyQt6.QtWidgets import QTableWidgetItem, QHeaderView, QAbstractItemView
# Menu related
from PyQt6.QtWidgets import QMenuBar, QMenu
# Other Qt Core/Gui
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QFont, QIcon, QAction, QColor

# --- Application Imports ---
# Change these to relative imports
from ..core.game_state import GameState # Changed from core.game_state
from ..puzzle.puzzle_types import Puzzle, ScenarioPuzzle # Changed from puzzle.puzzle_types
from ..puzzle.common import ClueType, HumanScenarioType # Changed from puzzle.common
# UI Creation Helpers (These are already relative using '.')
from .menu_bar import create_menu_bar
from .info_bar import populate_info_bar_layout
from .game_area import create_game_area_layout
from .control_bar import populate_control_bar_layout
from .puzzle_display import (
    create_symbol_puzzle_ui, create_scenario_puzzle_ui,
    display_symbol_clues, display_scenario_information,
    get_scenario_solution_from_ui, update_symbol_assignments_display,
    clear_layout, get_clue_prefix, get_puzzle_type_display_name,
    apply_visual_feedback, clear_visual_feedback
)
from .dialogs import PuzzleTypeDialog
# Theming
from .themes import THEMES # Changed from ..themes
# Tutorial
from ..tutorial import TutorialDialog, PracticePuzzleDialog # Changed from tutorial
# AI Solvers (If uncommented, would also need relative path)
# from ..ai import get_solver_instances, AbstractPuzzleSolver # Changed from ai 

# Setup logging
logger = logging.getLogger(__name__)

# --- Calculate Base Path for Resources ---
try:
    base_path = sys._MEIPASS
except AttributeError:
    base_path = os.path.abspath(".")

class SymbolCipherGame(QMainWindow):
    """Main application window for The Alchemist's Cipher & Logic Puzzles game."""
    def __init__(self):
        super().__init__()
        logger.info("Initializing main application window...")
        self.game_state = GameState()

        # --- UI Widget References ---
        # These will be populated by the UI creation functions
        # Info Bar
        self.level_label: Optional[QLabel] = None
        self.puzzle_type_label: Optional[QLabel] = None
        self.hints_label: Optional[QLabel] = None
        # Game Area
        self.game_area_layout: Optional[QHBoxLayout] = None
        self.puzzle_scroll_area: Optional[QScrollArea] = None
        self.puzzle_frame: Optional[QFrame] = None
        self.puzzle_area_layout: Optional[QVBoxLayout] = None
        self.puzzle_title_label: Optional[QLabel] = None
        self.puzzle_content_widget: Optional[QWidget] = None
        self.puzzle_content_layout: Optional[QVBoxLayout] = None # Layout for specific puzzle UI
        self.clues_title: Optional[QLabel] = None
        self.clues_text: Optional[QTextEdit] = None
        # Control Bar
        self.hint_button: Optional[QPushButton] = None
        self.check_button: Optional[QPushButton] = None
        self.reset_button: Optional[QPushButton] = None
        # Feedback
        self.feedback_label: Optional[QLabel] = None
        # Menu Actions (that need enabling/disabling)
        self.run_ai_action: Optional[QAction] = None
        self.stop_ai_action: Optional[QAction] = None
        self.theme_menu: Optional[QMenu] = None # Reference to the theme submenu
        # Puzzle Input Widgets (managed dynamically)
        self.assignment_widgets: Dict[str, Dict[str, QComboBox]] = {} # For Symbol Cipher {symbol: {'combo': QComboBox}}
        self.scenario_input_widget: Optional[QWidget] = None # Holds the main input widget (Table, LineEdit, ButtonGroup)
        self.scenario_input_widgets: Dict[str, Any] = {} # For complex scenarios needing multiple refs (e.g., logic grid column map)

        # --- AI Solver Attributes ---
        self.ai_timer = QTimer(self)
        self.ai_timer.timeout.connect(self._ai_step)
        self.is_ai_running = False
        self.ai_step_delay_ms = 750 # Time between AI showing solution and checking it

        # --- Window Setup ---
        self.setWindowTitle("The Alchemist's Cipher & Logic Puzzles")
        self.setMinimumSize(900, 700)

        # --- Set Window Icon ---
        try:
            # Path logic specifically for the icon
            if getattr(sys, 'frozen', False):
                # The application is running frozen (packed by PyInstaller)
                icon_base_path = sys._MEIPASS
            else:
                # The application is running in a normal Python environment
                icon_base_path = os.path.dirname(os.path.abspath(__file__))
                # If __file__ is in ui/, go up one level to project root relative path
                icon_base_path = os.path.join(icon_base_path, '..') 
            
            icon_path = os.path.join(icon_base_path, "icons/app-logo(V2).ico")
            icon_path = os.path.normpath(icon_path) # Normalize path separators
            
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
                logger.info(f"Loaded window icon from: {icon_path}")
            else:
                logger.warning(f"Window icon not found at calculated path: {icon_path}")
                # Fallback to theme icon if custom icon not found
                self.setWindowIcon(QIcon.fromTheme("applications-education")) 
        except Exception as e:
            logger.error(f"Error setting window icon: {e}", exc_info=True)
            # Fallback to theme icon on any error
            self.setWindowIcon(QIcon.fromTheme("applications-education")) 

        # --- UI Construction ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create UI sections by calling helper functions
        create_menu_bar(self) # Pass self to connect actions
        populate_info_bar_layout(main_layout, self) # Pass self to store widget references
        create_game_area_layout(main_layout, self) # Pass self
        populate_control_bar_layout(main_layout, self) # Pass self
        self._create_feedback_label(main_layout) # Simple enough to keep here or move

        # --- Initial Game Load ---
        try:
            self.game_state.load_game()
            if not self.game_state.current_puzzle:
                logger.info("No puzzle loaded from save, starting a new default puzzle.")
                # Check if generator is valid before starting
                if self.game_state.puzzle_generator is None:
                     QMessageBox.critical(self, "Initialization Error", "Failed to initialize puzzle generator. Cannot start game.")
                     # Optionally close the app or disable functionality
                     # sys.exit(1)
                else:
                    self.game_state.start_new_puzzle() # Start with default type
                    self._update_ui_for_puzzle()
            else:
                logger.info("Loaded existing puzzle from save file.")
                self._update_ui_for_puzzle() # Display loaded puzzle
        except RuntimeError as e:
             # Handle critical errors during load (like version mismatch or generator init fail)
             QMessageBox.critical(self, "Initialization Error", f"A critical error occurred during loading: {e}\nCannot continue.")
             # Close the application gracefully
             QTimer.singleShot(100, self.close) # Close after dialog
             return # Stop further initialization
        except Exception as e:
            logger.exception("Unexpected error during initial game load or puzzle start.")
            self.game_state = GameState() # Reset state
            # Ensure generator is okay before starting new puzzle
            if self.game_state.puzzle_generator:
                 self.game_state.start_new_puzzle()
                 self._update_ui_for_puzzle()
            else:
                 QMessageBox.critical(self, "Initialization Error", "Failed to initialize puzzle generator even after reset. Cannot start game.")
                 # Optionally close or disable

        # Apply initial theme
        self._apply_theme()
        logger.info("Main window initialization complete.")

    # --- UI Creation Helpers (Simple ones kept here) ---

    def _create_feedback_label(self, parent_layout):
        """Creates the label at the bottom for displaying feedback messages."""
        self.feedback_label = QLabel("")
        self.feedback_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.feedback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feedback_label.setMinimumHeight(30) # Ensure space for messages
        self.feedback_label.setWordWrap(True)
        # Add style sheet for default color?
        parent_layout.addWidget(self.feedback_label)

    # --- UI Update and Display Logic ---

    def _update_ui_for_puzzle(self):
        """Updates the entire UI to reflect the current puzzle state."""
        logger.debug(f"_update_ui_for_puzzle: self.puzzle_content_layout BEFORE check: {self.puzzle_content_layout} (id: {id(self.puzzle_content_layout if self.puzzle_content_layout else None)})")
        logger.debug("Updating UI for current puzzle...")
        puzzle = self.game_state.current_puzzle

        # --- Clear existing dynamic puzzle UI ---
        if self.puzzle_content_layout is not None:
            logger.debug(f"Clearing layout: {self.puzzle_content_layout} (id: {id(self.puzzle_content_layout)})")
            clear_layout(self.puzzle_content_layout)
        else:
            logger.error("Puzzle content layout reference is missing!")
            # Handle error: maybe recreate game area?
            return
        # Reset dynamic widget references
        self.assignment_widgets = {}
        self.scenario_input_widget = None
        self.scenario_input_widgets = {}

        # Determine if UI should be interactive
        is_interactive = not self.is_ai_running

        # --- Handle No Puzzle State ---
        if not puzzle:
            logger.warning("Updating UI, but no puzzle is active.")
            if self.puzzle_title_label: self.puzzle_title_label.setText("No Puzzle Loaded")
            self.puzzle_content_layout.addWidget(QLabel("Load a game or start a new puzzle via the 'Game' menu."))
            if self.level_label: self.level_label.setText("Level: -")
            if self.puzzle_type_label: self.puzzle_type_label.setText("Type: N/A")
            if self.hints_label: self.hints_label.setText("Hints Left: -")
            if self.clues_text: self.clues_text.clear(); self.clues_text.setEnabled(False)
            if self.clues_title: self.clues_title.setText("Information")
            if self.feedback_label: self.feedback_label.setText("No puzzle active.")
            # Disable controls
            if self.hint_button: self.hint_button.setEnabled(False)
            if self.check_button: self.check_button.setEnabled(False)
            if self.reset_button: self.reset_button.setEnabled(False)
            if self.run_ai_action: self.run_ai_action.setEnabled(False)
            # Stop AI Button should already be disabled if no AI is running
            return

        # --- Update UI for Active Puzzle ---
        # Enable/disable controls based on AI state
        if self.run_ai_action: self.run_ai_action.setEnabled(is_interactive)
        if self.check_button: self.check_button.setEnabled(is_interactive)
        if self.reset_button: self.reset_button.setEnabled(is_interactive)
        if self.clues_text: self.clues_text.setEnabled(True) # Enable clues text view

        # Update Info Bar
        if self.level_label: self.level_label.setText(f"Level: {puzzle.level + 1} (Solved: {self.game_state.puzzles_solved})")
        hints_left = self.game_state.max_hints_per_level - self.game_state.hints_used_this_level
        if self.hints_label: self.hints_label.setText(f"Hints Left: {hints_left}")
        if self.hint_button: self.hint_button.setEnabled(hints_left > 0 and is_interactive)

        # Reset feedback unless AI is running
        if not self.is_ai_running and self.feedback_label:
             self.feedback_label.setText("")
             self.feedback_label.setStyleSheet("") # Reset style

        # Clear and update Clues/Information Area
        if self.clues_text: self.clues_text.clear()

        # --- Display Puzzle Specific UI and Info ---
        puzzle_display_name = get_puzzle_type_display_name(puzzle)
        if self.puzzle_type_label: self.puzzle_type_label.setText(f"Type: {puzzle_display_name}")

        if isinstance(puzzle, Puzzle) and not puzzle.is_scenario:
            if self.puzzle_title_label: self.puzzle_title_label.setText("Symbols & Assignments")
            if self.clues_title: self.clues_title.setText("Alchemist's Notes (Clues)")
            # Call puzzle display function (passes self to store widget refs)
            create_symbol_puzzle_ui(puzzle, self.puzzle_content_layout, self)
            if self.clues_text: display_symbol_clues(puzzle, self.clues_text)
            # Restore user state for symbol puzzles
            update_symbol_assignments_display(self) # Uses self.assignment_widgets and self.game_state.user_mapping

        elif isinstance(puzzle, ScenarioPuzzle):
            if self.puzzle_title_label: self.puzzle_title_label.setText(f"Scenario: {puzzle_display_name}")
            if self.clues_title: self.clues_title.setText("Scenario Information & Clues")
            # Call puzzle display function (passes self to store widget refs)
            create_scenario_puzzle_ui(puzzle, self.puzzle_content_layout, self)
            if self.clues_text: display_scenario_information(puzzle, self.clues_text)
            # TODO: Restore user state for different scenario UIs if applicable (e.g., saved grid state)
            self._restore_scenario_ui_state()

        else:
            # Handle unknown puzzle type loaded? Should not happen with proper generation/loading.
             logger.error(f"Unknown puzzle type encountered in _update_ui_for_puzzle: {type(puzzle)}")
             if self.puzzle_title_label: self.puzzle_title_label.setText("Error")
             self.puzzle_content_layout.addWidget(QLabel("Error: Unknown puzzle type loaded."))

        # Ensure theme is applied correctly after UI changes
        self._apply_theme()
        # Force layout update if needed (usually automatic)
        # if self.puzzle_area_layout: self.puzzle_area_layout.activate()
        logger.debug("UI update complete.")

    def _restore_scenario_ui_state(self):
        """Restores the state of the scenario UI based on game_state."""
        logger.debug("Attempting to restore scenario UI state.")
        puzzle = self.game_state.current_puzzle
        user_state = self.game_state.scenario_user_state
        widget = self.scenario_input_widget

        if not isinstance(puzzle, ScenarioPuzzle) or not user_state or not widget:
            logger.debug("Skipping scenario UI restore: No puzzle, user state, or main widget.")
            return

        try:
            if puzzle.puzzle_type == HumanScenarioType.LOGIC_GRID and isinstance(widget, QTableWidget) and 'grid' in user_state:
                saved_grid = user_state['grid'] # Assumes format {entity: {cat: value}}
                # TODO: Implement logic to set combo boxes based on saved_grid
                logger.warning("Logic Grid UI state restoration not fully implemented.")
                pass # Needs mapping from saved state back to combo box selection ("✔️", "❌")
            elif isinstance(widget, QLineEdit) and 'answer' in user_state:
                 widget.setText(str(user_state['answer']))
            elif puzzle.puzzle_type == HumanScenarioType.RELATIONSHIP_MAP and isinstance(widget, QTextEdit) and 'map' in user_state:
                 # Reconstruct text from map {p1: p2, ...}
                 lines = []
                 processed = set()
                 for p1, p2 in user_state['map'].items():
                      pair = frozenset({p1, p2})
                      if pair not in processed:
                           lines.append(f"{p1} : {p2}")
                           processed.add(pair)
                 widget.setPlainText("\n".join(lines))
            elif puzzle.puzzle_type == HumanScenarioType.ORDERING and isinstance(widget, QTableWidget) and 'order' in user_state:
                 order_list = user_state['order']
                 if isinstance(order_list, list):
                     for r, item in enumerate(order_list):
                          if r < widget.rowCount():
                               cell_widget = widget.cellWidget(r, 0)
                               if isinstance(cell_widget, QComboBox):
                                    index = cell_widget.findText(str(item))
                                    if index >= 0: cell_widget.setCurrentIndex(index)
            elif puzzle.puzzle_type == HumanScenarioType.SCHEDULING and isinstance(widget, QTableWidget) and 'schedule' in user_state:
                 schedule_map = user_state['schedule'] # {person: {slot: status}}
                 people = [widget.verticalHeaderItem(r).text() for r in range(widget.rowCount())]
                 slots = [widget.horizontalHeaderItem(c).text() for c in range(widget.columnCount())]
                 for r, person in enumerate(people):
                     for c, slot in enumerate(slots):
                         status = schedule_map.get(person, {}).get(slot, "Available")
                         target_text = "✔️" if status == "Booked" else ""
                         cell_widget = widget.cellWidget(r, c)
                         if isinstance(cell_widget, QComboBox):
                             index = cell_widget.findText(target_text)
                             if index >= 0: cell_widget.setCurrentIndex(index)
            elif puzzle.puzzle_type == HumanScenarioType.DILEMMA and isinstance(widget, QButtonGroup) and 'choice' in user_state:
                 choice_text = user_state['choice']
                 for button in widget.buttons():
                     if button.text() == choice_text:
                         button.setChecked(True)
                         break
            # Add more types as needed
        except Exception as e:
            logger.exception(f"Error restoring scenario UI state for {puzzle.puzzle_type.name}: {e}")

    # --- Symbol Assignment Logic ---

    def _assign_letter(self, symbol: str, letter: str):
        """Handles user assigning a letter to a symbol via ComboBox."""
        if self.is_ai_running:
             logger.warning("User interaction ignored while AI is running.")
             return
        if not isinstance(self.game_state.current_puzzle, Puzzle) or self.game_state.current_puzzle.is_scenario:
            logger.warning("Assign letter called when not in Symbol Cipher puzzle.")
            return

        logger.debug(f"User assigning '{letter}' to symbol '{symbol}'")
        current_mapping = self.game_state.user_mapping
        previous_assignment = current_mapping.get(symbol)

        # Prevent assigning the same letter to multiple symbols
        existing_symbol_for_letter = None
        if letter: # Only check if assigning a non-empty letter
            for s, l in current_mapping.items():
                if l == letter and s != symbol:
                    existing_symbol_for_letter = s
                    break

        # Update the mapping in game state
        if letter: # Assigning a new letter
            if existing_symbol_for_letter:
                # Clear the letter from the other symbol first
                logger.debug(f"Letter '{letter}' was previously assigned to '{existing_symbol_for_letter}'. Unassigning it.")
                current_mapping.pop(existing_symbol_for_letter, None)
            # Assign the letter to the current symbol
            current_mapping[symbol] = letter
        else: # Unassigning (selected blank)
            current_mapping.pop(symbol, None) # Remove symbol if it exists

        # Update the UI to reflect changes (disable used letters, re-enable freed letters)
        update_symbol_assignments_display(self) # Pass self to access assignment_widgets and game_state

        # Provide feedback if a letter was cleared from another symbol
        if existing_symbol_for_letter and self.feedback_label:
            self.feedback_label.setText(f"Note: '{letter}' unassigned from '{existing_symbol_for_letter}'.")
            self.feedback_label.setStyleSheet("color: orange;")
            # Optional: Clear feedback after a delay
            QTimer.singleShot(3000, lambda: self.feedback_label.setText("") if self.feedback_label.text().startswith("Note:") else None)
        elif self.feedback_label and self.feedback_label.text().startswith("Note:"):
            # Clear previous note if a new assignment didn't trigger one
             self.feedback_label.setText("")
             self.feedback_label.setStyleSheet("")

    # --- Core Action Handlers (Hint, Check, Reset) ---

    def _use_hint(self):
        """Handles the 'Hint' button click."""
        if self.is_ai_running:
             logger.warning("Hint ignored while AI running.")
             return
        if not self.game_state.current_puzzle:
            self._set_feedback("No puzzle active to get a hint for.", "orange")
            return

        logger.info("Hint button clicked.")
        hint_result = self.game_state.get_hint()

        if not hint_result:
            self._set_feedback("Internal error: Failed to get hint.", "red")
            return

        hint_text_display = ""
        apply_hint_to_ui = False
        symbol_to_assign, letter_to_assign = None, None

        if isinstance(hint_result, str):
            # Handle messages like "No hints left", "Cannot provide hint", etc.
            if any(msg in hint_result for msg in ["No hints left", "No further hints", "No puzzle loaded", "Cannot provide hint"]):
                  self._set_feedback(hint_result, "orange")
                  if "No hints left" in hint_result and self.hint_button:
                      self.hint_button.setEnabled(False)
                  return # Don't proceed further
            else:
                 # Generic string hint (likely for scenarios)
                 hint_text_display = f"Hint: {hint_result}"
        elif isinstance(hint_result, tuple) and len(hint_result) == 3:
            # Symbol cipher hint: (symbol, letter, reason)
            symbol_to_assign, letter_to_assign, reason = hint_result
            hint_text_display = f"Hint ({reason}): Try mapping '{symbol_to_assign}' to '{letter_to_assign}'."
            apply_hint_to_ui = True # We should apply this assignment
        else:
            self._set_feedback("Received invalid hint format from game state.", "red")
            return

        # Display the hint text
        self._set_feedback(hint_text_display, "#007bff") # Blue color for hints

        # Update hints count display
        hints_left = self.game_state.max_hints_per_level - self.game_state.hints_used_this_level
        if self.hints_label: self.hints_label.setText(f"Hints Left: {hints_left}")
        if self.hint_button: self.hint_button.setEnabled(hints_left > 0)

        # Apply the hint directly to the UI for symbol puzzles
        if apply_hint_to_ui and symbol_to_assign and letter_to_assign:
            logger.info(f"Applying hint assignment: {symbol_to_assign} -> {letter_to_assign}")
            self._assign_letter(symbol_to_assign, letter_to_assign)

    def _check_solution(self, ai_initiated: bool = False):
        """
        Handles the 'Check Solution' button click or AI-initiated check.
        Gives feedback, handles unlocks, and advances the level if correct.
        """
        # If called by user button press and AI is running, ignore
        if not ai_initiated and self.is_ai_running:
             logger.warning("User check ignored while AI running.")
             return

        puzzle = self.game_state.current_puzzle
        if not puzzle:
             self._set_feedback("No puzzle active to check.", "orange")
             return

        logger.info(f"Checking solution for Level {puzzle.level + 1} ({'AI initiated' if ai_initiated else 'User initiated'})...")
        user_solution_data = None
        is_correct = False

        try:
            # --- Get User's Solution from UI ---
            if isinstance(puzzle, Puzzle) and not puzzle.is_scenario:
                 # Check if all symbols are mapped for symbol cipher
                 if len(self.game_state.user_mapping) < puzzle.num_elements:
                     if ai_initiated:
                          # This is an error state for AI - it should have fully mapped
                          logger.error("AI initiated check, but symbol puzzle not fully mapped by UI update.")
                          self._set_feedback("AI Error: Symbol mapping incomplete!", "red", bold=True)
                          self._stop_ai_solver() # Stop AI on error
                          return
                     else:
                          # User hasn't finished
                          self._set_feedback("Please assign a letter to all symbols first.", "orange")
                          return
                 # For symbol puzzles, check_solution uses the internal game_state.user_mapping
                 user_solution_data = None # Not needed for GameState.check_solution call
                 is_correct = self.game_state.check_solution()

            elif isinstance(puzzle, ScenarioPuzzle):
                 # Get the solution data structure from the current UI state
                 user_solution_data = get_scenario_solution_from_ui(self) # Pass self to access widgets
                 if user_solution_data is None:
                      # Error message (e.g., "Input incomplete") should have been set by get_scenario_solution_from_ui
                      if ai_initiated:
                           logger.error("AI initiated check, but failed to get solution from UI.")
                           self._set_feedback("AI Error: Failed to retrieve solution from UI!", "red", bold=True)
                           self._stop_ai_solver() # Stop AI on error
                      return # Stop check if UI data retrieval failed
                 # Check the retrieved data against the puzzle's solution
                 is_correct = self.game_state.check_solution(user_solution_data)
                 # Store the valid attempt in scenario_user_state *after* getting it from UI
                 self.game_state.scenario_user_state = user_solution_data

            else:
                 self._set_feedback("Error: Cannot check unknown puzzle type.", "red")
                 logger.error(f"Attempted to check unknown puzzle type: {type(puzzle)}")
                 if ai_initiated: self._stop_ai_solver()
                 return

            # --- Process Result ---
            if is_correct:
                logger.info(f"Level {puzzle.level + 1} SOLVED.")
                self._set_feedback(f"Correct! Level {puzzle.level + 1} Solved!", "green", bold=True)
                self.game_state.puzzles_solved += 1
                if self.level_label: self.level_label.setText(f"Level: {self.game_state.current_level + 1} (Solved: {self.game_state.puzzles_solved})")

                # Show educational feedback only if user solved it interactively
                if not ai_initiated:
                    try:
                        feedback_title = "Puzzle Solved!"
                        feedback_text = self._get_educational_feedback(puzzle)
                        QMessageBox.information(self, feedback_title, feedback_text)
                    except Exception as fb_err:
                        logger.error(f"Error generating educational feedback: {fb_err}", exc_info=True)

                # Check for theme unlocks
                unlocked_theme = self.game_state.check_unlockables()
                if unlocked_theme:
                    logger.info(f"Unlock condition met for theme: {unlocked_theme}")
                    if self.game_state.unlock_theme(unlocked_theme): # unlock_theme saves game
                        logger.info(f"Successfully unlocked theme: {unlocked_theme}")
                        if not ai_initiated:
                             QMessageBox.information(self, "Theme Unlocked!", f"Congratulations!\nYou have unlocked the '{unlocked_theme}' theme!")
                        else:
                             # Briefly update feedback during AI run without interrupting flow
                             self._set_feedback(f"AI Solver Running... Unlocked '{unlocked_theme}' theme!", "purple", bold=True)
                        self._update_theme_menu() # Update menu to reflect unlock
                    else:
                         logger.info(f"Theme '{unlocked_theme}' was already unlocked.")


                # --- Advance Level ---
                proceed_to_next = False
                if ai_initiated:
                    proceed_to_next = True # AI always proceeds automatically
                elif not self.is_ai_running: # Check user preference only if interactive
                    reply = QMessageBox.question(self, "Next Level?", "Proceed to the next level?",
                                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                                 QMessageBox.StandardButton.Yes)
                    proceed_to_next = (reply == QMessageBox.StandardButton.Yes)

                if proceed_to_next:
                    self.game_state.current_level += 1
                    logger.info(f"Advancing to level {self.game_state.current_level + 1}")
                    # Add slight delay before starting next puzzle if AI is running
                    if self.is_ai_running:
                        # Schedule the start of the next puzzle, then the AI step for it
                        QTimer.singleShot(int(self.ai_step_delay_ms / 3), self._start_next_ai_puzzle)
                    else:
                        self._start_next_human_puzzle() # Directly start for user
                else: # User chose not to proceed
                    logger.info("User chose not to proceed to the next level.")
                    # User solved it but doesn't want next level, disable further checks/hints
                    if self.check_button: self.check_button.setEnabled(False)
                    if self.hint_button: self.hint_button.setEnabled(False)
                    self._set_feedback(f"Level {puzzle.level + 1} Solved! Select 'New Puzzle' from Game menu for next.", "green")

            else: # Incorrect Solution
                logger.info(f"Solution check FAILED for Level {puzzle.level + 1}.")
                if ai_initiated:
                     # This implies the AI's provided solution was wrong, or internal solution is bad
                     logger.error(f"AI provided INCORRECT solution for Level {puzzle.level + 1}. Stopping AI.")
                     self._set_feedback(f"AI Error: Incorrect Solution Provided! Stopping.", "red", bold=True)
                     self._stop_ai_solver()
                else:
                     # Feedback for user
                     feedback_msg = "Incorrect solution. Keep trying!"
                     # Add more specific feedback for scenarios if possible
                     if isinstance(puzzle, ScenarioPuzzle):
                          feedback_msg += "\nDouble-check the information and your deductions."
                     self._set_feedback(feedback_msg, "red")

        except Exception as e:
             logger.exception("Error occurred during solution checking process.")
             self._set_feedback(f"Error checking solution: {e}", "red")
             if ai_initiated: self._stop_ai_solver() # Stop AI on any unexpected error during its check

    def _start_next_ai_puzzle(self):
        """Starts the next puzzle during an AI run."""
        if not self.is_ai_running:
             logger.warning("_start_next_ai_puzzle called when AI is not running.")
             return # Safety check

        logger.info("AI starting next puzzle...")
        try:
             self.game_state.start_new_puzzle() # Generate the next puzzle
             self._update_ui_for_puzzle() # Update UI for the new puzzle (disabling inputs)
             # Schedule the AI's first step (applying solution) for the *new* puzzle
             self.ai_timer.start(self.ai_step_delay_ms)
             self._set_feedback(f"AI: Starting Level {self.game_state.current_level + 1}...", "purple")
        except (ValueError, RuntimeError) as e:
            # Handle errors during puzzle generation
            logger.exception("AI failed to start next puzzle. Stopping AI.")
            self._set_feedback(f"AI Error starting next puzzle: {e}. Stopping.", "red", bold=True)
            self._stop_ai_solver()
        except Exception as e:
             # Handle unexpected errors
             logger.exception("Unexpected error starting next AI puzzle. Stopping AI.")
             self._set_feedback(f"Unexpected AI Error: {e}. Stopping.", "red", bold=True)
             self._stop_ai_solver()

    def _start_next_human_puzzle(self):
        """Starts the next puzzle after user solves interactively."""
        logger.info("User starting next puzzle...")
        try:
            self.game_state.start_new_puzzle()
            self._update_ui_for_puzzle()
            display_name = get_puzzle_type_display_name(self.game_state.current_puzzle)
            self._set_feedback(f"Started Level {self.game_state.current_level + 1}: {display_name}", "blue")
        except (ValueError, RuntimeError) as e:
             # Handle errors during puzzle generation
             logger.error(f"Failed to start next puzzle for user: {e}", exc_info=True)
             QMessageBox.critical(self, "Error", f"Could not generate the next puzzle:\n{e}")
             self._set_feedback("Error starting next puzzle.", "red")
             # What state should the UI be in? Maybe disable controls?
             if self.check_button: self.check_button.setEnabled(False)
             if self.hint_button: self.hint_button.setEnabled(False)
        except Exception as e:
             # Handle unexpected errors
             logger.exception("Unexpected error starting next human puzzle.")
             QMessageBox.critical(self, "Error", f"An unexpected error occurred:\n{e}")
             self._set_feedback("Error starting next puzzle.", "red")


    def _reset_puzzle(self):
        """Handles the 'Reset' button click."""
        if self.is_ai_running:
             logger.warning("Reset ignored while AI running.")
             return
        puzzle = self.game_state.current_puzzle
        if not puzzle:
            self._set_feedback("No puzzle active to reset.", "orange")
            return

        logger.info("Reset button clicked.")

        # Check if there's any progress to lose
        progress_made = False
        if isinstance(puzzle, Puzzle) and not puzzle.is_scenario and self.game_state.user_mapping:
             progress_made = True
        elif isinstance(puzzle, ScenarioPuzzle) and self.scenario_input_widget:
             # Basic check for common input types - could be more thorough
             widget = self.scenario_input_widget
             if isinstance(widget, (QLineEdit, QTextEdit)) and (widget.text() if isinstance(widget, QLineEdit) else widget.toPlainText()): progress_made = True
             elif isinstance(widget, QButtonGroup) and widget.checkedButton(): progress_made = True
             elif isinstance(widget, QTableWidget): # Assume table might have progress
                 # More detailed check: iterate through cells? For now, assume progress if table exists.
                 progress_made = True
        # Also consider hints used as progress
        if self.game_state.hints_used_this_level > 0:
            progress_made = True

        # Confirm with user if progress was made
        reply = QMessageBox.StandardButton.Yes
        if progress_made:
            reply = QMessageBox.question(self, "Confirm Reset",
                                         "Are you sure you want to reset all inputs and hints used for this puzzle?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            logger.info(f"Resetting puzzle state for Level {puzzle.level + 1}.")
            # Reset game state variables related to the current puzzle
            self.game_state.hints_used_this_level = 0
            self.game_state.user_mapping = {}
            self.game_state.scenario_user_state = None

            # Reset UI elements to initial state
            self._update_ui_for_puzzle() # This should redraw the puzzle UI in its default state
            # Explicitly update hints label after state reset
            if self.hints_label: self.hints_label.setText(f"Hints Left: {self.game_state.max_hints_per_level}")
            if self.hint_button: self.hint_button.setEnabled(True)
            if self.check_button: self.check_button.setEnabled(True) # Re-enable check button

            self._set_feedback("Puzzle reset.", "blue")
        else:
            logger.info("Puzzle reset cancelled by user.")


    # --- Helper Methods ---

    def _set_feedback(self, message: str, color: str = "", bold: bool = False):
        """Updates the feedback label with a message and optional color/style."""
        if not self.feedback_label:
            logger.warning("Feedback label not available.")
            return
        logger.debug(f"Setting feedback: '{message}' (Color: {color}, Bold: {bold})")
        self.feedback_label.setText(message)
        style = ""
        if color:
            style += f"color: {color};"
        if bold:
            style += "font-weight: bold;"
        self.feedback_label.setStyleSheet(style if style else "")
        # Ensure feedback is visible immediately
        QApplication.processEvents()

    def _get_educational_feedback(self, puzzle: Union[Puzzle, ScenarioPuzzle]) -> str:
        """Generates educational feedback text after a puzzle is solved."""
        logger.debug(f"Generating educational feedback for {type(puzzle).__name__}")
        base_feedback = "Puzzle Solved! Well done."
        details = ""

        try:
            if isinstance(puzzle, Puzzle) and not puzzle.is_scenario:
                details = "Symbol Cipher Solved!\n\nTechniques likely used:\n"
                techniques = set()
                # Access clue types used if stored, otherwise guess based on types present
                clue_types_used = getattr(puzzle, 'clue_types_used', set())
                if not isinstance(clue_types_used, set): clue_types_used = set()

                type_map = {
                    ClueType.DIRECT: "• Direct mapping (🔍)",
                    ClueType.EXCLUSION: "• Process of elimination (❌)",
                    ClueType.POSITIONAL: "• Positional reasoning (📍)",
                    ClueType.RELATIONAL: "• Relational analysis (↔️)",
                    ClueType.CATEGORY: "• Category-based reasoning (📑)",
                    ClueType.LOGICAL: "• Complex logical deduction (🧠)"
                }
                for clue_type in clue_types_used:
                    techniques.add(type_map.get(clue_type, f"• {clue_type.name} Clues"))

                if not techniques: techniques.add("• Careful deduction!")
                details += "\n".join(sorted(list(techniques)))
                return details

            elif isinstance(puzzle, ScenarioPuzzle):
                 scenario_type_name = get_puzzle_type_display_name(puzzle.puzzle_type)
                 details = f"Scenario Solved: {scenario_type_name}!\n\nSkills demonstrated:\n"
                 type_feedback = {
                    HumanScenarioType.LOGIC_GRID: "• Systematic grid deduction\n• Applying constraints logically",
                    HumanScenarioType.SCHEDULING: "• Constraint satisfaction\n• Time management logic",
                    HumanScenarioType.RELATIONSHIP_MAP: "• Mapping connections\n• Interpreting relational clues",
                    HumanScenarioType.ORDERING: "• Reconstructing sequences\n• Applying temporal logic",
                    HumanScenarioType.SOCIAL_DEDUCTION: "• Analyzing statements & motives\n• Identifying inconsistencies",
                    HumanScenarioType.COMMON_SENSE_GAP: "• Applying real-world knowledge\n• Identifying missing steps/items",
                    HumanScenarioType.DILEMMA: "• Evaluating consequences\n• Ethical or practical reasoning",
                    HumanScenarioType.AGENT_SIMULATION: "• Pattern recognition in behavior\n• Rule inference and application",
                 }
                 details += type_feedback.get(puzzle.puzzle_type, "• Careful reading and logical deduction")
                 return details
            else:
                 return base_feedback
        except Exception as e:
             logger.error(f"Error generating educational feedback details: {e}", exc_info=True)
             return base_feedback # Return generic feedback on error


    def _confirm_and_start_new_puzzle(self, puzzle_type: Optional[Union[str, HumanScenarioType]] = None):
        """Asks for confirmation if progress exists, then starts a new puzzle."""
        if self.is_ai_running:
             logger.warning("Manual new puzzle ignored while AI running.")
             self._set_feedback("Cannot start new puzzle while AI is running.", "orange")
             return

        puzzle = self.game_state.current_puzzle
        progress_made = False # Basic check if reset is meaningful

        if puzzle: # Only check for progress if a puzzle exists
            if isinstance(puzzle, Puzzle) and not puzzle.is_scenario and self.game_state.user_mapping: progress_made = True
            elif isinstance(puzzle, ScenarioPuzzle) and self.scenario_input_widget:
                widget = self.scenario_input_widget
                if isinstance(widget, (QLineEdit, QTextEdit)) and (widget.text() if isinstance(widget, QLineEdit) else widget.toPlainText()): progress_made = True
                elif isinstance(widget, QButtonGroup) and widget.checkedButton(): progress_made = True
                elif isinstance(widget, QTableWidget): progress_made = True # Assume table has progress
            if self.game_state.hints_used_this_level > 0: progress_made = True

        reply = QMessageBox.StandardButton.Yes
        if progress_made:
            reply = QMessageBox.question(self, "Confirm New Puzzle",
                                         "Start a new puzzle? Any progress on the current one will be lost.",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            logger.info(f"User confirmed starting new puzzle (Type requested: {puzzle_type}).")
            self.game_state.current_level = 0 # Reset level when starting manually
            self._start_next_human_puzzle() # Use the helper to start and update UI
        else:
             logger.info("User cancelled starting new puzzle.")


    def _save_game(self):
        """Handles the 'Save Game' menu action."""
        if self.is_ai_running:
            logger.warning("Manual save ignored while AI running.")
            self._set_feedback("Cannot save game while AI is running.", "orange")
            return

        logger.info("Save game action triggered.")
        try:
            # Ensure current UI state is saved if applicable (especially for scenarios)
            if isinstance(self.game_state.current_puzzle, ScenarioPuzzle):
                 current_ui_state = get_scenario_solution_from_ui(self, check_completeness=False)
                 if current_ui_state is not None:
                      self.game_state.scenario_user_state = current_ui_state
                 else:
                     logger.warning("Could not retrieve scenario state from UI for saving.")
                     # Decide whether to proceed without saving UI state or warn user further

            self.game_state.save_game()
            self._set_feedback("Game saved successfully!", "blue")
            # Clear feedback after delay
            QTimer.singleShot(3000, lambda: self._set_feedback("") if self.feedback_label and "saved successfully" in self.feedback_label.text() else None)
        except Exception as e:
            logger.exception("Error occurred during manual game save.")
            QMessageBox.warning(self, "Save Error", f"Could not save game state:\n{e}")
            self._set_feedback("Error saving game.", "red")


    def _update_theme_menu(self):
        """Updates the 'Themes' submenu based on available and unlocked themes."""
        if not self.theme_menu:
            logger.warning("Theme menu reference not set.")
            return
        self.theme_menu.clear()
        current_theme = self.game_state.current_theme
        unlocked = self.game_state.unlocked_themes

        logger.debug(f"Updating theme menu. Current: {current_theme}, Unlocked: {unlocked}")

        # Add actions for each theme defined in THEMES
        for theme_name in sorted(THEMES.keys()):
            action = QAction(theme_name, self, checkable=True)
            is_unlocked = theme_name in unlocked
            is_current = (theme_name == current_theme)

            action.setEnabled(is_unlocked)
            action.setChecked(is_current and is_unlocked)
            # Use lambda with default argument to capture the correct theme_name
            action.triggered.connect(lambda checked=False, name=theme_name: self._change_theme(name))

            # Optional: Add visual indication for locked themes?
            if not is_unlocked:
                 action.setText(f"{theme_name} (Locked)")
                 # action.setIcon(QIcon("path/to/lock/icon.png")) # Example

            self.theme_menu.addAction(action)


    def _change_theme(self, theme_name: str):
        """Applies the selected theme and saves the change."""
        if self.is_ai_running:
             logger.warning("Theme change ignored while AI running.")
             self._set_feedback("Cannot change theme while AI is running.", "orange")
             return

        if theme_name in self.game_state.unlocked_themes:
            if theme_name != self.game_state.current_theme:
                logger.info(f"Changing theme to: {theme_name}")
                self.game_state.current_theme = theme_name
                self._apply_theme()
                self._update_theme_menu() # Update checkmarks
                # Save the theme change
                try:
                    self.game_state.save_game()
                except Exception as e:
                    logger.error(f"Failed to save game after theme change: {e}")
                    QMessageBox.warning(self, "Save Error", f"Failed to save theme preference: {e}")
            else:
                logger.debug(f"Theme '{theme_name}' is already active.")
                # Ensure checkmark is correct even if clicked again
                self._update_theme_menu()

        else:
            logger.warning(f"Attempted to change to locked theme: {theme_name}")
            # Optionally show a message?
            # QMessageBox.information(self, "Theme Locked", f"The theme '{theme_name}' is not yet unlocked.")
            # Re-update menu to ensure correct checkmark state if user somehow triggered locked action
            self._update_theme_menu()


    def _apply_theme(self):
        """Applies the current theme's stylesheet to the main window."""
        theme_name = self.game_state.current_theme
        theme_data = THEMES.get(theme_name)
        if theme_data:
            logger.debug(f"Applying theme: {theme_name}")
            try:
                 self.setStyleSheet(theme_data.stylesheet)
                 # Reset feedback style to avoid theme overrides
                 if self.feedback_label and not self.is_ai_running: # Don't clear AI feedback
                      self.feedback_label.setStyleSheet("")
                 QApplication.processEvents() # Try to force style update
            except Exception as e:
                 logger.error(f"Error applying stylesheet for theme '{theme_name}': {e}")
                 self.setStyleSheet("") # Fallback to default style
        else:
            logger.warning(f"Theme '{theme_name}' not found in THEMES dictionary. Applying default style.")
            self.setStyleSheet("") # Apply default Qt style


    # --- Dialog Launchers ---

    def _select_puzzle_type(self):
        """Opens the dialog to select a new puzzle type."""
        if self.is_ai_running:
             logger.warning("Select puzzle type ignored while AI running.")
             return
        logger.debug("Opening puzzle type selection dialog.")
        dialog = PuzzleTypeDialog(self) # Parent is the main window
        if dialog.exec() == QDialog.DialogCode.Accepted:
             selected_type = dialog.selected_type
             logger.info(f"User selected puzzle type: {selected_type}")
             self._confirm_and_start_new_puzzle(selected_type)
        else:
             logger.debug("Puzzle type selection cancelled.")


    def _show_tutorial(self):
        """Displays the tutorial dialog."""
        if self.is_ai_running: return
        logger.debug("Showing tutorial dialog.")
        dialog = TutorialDialog(self)
        dialog.exec()

    def _show_practice_puzzle(self):
        """Displays the practice puzzle dialog."""
        if self.is_ai_running: return
        logger.debug("Showing practice puzzle dialog.")
        dialog = PracticePuzzleDialog(self)
        dialog.exec()

    def _show_how_to_play(self):
        """Displays the 'How to Play' information dialog."""
        if self.is_ai_running: return
        logger.debug("Showing How to Play dialog.")
        # Using a simple QMessageBox for now, but could be a custom dialog
        # Consider loading content from a file if it gets long
        how_to_play_text = """
        <h2>How to Play</h2>
        <p>Welcome to The Alchemist's Cipher & Logic Puzzles!</p>
        <ul>
            <li><b>Goal:</b> Solve the presented logic puzzle. This could be a Symbol Cipher or a various Scenario Puzzles.</li>
            <li><b>Symbol Ciphers:</b> Use the clues provided in the 'Alchemist's Notes' to deduce the correct letter for each symbol. Select the letter from the dropdown next to each symbol.</li>
            <li><b>Scenario Puzzles:</b> Read the scenario description, goal, and information carefully. Use the input area (which changes based on puzzle type - grid, text box, options, etc.) to enter your solution based on logical deduction.</li>
            <li><b>Controls:</b>
                <ul>
                    <li><b>Hint:</b> Use a hint if you're stuck (limited per puzzle). Hints may reveal part of the solution or guide your thinking.</li>
                    <li><b>Check:</b> Check if your current input/assignment is the correct solution.</li>
                    <li><b>Reset:</b> Clear your current inputs and hints used for the current puzzle.</li>
                    <li><b>AI Solver (Menu):</b> Let an AI attempt to solve the puzzle step-by-step (disables manual interaction).</li>
                </ul>
            </li>
            <li><b>Themes:</b> Unlock new visual themes by solving puzzles! Change themes via the 'Options' menu.</li>
            <li><b>Saving:</b> The game saves automatically when you start a new puzzle, unlock a theme, or exit. You can also save manually via the 'Game' menu.</li>
        </ul>
        <p>Good luck, strategist!</p>
        """
        QMessageBox.information(self, "How to Play", how_to_play_text)

    def _show_about(self):
        """Displays the 'About' information box."""
        if self.is_ai_running: return
        logger.debug("Showing About dialog.")
        version = "2.4.0" # Example version (consider storing centrally)
        save_version = self.game_state.SAVE_VERSION
        QMessageBox.about(self, "About The Alchemist's Cipher",
                          f"The Alchemist's Cipher & Logic Puzzles\n"
                          f"Version {version}\n\n"
                          f"A collection of logic puzzles and scenarios.\n"
                          f"Built with Python & PyQt6.\n\n"
                          f"(Save File Version: {save_version})\n"
                          f"(c) 2025 Epistemophile")


    # --- AI Solver Control Methods ---

    def _start_ai_solver(self):
        """Initiates the AI solver in step-by-step mode."""
        if self.is_ai_running:
             logger.warning("Start AI called when already running.")
             return
        if not self.game_state.current_puzzle:
             QMessageBox.warning(self, "AI Solver", "No puzzle active to solve.")
             return

        logger.info("Starting AI Solver (Step-by-Step)...")
        self.is_ai_running = True
        # Disable interactive elements and update menu states
        self._set_ui_interactive(False)
        # Start the first step after a short delay to allow UI update
        QTimer.singleShot(100, self._ai_step)
        self._set_feedback("AI Solver Running (Step Mode)...", "purple", bold=True)

    def _stop_ai_solver(self):
        """Stops the AI solver if it's running."""
        if not self.is_ai_running:
             logger.warning("Stop AI called when not running.")
             return
        logger.info("Stopping AI Solver.")
        self.is_ai_running = False
        self.ai_timer.stop() # Stop any pending timer activity (like next step)
        # Re-enable interactive elements and update menu states
        self._set_ui_interactive(True)
        self._set_feedback("AI Solver Stopped.", "blue")

    def _set_ui_interactive(self, interactive: bool, checking: bool = False):
        """Enables or disables UI elements based on AI running state."""
        logger.debug(f"Setting UI interactive state to: {interactive}")
        # Menu Actions
        if self.run_ai_action: self.run_ai_action.setEnabled(interactive)
        if self.stop_ai_action: self.stop_ai_action.setEnabled(self.is_ai_running)
        # Consider disabling other menus like Game->New, Options->Theme?
        # if self.game_menu: self.game_menu.setEnabled(interactive) # Example if menu ref stored
        # if self.options_menu: self.options_menu.setEnabled(interactive) # Example

        # Control Buttons
        if self.hint_button: self.hint_button.setEnabled(interactive and self.game_state.hints_used_this_level < self.game_state.max_hints_per_level)
        if self.check_button: self.check_button.setEnabled(interactive)
        if self.reset_button: self.reset_button.setEnabled(interactive)

        # Puzzle Input Widgets
        # Symbol Cipher Combos
        for symbol_data in self.assignment_widgets.values():
            combo = symbol_data.get('combo')
            if combo: combo.setEnabled(interactive)
        # Scenario Input Widget
        if self.scenario_input_widget:
            self.scenario_input_widget.setEnabled(interactive)
            # Special handling for tables/button groups if needed
            if isinstance(self.scenario_input_widget, QTableWidget):
                # Enable/disable individual cell widgets within the table
                table = self.scenario_input_widget
                for r in range(table.rowCount()):
                    for c in range(table.columnCount()):
                         cell_widget = table.cellWidget(r, c)
                         if cell_widget: cell_widget.setEnabled(interactive)
            elif isinstance(self.scenario_input_widget, QButtonGroup):
                 for button in self.scenario_input_widget.buttons():
                      button.setEnabled(interactive)

        # --- Control Bar Buttons --- 
        # Special handling during the brief "Correct!" message display period
        if checking and not interactive:
             if self.check_button: self.check_button.setEnabled(False)
             if self.reset_button: self.reset_button.setEnabled(False)
             if self.hint_button: self.hint_button.setEnabled(False)
        else: # Restore normal button state based on interactiveness and game state
             if self.check_button: self.check_button.setEnabled(interactive)
             if self.reset_button: self.reset_button.setEnabled(interactive)
             hints_left = 0
             if self.game_state and self.game_state.current_puzzle:
                  hints_left = self.game_state.max_hints_per_level - self.game_state.hints_used_this_level
             if self.hint_button: self.hint_button.setEnabled(interactive and hints_left > 0)
             
        logger.debug(f"UI Interactive state set to: {interactive}")


    def _ai_step(self):
        """Performs one step of the AI solver: Get solution, apply to UI."""
        if not self.is_ai_running: return # Stop if flag turned off externally

        puzzle = self.game_state.current_puzzle
        if not puzzle:
            logger.error("AI step: No puzzle found. Stopping.")
            self._set_feedback("AI Error: No Puzzle Active! Stopping.", "red", bold=True)
            self._stop_ai_solver()
            return

        level = puzzle.level + 1
        logger.debug(f"AI Step: Applying solution to UI for Level {level}")
        self._set_feedback(f"AI: Applying solution to Level {level}...", "purple")

        try:
            # --- Get the correct solution (using internal solver for step-by-step) ---
            # In a real scenario, you might call the selected external AI solver here,
            # but for step-by-step visualization, using the internal one makes sense.
            from ai.solvers import InternalSolver # Local import for clarity
            internal_solver = InternalSolver()
            correct_solution_data = internal_solver.solve(puzzle)

            if correct_solution_data is None:
                 logger.error(f"AI Step: Internal solver failed to get solution for Level {level}. Stopping.")
                 self._set_feedback(f"AI Error: Could not get internal solution for Level {level}! Stopping.", "red", bold=True)
                 self._stop_ai_solver()
                 return

            # --- Apply the solution visually to the UI ---
            success = self._ai_apply_solution_to_ui(correct_solution_data)

            if not success:
                 logger.error(f"AI Step: Failed to apply solution to UI for Level {level}. Stopping.")
                 self._set_feedback("AI Error: Failed applying solution to UI. Stopping.", "red", bold=True)
                 self._stop_ai_solver()
                 return

            # Solution applied visually, now schedule the check after a delay
            logger.debug(f"AI Step: Solution applied to UI. Scheduling check in {self.ai_step_delay_ms}ms.")
            self.ai_timer.singleShot(self.ai_step_delay_ms, lambda: self._check_solution(ai_initiated=True))

        except Exception as e:
            logger.exception(f"AI Step: Unexpected error applying solution to UI for Level {level}. Stopping.")
            self._set_feedback(f"AI Error applying solution: {e}. Stopping.", "red", bold=True)
            self._stop_ai_solver()


    def _ai_apply_solution_to_ui(self, solution_data: Dict[str, Any]) -> bool:
        """Reads the correct solution data and updates the UI widgets."""
        puzzle = self.game_state.current_puzzle
        if not puzzle:
            logger.error("AI Apply UI: No puzzle active.")
            return False

        logger.debug(f"AI applying solution data to UI: {solution_data}")

        try:
            if isinstance(puzzle, Puzzle) and not puzzle.is_scenario:
                # --- Apply Symbol Cipher Solution ---
                if not isinstance(solution_data, dict):
                    logger.error("AI Apply UI (Symbol): Solution data is not a dictionary.")
                    return False
                for symbol, letter in solution_data.items():
                    if symbol not in self.assignment_widgets:
                        logger.warning(f"AI Apply UI (Symbol): Symbol '{symbol}' from solution not found in UI widgets.")
                        continue # Skip symbols not in UI
                    if not self._ai_set_symbol_combo(symbol, str(letter)): # Ensure letter is string
                        logger.error(f"AI Apply UI (Symbol): Failed to set symbol '{symbol}' to '{letter}'.")
                        return False # Stop if any assignment fails
                # Ensure internal game state reflects the applied solution for the check
                self.game_state.user_mapping = solution_data.copy()
                
                # Add debug logging to track user_mapping state
                logger.debug(f"AI Set user_mapping: {self.game_state.user_mapping} (len: {len(self.game_state.user_mapping)})")
                logger.debug(f"Expected elements: {puzzle.num_elements}")
                
                # Double-check to ensure mapping is correct before proceeding
                if len(self.game_state.user_mapping) != puzzle.num_elements:
                    logger.error(f"AI Solution incomplete: user_mapping has {len(self.game_state.user_mapping)}/{puzzle.num_elements} elements")
                    # Try to repair if possible
                    for symbol in puzzle.symbols:
                        if symbol not in self.game_state.user_mapping and symbol in solution_data:
                            logger.warning(f"Fixing missing symbol '{symbol}' in user_mapping")
                            self.game_state.user_mapping[symbol] = solution_data[symbol]
                
                # Now update UI to match the corrected state
                update_symbol_assignments_display(self) # Update UI visual state (disabled letters)

            elif isinstance(puzzle, ScenarioPuzzle):
                # --- Apply Scenario Solution ---
                logger.debug(f"AI applying Scenario solution ({puzzle.puzzle_type.name}).")

                if puzzle.puzzle_type == HumanScenarioType.LOGIC_GRID:
                    if 'grid' not in solution_data or not isinstance(self.scenario_input_widget, QTableWidget): return False
                    grid_solution = solution_data['grid'] # {entity: {cat: val}}
                    if not self._ai_set_logic_grid(grid_solution): return False

                elif puzzle.puzzle_type == HumanScenarioType.RELATIONSHIP_MAP:
                    if 'map' not in solution_data or not isinstance(self.scenario_input_widget, QTextEdit): return False
                    map_solution = solution_data['map'] # {p1: p2, p2: p1, ...}
                    if not self._ai_set_relationship_map(map_solution): return False

                elif puzzle.puzzle_type == HumanScenarioType.ORDERING:
                    if 'order' not in solution_data or not isinstance(self.scenario_input_widget, QTableWidget): return False
                    order_solution = solution_data['order'] # ["item1", "item2", ...]
                    if not self._ai_set_ordering_table(order_solution): return False

                elif puzzle.puzzle_type == HumanScenarioType.SCHEDULING:
                    if 'schedule' not in solution_data or not isinstance(self.scenario_input_widget, QTableWidget): return False
                    schedule_solution = solution_data['schedule'] # {person: {slot: status}}
                    if not self._ai_set_scheduling_table(schedule_solution): return False

                elif puzzle.puzzle_type == HumanScenarioType.DILEMMA:
                    if 'choice' not in solution_data or not isinstance(self.scenario_input_widget, QButtonGroup): return False
                    choice_solution = solution_data['choice']
                    if not self._ai_set_dilemma_choice(choice_solution): return False

                elif puzzle.puzzle_type in [HumanScenarioType.SOCIAL_DEDUCTION, HumanScenarioType.COMMON_SENSE_GAP, HumanScenarioType.AGENT_SIMULATION]:
                    if 'answer' not in solution_data or not isinstance(self.scenario_input_widget, QLineEdit): return False
                    answer_solution = solution_data['answer']
                    if not self._ai_set_line_edit(answer_solution): return False

                else:
                    logger.warning(f"AI apply solution to UI: Update not implemented for {puzzle.puzzle_type.name}")
                    # For unimplemented types, we can't apply to UI.
                    # Should we fail, or proceed to check assuming internal state is correct?
                    # Let's return False for now, as UI update failed.
                    return False

            else:
                logger.error(f"AI Apply UI: Unknown puzzle type {type(puzzle)}")
                return False

            QApplication.processEvents() # Ensure UI updates are visible before proceeding
            logger.debug("AI successfully applied solution data to UI.")
            return True

        except Exception as e:
            logger.exception(f"Error in _ai_apply_solution_to_ui for {type(puzzle)}: {e}")
            return False

    # --- AI Helper methods to set UI values ---
    # These methods directly manipulate the UI widgets based on the AI's solution data.

    def _ai_set_symbol_combo(self, symbol: str, letter: str) -> bool:
        """Sets the QComboBox for a given symbol to the specified letter."""
        widget_dict = self.assignment_widgets.get(symbol)
        if not widget_dict or 'combo' not in widget_dict:
             logger.error(f"AI UI Set: Combo widget not found for symbol '{symbol}'.")
             return False
        combo_box: QComboBox = widget_dict['combo']
        index = combo_box.findText(letter)
        if index >= 0:
            combo_box.blockSignals(True) # Prevent triggering _assign_letter
            combo_box.setCurrentIndex(index)
            combo_box.blockSignals(False)
            # logger.debug(f"AI UI Set: Set '{symbol}' combo to '{letter}' (index {index}).")
            return True
        else:
            logger.warning(f"AI UI Set: Could not find letter '{letter}' in combo box items for symbol '{symbol}'. Items: {[combo_box.itemText(i) for i in range(combo_box.count())]}")
            return False # Letter not found in combo options

    def _ai_set_line_edit(self, text: str) -> bool:
        """Sets the text of the main scenario QLineEdit widget."""
        if isinstance(self.scenario_input_widget, QLineEdit):
            self.scenario_input_widget.setText(str(text)) # Ensure string
            logger.debug(f"AI UI Set: Set LineEdit text to '{text}'.")
            return True
        logger.error(f"AI UI Set: Expected QLineEdit, but found {type(self.scenario_input_widget)}.")
        return False

    def _ai_set_relationship_map(self, solution_map: Dict[str, str]) -> bool:
        """Formats the solution map and sets the text of the QTextEdit."""
        if not isinstance(self.scenario_input_widget, QTextEdit):
             logger.error(f"AI UI Set: Expected QTextEdit for Relationship Map, found {type(self.scenario_input_widget)}.")
             return False
        # Format the map into "P1 : P2" lines, avoiding duplicate pairs
        text_lines = []
        processed_pairs = set()
        for p1, p2 in solution_map.items():
             pair = frozenset({str(p1), str(p2)}) # Ensure strings for set
             if pair not in processed_pairs:
                  text_lines.append(f"{p1} : {p2}")
                  processed_pairs.add(pair)
        logger.debug(f"AI UI Set: Setting Relationship Map text to:\n{text_lines}")
        self.scenario_input_widget.setPlainText("\n".join(text_lines))
        return True

    def _ai_set_ordering_table(self, ordered_items: List[str]) -> bool:
        """Sets the QComboBoxes in the ordering table."""
        if not isinstance(self.scenario_input_widget, QTableWidget):
            logger.error(f"AI UI Set: Expected QTableWidget for Ordering, found {type(self.scenario_input_widget)}.")
            return False
        table: QTableWidget = self.scenario_input_widget
        if table.rowCount() != len(ordered_items):
            logger.error(f"AI UI Set (Ordering): Row count mismatch ({table.rowCount()} vs {len(ordered_items)} items).")
            return False
        logger.debug(f"AI UI Set: Setting Ordering table based on: {ordered_items}")
        for r, item in enumerate(ordered_items):
             cell_widget = table.cellWidget(r, 0)
             if isinstance(cell_widget, QComboBox):
                  index = cell_widget.findText(str(item)) # Ensure item is string
                  if index >= 0:
                      cell_widget.blockSignals(True)
                      cell_widget.setCurrentIndex(index)
                      cell_widget.blockSignals(False)
                  else:
                      logger.warning(f"AI UI Set (Ordering): Item '{item}' not found in combo box at row {r}.")
                      # Should we fail here? If the UI wasn't set up correctly maybe... Yes, fail.
                      return False
             else:
                 logger.error(f"AI UI Set (Ordering): Expected QComboBox at row {r}, found {type(cell_widget)}.")
                 return False
        return True

    def _ai_set_scheduling_table(self, schedule: Dict[str, Dict[str, str]]) -> bool:
        """Sets the QComboBoxes ('', '✔️') in the scheduling table."""
        if not isinstance(self.scenario_input_widget, QTableWidget):
            logger.error(f"AI UI Set: Expected QTableWidget for Scheduling, found {type(self.scenario_input_widget)}.")
            return False
        table: QTableWidget = self.scenario_input_widget
        try:
            people = [table.verticalHeaderItem(r).text() for r in range(table.rowCount())]
            slots = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
        except AttributeError:
             logger.error("AI UI Set (Scheduling): Could not get headers from table.")
             return False

        logger.debug(f"AI UI Set: Setting Scheduling table based on: {schedule}")
        for r, person in enumerate(people):
             if person not in schedule:
                 logger.warning(f"AI UI Set (Scheduling): Person '{person}' from UI not found in solution data.")
                 continue # Or fail?
             for c, slot in enumerate(slots):
                  if slot not in schedule[person]:
                      logger.warning(f"AI UI Set (Scheduling): Slot '{slot}' not found for person '{person}' in solution data.")
                      continue # Or fail?

                  status = schedule[person][slot] # Should be "Booked" or "Available"
                  target_text = "✔️" if status == "Booked" else ""
                  cell_widget = table.cellWidget(r, c)

                  if isinstance(cell_widget, QComboBox):
                       index = cell_widget.findText(target_text)
                       if index >= 0:
                            cell_widget.blockSignals(True)
                            cell_widget.setCurrentIndex(index)
                            cell_widget.blockSignals(False)
                       else:
                            logger.warning(f"AI UI Set (Scheduling): Text '{target_text}' not found in combo at ({r},{c}). Items: {[cell_widget.itemText(i) for i in range(cell_widget.count())]}")
                            # Fail if the expected state isn't an option
                            return False
                  else:
                      logger.error(f"AI UI Set (Scheduling): Expected QComboBox at ({r},{c}), found {type(cell_widget)}.")
                      return False
        return True

    def _ai_set_dilemma_choice(self, choice_text: str) -> bool:
        """Checks the radio button corresponding to the solution choice."""
        if not isinstance(self.scenario_input_widget, QButtonGroup):
            logger.error(f"AI UI Set: Expected QButtonGroup for Dilemma, found {type(self.scenario_input_widget)}.")
            return False
        group: QButtonGroup = self.scenario_input_widget
        logger.debug(f"AI UI Set: Setting Dilemma choice to '{choice_text}'.")
        found = False
        for button in group.buttons():
            if isinstance(button, QRadioButton) and button.text() == choice_text:
                button.setChecked(True)
                found = True
                break
        if not found:
            logger.warning(f"AI UI Set (Dilemma): Choice text '{choice_text}' not found among radio buttons.")
            # Fail if the correct option doesn't exist in the UI
            return False
        return True

    def _ai_set_logic_grid(self, grid_solution: Dict[str, Dict[str, str]]) -> bool:
        """Sets the combo boxes ('✔️', '❌') in the logic grid table."""
        if not isinstance(self.scenario_input_widget, QTableWidget):
            logger.error(f"AI UI Set: Expected QTableWidget for Logic Grid, found {type(self.scenario_input_widget)}.")
            return False
        table: QTableWidget = self.scenario_input_widget
        col_map = self.scenario_input_widgets.get('logic_grid_col_map') # {col_index: (cat_name, elem_value)}

        if not col_map:
            logger.error("AI UI Set (Logic Grid): Column mapping data ('logic_grid_col_map') not found.")
            return False

        try:
            row_headers = [table.verticalHeaderItem(r).text() for r in range(table.rowCount())]
        except AttributeError:
            logger.error("AI UI Set (Logic Grid): Could not get row headers.")
            return False

        logger.debug(f"AI UI Set: Setting Logic Grid table based on: {grid_solution}")

        for r, entity_name in enumerate(row_headers):
            if entity_name not in grid_solution:
                logger.warning(f"AI UI Set (Logic Grid): Entity '{entity_name}' from UI not in solution grid.")
                continue # Or fail?

            entity_solution = grid_solution[entity_name] # {cat: value}

            for c in range(table.columnCount()):
                 if c not in col_map:
                      logger.error(f"AI UI Set (Logic Grid): Column index {c} not in column map.")
                      return False # Mapping error
                 category_name, element_value = col_map[c]

                 cell_widget = table.cellWidget(r, c)
                 if not isinstance(cell_widget, QComboBox):
                     logger.error(f"AI UI Set (Logic Grid): Expected QComboBox at ({r},{c}), found {type(cell_widget)}.")
                     return False

                 # Determine if this cell should be Yes (✔️) or No (❌) based on the solution
                 # This assumes the solution grid *only* contains the 'Yes' mappings.
                 is_yes = (entity_solution.get(category_name) == element_value)
                 target_text = "✔️" if is_yes else "❌"

                 index = cell_widget.findText(target_text)
                 if index >= 0:
                     cell_widget.blockSignals(True)
                     cell_widget.setCurrentIndex(index)
                     cell_widget.blockSignals(False)
                 else:
                      logger.warning(f"AI UI Set (Logic Grid): Text '{target_text}' not found in combo at ({r},{c}) for {entity_name}/{category_name}={element_value}. Items: {[cell_widget.itemText(i) for i in range(cell_widget.count())]}")
                      return False # Fail if expected UI state isn't possible
        return True


    # --- Event Handlers ---

    def closeEvent(self, event):
        """Handles the main window closing event."""
        logger.info("Close event triggered.")
        # Stop AI if running
        if self.is_ai_running:
            logger.info("Stopping AI solver before closing.")
            self._stop_ai_solver()

        # Attempt to save game state
        try:
            # Ensure current UI state is captured before saving
            if isinstance(self.game_state.current_puzzle, ScenarioPuzzle):
                 current_ui_state = get_scenario_solution_from_ui(self, check_completeness=False)
                 if current_ui_state is not None: self.game_state.scenario_user_state = current_ui_state

            logger.info("Attempting to save game on exit...")
            self.game_state.save_game()
            logger.info("Game saved successfully on exit.")
            event.accept() # Allow window to close
        except Exception as e:
            logger.error(f"Failed to save game state on exit: {e}", exc_info=True)
            reply = QMessageBox.warning(self, "Save Error",
                                        f"Could not save game state on exit:\n{e}\n\nExit without saving?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                        QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                logger.warning("Exiting without saving due to error and user confirmation.")
                event.accept() # Allow closing despite save error
            else:
                logger.info("Exit cancelled by user due to save error.")
                event.ignore() # Prevent window from closing

# --- main Function (Entry Point) ---
def main():
    """Main function to initialize and run the PyQt application."""
    app = QApplication(sys.argv)
    # Set application details (optional but good practice)
    app.setApplicationName("Alchemist Cipher Logic Puzzles")
    app.setOrganizationName("AI Logic Games") # Replace with your org/name

    # --- Set Application Icon ---
    try:
        # Path logic specifically for the icon
        if getattr(sys, 'frozen', False):
            # The application is running frozen (packed by PyInstaller)
            icon_base_path = sys._MEIPASS
        else:
            # The application is running in a normal Python environment
            icon_base_path = os.path.dirname(os.path.abspath(__file__))
            # If __file__ is in ui/, go up one level to project root relative path
            icon_base_path = os.path.join(icon_base_path, '..') 
        
        icon_path = os.path.join(icon_base_path, "icons/app-logo(V2).ico")
        icon_path = os.path.normpath(icon_path) # Normalize path separators
        
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
            logging.info(f"Loaded window icon from: {icon_path}")
        else:
            logging.warning(f"Window icon not found at calculated path: {icon_path}")
            # Fallback to theme icon if custom icon not found
            app.setWindowIcon(QIcon.fromTheme("applications-education")) 
    except Exception as e:
        logging.error(f"Error setting window icon: {e}", exc_info=True)
        # Fallback to theme icon on any error
        app.setWindowIcon(QIcon.fromTheme("applications-education")) 

    # Set level to DEBUG to see detailed logs
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s')
    # Explicitly set root logger level AFTER basicConfig to ensure it takes effect
    logging.getLogger().setLevel(logging.DEBUG)
    logger.info("Application starting...")

    window = SymbolCipherGame()
    window.show()

    logger.info("Entering application event loop.")
    exit_code = app.exec()
    logger.info(f"Application exiting with code {exit_code}.")
    sys.exit(exit_code)

# Ensure this script can be run directly
if __name__ == '__main__':
    main()