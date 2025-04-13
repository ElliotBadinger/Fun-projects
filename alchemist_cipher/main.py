import sys
from typing import Optional, Dict, Any, Union
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QPushButton, QLabel, QComboBox,
                           QTextEdit, QMessageBox, QMenuBar, QMenu, QGridLayout,
                           QFrame, QSizePolicy, QTableWidget, QTableWidgetItem,
                           QHeaderView, QLineEdit, QDialog, QRadioButton, QButtonGroup,
                           QScrollArea, QAbstractItemView)
from PyQt6.QtCore import Qt, QSize, QTimer # Import QTimer
from PyQt6.QtGui import QFont, QIcon, QAction

from .game_state import GameState
from .themes import THEMES
from .tutorial import TutorialDialog, PracticePuzzleDialog
from .puzzle import Puzzle, ScenarioPuzzle, ClueType, HumanScenarioType, PuzzleGenerator
import logging

# Setup basic logging if not already done elsewhere
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class SymbolCipherGame(QMainWindow):
    """Main application window for The Alchemist's Cipher & Logic Puzzles game.

    Handles the game UI, interactions, state management calls, and puzzle display.
    """
    def __init__(self):
        """Initializes the main game window, game state, and UI components."""
        super().__init__()
        self.game_state = GameState()
        self.assignment_widgets: Dict[str, Dict[str, QComboBox]] = {}
        self.scenario_input_widget: Optional[QWidget] = None
        self.scenario_input_widgets: Dict[str, QWidget] = {}

        # --- AI Solver Attributes ---
        self.ai_timer = QTimer(self)
        self.ai_timer.timeout.connect(self._ai_step)
        self.is_ai_running = False
        self.ai_update_interval_ms = 500 # Time between AI steps (milliseconds)
        # --- End AI Solver Attributes ---

        self.setWindowTitle("The Alchemist's Cipher & Logic Puzzles")
        self.setMinimumSize(900, 700)

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self._create_menu_bar()
        self._create_info_bar(main_layout)
        self._create_game_area(main_layout)
        self._create_control_bar(main_layout)
        self._create_feedback_label(main_layout)

        # Load game or start new
        try:
            self.game_state.load_game()
            if not self.game_state.current_puzzle:
                logging.info("No puzzle loaded, starting a new default puzzle.")
                # Don't confirm if no puzzle exists
                self.game_state.start_new_puzzle()
                self._update_ui_for_puzzle()
            else:
                # Puzzle loaded, just update UI
                self._update_ui_for_puzzle()

        except Exception as e:
            logging.exception("Error during initial game load or puzzle start.")
            QMessageBox.critical(self, "Initialization Error",
                                 f"An error occurred during loading or initialization: {e}\n"
                                 "Starting a fresh game state.")
            self.game_state = GameState()
            # Don't confirm if starting fresh
            self.game_state.start_new_puzzle()
            self._update_ui_for_puzzle()

        self._apply_theme()

    def _create_menu_bar(self):
        """Creates the main menu bar (Game, Options, Help)."""
        menubar = self.menuBar()

        # Game Menu
        game_menu = menubar.addMenu("Game")
        new_action = QAction("New Random Puzzle", self)
        new_action.triggered.connect(lambda: self._confirm_and_start_new_puzzle(None))
        game_menu.addAction(new_action)

        select_type_action = QAction("Select Puzzle Type...", self)
        select_type_action.triggered.connect(self._select_puzzle_type)
        game_menu.addAction(select_type_action)

        save_action = QAction("Save Game", self)
        save_action.triggered.connect(self._save_game)
        game_menu.addAction(save_action)
        game_menu.addSeparator()

        # --- AI Solver Menu Items ---
        self.run_ai_action = QAction("Run AI Solver", self)
        self.run_ai_action.triggered.connect(self._start_ai_solver)
        game_menu.addAction(self.run_ai_action)

        self.stop_ai_action = QAction("Stop AI Solver", self)
        self.stop_ai_action.triggered.connect(self._stop_ai_solver)
        self.stop_ai_action.setEnabled(False) # Initially disabled
        game_menu.addAction(self.stop_ai_action)
        # --- End AI Solver Menu Items ---

        game_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        game_menu.addAction(exit_action)

        # Options Menu
        options_menu = menubar.addMenu("Options")
        self.theme_menu = options_menu.addMenu("Themes")
        self._update_theme_menu()

        # Help Menu
        help_menu = menubar.addMenu("Help")
        tutorial_action = QAction("Logic Tutorial", self)
        tutorial_action.triggered.connect(self._show_tutorial)
        help_menu.addAction(tutorial_action)

        practice_action = QAction("Practice Puzzle", self)
        practice_action.triggered.connect(self._show_practice_puzzle)
        help_menu.addAction(practice_action)

        how_to_play = QAction("How to Play", self)
        how_to_play.triggered.connect(self._show_how_to_play)
        help_menu.addAction(how_to_play)

        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    # --- Rest of the methods from ui.py (like _create_info_bar, _create_game_area etc.) remain the same ---
    # --- Paste them here, unchanged, unless explicitly modified below ---

    def _create_info_bar(self, parent_layout):
        """Creates the top information bar displaying level, puzzle type, and hints."""
        info_bar = QHBoxLayout()
        self.level_label = QLabel("Level: 1")
        self.level_label.setFont(QFont("Arial", 12))
        info_bar.addWidget(self.level_label)

        info_bar.addStretch()

        self.puzzle_type_label = QLabel("Type: Unknown")
        self.puzzle_type_label.setFont(QFont("Arial", 12))
        info_bar.addWidget(self.puzzle_type_label)

        info_bar.addStretch()

        self.hints_label = QLabel(f"Hints Left: {self.game_state.max_hints_per_level}")
        self.hints_label.setFont(QFont("Arial", 12))
        info_bar.addWidget(self.hints_label)

        parent_layout.addLayout(info_bar)

    def _create_game_area(self, parent_layout):
        """Creates the main game area layout, including puzzle input and clues sections."""
        self.game_area_layout = QHBoxLayout()

        # Puzzle Area (Left - Scrollable)
        self.puzzle_scroll_area = QScrollArea()
        self.puzzle_scroll_area.setWidgetResizable(True)
        self.puzzle_frame = QFrame(self.puzzle_scroll_area)
        self.puzzle_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        self.puzzle_area_layout = QVBoxLayout(self.puzzle_frame)
        self.puzzle_scroll_area.setWidget(self.puzzle_frame)

        # Add title placeholder to the inner layout
        self.puzzle_title_label = QLabel("Puzzle Area")
        self.puzzle_title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.puzzle_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.puzzle_area_layout.addWidget(self.puzzle_title_label)

        # Add a widget to hold the specific puzzle UI elements
        self.puzzle_content_widget = QWidget()
        self.puzzle_content_layout = QVBoxLayout(self.puzzle_content_widget)
        self.puzzle_area_layout.addWidget(self.puzzle_content_widget)
        self.puzzle_area_layout.addStretch()

        self.game_area_layout.addWidget(self.puzzle_scroll_area, stretch=3)

        # Clues Area (Right)
        clues_frame = QFrame()
        clues_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        clues_layout = QVBoxLayout(clues_frame)

        self.clues_title = QLabel("Information")
        self.clues_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.clues_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        clues_layout.addWidget(self.clues_title)

        self.clues_text = QTextEdit()
        self.clues_text.setReadOnly(True)
        self.clues_text.setFont(QFont("Arial", 11))
        clues_layout.addWidget(self.clues_text)

        self.game_area_layout.addWidget(clues_frame, stretch=2)

        parent_layout.addLayout(self.game_area_layout)


    def _create_control_bar(self, parent_layout):
        """Creates the bottom control bar with Hint, Check, and Reset buttons."""
        control_bar = QHBoxLayout()

        self.hint_button = QPushButton("Get Hint")
        self.hint_button.setIcon(QIcon.fromTheme("help-contextual"))
        self.hint_button.clicked.connect(self._use_hint)
        control_bar.addWidget(self.hint_button)

        self.check_button = QPushButton("Check Solution")
        self.check_button.setIcon(QIcon.fromTheme("dialog-ok-apply"))
        self.check_button.clicked.connect(self._check_solution)
        control_bar.addWidget(self.check_button)

        self.reset_button = QPushButton("Reset Puzzle")
        self.reset_button.setIcon(QIcon.fromTheme("edit-undo"))
        self.reset_button.clicked.connect(self._reset_puzzle)
        control_bar.addWidget(self.reset_button)

        parent_layout.addLayout(control_bar)

    def _create_feedback_label(self, parent_layout):
        """Creates the label at the bottom for displaying feedback messages."""
        self.feedback_label = QLabel("")
        self.feedback_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.feedback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feedback_label.setMinimumHeight(30)
        self.feedback_label.setWordWrap(True)
        parent_layout.addWidget(self.feedback_label)

    def _update_ui_for_puzzle(self):
        """Updates the entire UI to reflect the current puzzle state."""
        puzzle = self.game_state.current_puzzle
        self._clear_layout(self.puzzle_content_layout)
        self.assignment_widgets = {}
        self.scenario_input_widget = None
        self.scenario_input_widgets = {}

        # Disable controls if AI is running
        is_interactive = not self.is_ai_running

        if not puzzle:
            self.puzzle_title_label.setText("No Puzzle Loaded")
            self.puzzle_content_layout.addWidget(QLabel("Load a game or start a new puzzle from the Game menu."))
            self.level_label.setText("Level: -")
            self.puzzle_type_label.setText("Type: N/A")
            self.hints_label.setText("Hints Left: -")
            self.hint_button.setEnabled(False)
            self.check_button.setEnabled(False)
            self.reset_button.setEnabled(False)
            self.clues_text.clear()
            self.feedback_label.setText("No puzzle active.")
            # Also disable AI controls if no puzzle
            self.run_ai_action.setEnabled(False)
            self.stop_ai_action.setEnabled(False)
            return

        # Re-enable AI start if puzzle loaded and AI not running
        self.run_ai_action.setEnabled(is_interactive)

        self.check_button.setEnabled(is_interactive)
        self.reset_button.setEnabled(is_interactive)

        self.level_label.setText(f"Level: {puzzle.level + 1} (Solved: {self.game_state.puzzles_solved})") # Show solved count
        hints_left = self.game_state.max_hints_per_level - self.game_state.hints_used_this_level
        self.hints_label.setText(f"Hints Left: {hints_left}")
        self.hint_button.setEnabled(hints_left > 0 and is_interactive) # Also disable hint if AI runs
        if not self.is_ai_running: # Clear feedback only if user is playing
             self.feedback_label.setText("")
        self.clues_text.clear()

        if isinstance(puzzle, Puzzle) and not puzzle.is_scenario:
            self.puzzle_type_label.setText("Type: Symbol Cipher")
            self.puzzle_title_label.setText("Symbols & Assignments")
            self.clues_title.setText("Alchemist's Notes (Clues)")
            self._create_symbol_puzzle_ui(puzzle)
            self._display_symbol_clues(puzzle)
        elif isinstance(puzzle, ScenarioPuzzle):
            puzzle_type_str = self._get_puzzle_type_display_name(puzzle.puzzle_type) # Use helper
            self.puzzle_type_label.setText(f"Type: {puzzle_type_str}")
            self.puzzle_title_label.setText(f"Scenario: {puzzle_type_str}")
            self.clues_title.setText("Scenario Information & Clues")
            self._create_scenario_puzzle_ui(puzzle)
            self._display_scenario_information(puzzle)
        else:
            self.puzzle_title_label.setText("Error")
            self.puzzle_content_layout.addWidget(QLabel("Error: Unknown puzzle type encountered."))
            logging.error(f"Unknown puzzle type in _update_ui_for_puzzle: {type(puzzle)}")

        # Ensure combo boxes are enabled/disabled correctly based on AI state
        for symbol_widgets in self.assignment_widgets.values():
             combo = symbol_widgets.get('combo')
             if combo:
                 combo.setEnabled(is_interactive)
        if self.scenario_input_widget:
             self.scenario_input_widget.setEnabled(is_interactive)
        # Add specific disabling for table cells etc. if needed for scenarios

        self._apply_theme()
        self.puzzle_area_layout.activate() # Force layout update


    def _display_symbol_clues(self, puzzle: Puzzle):
        """Displays formatted clues for a symbol puzzle."""
        clue_style = "<style>li { margin-bottom: 5px; }</style><ul>"
        for clue_text, clue_type in puzzle.clues:
            prefix = self._get_clue_prefix(clue_type)
            clue_style += f"<li>{prefix}{clue_text}</li>"
        clue_style += "</ul>"
        self.clues_text.setHtml(clue_style)

    def _display_scenario_information(self, puzzle: ScenarioPuzzle):
        """Displays formatted information/clues for a scenario puzzle."""
        html_content = f"<h3>Description:</h3><p>{puzzle.description}</p>"
        html_content += f"<h3>Goal:</h3><p>{puzzle.goal}</p><hr>"

        if puzzle.characters:
            html_content += "<h3>Characters/Entities Involved:</h3><ul>"
            for char in puzzle.characters:
                # Safely access name and other details
                name = char.get('name', 'Unknown')
                details_list = []
                for k, v in char.items():
                    if k not in ['name', 'state_history', 'details']: # Exclude name, history, and potential duplicate 'details'
                        details_list.append(f"{k}: {v}")
                # Append details if they exist
                if 'details' in char and isinstance(char['details'], str) and char['details'] != "N/A":
                     details_list.append(f"info: {char['details']}")
                elif 'details' in char and isinstance(char['details'], list):
                     details_list.append(f"info: {', '.join(char['details'])}")

                details_str = ", ".join(details_list)
                html_content += f"<li><b>{name}</b>{f': {details_str}' if details_str else ''}</li>"
            html_content += "</ul>"

        if puzzle.setting and puzzle.setting.get('name') != "N/A":
             setting_name = puzzle.setting.get('name', '')
             setting_details_list = puzzle.setting.get('details', [])
             details_str = ""
             if isinstance(setting_details_list, list) and setting_details_list:
                 details_str = f" ({', '.join(setting_details_list)})"
             elif isinstance(setting_details_list, str) and setting_details_list:
                 details_str = f" ({setting_details_list})"
             html_content += f"<h3>Setting:</h3><p>{setting_name}{details_str}</p>"

        html_content += "<h3>Information & Clues:</h3>"
        if puzzle.information:
            html_content += "<ul>"
            for info in puzzle.information:
                # Basic type check
                if not isinstance(info, str):
                    info = str(info) # Attempt conversion if not string

                if info.startswith("Rule Observed:"):
                     html_content += f"<li style='color: #007bff;'><i>{info}</i></li>"
                elif info.startswith("Hint:"):
                    html_content += f"<li style='font-style: italic; color: #6c757d;'>{info}</li>"
                else:
                     html_content += f"<li>{info}</li>"
            html_content += "</ul>"
        else:
            html_content += "<p>No specific clues provided. Rely on the description and goal.</p>"

        self.clues_text.setHtml(html_content)

    def _get_clue_prefix(self, clue_type: ClueType) -> str:
        """Returns a visual prefix for different clue types."""
        prefixes = {
            ClueType.DIRECT: "🔍 ",
            ClueType.EXCLUSION: "❌ ",
            ClueType.POSITIONAL: "📍 ",
            ClueType.RELATIONAL: "↔️ ",
            ClueType.CATEGORY: "📑 ",
            ClueType.LOGICAL: "🧠 ",
        }
        return prefixes.get(clue_type, "• ")

    def _create_symbol_puzzle_ui(self, puzzle: Puzzle):
        """Creates the UI elements within puzzle_content_layout for a Symbol Cipher puzzle."""
        self._clear_layout(self.puzzle_content_layout)
        self.assignment_widgets = {}
        is_interactive = not self.is_ai_running # Check AI state

        assignments_grid = QGridLayout()
        symbols = puzzle.symbols
        letters_for_combo = [""] + sorted(puzzle.letters)
        # Adjust columns based on number of symbols for better layout
        num_symbols = len(symbols)
        num_cols = 2 if num_symbols <= 6 else 3 if num_symbols <= 15 else 4

        for i, symbol in enumerate(symbols):
            row, col = divmod(i, num_cols)

            symbol_label = QLabel(symbol)
            symbol_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
            symbol_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            symbol_label.setMinimumWidth(40)
            assignments_grid.addWidget(symbol_label, row, col * 2)

            letter_combo = QComboBox()
            letter_combo.addItems(letters_for_combo)
            letter_combo.setFont(QFont("Arial", 14))
            letter_combo.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
            letter_combo.setMinimumWidth(60)
            letter_combo.setEnabled(is_interactive) # Set enabled based on AI state
            letter_combo.currentTextChanged.connect(
                lambda text, s=symbol: self._assign_letter(s, text)
            )
            assignments_grid.addWidget(letter_combo, row, col * 2 + 1)

            self.assignment_widgets[symbol] = {'combo': letter_combo}

        self.puzzle_content_layout.addLayout(assignments_grid)
        self._update_assignments_display()


    def _create_scenario_puzzle_ui(self, puzzle: ScenarioPuzzle):
        """Creates the UI elements within puzzle_content_layout for a scenario puzzle."""
        self._clear_layout(self.puzzle_content_layout)
        self.scenario_input_widget = None
        self.scenario_input_widgets = {}
        is_interactive = not self.is_ai_running # Check AI state

        label_map = {
            HumanScenarioType.SOCIAL_DEDUCTION: "Who is the target individual?",
            HumanScenarioType.COMMON_SENSE_GAP: "What essential item is missing?",
            HumanScenarioType.AGENT_SIMULATION: "Enter your deduction (Location/Trait/Rule):",
        }

        if puzzle.puzzle_type == HumanScenarioType.LOGIC_GRID:
             self._create_logic_grid_ui(puzzle) # Logic grid handles enable state internally now
        elif puzzle.puzzle_type in [HumanScenarioType.SOCIAL_DEDUCTION,
                                     HumanScenarioType.COMMON_SENSE_GAP,
                                     HumanScenarioType.AGENT_SIMULATION]:
            self.scenario_input_widget = self._create_line_edit_input(
                label_map.get(puzzle.puzzle_type, "Your Answer:"),
                is_interactive
            )
        elif puzzle.puzzle_type == HumanScenarioType.RELATIONSHIP_MAP:
            input_label = QLabel("Enter Pairs (one per line, e.g., 'Alice : Bob'):")
            self.scenario_input_widget = QTextEdit()
            self.scenario_input_widget.setPlaceholderText("Alice : Bob\nChloe : David\n...")
            self.scenario_input_widget.setFont(QFont("Arial", 11))
            self.scenario_input_widget.setFixedHeight(100)
            self.scenario_input_widget.setEnabled(is_interactive) # Set enabled
            self.puzzle_content_layout.addWidget(input_label)
            self.puzzle_content_layout.addWidget(self.scenario_input_widget)
        elif puzzle.puzzle_type == HumanScenarioType.ORDERING:
             input_label = QLabel("Enter Sequence (Top to Bottom):")
             self.puzzle_content_layout.addWidget(input_label)
             items_to_order = puzzle.solution.get('order', [])
             if not items_to_order:
                  items_to_order = [f"Item {i+1}" for i in range(getattr(puzzle, 'num_items', 4))]
                  logging.warning("Could not determine items for Ordering puzzle from solution key.")

             num_items = len(items_to_order)
             table = QTableWidget(num_items, 1)
             table.setHorizontalHeaderLabels(["Item"])
             # Don't set vertical headers if we use position labels
             # table.setVerticalHeaderLabels([str(i+1) for i in range(num_items)])
             table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
             for r in range(num_items):
                 # Add label for position
                 pos_label = QLabel(f"Position {r+1}:")
                 pos_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                 # table.setCellWidget(r, 0, pos_label) # Labels don't go in cells

                 combo = QComboBox()
                 combo.addItems([""] + sorted(items_to_order))
                 combo.setEnabled(is_interactive) # Set enabled
                 # Place label and combo in a layout, then set that layout in the cell? No...
                 # Use setCellWidget for the combo
                 table.setCellWidget(r, 0, combo)
                 # Set vertical header instead of label in cell
                 table.setVerticalHeaderItem(r, QTableWidgetItem(f"Pos {r+1}"))


             self.scenario_input_widget = table
             table.setEnabled(is_interactive) # Can disable the whole table
             table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
             self.puzzle_content_layout.addWidget(table)
             table.setMinimumHeight(num_items * 40 + table.horizontalHeader().height())


        elif puzzle.puzzle_type == HumanScenarioType.SCHEDULING:
             input_label = QLabel("Enter Schedule (✔️ = Booked, leave blank = Available):")
             self.puzzle_content_layout.addWidget(input_label)
             schedule_data = puzzle.solution.get('schedule', {})
             if not schedule_data:
                 logging.error("Cannot create scheduling UI: puzzle.solution['schedule'] is empty or missing.")
                 self.puzzle_content_layout.addWidget(QLabel("Error: Scheduling data missing."))
                 return

             people = sorted(list(schedule_data.keys()))
             # Get time slots from the first person, assuming consistency
             time_slots = sorted(list(schedule_data.get(people[0], {}).keys())) if people else []

             if not people or not time_slots:
                 logging.error("Cannot create scheduling UI: People or time slots missing.")
                 self.puzzle_content_layout.addWidget(QLabel("Error: People or time slots missing."))
                 return

             table = QTableWidget(len(people), len(time_slots))
             table.setVerticalHeaderLabels(people)
             table.setHorizontalHeaderLabels(time_slots)

             for r in range(len(people)):
                 for c in range(len(time_slots)):
                     combo = QComboBox()
                     combo.addItems(["", "✔️"]) # Simple available/booked choice
                     combo.setFont(QFont("Arial", 12))
                     combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                     combo.setEnabled(is_interactive) # Set enabled
                     table.setCellWidget(r, c, combo)

             table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
             table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
             self.scenario_input_widget = table
             table.setEnabled(is_interactive) # Disable whole table
             self.puzzle_content_layout.addWidget(table)
             table.setMinimumHeight(len(people) * 40 + table.horizontalHeader().height())


        elif puzzle.puzzle_type == HumanScenarioType.DILEMMA:
             input_label = QLabel("Select the most appropriate action:")
             self.puzzle_content_layout.addWidget(input_label)
             group_box = QWidget()
             group_layout = QVBoxLayout(group_box)
             group_layout.setContentsMargins(5, 5, 5, 5)

             self.scenario_input_widget = QButtonGroup(self)

             options_to_display = getattr(puzzle, 'options', None)
             if not options_to_display:
                 logging.error("Dilemma puzzle loaded without options attribute.")
                 options_to_display = ["Error: Option A", "Error: Option B"]

             for i, option_text in enumerate(options_to_display):
                 radio_button = QRadioButton(option_text)
                 radio_button.setFont(QFont("Arial", 11))
                 radio_button.setEnabled(is_interactive) # Set enabled
                 self.scenario_input_widget.addButton(radio_button, i)
                 group_layout.addWidget(radio_button)

             self.puzzle_content_layout.addWidget(group_box)
             group_box.setEnabled(is_interactive) # Disable the container
        else:
             self.puzzle_content_layout.addWidget(QLabel(f"Input UI not implemented for type: {puzzle.puzzle_type.name}"))

        self.puzzle_content_layout.addStretch()


    def _create_line_edit_input(self, label_text: str, enabled: bool) -> QLineEdit:
        """Helper to create a label and line edit pair."""
        input_layout = QHBoxLayout()
        input_label = QLabel(label_text)
        line_edit = QLineEdit()
        line_edit.setFont(QFont("Arial", 11))
        line_edit.setEnabled(enabled) # Set enabled state
        input_layout.addWidget(input_label)
        input_layout.addWidget(line_edit)
        self.puzzle_content_layout.addLayout(input_layout)
        return line_edit


    def _create_logic_grid_ui(self, puzzle: ScenarioPuzzle):
        """Creates the QTableWidget UI for a Logic Grid scenario puzzle."""
        if not puzzle.elements or len(puzzle.elements) < 2:
            self.puzzle_content_layout.addWidget(QLabel("Error: Insufficient elements for logic grid."))
            return
        is_interactive = not self.is_ai_running # Check AI state

        categories = list(puzzle.elements.keys())
        row_category = categories[0]
        col_categories = categories[1:]
        row_items = puzzle.elements[row_category]

        num_rows = len(row_items)
        num_cols = sum(len(puzzle.elements[cat]) for cat in col_categories)

        table = QTableWidget(num_rows, num_cols)
        table.setVerticalHeaderLabels(row_items)

        col_headers = []
        col_category_map = {}
        flat_col_index = 0
        for cat_name in col_categories:
            elements_in_cat = puzzle.elements[cat_name]
            for element_name in elements_in_cat:
                # Shorten header: Max 3 chars for category, then element name
                short_cat = cat_name[:3]
                col_headers.append(f"{short_cat}:{element_name}")
                col_category_map[flat_col_index] = (cat_name, element_name)
                flat_col_index += 1
        table.setHorizontalHeaderLabels(col_headers)
        self.scenario_input_widgets['logic_grid_col_map'] = col_category_map


        for r in range(num_rows):
            for c in range(num_cols):
                cell_combo = QComboBox()
                cell_combo.addItems(["", "✔️", "❌"]) # Blank, Yes, No
                cell_combo.setFont(QFont("Arial", 12))
                cell_combo.setEnabled(is_interactive) # Set enabled state
                table.setCellWidget(r, c, cell_combo)

        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents) # Resize to contents first
        table.horizontalHeader().setStretchLastSection(True) # Then stretch last
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        # table.resizeColumnsToContents() # Resize again after headers set

        self.scenario_input_widget = table
        table.setEnabled(is_interactive) # Disable whole table if needed
        self.puzzle_content_layout.addWidget(table)

        # Adjust minimum height calculation (estimate cell width maybe?)
        header_height = table.horizontalHeader().height()
        row_height_estimate = 40
        table.setMinimumHeight(num_rows * row_height_estimate + header_height)
        # Estimate width - this is harder
        # total_width = table.verticalHeader().width() + sum(table.columnWidth(c) for c in range(num_cols)) + 20 # Add margin
        # table.setMinimumWidth(total_width)


    def _clear_layout(self, layout):
        """Removes all widgets and sub-layouts from a given Qt layout."""
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    sub_layout = item.layout()
                    if sub_layout is not None:
                        self._clear_layout(sub_layout)

    def _update_assignments_display(self):
        """Updates the symbol assignment ComboBoxes based on the current game state.
           Disables letters already assigned elsewhere.
        """
        if not isinstance(self.game_state.current_puzzle, Puzzle) or self.game_state.current_puzzle.is_scenario:
            return

        puzzle = self.game_state.current_puzzle
        current_mapping = self.game_state.user_mapping
        assigned_letters = set(current_mapping.values())

        symbols_in_ui = list(self.assignment_widgets.keys())

        for symbol in symbols_in_ui:
            widget_dict = self.assignment_widgets.get(symbol)
            if not widget_dict or 'combo' not in widget_dict: continue

            combo_box = widget_dict['combo']
            current_assignment = current_mapping.get(symbol, "")

            combo_box.blockSignals(True)

            # Store current index before clearing (use findText to be safe)
            current_text_index = combo_box.findText(current_assignment)

            combo_box.clear()
            combo_box.addItem("") # Add the blank item first

            # Add all possible letters
            for letter in sorted(puzzle.letters):
                combo_box.addItem(letter)

            # Set the index *after* adding all items
            if current_assignment and current_text_index != -1:
                 # Find the index of the current assignment in the *new* list
                 new_index = combo_box.findText(current_assignment)
                 if new_index != -1:
                     combo_box.setCurrentIndex(new_index)
                 else: # Should not happen if letter is valid
                     combo_box.setCurrentIndex(0) # Fallback to blank
            else:
                 combo_box.setCurrentIndex(0) # Default to blank

            # Now, disable items assigned elsewhere *without changing the current index*
            for i in range(1, combo_box.count()): # Skip the blank item at index 0
                letter = combo_box.itemText(i)
                item = combo_box.model().item(i)
                if item:
                    is_assigned_elsewhere = (letter in assigned_letters and letter != current_assignment)
                    item.setEnabled(not is_assigned_elsewhere)

            combo_box.blockSignals(False)


    def _assign_letter(self, symbol: str, letter: str):
        """Handles the signal when a letter is assigned via ComboBox for Symbol Puzzles."""
        if self.is_ai_running: return # Ignore user input if AI is active

        if not isinstance(self.game_state.current_puzzle, Puzzle) or self.game_state.current_puzzle.is_scenario:
            return

        current_mapping = self.game_state.user_mapping

        # Find if the selected letter is already assigned to another symbol
        existing_symbol_for_letter = None
        for s, l in current_mapping.items():
            if l == letter and s != symbol and letter != "": # Ensure letter is not blank
                existing_symbol_for_letter = s
                break

        if letter: # If a non-blank letter is selected
            # If this letter was previously assigned to another symbol, clear that other symbol's assignment
            if existing_symbol_for_letter:
                current_mapping.pop(existing_symbol_for_letter, None)
                # No need to manually update the other combo's index here,
                # _update_assignments_display will handle it.

            # Assign the letter to the current symbol
            current_mapping[symbol] = letter
        else: # If the blank item is selected
            # Remove the assignment for the current symbol
            current_mapping.pop(symbol, None)

        # Update all combo boxes to reflect the new state and disable conflicting options
        self._update_assignments_display()


    def _use_hint(self):
        """Handles the 'Get Hint' button click."""
        if self.is_ai_running: return # Ignore if AI running

        hint_result = self.game_state.get_hint()

        if not hint_result:
            self.feedback_label.setText("Internal error: Hint request failed.")
            self.feedback_label.setStyleSheet("color: red;")
            return
        elif isinstance(hint_result, str) and ("No hints left" in hint_result or "No further hints" in hint_result or "No puzzle loaded" in hint_result):
             self.feedback_label.setText(hint_result)
             self.feedback_label.setStyleSheet("color: orange;")
             # Don't disable button if no more hints available, just show message
             self.hint_button.setEnabled(False if "No hints left" in hint_result else True)
             return
        elif isinstance(hint_result, str) and "Cannot provide hint" in hint_result: # Handle specific error case
            self.feedback_label.setText(hint_result)
            self.feedback_label.setStyleSheet("color: orange;")
            return


        # Handle tuple hint (Symbol Cipher) vs string hint (Scenario)
        hint_text_display = ""
        if isinstance(hint_result, tuple) and len(hint_result) == 3:
            symbol, letter, reason = hint_result
            hint_text_display = f"Hint ({reason}): Try mapping '{symbol}' to '{letter}'."
        elif isinstance(hint_result, str):
            hint_text_display = f"Hint: {hint_result}"
        else:
             self.feedback_label.setText("Received unexpected hint format.")
             self.feedback_label.setStyleSheet("color: red;")
             return

        self.feedback_label.setText(hint_text_display)
        self.feedback_label.setStyleSheet("color: #007bff;") # Blue color for hints

        hints_left = self.game_state.max_hints_per_level - self.game_state.hints_used_this_level
        self.hints_label.setText(f"Hints Left: {hints_left}")
        self.hint_button.setEnabled(hints_left > 0) # Disable if 0 hints left

        # If it was a symbol cipher hint, automatically apply it
        if isinstance(hint_result, tuple) and len(hint_result) == 3:
             symbol_to_assign, letter_to_assign, _ = hint_result
             if symbol_to_assign in self.assignment_widgets:
                  logging.info(f"Hint revealed mapping: {symbol_to_assign} -> {letter_to_assign}. Applying to UI.")
                  self._assign_letter(symbol_to_assign, letter_to_assign) # Use assign method to handle conflicts


    def _check_solution(self):
        """Handles the 'Check Solution' button click, retrieves UI solution, and gives feedback."""
        if self.is_ai_running: return # Ignore if AI running

        puzzle = self.game_state.current_puzzle
        if not puzzle:
             self.feedback_label.setText("No puzzle active to check.")
             return

        user_solution_data = None
        is_correct = False

        try:
            if isinstance(puzzle, Puzzle) and not puzzle.is_scenario:
                 # Check if all symbols have been assigned
                 if len(self.game_state.user_mapping) < puzzle.num_elements:
                     self.feedback_label.setText("Please assign a letter to all symbols first.")
                     self.feedback_label.setStyleSheet("color: orange;")
                     return
                 # check_solution for symbol uses internal user_mapping
                 is_correct = self.game_state.check_solution()
            elif isinstance(puzzle, ScenarioPuzzle):
                 user_solution_data = self._get_scenario_solution_from_ui()
                 if user_solution_data is None:
                      # Feedback is usually set within _get_scenario_solution_from_ui
                      # self.feedback_label.setText("Please complete the puzzle input.")
                      # self.feedback_label.setStyleSheet("color: orange;")
                      return
                 is_correct = self.game_state.check_solution(user_solution_data)
            else:
                 self.feedback_label.setText("Error: Cannot check unknown puzzle type.")
                 self.feedback_label.setStyleSheet("color: red;")
                 return

            if is_correct:
                self.feedback_label.setText(f"Correct! Level {puzzle.level + 1} Solved!")
                self.feedback_label.setStyleSheet("color: green;")
                self.game_state.puzzles_solved += 1 # Increment solved count
                self.level_label.setText(f"Level: {self.game_state.current_level + 1} (Solved: {self.game_state.puzzles_solved})") # Update label

                feedback_title = "Puzzle Solved!"
                feedback_text = self._get_educational_feedback(puzzle)
                # Don't block with message box if AI is running
                if not self.is_ai_running:
                     QMessageBox.information(self, feedback_title, feedback_text)

                unlocked_theme = self.game_state.check_unlockables()
                if unlocked_theme:
                    if self.game_state.unlock_theme(unlocked_theme):
                        if not self.is_ai_running: # Only show msg box if user is playing
                             QMessageBox.information(self, "Theme Unlocked!",
                                 f"Congratulations!\nYou've unlocked the '{unlocked_theme}' theme!")
                        self._update_theme_menu()

                # Ask to proceed only if user is playing
                proceed = True # Default to proceed for AI
                if not self.is_ai_running:
                    reply = QMessageBox.question(self, "Next Level?",
                        "Proceed to the next level?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes)
                    proceed = (reply == QMessageBox.StandardButton.Yes)

                if proceed:
                    self.game_state.current_level += 1
                    self.game_state.start_new_puzzle() # Game state handles starting new puzzle
                    self._update_ui_for_puzzle()
                else:
                    # User chose not to proceed
                    self.check_button.setEnabled(False) # Disable check button for solved puzzle
                    self.hint_button.setEnabled(False)

            else:
                self.feedback_label.setText("Incorrect solution. Keep trying!")
                self.feedback_label.setStyleSheet("color: red;")
                if isinstance(puzzle, ScenarioPuzzle):
                    self.feedback_label.setText(self.feedback_label.text() +
                                                  "\nReview the information and your deductions.")

        except Exception as e:
             logging.exception("Error occurred during solution checking.")
             self.feedback_label.setText(f"Error checking solution: {e}")
             self.feedback_label.setStyleSheet("color: red;")


    def _get_educational_feedback(self, puzzle: Union[Puzzle, ScenarioPuzzle]) -> str:
        """Generates educational feedback text based on the solved puzzle type."""
        if isinstance(puzzle, Puzzle) and not puzzle.is_scenario:
            feedback = "Symbol Cipher Solved!\n\nYou likely used techniques such as:\n"
            techniques = set()
            # Ensure clue_types_used exists, default to empty set if not
            clue_types_used = getattr(puzzle, 'clue_types_used', set())
            if not isinstance(clue_types_used, set): # Check if it's actually a set
                clue_types_used = set() # Reset if not

            for clue_type in clue_types_used:
                 if clue_type == ClueType.DIRECT: techniques.add("• Direct mapping (🔍)")
                 elif clue_type == ClueType.EXCLUSION: techniques.add("• Process of elimination (❌)")
                 elif clue_type == ClueType.POSITIONAL: techniques.add("• Positional reasoning (📍)")
                 elif clue_type == ClueType.RELATIONAL: techniques.add("• Relational analysis (↔️)")
                 elif clue_type == ClueType.CATEGORY: techniques.add("• Category-based reasoning (📑)")
                 elif clue_type == ClueType.LOGICAL: techniques.add("• Complex logical deduction (🧠)")
            if not techniques: techniques.add("• Careful deduction!")
            feedback += "\n".join(sorted(list(techniques)))
            return feedback

        elif isinstance(puzzle, ScenarioPuzzle):
             scenario_type_name = self._get_puzzle_type_display_name(puzzle.puzzle_type) # Use helper
             feedback = f"Scenario Solved: {scenario_type_name}!\n\n"
             feedback += "Skills demonstrated might include:\n"
             if puzzle.puzzle_type == HumanScenarioType.SOCIAL_DEDUCTION:
                 feedback += "• Analyzing statements and motivations\n• Identifying inconsistencies\n• Inferring truthfulness"
             elif puzzle.puzzle_type == HumanScenarioType.COMMON_SENSE_GAP:
                 feedback += "• Applying real-world knowledge\n• Identifying missing steps/items\n• Contextual reasoning"
             elif puzzle.puzzle_type == HumanScenarioType.LOGIC_GRID:
                  feedback += "• Systematic grid deduction\n• Applying positive/negative constraints\n• Cross-referencing clues"
             elif puzzle.puzzle_type == HumanScenarioType.AGENT_SIMULATION:
                  feedback += "• Pattern recognition from behavior\n• Rule inference from observations\n• Predicting outcomes based on logic"
             elif puzzle.puzzle_type == HumanScenarioType.RELATIONSHIP_MAP:
                  feedback += "• Mapping connections between entities\n• Interpreting relational clues (positive/negative)\n• Structuring network information"
             elif puzzle.puzzle_type == HumanScenarioType.ORDERING:
                  feedback += "• Reconstructing sequences\n• Applying temporal logic (before/after)\n• Handling adjacency constraints"
             elif puzzle.puzzle_type == HumanScenarioType.SCHEDULING:
                  feedback += "• Constraint satisfaction\n• Managing resource allocation (time slots)\n• Resolving conflicts based on rules"
             elif puzzle.puzzle_type == HumanScenarioType.DILEMMA:
                   feedback += "• Evaluating consequences of actions\n• Applying ethical reasoning\n• Weighing conflicting values"
             else:
                  feedback += "• Careful reading and logical deduction"
             return feedback
        else:
            return "Puzzle Solved! Well done."


    def _get_scenario_solution_from_ui(self) -> Optional[Dict[str, Any]]:
        """Retrieves the user's solution input from the dynamic scenario UI."""
        puzzle = self.game_state.current_puzzle
        if not isinstance(puzzle, ScenarioPuzzle):
            logging.error("_get_scenario_solution_from_ui called for non-scenario puzzle.")
            return None

        widget = self.scenario_input_widget
        solution_dict = {}

        try:
            if puzzle.puzzle_type == HumanScenarioType.LOGIC_GRID:
                if not isinstance(widget, QTableWidget):
                     QMessageBox.warning(self, "Input Error", "Logic grid UI not found.")
                     return None
                # grid_solution = {} # This was unused
                solved_map = {} # Use this to build the solution structure expected by GameState
                rows = widget.rowCount()
                cols = widget.columnCount()
                row_headers = [widget.verticalHeaderItem(r).text() for r in range(rows)]
                col_map = self.scenario_input_widgets.get('logic_grid_col_map', {})
                if not col_map or len(col_map) != cols:
                     QMessageBox.critical(self, "Internal Error", "Logic grid column mapping is missing or incorrect.")
                     return None

                # Initialize solved_map correctly
                for entity in row_headers: solved_map[entity] = {}

                # Logic to check if grid is *completely* filled (either Yes or No for every cell)
                all_cells_filled = True
                for r in range(rows):
                    for c in range(cols):
                        cell_widget = widget.cellWidget(r, c)
                        if isinstance(cell_widget, QComboBox):
                             if cell_widget.currentText() == "": # Blank means not filled
                                  all_cells_filled = False
                                  break # No need to check further
                        else:
                             logging.warning(f"Non-ComboBox widget in logic grid cell ({r},{c})")
                             all_cells_filled = False; break
                    if not all_cells_filled: break


                # Temporary structure to validate before building final solution_dict
                temp_validation_map = {entity: {} for entity in row_headers}
                validation_passed = True

                for r in range(rows):
                    entity_name = row_headers[r]
                    positive_assignments_per_category = {cat_name: 0 for cat_name, _ in col_map.values()}

                    for c in range(cols):
                        cell_widget = widget.cellWidget(r, c)
                        if isinstance(cell_widget, QComboBox):
                             selection = cell_widget.currentText()
                             if selection == "": continue # Skip blank cells for validation logic below

                             category_name, element_value = col_map[c]

                             if selection == "✔️":
                                 # Check for contradictions within the row
                                 if category_name in temp_validation_map[entity_name] and temp_validation_map[entity_name][category_name] != element_value:
                                      QMessageBox.warning(self, "Input Error", f"Contradiction in grid for {entity_name}: Trying to assign {element_value} to {category_name}, but already assigned {temp_validation_map[entity_name][category_name]}. Only one 'Yes' per category group per row.")
                                      validation_passed = False; break
                                 # Check for contradictions across columns (same value assigned to multiple entities)
                                 for other_entity, assignments in temp_validation_map.items():
                                      if other_entity != entity_name and assignments.get(category_name) == element_value:
                                           QMessageBox.warning(self, "Input Error", f"Contradiction in grid: {element_value} ({category_name}) is already assigned to {other_entity}, cannot also assign to {entity_name}. Only one 'Yes' per category group per column.")
                                           validation_passed = False; break
                                 if not validation_passed: break

                                 temp_validation_map[entity_name][category_name] = element_value
                                 positive_assignments_per_category[category_name] += 1

                             elif selection == "❌":
                                  # Check for contradiction: Marked 'No' but already marked 'Yes'
                                  if temp_validation_map.get(entity_name, {}).get(category_name) == element_value:
                                       QMessageBox.warning(self, "Input Error", f"Contradiction in grid for {entity_name}: Marked 'No' for {element_value} ({category_name}), but it was previously marked 'Yes'.")
                                       validation_passed = False; break

                    if not validation_passed: break # Break outer loop if inner failed

                    # Check if exactly one 'Yes' per category group was selected for this row
                    if all_cells_filled: # Only perform this check if grid is fully marked
                         for cat_name, count in positive_assignments_per_category.items():
                              # Group check needs to happen per category 'group' not just category name
                              # How many elements *belong* to this category name?
                              num_elements_in_category = len(puzzle.elements[cat_name])
                              # This check is tricky. Basic check: Ensure *at least* one yes per cat name
                              # A better check: Ensure exactly one 'Yes' per category group overall
                              # Let's stick to the simpler check for now.
                              # if count != 1:
                              #      QMessageBox.warning(self, "Input Error", f"Input incomplete/invalid for {entity_name}: Ensure exactly one '✔️' is selected for the '{cat_name}' category group.")
                              #      validation_passed = False; break
                              pass # Skip count validation for now, rely on direct contradiction checks


                    if not validation_passed: break # Break outer loop


                if not validation_passed:
                    return None # Validation failed

                if not all_cells_filled:
                     QMessageBox.information(self, "Input Incomplete", "Please make a selection (✔️ or ❌) for every cell in the logic grid.")
                     return None


                # If validation passed and grid is full, build the solution map from the 'Yes' values
                # This structure should match game_state.check_solution's expectation
                final_solved_map = {entity: {} for entity in row_headers}
                for r in range(rows):
                     entity_name = row_headers[r]
                     for c in range(cols):
                         cell_widget = widget.cellWidget(r,c)
                         if isinstance(cell_widget, QComboBox) and cell_widget.currentText() == "✔️":
                             category_name, element_value = col_map[c]
                             final_solved_map[entity_name][category_name] = element_value

                solution_dict = {"grid": final_solved_map}


            elif isinstance(widget, QLineEdit) or isinstance(widget, QTextEdit):
                if isinstance(widget, QLineEdit):
                    answer = widget.text().strip()
                    if not answer:
                        QMessageBox.information(self, "Input Needed", "Please enter your answer.")
                        return None
                    solution_dict = {"answer": answer}
                elif isinstance(widget, QTextEdit) and puzzle.puzzle_type == HumanScenarioType.RELATIONSHIP_MAP:
                    raw_text = widget.toPlainText().strip()
                    user_map_input = {}
                    expected_pair_count = 0
                    if puzzle.characters:
                         expected_pair_count = len(puzzle.characters) // 2


                    if raw_text:
                        lines = raw_text.split('\n')
                        processed_people = set()
                        for i, line in enumerate(lines):
                            line = line.strip()
                            if not line: continue
                            parts = line.split(':', 1)
                            if len(parts) == 2:
                                person1 = parts[0].strip()
                                person2 = parts[1].strip()
                                if person1 and person2:
                                    # Check if people are valid characters from the puzzle
                                    puzzle_char_names = {char['name'] for char in puzzle.characters} if puzzle.characters else set()
                                    if person1 not in puzzle_char_names or person2 not in puzzle_char_names:
                                         QMessageBox.warning(self, "Input Error", f"Invalid name found on line {i+1}: '{person1}' or '{person2}'. Use names from the scenario description.")
                                         return None
                                    if person1 == person2:
                                         QMessageBox.warning(self, "Input Error", f"Cannot pair '{person1}' with themselves on line {i+1}.")
                                         return None

                                    # Check for duplicates: person appearing on left or right more than once
                                    if person1 in processed_people or person2 in processed_people:
                                         QMessageBox.warning(self, "Input Error", f"Duplicate person found on line {i+1}: '{person1}' or '{person2}' already included in another pair.")
                                         return None

                                    user_map_input[person1] = person2
                                    processed_people.add(person1)
                                    processed_people.add(person2)
                                else:
                                    QMessageBox.warning(self, "Input Error", f"Invalid format on line {i+1}: '{line}'. Use 'Name1 : Name2'. Missing name.")
                                    return None
                            else:
                                QMessageBox.warning(self, "Input Error", f"Invalid format on line {i+1}: '{line}'. Use 'Name1 : Name2'. Missing colon.")
                                return None

                    # Check if the correct number of pairs was entered
                    if len(user_map_input) != expected_pair_count:
                         QMessageBox.information(self, "Input Incomplete", f"Please enter exactly {expected_pair_count} pairs, ensuring all {len(puzzle.characters)} individuals are included.")
                         return None

                    solution_dict = {"map": user_map_input}

            elif isinstance(widget, QTableWidget) and puzzle.puzzle_type == HumanScenarioType.ORDERING:
                 rows = widget.rowCount()
                 ordered_items = []
                 seen_items = set()
                 all_selected = True
                 for r in range(rows):
                     cell_widget = widget.cellWidget(r, 0)
                     if isinstance(cell_widget, QComboBox):
                          item = cell_widget.currentText()
                          if not item:
                              all_selected = False
                              break
                          if item in seen_items:
                               QMessageBox.warning(self, "Input Error", f"Item '{item}' selected multiple times. Each item must appear only once in the sequence.")
                               return None
                          ordered_items.append(item)
                          seen_items.add(item)
                     else:
                          logging.warning("Non-ComboBox widget found in ordering table.")
                          return None

                 if not all_selected:
                      QMessageBox.information(self, "Input Incomplete", "Please select an item for each position in the sequence.")
                      return None
                 solution_dict = {"order": ordered_items}

            elif isinstance(widget, QTableWidget) and puzzle.puzzle_type == HumanScenarioType.SCHEDULING:
                rows = widget.rowCount()
                cols = widget.columnCount()
                schedule_map = {}
                people = [widget.verticalHeaderItem(r).text() for r in range(rows)]
                time_slots = [widget.horizontalHeaderItem(c).text() for c in range(cols)]

                for r, person in enumerate(people):
                    schedule_map[person] = {}
                    for c, slot in enumerate(time_slots):
                        cell_widget = widget.cellWidget(r, c)
                        if isinstance(cell_widget, QComboBox):
                            selection = cell_widget.currentText()
                            status = "Booked" if selection == "✔️" else "Available"
                            schedule_map[person][slot] = status
                        else:
                             logging.warning("Non-ComboBox widget found in scheduling table.")
                             return None

                solution_dict = {"schedule": schedule_map}

            elif isinstance(widget, QButtonGroup) and puzzle.puzzle_type == HumanScenarioType.DILEMMA:
                 checked_button = widget.checkedButton()
                 if checked_button:
                      solution_dict = {"choice": checked_button.text()}
                 else:
                      QMessageBox.information(self, "Input Needed", "Please select a choice for the dilemma.")
                      return None

            else:
                QMessageBox.critical(self, "UI Error", f"Could not retrieve solution from UI for puzzle type {puzzle.puzzle_type.name}. Input widget might be missing or incorrect.")
                return None

        except Exception as e:
            logging.exception("Error retrieving solution from UI.")
            QMessageBox.critical(self, "UI Error", f"An unexpected error occurred while reading your solution: {e}")
            return None

        return solution_dict


    def _reset_puzzle(self):
        """Handles the 'Reset Puzzle' button click, clearing user input."""
        if self.is_ai_running: return # Ignore if AI running

        puzzle = self.game_state.current_puzzle
        if not puzzle: return

        reply = QMessageBox.StandardButton.Yes # Default to Yes if no puzzle? No, should only be called if puzzle exists.
        # Only ask confirmation if there's actually input to reset
        progress_made = False
        if isinstance(puzzle, Puzzle) and not puzzle.is_scenario and self.game_state.user_mapping:
            progress_made = True
        elif isinstance(puzzle, ScenarioPuzzle):
            # Need a light check if any scenario input exists without fully parsing
            # This is tricky. Let's assume asking is fine.
            progress_made = True # Assume progress might exist for scenarios

        if progress_made:
             reply = QMessageBox.question(self, "Confirm Reset",
                                       "Reset all your inputs for this puzzle?\n(Hints used will also be reset)",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                       QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self.game_state.hints_used_this_level = 0
            self.game_state.user_mapping = {}
            self.game_state.scenario_user_state = None

            # Reset UI elements
            if isinstance(puzzle, Puzzle) and not puzzle.is_scenario:
                for symbol, widget_dict in self.assignment_widgets.items():
                    combo = widget_dict.get('combo')
                    if combo:
                        combo.blockSignals(True)
                        combo.setCurrentIndex(0)
                        combo.blockSignals(False)
                self._update_assignments_display()

            elif isinstance(puzzle, ScenarioPuzzle):
                widget = self.scenario_input_widget
                if isinstance(widget, QLineEdit) or isinstance(widget, QTextEdit):
                    widget.clear()
                elif isinstance(widget, QTableWidget):
                    rows = widget.rowCount()
                    cols = widget.columnCount()
                    for r in range(rows):
                        for c in range(cols):
                            cell_widget = widget.cellWidget(r, c)
                            if isinstance(cell_widget, QComboBox):
                                cell_widget.setCurrentIndex(0)
                            elif isinstance(cell_widget, QLineEdit): # Example if other widgets used
                                cell_widget.clear()

                elif isinstance(widget, QButtonGroup):
                    # Use id -1 to uncheck all buttons in an exclusive group
                    checked_button = widget.checkedButton()
                    if checked_button:
                         # Setting autoExclusive False/True is needed to allow unchecking
                         widget.setExclusive(False)
                         checked_button.setChecked(False)
                         widget.setExclusive(True)

            # Update hint count display and button states
            self.hints_label.setText(f"Hints Left: {self.game_state.max_hints_per_level}")
            self.hint_button.setEnabled(True)
            self.check_button.setEnabled(True) # Re-enable check button after reset
            self.feedback_label.setText("Puzzle reset.")
            self.feedback_label.setStyleSheet("")


    def _confirm_and_start_new_puzzle(self, puzzle_type: Optional[Union[str, HumanScenarioType]] = None):
        """Unified method to confirm (if needed) and start a new puzzle."""
        if self.is_ai_running:
             logging.warning("Attempted to start new puzzle manually while AI is running. Ignoring.")
             return # Don't allow manual start if AI runs

        progress_made = False
        puzzle = self.game_state.current_puzzle
        if puzzle:
             if isinstance(puzzle, Puzzle) and not puzzle.is_scenario and self.game_state.user_mapping:
                 progress_made = True
             elif isinstance(puzzle, ScenarioPuzzle):
                  # Simple check: is the scenario input widget non-empty?
                  widget = self.scenario_input_widget
                  if isinstance(widget, QLineEdit) and widget.text(): progress_made = True
                  elif isinstance(widget, QTextEdit) and widget.toPlainText(): progress_made = True
                  elif isinstance(widget, QButtonGroup) and widget.checkedButton(): progress_made = True
                  # Checking tables is more complex, might require iterating cells. Assume progress if table exists.
                  elif isinstance(widget, QTableWidget): progress_made = True


        # Only ask for confirmation if progress was likely made
        if progress_made:
             reply = QMessageBox.question(self, "Confirm New Puzzle",
                                          "Start a new puzzle? Your current progress on this puzzle will be lost.",
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                          QMessageBox.StandardButton.No)
             if reply == QMessageBox.StandardButton.No:
                 return

        try:
            self.game_state.start_new_puzzle(puzzle_type)
            self._update_ui_for_puzzle()
            display_name = self._get_puzzle_type_display_name(self.game_state.current_puzzle)
            self.feedback_label.setText(f"New puzzle started: {display_name}")
            self.feedback_label.setStyleSheet("")
        except (ValueError, RuntimeError) as e:
             logging.error(f"Failed to start new puzzle: {e}")
             QMessageBox.critical(self, "Error", f"Could not generate the next puzzle:\n{e}")
             self.feedback_label.setText("Error starting new puzzle.")
             self.feedback_label.setStyleSheet("color: red;")


    def _save_game(self):
        """Handles the 'Save Game' menu action."""
        if self.is_ai_running:
             logging.warning("Attempted manual save while AI running. Ignoring.")
             self.feedback_label.setText("Cannot save while AI is running.")
             self.feedback_label.setStyleSheet("color: orange;")
             return

        try:
            self.game_state.save_game()
            self.feedback_label.setText("Game saved successfully!")
            self.feedback_label.setStyleSheet("color: blue;")
        except Exception as e:
            logging.exception("Error during manual game save.")
            QMessageBox.warning(self, "Save Error", f"Could not save game: {e}")
            self.feedback_label.setText("Error saving game.")
            self.feedback_label.setStyleSheet("color: red;")


    def _update_theme_menu(self):
        """Updates the 'Themes' menu with available and unlocked themes."""
        self.theme_menu.clear()
        for theme_name in sorted(THEMES.keys()): # Sort themes alphabetically
            action = QAction(theme_name, self, checkable=True)
            is_unlocked = theme_name in self.game_state.unlocked_themes
            is_current = theme_name == self.game_state.current_theme

            action.setEnabled(is_unlocked)
            action.setChecked(is_current and is_unlocked)
            # Use lambda with default argument to capture the current theme_name
            action.triggered.connect(lambda checked=False, name=theme_name: self._change_theme(name))
            self.theme_menu.addAction(action)

    def _change_theme(self, theme_name: str):
        """Changes the current theme if unlocked and applies it."""
        if self.is_ai_running:
             logging.warning("Attempted theme change while AI running. Ignoring.")
             return # Don't allow theme change if AI runs

        if theme_name in self.game_state.unlocked_themes:
            self.game_state.current_theme = theme_name
            self._apply_theme()
            self._update_theme_menu() # Update checkmarks
            try:
                self.game_state.save_game() # Save theme choice
            except Exception as e:
                 logging.error(f"Could not save game after theme change: {e}")
                 QMessageBox.warning(self, "Save Error", f"Failed to save theme change: {e}")


    def _apply_theme(self):
        """Applies the current theme's stylesheet to the application."""
        theme_data = THEMES.get(self.game_state.current_theme)
        if theme_data:
            self.setStyleSheet(theme_data.stylesheet)
            # Re-apply theme-specific styles if needed (e.g., feedback label colors)
            # self._update_assignments_display() # Update assignments handles its own styles
            self.feedback_label.setStyleSheet("") # Reset feedback style on theme change
        else:
            logging.warning(f"Theme '{self.game_state.current_theme}' not found in THEMES.")
            self.setStyleSheet("") # Reset to default Qt style if theme missing


    def _show_how_to_play(self):
        """Displays a scrollable dialog explaining gameplay mechanics for all types."""
        dialog = QDialog(self)
        dialog.setWindowTitle("How to Play")
        dialog.setMinimumSize(600, 500)
        layout = QVBoxLayout(dialog)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        # Wrap HTML content in triple quotes for readability
        text_edit.setHtml("""
        <h1>The Alchemist's Cipher & Logic Puzzles</h1>

        <h2>1. Objective</h2>
        <p>Solve logic puzzles! Decode symbol-to-letter mappings using clues, or tackle various scenario-based logic challenges.</p>

        <h2>2. Interface</h2>
        <ul>
            <li><b>Top Bar:</b> Shows current level, solved count, puzzle type, and hints remaining.</li>
            <li><b>Left Area:</b> The main puzzle interaction area (symbol assignments, logic grids, text input, etc.).</li>
            <li><b>Right Area:</b> Displays clues, scenario descriptions, goals, and other relevant information.</li>
            <li><b>Bottom Bar:</b> Buttons to Get Hint, Check Solution, and Reset the current puzzle.</li>
            <li><b>Feedback Area:</b> Shows messages about your progress, hints, correctness, and errors.</li>
            <li><b>Menu Bar:</b> Access Game options (New Puzzle, Select Type, Save, AI Solver, Exit), Options (Themes), and Help (Tutorial, Practice, How to Play, About).</li>
        </ul>

        <h2>3. Puzzle Types</h2>

        <h3>Symbol Cipher</h3>
        <ul>
            <li><b>Goal:</b> Figure out which letter corresponds to each unique symbol.</li>
            <li><b>Input:</b> Use the dropdown boxes next to each symbol to select a letter. Letters assigned to one symbol cannot be assigned to another simultaneously.</li>
            <li><b>Clues:</b> Various types help you deduce the mapping (Direct 🔍, Exclusion ❌, Category 📑, Relational ↔️, Positional 📍, Logical 🧠).</li>
            <li><b>Strategy:</b> Start with direct clues. Use exclusion to narrow options. Combine clues. Use process of elimination.</li>
        </ul>

        <h3>Scenario Puzzles</h3>
        <p>These puzzles present a situation requiring logical deduction. Use the information in the right panel and the input area on the left.</p>
        <ul>
            <li><b>Logic Grid:</b>
                <ul><li><b>Goal:</b> Match items across several categories (e.g., Person -> Job -> Pet).</li>
                    <li><b>Input:</b> Use the grid. Mark cells with ✔️ (Yes) or ❌ (No) using the dropdowns. A 'Yes' indicates a definite match between the row item and the column item's category/value.</li>
                    <li><b>Strategy:</b> Fill the grid based on clues. Use 'No' to eliminate possibilities. Look for implications (if A is with B, and B is not with C, then A is not with C). Ensure each row item matches exactly one element from each column category group (one ✔️ per group per row/column). Complete the entire grid before checking.</li></ul>
            </li>
            <li><b>Social Deduction:</b>
                <ul><li><b>Goal:</b> Identify a person based on statements, roles, or actions (e.g., who is lying, who did it).</li>
                    <li><b>Input:</b> Type the name or identifier into the text box exactly as it appears in the scenario.</li>
                    <li><b>Strategy:</b> Analyze statements for contradictions or consistency with known traits/facts. Look for motives or opportunities.</li></ul>
            </li>
            <li><b>Common Sense Gap:</b>
                <ul><li><b>Goal:</b> Identify a missing item, step, or piece of information needed for a task or process.</li>
                    <li><b>Input:</b> Type the missing item/concept into the text box.</li>
                    <li><b>Strategy:</b> Read the description carefully. Think about the logical steps or components required for the described activity. What is essential but not mentioned?</li></ul>
             <li><b>Relationship Map:</b>
                <ul><li><b>Goal:</b> Determine the pairs or connections between individuals in a group.</li>
                    <li><b>Input:</b> Enter pairs in the text area, one per line using the format "Name1 : Name2". Ensure names match the scenario exactly.</li>
                    <li><b>Strategy:</b> Use positive clues ("A works with B") and negative clues ("C does not work with D") to establish links and exclusions. Ensure every individual is included in exactly one pair.</li></ul>
            </li>
             <li><b>Ordering:</b>
                <ul><li><b>Goal:</b> Determine the correct sequence of items or events.</li>
                    <li><b>Input:</b> Select the correct item for each position (Pos 1, Pos 2, etc.) in the table using the dropdowns.</li>
                    <li><b>Strategy:</b> Use clues about relative order ("A is before B"), absolute position ("C is first"), or adjacency ("D is immediately after E"). Ensure each item is used exactly once.</li></ul>
            </li>
             <li><b>Scheduling:</b>
                <ul><li><b>Goal:</b> Determine the availability or booking status (✔️=Booked, Blank=Available) for individuals across time slots based on constraints.</li>
                    <li><b>Input:</b> Use the table. Select ✔️ (Booked) or leave blank (Available) in each cell using the dropdowns.</li>
                    <li><b>Strategy:</b> Apply constraints systematically. Mark unavailable slots first based on clues. Resolve conflicts based on rules ('before', 'together', 'apart'). The final schedule must satisfy all conditions.</li></ul>
            </li>
             <li><b>Dilemma:</b>
                <ul><li><b>Goal:</b> Choose the most appropriate course of action in a complex situation with potential trade-offs, based on the provided context.</li>
                    <li><b>Input:</b> Select one of the radio button options representing the choices.</li>
                    <li><b>Strategy:</b> Carefully read the scenario and the contextual information/hints. Evaluate the potential consequences (short-term and long-term) of each option. Consider ethical implications, professional standards, and relationships.</li></ul>
            </li>
             <li><b>Agent Simulation / Identify Rule:</b>
                <ul><li><b>Goal:</b> Deduce agent behavior, predict future states, identify traits, or uncover hidden rules based on observations of a simulated system.</li>
                    <li><b>Input:</b> Type the answer (location, trait, rule text) into the text box. Match spelling/phrasing if identifying a rule.</li>
                    <li><b>Strategy:</b> Analyze the provided observations (agent locations over time, T=0, T=1...). Correlate movements with the known/observed rules. Look for patterns that suggest unstated rules or specific agent goals/traits driving the behavior.</li></ul>
            </li>
            </ul>

            <h2>4. Selecting Puzzle Types</h2>
            <ul>
            <li>Use the Game menu -> "Select Puzzle Type..."</li>
            <li>Choose "Symbol Cipher" or "Scenario Puzzle".</li>
            <li>If Scenario, you can choose a specific type (like Logic Grid, Ordering) or leave it as "Random Scenario" to get any scenario type.</li>
            </ul>

            <h2>5. AI Solver</h2>
            <ul>
            <li>Use Game -> "Run AI Solver" to have the game automatically solve puzzles and advance levels indefinitely.</li>
            <li>The AI uses the pre-calculated solution, demonstrating perfect play.</li>
            <li>Input controls will be disabled while the AI is running.</li>
            <li>Use Game -> "Stop AI Solver" to halt the AI and regain manual control.</li>
            <li>Progress made by the AI (levels, unlocks) is saved.</li>
            </ul>

            <h2>6. Hints & Solving</h2>
            <ul>
            <li>Use hints sparingly when stuck (limited per level). Hints may automatically apply for Symbol Ciphers.</li>
            <li>Check your solution when you think you've solved it. Ensure all inputs are complete.</li>
            <li>Reset the puzzle if you want to clear your inputs and start fresh (resets hint count too).</li>
            <li>Solve puzzles to increase your level, gain bragging rights, and unlock new visual themes!</li>
            </ul>

            <h2>7. Saving</h2>
            <p>Your progress (current level, solved count, unlocked themes, and current puzzle state) is automatically saved when you close the game or start a new puzzle. You can also save manually via the Game menu (not available while AI Solver is running).</p>
        """)
        layout.addWidget(text_edit)

        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        dialog.exec()


    def _show_about(self):
        """Displays a message box with information about the game."""
        QMessageBox.about(self, "About The Alchemist's Cipher",
                         f"The Alchemist's Cipher & Logic Puzzles\nVersion 2.2\n\n" # Increment version maybe
                         "A collection of logic puzzles including symbol ciphers and various human-centric scenarios.\n\n"
                         "Built with Python and PyQt6.\n"
                         f"(Save File Version: {self.game_state.SAVE_VERSION})")


    def _show_tutorial(self):
        """Shows the Logic Tutorial dialog window."""
        if self.is_ai_running: return # Ignore if AI running
        tutorial_dialog = TutorialDialog(self)
        tutorial_dialog.exec()


    def _show_practice_puzzle(self):
        """Shows the Practice Puzzle dialog window."""
        if self.is_ai_running: return # Ignore if AI running
        practice_dialog = PracticePuzzleDialog(self)
        practice_dialog.exec()


    def closeEvent(self, event):
        """Handles the main window close event, ensuring game is saved."""
        # Stop AI first if running
        if self.is_ai_running:
            self._stop_ai_solver()

        try:
            self.game_state.save_game() # Use internal save method now
            logging.info("Game saved on exit.")
        except Exception as e:
            logging.error(f"Error saving game on exit: {e}")
            reply = QMessageBox.warning(self, "Save Error",
                                        f"Could not save game state: {e}\n\nExit without saving?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                        QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

        event.accept()


    def _select_puzzle_type(self):
        """Opens a dialog to allow the user to select a specific puzzle type to start."""
        if self.is_ai_running: return # Ignore if AI running

        puzzle_type_dialog = PuzzleTypeDialog(self)
        if puzzle_type_dialog.exec() == QDialog.DialogCode.Accepted:
            selected_type = puzzle_type_dialog.selected_type
            self._confirm_and_start_new_puzzle(selected_type)


    def _get_puzzle_type_display_name(self, puzzle_or_type: Union[Puzzle, ScenarioPuzzle, HumanScenarioType, str, None]) -> str:
        """Gets a user-friendly display name for a puzzle instance or type identifier."""
        if isinstance(puzzle_or_type, Puzzle) and not puzzle_or_type.is_scenario:
            return "Symbol Cipher"
        elif isinstance(puzzle_or_type, ScenarioPuzzle):
             # Access the enum member directly if it's a puzzle instance
             p_type = getattr(puzzle_or_type, 'puzzle_type', None)
             if isinstance(p_type, HumanScenarioType):
                 return p_type.name.replace('_', ' ').title()
             else:
                 return "Scenario (Unknown Type)" # Fallback
        elif isinstance(puzzle_or_type, HumanScenarioType):
             # If it's the enum member itself
             return puzzle_or_type.name.replace('_', ' ').title()
        elif isinstance(puzzle_or_type, str):
             # Handle string identifiers used in selection dialog
             if puzzle_or_type == "Symbol": return "Symbol Cipher"
             if puzzle_or_type == "Scenario": return "Scenario (Random)"
             # Attempt to match string to enum name (case-insensitive, replace space/underscore)
             test_name = puzzle_or_type.replace(' ', '_').upper()
             try:
                 enum_match = HumanScenarioType[test_name]
                 return enum_match.name.replace('_', ' ').title()
             except KeyError:
                 return puzzle_or_type # Return original string if no match
        elif puzzle_or_type is None:
             return "Random (Default)"
        else:
             logging.warning(f"Could not get display name for type: {type(puzzle_or_type)}")
             return "Unknown Type"

    # --- AI Solver Methods ---

    def _start_ai_solver(self):
        """Starts the AI solver timer and updates UI state."""
        if self.is_ai_running:
            return
        if not self.game_state.current_puzzle:
             QMessageBox.warning(self, "AI Solver", "Cannot start AI solver, no puzzle is active.")
             return

        logging.info("Starting AI Solver...")
        self.is_ai_running = True
        self.ai_timer.start(self.ai_update_interval_ms)

        # Update UI: Disable interactive elements, enable Stop AI
        self.run_ai_action.setEnabled(False)
        self.stop_ai_action.setEnabled(True)
        self.check_button.setEnabled(False)
        self.reset_button.setEnabled(False)
        self.hint_button.setEnabled(False)
        # Disable puzzle input widgets (will be handled in _update_ui_for_puzzle)
        self._update_ui_for_puzzle() # Re-run to disable inputs

        self.feedback_label.setText("AI Solver Running...")
        self.feedback_label.setStyleSheet("color: purple;")


    def _stop_ai_solver(self):
        """Stops the AI solver timer and updates UI state."""
        if not self.is_ai_running:
            return

        logging.info("Stopping AI Solver.")
        self.is_ai_running = False
        self.ai_timer.stop()

        # Update UI: Enable interactive elements, disable Stop AI
        self.run_ai_action.setEnabled(True)
        self.stop_ai_action.setEnabled(False)
        # Re-enable based on puzzle state (will be handled in _update_ui_for_puzzle)
        self._update_ui_for_puzzle() # Re-run to enable inputs

        self.feedback_label.setText("AI Solver Stopped.")
        self.feedback_label.setStyleSheet("") # Reset style


    def _ai_step(self):
        """Performs one step of the AI solver logic."""
        if not self.is_ai_running:
            return

        try:
            logging.debug(f"AI step triggered for level {self.game_state.current_level + 1}")
            solved = self.game_state.ai_take_turn()

            if solved:
                # Puzzle was solved, game state advanced, new puzzle started
                self._update_ui_for_puzzle() # Update UI for the *new* puzzle

                # Check for unlocks immediately after solve
                unlocked_theme = self.game_state.check_unlockables()
                if unlocked_theme:
                    if self.game_state.unlock_theme(unlocked_theme):
                        logging.info(f"AI unlocked theme: {unlocked_theme}")
                        # Update theme menu non-blockingly
                        self._update_theme_menu()
                        self.feedback_label.setText(f"AI Solver Running... Unlocked '{unlocked_theme}'!")
                        self.feedback_label.setStyleSheet("color: purple; font-weight: bold;")
                    else: # Already unlocked, just proceed
                         self.feedback_label.setText(f"AI Solver Running... Level {self.game_state.current_level + 1}")
                         self.feedback_label.setStyleSheet("color: purple;")
                else: # No unlock, just update level info
                     self.feedback_label.setText(f"AI Solver Running... Level {self.game_state.current_level + 1}")
                     self.feedback_label.setStyleSheet("color: purple;")

            else:
                # AI failed to solve (error occurred in game_state.ai_take_turn)
                logging.error("AI step failed to solve puzzle. Stopping AI.")
                self.feedback_label.setText("AI encountered an error. Stopping.")
                self.feedback_label.setStyleSheet("color: red;")
                self._stop_ai_solver() # Stop the AI on error

        except Exception as e:
            logging.exception("Unexpected error during AI step execution.")
            self.feedback_label.setText(f"AI critical error: {e}. Stopping.")
            self.feedback_label.setStyleSheet("color: red;")
            self._stop_ai_solver() # Stop on any unexpected exception


# --- PuzzleTypeDialog Class (keep as is) ---
class PuzzleTypeDialog(QDialog):
    """Dialog window for selecting a specific puzzle type to generate."""
    def __init__(self, parent=None):
        """Initializes the puzzle type selection dialog."""
        super().__init__(parent)
        self.setWindowTitle("Select Puzzle Type")
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        desc_label = QLabel("Choose the type of puzzle you'd like to solve:")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        main_type_box = QFrame()
        main_type_box.setFrameShape(QFrame.Shape.StyledPanel)
        main_type_layout = QVBoxLayout(main_type_box)
        self.type_group = QButtonGroup(self)

        self.symbol_radio = QRadioButton("Symbol Cipher")
        self.symbol_radio.setChecked(True)
        self.type_group.addButton(self.symbol_radio)
        main_type_layout.addWidget(self.symbol_radio)
        symbol_desc = QLabel("    Decode alchemical symbols using logical clues.")
        symbol_desc.setWordWrap(True)
        main_type_layout.addWidget(symbol_desc)

        self.scenario_radio = QRadioButton("Scenario Puzzle")
        self.type_group.addButton(self.scenario_radio)
        main_type_layout.addWidget(self.scenario_radio)
        scenario_desc = QLabel("    Solve logic puzzles based on human scenarios.")
        scenario_desc.setWordWrap(True)
        main_type_layout.addWidget(scenario_desc)

        layout.addWidget(main_type_box)

        self.scenario_details_box = QFrame()
        self.scenario_details_box.setFrameShape(QFrame.Shape.StyledPanel)
        scenario_details_layout = QHBoxLayout(self.scenario_details_box)
        scenario_type_label = QLabel("Specific Scenario Type:")
        scenario_details_layout.addWidget(scenario_type_label)

        self.scenario_type_combo = QComboBox()
        self.scenario_type_combo.addItem("Random Scenario", "Scenario") # UserData "Scenario" means random
        # Populate with actual enum members as UserData
        for scenario_type in HumanScenarioType:
            display_name = scenario_type.name.replace('_', ' ').title()
            self.scenario_type_combo.addItem(display_name, scenario_type) # Store enum member

        scenario_details_layout.addWidget(self.scenario_type_combo, stretch=1)
        layout.addWidget(self.scenario_details_box)

        # Connect radio toggle to combo box enabled state
        self.scenario_radio.toggled.connect(self.scenario_details_box.setEnabled)
        # Initial state based on radio button
        self.scenario_details_box.setEnabled(self.scenario_radio.isChecked())


        layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.ok_button = QPushButton("Create Selected")
        self.ok_button.setDefault(True)
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        # Initialize selected_type based on default radio button
        self.selected_type: Optional[Union[str, HumanScenarioType]] = "Symbol" if self.symbol_radio.isChecked() else self.scenario_type_combo.currentData()


    def accept(self):
        """Handles the 'Create Selected' button click."""
        if self.symbol_radio.isChecked():
            self.selected_type = "Symbol" # Use string identifier
        elif self.scenario_radio.isChecked():
            # Get the data associated with the selected item (should be enum or "Scenario")
            self.selected_type = self.scenario_type_combo.currentData()
        super().accept()


# --- main Function (keep as is) ---
def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Alchemist Cipher Logic Puzzles")
    app.setOrganizationName("AI Logic Games") # Example organization
    app.setWindowIcon(QIcon.fromTheme("applications-education")) # Use a default theme icon

    # Apply a base style? Optional.
    # app.setStyle("Fusion")

    window = SymbolCipherGame()
    window.show()
    sys.exit(app.exec())

# --- Conditional Execution ---
if __name__ == '__main__':
    main()