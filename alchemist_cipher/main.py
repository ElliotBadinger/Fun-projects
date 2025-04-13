import sys
from typing import Optional, Dict, Any, Union, Tuple, List # Added List
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QPushButton, QLabel, QComboBox,
                           QTextEdit, QMessageBox, QMenuBar, QMenu, QGridLayout,
                           QFrame, QSizePolicy, QTableWidget, QTableWidgetItem,
                           QHeaderView, QLineEdit, QDialog, QRadioButton, QButtonGroup,
                           QScrollArea, QAbstractItemView)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QFont, QIcon, QAction

from .game_state import GameState
from .themes import THEMES
from .tutorial import TutorialDialog, PracticePuzzleDialog
from .puzzle import Puzzle, ScenarioPuzzle, ClueType, HumanScenarioType, PuzzleGenerator
import logging
import time # Import time for potential sleep (though QTimer is better)

# Setup basic logging if not already done elsewhere
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class SymbolCipherGame(QMainWindow):
    """Main application window for The Alchemist's Cipher & Logic Puzzles game."""
    def __init__(self):
        super().__init__()
        self.game_state = GameState()
        self.assignment_widgets: Dict[str, Dict[str, QComboBox]] = {}
        self.scenario_input_widget: Optional[QWidget] = None
        self.scenario_input_widgets: Dict[str, QWidget] = {}

        # --- AI Solver Attributes ---
        self.ai_timer = QTimer(self)
        self.ai_timer.timeout.connect(self._ai_step)
        self.is_ai_running = False
        self.ai_step_delay_ms = 750 # Time between AI showing solution and checking it
        # --- End AI Solver Attributes ---

        self.setWindowTitle("The Alchemist's Cipher & Logic Puzzles")
        self.setMinimumSize(900, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self._create_menu_bar()
        self._create_info_bar(main_layout)
        self._create_game_area(main_layout)
        self._create_control_bar(main_layout)
        self._create_feedback_label(main_layout)

        try:
            self.game_state.load_game()
            if not self.game_state.current_puzzle:
                logging.info("No puzzle loaded, starting a new default puzzle.")
                self.game_state.start_new_puzzle()
                self._update_ui_for_puzzle()
            else:
                self._update_ui_for_puzzle()
        except Exception as e:
            logging.exception("Error during initial game load or puzzle start.")
            QMessageBox.critical(self, "Initialization Error", f"An error occurred: {e}\nStarting fresh.")
            self.game_state = GameState()
            self.game_state.start_new_puzzle()
            self._update_ui_for_puzzle()

        self._apply_theme()

    # --- Menu Bar Creation (remains the same, including AI options) ---
    def _create_menu_bar(self):
        menubar = self.menuBar()
        game_menu = menubar.addMenu("Game")
        # ... (New, Select, Save actions) ...
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

        self.run_ai_action = QAction("Run AI Solver (Step-by-Step)", self)
        self.run_ai_action.triggered.connect(self._start_ai_solver)
        game_menu.addAction(self.run_ai_action)
        self.stop_ai_action = QAction("Stop AI Solver", self)
        self.stop_ai_action.triggered.connect(self._stop_ai_solver)
        self.stop_ai_action.setEnabled(False)
        game_menu.addAction(self.stop_ai_action)
        game_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        game_menu.addAction(exit_action)

        # --- Options and Help Menus (remain the same) ---
        options_menu = menubar.addMenu("Options")
        self.theme_menu = options_menu.addMenu("Themes")
        self._update_theme_menu()
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

    # --- UI Creation Methods (_create_info_bar, _create_game_area, etc.) remain largely the same ---
    # --- Ensure they disable/enable widgets based on self.is_ai_running ---
    # (Include the methods from the previous response here, ensuring enable/disable logic is present)
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
        self.puzzle_scroll_area = QScrollArea()
        self.puzzle_scroll_area.setWidgetResizable(True)
        self.puzzle_frame = QFrame(self.puzzle_scroll_area)
        self.puzzle_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        self.puzzle_area_layout = QVBoxLayout(self.puzzle_frame)
        self.puzzle_scroll_area.setWidget(self.puzzle_frame)
        self.puzzle_title_label = QLabel("Puzzle Area")
        self.puzzle_title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.puzzle_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.puzzle_area_layout.addWidget(self.puzzle_title_label)
        self.puzzle_content_widget = QWidget()
        self.puzzle_content_layout = QVBoxLayout(self.puzzle_content_widget)
        self.puzzle_area_layout.addWidget(self.puzzle_content_widget)
        self.puzzle_area_layout.addStretch()
        self.game_area_layout.addWidget(self.puzzle_scroll_area, stretch=3)
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
        control_layout = QHBoxLayout()
        control_frame = QFrame() # Use QFrame for better visual separation/styling
        control_frame.setFrameShape(QFrame.Shape.StyledPanel)
        control_frame_layout = QHBoxLayout(control_frame)

        icon_size = QSize(24, 24) # Define standard icon size

        # --- AI Control Buttons ---
        self.start_ai_button = QPushButton()
        self.start_ai_button.setIcon(QIcon.fromTheme("media-playback-start", QIcon("icons/play.png"))) # Example icon path
        self.start_ai_button.setIconSize(icon_size)
        self.start_ai_button.setToolTip("Start AI Solver")
        self.start_ai_button.clicked.connect(self._start_ai_solver)
        control_frame_layout.addWidget(self.start_ai_button)

        self.stop_ai_button = QPushButton()
        self.stop_ai_button.setIcon(QIcon.fromTheme("media-playback-stop", QIcon("icons/stop.png"))) # Example icon path
        self.stop_ai_button.setIconSize(icon_size)
        self.stop_ai_button.setToolTip("Stop AI Solver")
        self.stop_ai_button.clicked.connect(self._stop_ai_solver)
        self.stop_ai_button.setEnabled(False) # Initially disabled
        control_frame_layout.addWidget(self.stop_ai_button)

        control_frame_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # --- Check Button ---
        self.check_button = QPushButton()
        self.check_button.setIcon(QIcon.fromTheme("dialog-ok-apply", QIcon("icons/check.png"))) # Example icon path
        self.check_button.setIconSize(icon_size)
        self.check_button.setToolTip("Check Solution")
        self.check_button.clicked.connect(self._check_solution)
        control_frame_layout.addWidget(self.check_button)

        # --- Reset Button ---
        self.reset_button = QPushButton()
        self.reset_button.setIcon(QIcon.fromTheme("edit-undo", QIcon("icons/reset.png"))) # Example icon path
        self.reset_button.setIconSize(icon_size)
        self.reset_button.setToolTip("Reset Puzzle")
        self.reset_button.clicked.connect(self._reset_puzzle)
        control_frame_layout.addWidget(self.reset_button)

        control_layout.addWidget(control_frame)
        parent_layout.addLayout(control_layout)

    def _create_feedback_label(self, parent_layout):
        """Creates the label at the bottom for displaying feedback messages."""
        self.feedback_label = QLabel("")
        self.feedback_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.feedback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feedback_label.setMinimumHeight(30)
        self.feedback_label.setWordWrap(True)
        parent_layout.addWidget(self.feedback_label)

    # --- UI Update and Display Methods (largely the same, check enable logic) ---
    def _update_ui_for_puzzle(self):
        puzzle = self.game_state.current_puzzle
        self._clear_layout(self.puzzle_content_layout)
        self.assignment_widgets = {}
        self.scenario_input_widget = None
        self.scenario_input_widgets = {}
        is_interactive = not self.is_ai_running

        if not puzzle:
            # ... (handling for no puzzle) ...
            self.puzzle_title_label.setText("No Puzzle Loaded")
            self.puzzle_content_layout.addWidget(QLabel("Load a game or start a new puzzle."))
            self.level_label.setText("Level: -")
            self.puzzle_type_label.setText("Type: N/A")
            self.hints_label.setText("Hints Left: -")
            self.hint_button.setEnabled(False)
            self.check_button.setEnabled(False)
            self.reset_button.setEnabled(False)
            self.clues_text.clear()
            self.feedback_label.setText("No puzzle active.")
            self.run_ai_action.setEnabled(False)
            self.stop_ai_action.setEnabled(False)
            return

        self.run_ai_action.setEnabled(is_interactive) # Enable Run AI only if interactive
        self.check_button.setEnabled(is_interactive)
        self.reset_button.setEnabled(is_interactive)
        self.level_label.setText(f"Level: {puzzle.level + 1} (Solved: {self.game_state.puzzles_solved})")
        hints_left = self.game_state.max_hints_per_level - self.game_state.hints_used_this_level
        self.hints_label.setText(f"Hints Left: {hints_left}")
        self.hint_button.setEnabled(hints_left > 0 and is_interactive)
        if not self.is_ai_running: self.feedback_label.setText("")
        self.clues_text.clear()

        if isinstance(puzzle, Puzzle) and not puzzle.is_scenario:
            self.puzzle_type_label.setText("Type: Symbol Cipher")
            self.puzzle_title_label.setText("Symbols & Assignments")
            self.clues_title.setText("Alchemist's Notes (Clues)")
            self._create_symbol_puzzle_ui(puzzle) # Handles enable state internally
            self._display_symbol_clues(puzzle)
        elif isinstance(puzzle, ScenarioPuzzle):
            puzzle_type_str = self._get_puzzle_type_display_name(puzzle.puzzle_type)
            self.puzzle_type_label.setText(f"Type: {puzzle_type_str}")
            self.puzzle_title_label.setText(f"Scenario: {puzzle_type_str}")
            self.clues_title.setText("Scenario Information & Clues")
            self._create_scenario_puzzle_ui(puzzle) # Handles enable state internally
            self._display_scenario_information(puzzle)
        else:
            # ... (error handling) ...
             self.puzzle_title_label.setText("Error")
             self.puzzle_content_layout.addWidget(QLabel("Error: Unknown puzzle type."))

        self._apply_theme()
        self.puzzle_area_layout.activate()

    def _display_symbol_clues(self, puzzle: Puzzle):
        """Displays formatted clues for a symbol puzzle."""
        # ... (same as before) ...
        clue_style = "<style>li { margin-bottom: 5px; }</style><ul>"
        for clue_text, clue_type in puzzle.clues:
            prefix = self._get_clue_prefix(clue_type)
            clue_style += f"<li>{prefix}{clue_text}</li>"
        clue_style += "</ul>"
        self.clues_text.setHtml(clue_style)

    def _display_scenario_information(self, puzzle: ScenarioPuzzle):
        """Displays formatted information/clues for a scenario puzzle."""
        # ... (same as before, ensure safe access) ...
        html_content = f"<h3>Description:</h3><p>{puzzle.description}</p>"
        html_content += f"<h3>Goal:</h3><p>{puzzle.goal}</p><hr>"
        if puzzle.characters:
            html_content += "<h3>Characters/Entities Involved:</h3><ul>"
            for char in puzzle.characters:
                name = char.get('name', 'Unknown')
                details_list = []
                for k, v in char.items():
                    if k not in ['name', 'state_history', 'details']:
                        details_list.append(f"{k}: {v}")
                if 'details' in char:
                     details_val = char['details']
                     if isinstance(details_val, str) and details_val != "N/A": details_list.append(f"info: {details_val}")
                     elif isinstance(details_val, list) and details_val: details_list.append(f"info: {', '.join(details_val)}")
                details_str = ", ".join(details_list)
                html_content += f"<li><b>{name}</b>{f': {details_str}' if details_str else ''}</li>"
            html_content += "</ul>"
        if puzzle.setting and puzzle.setting.get('name') != "N/A":
             setting_name = puzzle.setting.get('name', '')
             setting_details_list = puzzle.setting.get('details', [])
             details_str = ""
             if isinstance(setting_details_list, list) and setting_details_list: details_str = f" ({', '.join(setting_details_list)})"
             elif isinstance(setting_details_list, str) and setting_details_list: details_str = f" ({setting_details_list})"
             html_content += f"<h3>Setting:</h3><p>{setting_name}{details_str}</p>"
        html_content += "<h3>Information & Clues:</h3>"
        if puzzle.information:
            html_content += "<ul>"
            for info in puzzle.information:
                if not isinstance(info, str): info = str(info)
                if info.startswith("Rule Observed:"): html_content += f"<li style='color: #007bff;'><i>{info}</i></li>"
                elif info.startswith("Hint:"): html_content += f"<li style='font-style: italic; color: #6c757d;'>{info}</li>"
                else: html_content += f"<li>{info}</li>"
            html_content += "</ul>"
        else: html_content += "<p>No specific clues provided.</p>"
        self.clues_text.setHtml(html_content)


    def _get_clue_prefix(self, clue_type: ClueType) -> str:
        """Returns a visual prefix for different clue types."""
        # ... (same as before) ...
        prefixes = { ClueType.DIRECT: "🔍 ", ClueType.EXCLUSION: "❌ ", ClueType.POSITIONAL: "📍 ", ClueType.RELATIONAL: "↔️ ", ClueType.CATEGORY: "📑 ", ClueType.LOGICAL: "🧠 ", }
        return prefixes.get(clue_type, "• ")

    # --- UI Creation Methods (ensure enable state is set based on is_interactive) ---
    def _create_symbol_puzzle_ui(self, puzzle: Puzzle):
        # ... (same as before, but check enable state inside) ...
        self._clear_layout(self.puzzle_content_layout)
        self.assignment_widgets = {}
        is_interactive = not self.is_ai_running
        assignments_grid = QGridLayout()
        symbols = puzzle.symbols
        letters_for_combo = [""] + sorted(puzzle.letters)
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
            letter_combo.setEnabled(is_interactive) # Set enabled
            letter_combo.currentTextChanged.connect(lambda text, s=symbol: self._assign_letter(s, text))
            assignments_grid.addWidget(letter_combo, row, col * 2 + 1)
            self.assignment_widgets[symbol] = {'combo': letter_combo}
        self.puzzle_content_layout.addLayout(assignments_grid)
        self._update_assignments_display() # Apply loaded state if any

    def _create_scenario_puzzle_ui(self, puzzle: ScenarioPuzzle):
        # ... (same as before, ensure enable state is passed/checked) ...
        self._clear_layout(self.puzzle_content_layout)
        self.scenario_input_widget = None
        self.scenario_input_widgets = {}
        is_interactive = not self.is_ai_running
        label_map = { HumanScenarioType.SOCIAL_DEDUCTION: "Who is the target individual?", HumanScenarioType.COMMON_SENSE_GAP: "What essential item is missing?", HumanScenarioType.AGENT_SIMULATION: "Enter your deduction (Location/Trait/Rule):", }
        if puzzle.puzzle_type == HumanScenarioType.LOGIC_GRID: self._create_logic_grid_ui(puzzle)
        elif puzzle.puzzle_type in label_map: self.scenario_input_widget = self._create_line_edit_input(label_map[puzzle.puzzle_type], is_interactive)
        elif puzzle.puzzle_type == HumanScenarioType.RELATIONSHIP_MAP:
            input_label = QLabel("Enter Pairs (one per line, e.g., 'Alice : Bob'):")
            self.scenario_input_widget = QTextEdit(); self.scenario_input_widget.setPlaceholderText("Alice : Bob\nChloe : David\n..."); self.scenario_input_widget.setFont(QFont("Arial", 11)); self.scenario_input_widget.setFixedHeight(100); self.scenario_input_widget.setEnabled(is_interactive)
            self.puzzle_content_layout.addWidget(input_label); self.puzzle_content_layout.addWidget(self.scenario_input_widget)
        elif puzzle.puzzle_type == HumanScenarioType.ORDERING: self._create_ordering_ui(puzzle, is_interactive)
        elif puzzle.puzzle_type == HumanScenarioType.SCHEDULING: self._create_scheduling_ui(puzzle, is_interactive)
        elif puzzle.puzzle_type == HumanScenarioType.DILEMMA: self._create_dilemma_ui(puzzle, is_interactive)
        else: self.puzzle_content_layout.addWidget(QLabel(f"Input UI not implemented for type: {puzzle.puzzle_type.name}"))
        self.puzzle_content_layout.addStretch()

    def _create_line_edit_input(self, label_text: str, enabled: bool) -> QLineEdit:
        # ... (same as before) ...
        input_layout = QHBoxLayout(); input_label = QLabel(label_text); line_edit = QLineEdit(); line_edit.setFont(QFont("Arial", 11)); line_edit.setEnabled(enabled)
        input_layout.addWidget(input_label); input_layout.addWidget(line_edit); self.puzzle_content_layout.addLayout(input_layout)
        return line_edit

    def _create_logic_grid_ui(self, puzzle: ScenarioPuzzle):
        # ... (ensure combo boxes are enabled/disabled) ...
        if not puzzle.elements or len(puzzle.elements) < 2: self.puzzle_content_layout.addWidget(QLabel("Error: Insufficient elements.")); return
        is_interactive = not self.is_ai_running
        categories = list(puzzle.elements.keys()); row_category = categories[0]; col_categories = categories[1:]; row_items = puzzle.elements[row_category]
        num_rows = len(row_items); num_cols = sum(len(puzzle.elements[cat]) for cat in col_categories)
        table = QTableWidget(num_rows, num_cols); table.setVerticalHeaderLabels(row_items)
        col_headers = []; col_category_map = {}; flat_col_index = 0
        for cat_name in col_categories:
            elements_in_cat = puzzle.elements[cat_name]
            for element_name in elements_in_cat: short_cat = cat_name[:3]; col_headers.append(f"{short_cat}:{element_name}"); col_category_map[flat_col_index] = (cat_name, element_name); flat_col_index += 1
        table.setHorizontalHeaderLabels(col_headers); self.scenario_input_widgets['logic_grid_col_map'] = col_category_map
        for r in range(num_rows):
            for c in range(num_cols): cell_combo = QComboBox(); cell_combo.addItems(["", "✔️", "❌"]); cell_combo.setFont(QFont("Arial", 12)); cell_combo.setEnabled(is_interactive); table.setCellWidget(r, c, cell_combo)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents); table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.scenario_input_widget = table; table.setEnabled(is_interactive); self.puzzle_content_layout.addWidget(table)
        table.setMinimumHeight(num_rows * 40 + table.horizontalHeader().height())


    def _create_ordering_ui(self, puzzle, is_interactive):
        input_label = QLabel("Enter Sequence (Top to Bottom):")
        self.puzzle_content_layout.addWidget(input_label)
        items_to_order = puzzle.solution.get('order', [])
        if not items_to_order: items_to_order = [f"Item {i+1}" for i in range(getattr(puzzle, 'num_items', 4))]; logging.warning("No ordering items in solution.")
        num_items = len(items_to_order)
        table = QTableWidget(num_items, 1); table.setHorizontalHeaderLabels(["Item"]); table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for r in range(num_items): combo = QComboBox(); combo.addItems([""] + sorted(items_to_order)); combo.setEnabled(is_interactive); table.setCellWidget(r, 0, combo); table.setVerticalHeaderItem(r, QTableWidgetItem(f"Pos {r+1}"))
        self.scenario_input_widget = table; table.setEnabled(is_interactive); table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.puzzle_content_layout.addWidget(table); table.setMinimumHeight(num_items * 40 + table.horizontalHeader().height())

    def _create_scheduling_ui(self, puzzle, is_interactive):
        input_label = QLabel("Enter Schedule (✔️ = Booked, leave blank = Available):")
        self.puzzle_content_layout.addWidget(input_label)
        schedule_data = puzzle.solution.get('schedule', {})
        if not schedule_data: self.puzzle_content_layout.addWidget(QLabel("Error: Sched data missing.")); return
        people = sorted(list(schedule_data.keys()))
        time_slots = sorted(list(schedule_data.get(people[0], {}).keys())) if people else []
        if not people or not time_slots: self.puzzle_content_layout.addWidget(QLabel("Error: People/Slots missing.")); return
        table = QTableWidget(len(people), len(time_slots)); table.setVerticalHeaderLabels(people); table.setHorizontalHeaderLabels(time_slots)
        for r in range(len(people)):
            for c in range(len(time_slots)): combo = QComboBox(); combo.addItems(["", "✔️"]); combo.setFont(QFont("Arial", 12)); combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding); combo.setEnabled(is_interactive); table.setCellWidget(r, c, combo)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.scenario_input_widget = table; table.setEnabled(is_interactive); self.puzzle_content_layout.addWidget(table)
        table.setMinimumHeight(len(people) * 40 + table.horizontalHeader().height())

    def _create_dilemma_ui(self, puzzle, is_interactive):
        input_label = QLabel("Select the most appropriate action:")
        self.puzzle_content_layout.addWidget(input_label)
        group_box = QWidget(); group_layout = QVBoxLayout(group_box); group_layout.setContentsMargins(5, 5, 5, 5)
        self.scenario_input_widget = QButtonGroup(self)
        options_to_display = getattr(puzzle, 'options', ["Error: Option A", "Error: Option B"])
        for i, option_text in enumerate(options_to_display): radio_button = QRadioButton(option_text); radio_button.setFont(QFont("Arial", 11)); radio_button.setEnabled(is_interactive); self.scenario_input_widget.addButton(radio_button, i); group_layout.addWidget(radio_button)
        self.puzzle_content_layout.addWidget(group_box); group_box.setEnabled(is_interactive)


    # --- Clear Layout Method ---
    def _clear_layout(self, layout):
        # ... (same as before) ...
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0); widget = item.widget()
                if widget is not None: widget.deleteLater()
                else: sub_layout = item.layout();
                if sub_layout is not None: self._clear_layout(sub_layout)

    # --- Assignment Logic ---
    def _update_assignments_display(self):
        # ... (same as before, ensures enable state is handled by creation method) ...
        if not isinstance(self.game_state.current_puzzle, Puzzle) or self.game_state.current_puzzle.is_scenario: return
        puzzle = self.game_state.current_puzzle; current_mapping = self.game_state.user_mapping; assigned_letters = set(current_mapping.values()); symbols_in_ui = list(self.assignment_widgets.keys())
        for symbol in symbols_in_ui:
            widget_dict = self.assignment_widgets.get(symbol);
            if not widget_dict or 'combo' not in widget_dict: continue
            combo_box = widget_dict['combo']; current_assignment = current_mapping.get(symbol, "")
            combo_box.blockSignals(True)
            current_text_index = combo_box.findText(current_assignment); combo_box.clear(); combo_box.addItem("")
            for letter in sorted(puzzle.letters): combo_box.addItem(letter)
            new_index = combo_box.findText(current_assignment) if current_assignment else 0
            combo_box.setCurrentIndex(new_index if new_index != -1 else 0)
            for i in range(1, combo_box.count()):
                letter = combo_box.itemText(i); item = combo_box.model().item(i)
                if item: is_assigned_elsewhere = (letter in assigned_letters and letter != current_assignment); item.setEnabled(not is_assigned_elsewhere)
            combo_box.blockSignals(False)

    def _assign_letter(self, symbol: str, letter: str):
        # ... (same as before, but uses _update_assignments_display) ...
        if self.is_ai_running: return
        if not isinstance(self.game_state.current_puzzle, Puzzle) or self.game_state.current_puzzle.is_scenario: return
        current_mapping = self.game_state.user_mapping; existing_symbol_for_letter = None
        for s, l in current_mapping.items():
            if l == letter and s != symbol and letter != "": existing_symbol_for_letter = s; break
        if letter:
            if existing_symbol_for_letter: current_mapping.pop(existing_symbol_for_letter, None)
            current_mapping[symbol] = letter
        else: current_mapping.pop(symbol, None)
        self._update_assignments_display()

    # --- Hint, Check, Reset (modified check) ---
    def _use_hint(self):
        # ... (same as before, respects AI state) ...
        if self.is_ai_running: return
        hint_result = self.game_state.get_hint()
        # ... (rest of hint logic - handling tuple/str, applying hint if symbol) ...
        if not hint_result: self.feedback_label.setText("Internal error: Hint failed."); self.feedback_label.setStyleSheet("color: red;"); return
        hint_text_display = ""
        if isinstance(hint_result, str):
             if "No hints left" in hint_result or "No further hints" in hint_result or "No puzzle loaded" in hint_result or "Cannot provide hint" in hint_result:
                  self.feedback_label.setText(hint_result); self.feedback_label.setStyleSheet("color: orange;")
                  self.hint_button.setEnabled(False if "No hints left" in hint_result else True); return
             else: hint_text_display = f"Hint: {hint_result}" # Generic string hint
        elif isinstance(hint_result, tuple) and len(hint_result) == 3: # Symbol cipher hint
            symbol, letter, reason = hint_result; hint_text_display = f"Hint ({reason}): Try mapping '{symbol}' to '{letter}'."
        else: self.feedback_label.setText("Bad hint format."); self.feedback_label.setStyleSheet("color: red;"); return
        self.feedback_label.setText(hint_text_display); self.feedback_label.setStyleSheet("color: #007bff;")
        hints_left = self.game_state.max_hints_per_level - self.game_state.hints_used_this_level
        self.hints_label.setText(f"Hints Left: {hints_left}"); self.hint_button.setEnabled(hints_left > 0)
        if isinstance(hint_result, tuple) and len(hint_result) == 3: symbol_to_assign, letter_to_assign, _ = hint_result; self._assign_letter(symbol_to_assign, letter_to_assign)


    def _check_solution(self, ai_initiated: bool = False):
        """Handles the 'Check Solution' button click or AI check, gives feedback, and maybe advances."""
        # If called by user button press and AI is running, ignore
        if not ai_initiated and self.is_ai_running:
             logging.warning("User check ignored while AI running.")
             return

        puzzle = self.game_state.current_puzzle
        if not puzzle:
             self.feedback_label.setText("No puzzle active to check.")
             return

        user_solution_data = None
        is_correct = False

        try:
            # Get solution data (either from UI or state)
            if isinstance(puzzle, Puzzle) and not puzzle.is_scenario:
                 if len(self.game_state.user_mapping) < puzzle.num_elements:
                     # Don't proceed if AI initiated and puzzle not fully mapped by AI (error state)
                     if ai_initiated:
                          logging.error("AI initiated check, but symbol puzzle not fully mapped.")
                          self._stop_ai_solver()
                          return
                     self.feedback_label.setText("Please assign a letter to all symbols first.")
                     self.feedback_label.setStyleSheet("color: orange;")
                     return
                 is_correct = self.game_state.check_solution() # Checks internal mapping
            elif isinstance(puzzle, ScenarioPuzzle):
                 user_solution_data = self._get_scenario_solution_from_ui()
                 if user_solution_data is None:
                      if ai_initiated:
                           logging.error("AI initiated check, but failed to get solution from UI.")
                           self._stop_ai_solver()
                           return
                      # Feedback already set by _get_scenario_solution_from_ui
                      return
                 is_correct = self.game_state.check_solution(user_solution_data)
            else:
                 # ... (handle unknown puzzle type error) ...
                 self.feedback_label.setText("Error: Cannot check unknown puzzle type."); self.feedback_label.setStyleSheet("color: red;"); return

            # --- Process result ---
            if is_correct:
                self.feedback_label.setText(f"Correct! Level {puzzle.level + 1} Solved!")
                self.feedback_label.setStyleSheet("color: green;")
                self.game_state.puzzles_solved += 1
                self.level_label.setText(f"Level: {self.game_state.current_level + 1} (Solved: {self.game_state.puzzles_solved})")

                # Show educational feedback only if user solved it
                if not ai_initiated:
                    feedback_title = "Puzzle Solved!"
                    feedback_text = self._get_educational_feedback(puzzle)
                    QMessageBox.information(self, feedback_title, feedback_text)

                # Check unlocks
                unlocked_theme = self.game_state.check_unlockables()
                if unlocked_theme and self.game_state.unlock_theme(unlocked_theme):
                    if not ai_initiated:
                         QMessageBox.information(self, "Theme Unlocked!", f"Congrats! Unlocked '{unlocked_theme}' theme!")
                    else:
                         logging.info(f"AI unlocked theme: {unlocked_theme}")
                         # Briefly update feedback during AI run
                         self.feedback_label.setText(f"AI Solver Running... Unlocked '{unlocked_theme}'!")
                         self.feedback_label.setStyleSheet("color: purple; font-weight: bold;")
                    self._update_theme_menu()

                # --- Advance Level ---
                proceed = False
                if ai_initiated:
                    proceed = True # AI always proceeds
                elif not self.is_ai_running: # Check user preference only if interactive
                    reply = QMessageBox.question(self, "Next Level?", "Proceed to the next level?",
                                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                                 QMessageBox.StandardButton.Yes)
                    proceed = (reply == QMessageBox.StandardButton.Yes)

                if proceed:
                    self.game_state.current_level += 1
                    # Add slight delay before starting next puzzle if AI is running
                    if self.is_ai_running:
                        QTimer.singleShot(int(self.ai_step_delay_ms / 2), self._start_next_ai_puzzle)
                    else:
                        self._start_next_human_puzzle() # Directly start for user
                else:
                    # User chose not to proceed, disable controls
                    self.check_button.setEnabled(False)
                    self.hint_button.setEnabled(False)

            else: # Incorrect Solution
                if ai_initiated:
                     # This implies the AI's solution was wrong (or internal solution is bad)
                     logging.error(f"AI provided INCORRECT solution for Level {puzzle.level + 1}. Stopping AI.")
                     self.feedback_label.setText(f"AI Error: Incorrect Solution! Stopping.")
                     self.feedback_label.setStyleSheet("color: red; font-weight: bold;")
                     self._stop_ai_solver()
                else:
                     # Feedback for user
                     self.feedback_label.setText("Incorrect solution. Keep trying!")
                     self.feedback_label.setStyleSheet("color: red;")
                     if isinstance(puzzle, ScenarioPuzzle): self.feedback_label.setText(self.feedback_label.text() + "\nReview info and deductions.")

        except Exception as e:
             logging.exception("Error occurred during solution checking.")
             self.feedback_label.setText(f"Error checking solution: {e}")
             self.feedback_label.setStyleSheet("color: red;")
             if ai_initiated: self._stop_ai_solver() # Stop AI on error

    def _start_next_ai_puzzle(self):
        """Starts the next puzzle during AI run."""
        if not self.is_ai_running: return # Safety check
        try:
             self.game_state.start_new_puzzle()
             self._update_ui_for_puzzle()
             # Schedule the next AI step (applying solution to the new puzzle)
             self.ai_timer.start(self.ai_step_delay_ms)
        except Exception as e:
            logging.exception("AI failed to start next puzzle. Stopping.")
            self.feedback_label.setText(f"AI Error starting next puzzle: {e}. Stopping.")
            self.feedback_label.setStyleSheet("color: red;")
            self._stop_ai_solver()

    def _start_next_human_puzzle(self):
        """Starts the next puzzle after user solves."""
        try:
            self.game_state.start_new_puzzle()
            self._update_ui_for_puzzle()
        except Exception as e:
             logging.error(f"Failed to start next puzzle for user: {e}")
             QMessageBox.critical(self, "Error", f"Could not generate next puzzle:\n{e}")


    def _reset_puzzle(self):
        # ... (same as before, respects AI state) ...
        if self.is_ai_running: return
        puzzle = self.game_state.current_puzzle;
        if not puzzle: return
        progress_made = False # Basic check if reset is meaningful
        if isinstance(puzzle, Puzzle) and not puzzle.is_scenario and self.game_state.user_mapping: progress_made = True
        elif isinstance(puzzle, ScenarioPuzzle):
             widget = self.scenario_input_widget # Check common input types
             if isinstance(widget, (QLineEdit, QTextEdit)) and (widget.text() if isinstance(widget, QLineEdit) else widget.toPlainText()): progress_made = True
             elif isinstance(widget, QButtonGroup) and widget.checkedButton(): progress_made = True
             elif isinstance(widget, QTableWidget): progress_made = True # Assume table has progress
        reply = QMessageBox.StandardButton.Yes
        if progress_made: reply = QMessageBox.question(self, "Confirm Reset", "Reset inputs & hints?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if not progress_made or reply == QMessageBox.StandardButton.Yes:
            self.game_state.hints_used_this_level = 0; self.game_state.user_mapping = {}; self.game_state.scenario_user_state = None
            if isinstance(puzzle, Puzzle) and not puzzle.is_scenario:
                for symbol, widget_dict in self.assignment_widgets.items(): combo = widget_dict.get('combo');
                if combo: combo.blockSignals(True); combo.setCurrentIndex(0); combo.blockSignals(False)
                self._update_assignments_display()
            elif isinstance(puzzle, ScenarioPuzzle):
                widget = self.scenario_input_widget
                if isinstance(widget, (QLineEdit, QTextEdit)): widget.clear()
                elif isinstance(widget, QTableWidget):
                     for r in range(widget.rowCount()):
                         for c in range(widget.columnCount()): cell_widget = widget.cellWidget(r, c);
                         if isinstance(cell_widget, QComboBox): cell_widget.setCurrentIndex(0)
                         elif isinstance(cell_widget, QLineEdit): cell_widget.clear()
                elif isinstance(widget, QButtonGroup): checked_button = widget.checkedButton();
                if checked_button: widget.setExclusive(False); checked_button.setChecked(False); widget.setExclusive(True)
            self.hints_label.setText(f"Hints Left: {self.game_state.max_hints_per_level}"); self.hint_button.setEnabled(True); self.check_button.setEnabled(True)
            self.feedback_label.setText("Puzzle reset."); self.feedback_label.setStyleSheet("")


    def _get_educational_feedback(self, puzzle: Union[Puzzle, ScenarioPuzzle]) -> str:
        # ... (same as before) ...
        if isinstance(puzzle, Puzzle) and not puzzle.is_scenario:
            feedback = "Symbol Cipher Solved!\n\nTechniques likely used:\n"; techniques = set(); clue_types_used = getattr(puzzle, 'clue_types_used', set())
            if not isinstance(clue_types_used, set): clue_types_used = set()
            for clue_type in clue_types_used:
                 if clue_type == ClueType.DIRECT: techniques.add("• Direct mapping (🔍)")
                 elif clue_type == ClueType.EXCLUSION: techniques.add("• Process of elimination (❌)")
                 elif clue_type == ClueType.POSITIONAL: techniques.add("• Positional reasoning (📍)")
                 elif clue_type == ClueType.RELATIONAL: techniques.add("• Relational analysis (↔️)")
                 elif clue_type == ClueType.CATEGORY: techniques.add("• Category-based reasoning (📑)")
                 elif clue_type == ClueType.LOGICAL: techniques.add("• Complex logical deduction (🧠)")
            if not techniques: techniques.add("• Careful deduction!")
            feedback += "\n".join(sorted(list(techniques))); return feedback
        elif isinstance(puzzle, ScenarioPuzzle):
             scenario_type_name = self._get_puzzle_type_display_name(puzzle.puzzle_type); feedback = f"Scenario Solved: {scenario_type_name}!\n\nSkills demonstrated:\n"
             type_feedback = { HumanScenarioType.SOCIAL_DEDUCTION: "• Analyzing statements/motives\n• Identifying inconsistencies", HumanScenarioType.COMMON_SENSE_GAP: "• Applying real-world knowledge\n• Identifying missing steps", HumanScenarioType.LOGIC_GRID: "• Systematic grid deduction\n• Applying constraints", HumanScenarioType.AGENT_SIMULATION: "• Pattern recognition\n• Rule inference", HumanScenarioType.RELATIONSHIP_MAP: "• Mapping connections\n• Interpreting relational clues", HumanScenarioType.ORDERING: "• Reconstructing sequences\n• Applying temporal logic", HumanScenarioType.SCHEDULING: "• Constraint satisfaction\n• Resource allocation", HumanScenarioType.DILEMMA: "• Evaluating consequences\n• Ethical reasoning", }
             feedback += type_feedback.get(puzzle.puzzle_type, "• Careful reading and logical deduction"); return feedback
        else: return "Puzzle Solved! Well done."

    def _get_scenario_solution_from_ui(self) -> Optional[Dict[str, Any]]:
        # ... (same robust implementation as before) ...
        puzzle = self.game_state.current_puzzle;
        if not isinstance(puzzle, ScenarioPuzzle): logging.error("Non-scenario in get UI solution."); return None
        widget = self.scenario_input_widget; solution_dict = {}
        try:
            if puzzle.puzzle_type == HumanScenarioType.LOGIC_GRID:
                 if not isinstance(widget, QTableWidget): QMessageBox.warning(self, "Input Error", "Logic grid UI not found."); return None
                 solved_map = {}; rows = widget.rowCount(); cols = widget.columnCount(); row_headers = [widget.verticalHeaderItem(r).text() for r in range(rows)]; col_map = self.scenario_input_widgets.get('logic_grid_col_map', {})
                 if not col_map or len(col_map) != cols: QMessageBox.critical(self, "Internal Error", "Grid mapping error."); return None
                 for entity in row_headers: solved_map[entity] = {}
                 all_cells_filled = True; validation_passed = True; temp_validation_map = {entity: {} for entity in row_headers}
                 for r in range(rows):
                      if not validation_passed: break
                      entity_name = row_headers[r]
                      for c in range(cols):
                           cell_widget = widget.cellWidget(r, c)
                           if isinstance(cell_widget, QComboBox):
                                selection = cell_widget.currentText()
                                if selection == "": all_cells_filled = False; continue # Skip blanks for validation logic but mark as not filled
                                category_name, element_value = col_map[c]
                                if selection == "✔️":
                                     if category_name in temp_validation_map[entity_name] and temp_validation_map[entity_name][category_name] != element_value: QMessageBox.warning(self, "Input Error", f"Grid Contradiction (Row): {entity_name} / {category_name}"); validation_passed = False; break
                                     for other_entity, assignments in temp_validation_map.items():
                                          if other_entity != entity_name and assignments.get(category_name) == element_value: QMessageBox.warning(self, "Input Error", f"Grid Contradiction (Col): {element_value} / {category_name}"); validation_passed = False; break
                                     if not validation_passed: break
                                     temp_validation_map[entity_name][category_name] = element_value
                                elif selection == "❌":
                                     if temp_validation_map.get(entity_name, {}).get(category_name) == element_value: QMessageBox.warning(self, "Input Error", f"Grid Contradiction (No vs Yes): {entity_name} / {element_value}"); validation_passed = False; break
                           else: logging.warning(f"Non-combo in grid cell ({r},{c})"); all_cells_filled = False; validation_passed = False; break
                      if not validation_passed: break
                 if not validation_passed: return None
                 if not all_cells_filled: QMessageBox.information(self, "Input Incomplete", "Please mark every cell (✔️ or ❌)."); return None
                 # Build final map from validated 'Yes' marks
                 final_solved_map = {entity: {} for entity in row_headers}
                 for r in range(rows):
                      entity_name = row_headers[r]
                      for c in range(cols):
                          cell_widget = widget.cellWidget(r,c);
                          if isinstance(cell_widget, QComboBox) and cell_widget.currentText() == "✔️": category_name, element_value = col_map[c]; final_solved_map[entity_name][category_name] = element_value
                 solution_dict = {"grid": final_solved_map}

            elif isinstance(widget, QLineEdit) or isinstance(widget, QTextEdit):
                if isinstance(widget, QLineEdit): answer = widget.text().strip();
                if not answer: QMessageBox.information(self, "Input Needed", "Please enter answer."); return None; solution_dict = {"answer": answer}
                elif isinstance(widget, QTextEdit) and puzzle.puzzle_type == HumanScenarioType.RELATIONSHIP_MAP:
                     raw_text = widget.toPlainText().strip(); user_map_input = {}; expected_pair_count = len(puzzle.characters) // 2 if puzzle.characters else 0; puzzle_char_names = {char['name'] for char in puzzle.characters} if puzzle.characters else set()
                     if raw_text:
                          lines = raw_text.split('\n'); processed_people = set()
                          for i, line in enumerate(lines):
                               line = line.strip();
                               if not line: continue
                               parts = line.split(':', 1)
                               if len(parts) == 2:
                                    person1 = parts[0].strip(); person2 = parts[1].strip()
                                    if person1 and person2:
                                         if person1 not in puzzle_char_names or person2 not in puzzle_char_names: QMessageBox.warning(self, "Input Error", f"Invalid name line {i+1}."); return None
                                         if person1 == person2: QMessageBox.warning(self, "Input Error", f"Cannot pair self line {i+1}."); return None
                                         if person1 in processed_people or person2 in processed_people: QMessageBox.warning(self, "Input Error", f"Duplicate person line {i+1}."); return None
                                         user_map_input[person1] = person2; processed_people.add(person1); processed_people.add(person2)
                                    else: QMessageBox.warning(self, "Input Error", f"Invalid fmt line {i+1} (missing name)."); return None
                               else: QMessageBox.warning(self, "Input Error", f"Invalid fmt line {i+1} (missing colon)."); return None
                     if len(user_map_input) != expected_pair_count: QMessageBox.information(self, "Input Incomplete", f"Enter {expected_pair_count} pairs for {len(puzzle.characters)} individuals."); return None
                     solution_dict = {"map": user_map_input}

            elif isinstance(widget, QTableWidget) and puzzle.puzzle_type == HumanScenarioType.ORDERING:
                 rows = widget.rowCount(); ordered_items = []; seen_items = set(); all_selected = True
                 for r in range(rows):
                      cell_widget = widget.cellWidget(r, 0)
                      if isinstance(cell_widget, QComboBox):
                           item = cell_widget.currentText()
                           if not item:
                                all_selected = False
                                break
                           if item in seen_items:
                                QMessageBox.warning(self, "Input Error", f"Item '{item}' duplicated.")
                                return None
                           ordered_items.append(item)
                           seen_items.add(item)
                      else:
                           logging.warning("Non-combo in ordering table.")
                           return None
                 if not all_selected: QMessageBox.information(self, "Input Incomplete", "Select item for each position."); return None
                 solution_dict = {"order": ordered_items}

            elif isinstance(widget, QTableWidget) and puzzle.puzzle_type == HumanScenarioType.SCHEDULING:
                 rows = widget.rowCount(); cols = widget.columnCount(); schedule_map = {}; people = [widget.verticalHeaderItem(r).text() for r in range(rows)]; time_slots = [widget.horizontalHeaderItem(c).text() for c in range(cols)]
                 for r, person in enumerate(people):
                      schedule_map[person] = {}
                      for c, slot in enumerate(time_slots):
                           cell_widget = widget.cellWidget(r, c)
                           if isinstance(cell_widget, QComboBox): selection = cell_widget.currentText(); status = "Booked" if selection == "✔️" else "Available"; schedule_map[person][slot] = status
                           else: logging.warning("Non-combo in scheduling table."); return None
                 solution_dict = {"schedule": schedule_map}

            elif isinstance(widget, QButtonGroup) and puzzle.puzzle_type == HumanScenarioType.DILEMMA:
                 checked_button = widget.checkedButton()
                 if checked_button: solution_dict = {"choice": checked_button.text()}
                 else: QMessageBox.information(self, "Input Needed", "Select a choice."); return None

            else: QMessageBox.critical(self, "UI Error", f"Cannot get UI solution for {puzzle.puzzle_type.name}."); return None

        except Exception as e: logging.exception("Error getting solution from UI."); QMessageBox.critical(self, "UI Error", f"Error reading solution: {e}"); return None
        return solution_dict


    # --- Theme and Misc Methods ---
    def _confirm_and_start_new_puzzle(self, puzzle_type: Optional[Union[str, HumanScenarioType]] = None):
        # ... (same as before, respects AI state) ...
        if self.is_ai_running: logging.warning("Manual new puzzle ignored while AI running."); return
        progress_made = False # Basic check if reset is meaningful
        if puzzle_type is None:
            puzzle = self.game_state.current_puzzle
            if puzzle:
                if isinstance(puzzle, Puzzle) and not puzzle.is_scenario and self.game_state.user_mapping: progress_made = True
                elif isinstance(puzzle, ScenarioPuzzle):
                    widget = self.scenario_input_widget # Check common input types
                    if isinstance(widget, (QLineEdit, QTextEdit)) and (widget.text() if isinstance(widget, QLineEdit) else widget.toPlainText()): progress_made = True
                    elif isinstance(widget, QButtonGroup) and widget.checkedButton(): progress_made = True
                    elif isinstance(widget, QTableWidget): progress_made = True # Assume table has progress
        if progress_made: reply = QMessageBox.question(self, "Confirm New Puzzle", "Start new puzzle? Progress lost.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No);
        if not progress_made or reply == QMessageBox.StandardButton.Yes:
            try: self.game_state.start_new_puzzle(puzzle_type); self._update_ui_for_puzzle(); display_name = self._get_puzzle_type_display_name(self.game_state.current_puzzle); self.feedback_label.setText(f"New puzzle started: {display_name}"); self.feedback_label.setStyleSheet("")
            except (ValueError, RuntimeError) as e: logging.error(f"Failed start new: {e}"); QMessageBox.critical(self, "Error", f"Could not generate puzzle:\n{e}"); self.feedback_label.setText("Error starting puzzle."); self.feedback_label.setStyleSheet("color: red;")

    def _save_game(self):
        # ... (same as before, respects AI state) ...
        if self.is_ai_running: logging.warning("Manual save ignored while AI running."); self.feedback_label.setText("Cannot save while AI is running."); self.feedback_label.setStyleSheet("color: orange;"); return
        try: self.game_state.save_game(); self.feedback_label.setText("Game saved!"); self.feedback_label.setStyleSheet("color: blue;")
        except Exception as e: logging.exception("Manual save error."); QMessageBox.warning(self, "Save Error", f"Could not save: {e}"); self.feedback_label.setText("Error saving."); self.feedback_label.setStyleSheet("color: red;")

    def _update_theme_menu(self):
        # ... (same as before) ...
        self.theme_menu.clear()
        for theme_name in sorted(THEMES.keys()): action = QAction(theme_name, self, checkable=True); is_unlocked = theme_name in self.game_state.unlocked_themes; is_current = theme_name == self.game_state.current_theme; action.setEnabled(is_unlocked); action.setChecked(is_current and is_unlocked); action.triggered.connect(lambda checked=False, name=theme_name: self._change_theme(name)); self.theme_menu.addAction(action)

    def _change_theme(self, theme_name: str):
        # ... (same as before, respects AI state) ...
        if self.is_ai_running: logging.warning("Theme change ignored while AI running."); return
        if theme_name in self.game_state.unlocked_themes:
            self.game_state.current_theme = theme_name; self._apply_theme(); self._update_theme_menu()
            try: self.game_state.save_game()
            except Exception as e: logging.error(f"Save fail on theme change: {e}"); QMessageBox.warning(self, "Save Error", f"Failed save theme: {e}")

    def _apply_theme(self):
        # ... (same as before) ...
        theme_data = THEMES.get(self.game_state.current_theme)
        if theme_data: self.setStyleSheet(theme_data.stylesheet); self.feedback_label.setStyleSheet("") # Reset feedback style
        else: logging.warning(f"Theme '{self.game_state.current_theme}' not found."); self.setStyleSheet("")

    def _show_how_to_play(self):
        # ... (same as before, update text if needed) ...
        dialog = QDialog(self); dialog.setWindowTitle("How to Play"); dialog.setMinimumSize(600, 500); layout = QVBoxLayout(dialog); text_edit = QTextEdit(); text_edit.setReadOnly(True)
        # Consider updating HTML content here if gameplay changed significantly
        text_edit.setHtml(""" ... [HTML from previous response] ... """) # Keep the existing HTML for now
        layout.addWidget(text_edit); close_button = QPushButton("Close"); close_button.clicked.connect(dialog.accept); button_layout = QHBoxLayout(); button_layout.addStretch(); button_layout.addWidget(close_button); button_layout.addStretch(); layout.addLayout(button_layout); dialog.exec()

    def _show_about(self):
        # ... (same as before) ...
        QMessageBox.about(self, "About The Alchemist's Cipher", f"The Alchemist's Cipher & Logic Puzzles\nVersion 2.3\n\nLogic puzzles and scenarios.\nBuilt with Python & PyQt6.\n(Save File Version: {self.game_state.SAVE_VERSION})")

    def _show_tutorial(self):
        # ... (same as before, respects AI state) ...
        if self.is_ai_running: return; tutorial_dialog = TutorialDialog(self); tutorial_dialog.exec()

    def _show_practice_puzzle(self):
        # ... (same as before, respects AI state) ...
        if self.is_ai_running: return; practice_dialog = PracticePuzzleDialog(self); practice_dialog.exec()

    def closeEvent(self, event):
        # ... (same as before, stops AI first) ...
        if self.is_ai_running: self._stop_ai_solver()
        try: self.game_state.save_game(); logging.info("Game saved on exit.")
        except Exception as e:
            logging.error(f"Save error on exit: {e}")
            reply = QMessageBox.warning(self, "Save Error", f"Could not save state: {e}\n\nExit anyway?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No: event.ignore(); return
        event.accept()

    def _select_puzzle_type(self):
        # ... (same as before, respects AI state) ...
        if self.is_ai_running: return
        puzzle_type_dialog = PuzzleTypeDialog(self)
        if puzzle_type_dialog.exec() == QDialog.DialogCode.Accepted: self.selected_type = puzzle_type_dialog.selected_type; self._confirm_and_start_new_puzzle(self.selected_type)

    def _get_puzzle_type_display_name(self, puzzle_or_type: Union[Puzzle, ScenarioPuzzle, HumanScenarioType, str, None]) -> str:
        # ... (same robust implementation as before) ...
        if isinstance(puzzle_or_type, Puzzle) and not puzzle_or_type.is_scenario: return "Symbol Cipher"
        elif isinstance(puzzle_or_type, ScenarioPuzzle): p_type = getattr(puzzle_or_type, 'puzzle_type', None); return p_type.name.replace('_', ' ').title() if isinstance(p_type, HumanScenarioType) else "Scenario (Unknown Type)"
        elif isinstance(puzzle_or_type, HumanScenarioType): return puzzle_or_type.name.replace('_', ' ').title()
        elif isinstance(puzzle_or_type, str):
             if puzzle_or_type == "Symbol": return "Symbol Cipher"
             if puzzle_or_type == "Scenario": return "Scenario (Random)"
             try: test_name = puzzle_or_type.replace(' ', '_').upper(); enum_match = HumanScenarioType[test_name]; return enum_match.name.replace('_', ' ').title()
             except KeyError: return puzzle_or_type
        elif puzzle_or_type is None: return "Random (Default)"
        else: logging.warning(f"Unknown type for display name: {type(puzzle_or_type)}"); return "Unknown Type"

    # --- AI Solver Methods ---

    def _start_ai_solver(self):
        if self.is_ai_running: return
        if not self.game_state.current_puzzle: QMessageBox.warning(self, "AI Solver", "No puzzle active."); return
        logging.info("Starting AI Solver (Step-by-Step)...")
        self.is_ai_running = True
        # Start the first step immediately
        QTimer.singleShot(100, self._ai_step) # Start step after short delay
        self.run_ai_action.setEnabled(False)
        self.stop_ai_action.setEnabled(True)
        self._update_ui_for_puzzle() # Disable interactive elements
        self.feedback_label.setText("AI Solver Running (Step Mode)...")
        self.feedback_label.setStyleSheet("color: purple;")

    def _stop_ai_solver(self):
        if not self.is_ai_running: return
        logging.info("Stopping AI Solver.")
        self.is_ai_running = False
        self.ai_timer.stop() # Stop any pending timer activity
        self.run_ai_action.setEnabled(True)
        self.stop_ai_action.setEnabled(False)
        self._update_ui_for_puzzle() # Re-enable interactive elements
        self.feedback_label.setText("AI Solver Stopped.")
        self.feedback_label.setStyleSheet("")

    def _ai_step(self):
        """Performs one step of the AI solver: Apply solution to UI."""
        if not self.is_ai_running: return # Stop if flag turned off

        puzzle = self.game_state.current_puzzle
        if not puzzle:
            logging.error("AI step: No puzzle found. Stopping.")
            self._stop_ai_solver()
            return

        logging.debug(f"AI Step: Applying solution to UI for Level {puzzle.level + 1}")
        self.feedback_label.setText(f"AI: Applying solution to Level {puzzle.level + 1}...")
        self.feedback_label.setStyleSheet("color: purple;")
        QApplication.processEvents() # Allow UI to update

        try:
            success = self._ai_apply_solution_to_ui()
            if not success:
                 logging.error("AI Step: Failed to apply solution to UI. Stopping.")
                 self.feedback_label.setText("AI Error: Failed applying solution. Stopping.")
                 self.feedback_label.setStyleSheet("color: red;")
                 self._stop_ai_solver()
                 return

            # Solution applied visually, now schedule the check
            QTimer.singleShot(self.ai_step_delay_ms, lambda: self._check_solution(ai_initiated=True))

        except Exception as e:
            logging.exception("AI Step: Error applying solution to UI. Stopping.")
            self.feedback_label.setText(f"AI Error applying solution: {e}. Stopping.")
            self.feedback_label.setStyleSheet("color: red;")
            self._stop_ai_solver()


    def _ai_apply_solution_to_ui(self) -> bool:
        """Reads the correct solution and updates the UI widgets."""
        puzzle = self.game_state.current_puzzle
        if not puzzle: return False

        try:
            if isinstance(puzzle, Puzzle) and not puzzle.is_scenario:
                solution_map = puzzle.solution_mapping
                logging.debug(f"AI applying Symbol solution: {solution_map}")
                for symbol, letter in solution_map.items():
                    if not self._ai_set_symbol_combo(symbol, letter):
                        logging.error(f"AI failed to set symbol '{symbol}' to '{letter}'")
                        return False
                 # Explicitly call update assignments to handle disabling correctly visually
                self.game_state.user_mapping = solution_map.copy() # Ensure internal state matches
                self._update_assignments_display()

            elif isinstance(puzzle, ScenarioPuzzle):
                solution_data = puzzle.solution # This is the ground truth
                logging.debug(f"AI applying Scenario solution ({puzzle.puzzle_type.name}): {solution_data}")

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
                    logging.warning(f"AI apply solution: UI update not implemented for {puzzle.puzzle_type.name}")
                    # For unimplemented types, maybe just skip applying to UI and directly check?
                    # For now, return False to indicate failure to apply.
                    return False

            QApplication.processEvents() # Ensure UI updates are visible
            return True

        except Exception as e:
            logging.exception(f"Error in _ai_apply_solution_to_ui for {type(puzzle)}")
            return False

    # --- AI Helper methods to set UI values ---

    def _ai_set_symbol_combo(self, symbol: str, letter: str) -> bool:
        widget_dict = self.assignment_widgets.get(symbol)
        if not widget_dict or 'combo' not in widget_dict: return False
        combo_box: QComboBox = widget_dict['combo']
        index = combo_box.findText(letter)
        if index >= 0:
            combo_box.setCurrentIndex(index)
            return True
        logging.warning(f"AI could not find letter '{letter}' in combo for symbol '{symbol}'")
        return False

    def _ai_set_line_edit(self, text: str) -> bool:
        if isinstance(self.scenario_input_widget, QLineEdit):
            self.scenario_input_widget.setText(str(text)) # Ensure string
            return True
        return False

    def _ai_set_relationship_map(self, solution_map: Dict[str, str]) -> bool:
        if not isinstance(self.scenario_input_widget, QTextEdit): return False
        # Format the map into "P1 : P2" lines, avoiding duplicates
        text_lines = []
        processed_pairs = set()
        for p1, p2 in solution_map.items():
             pair = frozenset([p1, p2])
             if pair not in processed_pairs:
                  text_lines.append(f"{p1} : {p2}")
                  processed_pairs.add(pair)
        self.scenario_input_widget.setText("\n".join(text_lines))
        return True

    def _ai_set_ordering_table(self, ordered_items: List[str]) -> bool:
        if not isinstance(self.scenario_input_widget, QTableWidget): return False
        table: QTableWidget = self.scenario_input_widget
        if table.rowCount() != len(ordered_items): return False
        for r, item in enumerate(ordered_items):
             cell_widget = table.cellWidget(r, 0)
             if isinstance(cell_widget, QComboBox):
                  index = cell_widget.findText(item)
                  if index >= 0: cell_widget.setCurrentIndex(index)
                  else: logging.warning(f"AI ordering: item '{item}' not found in combo row {r}"); return False
             else: return False
        return True

    def _ai_set_scheduling_table(self, schedule: Dict[str, Dict[str, str]]) -> bool:
        if not isinstance(self.scenario_input_widget, QTableWidget): return False
        table: QTableWidget = self.scenario_input_widget
        people = [table.verticalHeaderItem(r).text() for r in range(table.rowCount())]
        slots = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
        for r, person in enumerate(people):
             if person not in schedule: return False
             for c, slot in enumerate(slots):
                  if slot not in schedule[person]: return False
                  status = schedule[person][slot] # Should be "Booked" or "Available"
                  target_text = "✔️" if status == "Booked" else ""
                  cell_widget = table.cellWidget(r, c)
                  if isinstance(cell_widget, QComboBox):
                       index = cell_widget.findText(target_text)
                       if index >= 0: cell_widget.setCurrentIndex(index)
                       else: logging.warning(f"AI sched: text '{target_text}' not found row {r} col {c}"); return False
                  else: return False
        return True

    def _ai_set_dilemma_choice(self, choice_text: str) -> bool:
        if not isinstance(self.scenario_input_widget, QButtonGroup): return False
        group: QButtonGroup = self.scenario_input_widget
        for button in group.buttons():
            if button.text() == choice_text:
                button.setChecked(True)
                return True
        logging.warning(f"AI dilemma: choice '{choice_text}' not found.")
        return False

    def _ai_set_logic_grid(self, grid_solution: Dict[str, Dict[str, str]]) -> bool:
         if not isinstance(self.scenario_input_widget, QTableWidget): return False
         table: QTableWidget = self.scenario_input_widget
         rows = table.rowCount()
         cols = table.columnCount()
         row_headers = [table.verticalHeaderItem(r).text() for r in range(rows)]
         col_map = self.scenario_input_widgets.get('logic_grid_col_map', {})
         if not col_map or len(col_map) != cols: return False

         # Set all cells based on the solution
         for r, entity_name in enumerate(row_headers):
              if entity_name not in grid_solution: return False # Entity missing in solution
              entity_solution = grid_solution[entity_name] # {cat: val}

              for c in range(cols):
                   category_name, element_value = col_map[c]
                   cell_widget = table.cellWidget(r, c)
                   if not isinstance(cell_widget, QComboBox): return False

                   # Determine if this cell should be Yes or No
                   is_yes = entity_solution.get(category_name) == element_value
                   target_text = "✔️" if is_yes else "❌"

                   index = cell_widget.findText(target_text)
                   if index >= 0:
                        cell_widget.setCurrentIndex(index)
                   else:
                        logging.warning(f"AI Logic Grid: Text '{target_text}' not found for {entity_name}, {category_name}={element_value}")
                        # Fallback: try setting to blank if text not found? Or fail? Fail for now.
                        return False
         return True



# --- PuzzleTypeDialog Class (remains the same) ---
class PuzzleTypeDialog(QDialog):
    # ... (same as before) ...
    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowTitle("Select Puzzle Type"); self.setMinimumWidth(450); layout = QVBoxLayout(self); layout.setSpacing(10)
        desc_label = QLabel("Choose puzzle type:"); desc_label.setWordWrap(True); layout.addWidget(desc_label)
        main_type_box = QFrame(); main_type_box.setFrameShape(QFrame.Shape.StyledPanel); main_type_layout = QVBoxLayout(main_type_box); self.type_group = QButtonGroup(self)
        self.symbol_radio = QRadioButton("Symbol Cipher"); self.symbol_radio.setChecked(True); self.type_group.addButton(self.symbol_radio); main_type_layout.addWidget(self.symbol_radio); symbol_desc = QLabel("    Decode symbols using logical clues."); symbol_desc.setWordWrap(True); main_type_layout.addWidget(symbol_desc)
        self.scenario_radio = QRadioButton("Scenario Puzzle"); self.type_group.addButton(self.scenario_radio); main_type_layout.addWidget(self.scenario_radio); scenario_desc = QLabel("    Solve logic puzzles based on scenarios."); scenario_desc.setWordWrap(True); main_type_layout.addWidget(scenario_desc)
        layout.addWidget(main_type_box)
        self.scenario_details_box = QFrame(); self.scenario_details_box.setFrameShape(QFrame.Shape.StyledPanel); scenario_details_layout = QHBoxLayout(self.scenario_details_box); scenario_type_label = QLabel("Specific Scenario Type:"); scenario_details_layout.addWidget(scenario_type_label)
        self.scenario_type_combo = QComboBox(); self.scenario_type_combo.addItem("Random Scenario", "Scenario")
        for scenario_type in HumanScenarioType: display_name = scenario_type.name.replace('_', ' ').title(); self.scenario_type_combo.addItem(display_name, scenario_type)
        scenario_details_layout.addWidget(self.scenario_type_combo, stretch=1); layout.addWidget(self.scenario_details_box)
        self.scenario_radio.toggled.connect(self.scenario_details_box.setEnabled); self.scenario_details_box.setEnabled(self.scenario_radio.isChecked())
        layout.addStretch(); button_layout = QHBoxLayout(); button_layout.addStretch()
        self.ok_button = QPushButton("Create Selected"); self.ok_button.setDefault(True); self.ok_button.clicked.connect(self.accept); button_layout.addWidget(self.ok_button)
        self.cancel_button = QPushButton("Cancel"); self.cancel_button.clicked.connect(self.reject); button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout); self.selected_type: Optional[Union[str, HumanScenarioType]] = "Symbol" if self.symbol_radio.isChecked() else self.scenario_type_combo.currentData()
    def accept(self):
        if self.symbol_radio.isChecked(): self.selected_type = "Symbol"
        elif self.scenario_radio.isChecked(): self.selected_type = self.scenario_type_combo.currentData()
        super().accept()

# --- main Function (remains the same) ---
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Alchemist Cipher Logic Puzzles")
    app.setOrganizationName("AI Logic Games")
    app.setWindowIcon(QIcon.fromTheme("applications-education"))
    window = SymbolCipherGame()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()