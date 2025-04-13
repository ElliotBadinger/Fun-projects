import sys
from typing import Optional, Dict, Any, Union
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QPushButton, QLabel, QComboBox,
                           QTextEdit, QMessageBox, QMenuBar, QMenu, QGridLayout,
                           QFrame, QSizePolicy, QTableWidget, QTableWidgetItem,
                           QHeaderView, QLineEdit, QDialog, QRadioButton, QButtonGroup,
                           QScrollArea, QAbstractItemView) 
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon, QAction 

from .game_state import GameState
from .themes import THEMES
from .tutorial import TutorialDialog, PracticePuzzleDialog
from .puzzle import Puzzle, ScenarioPuzzle, ClueType, HumanScenarioType, PuzzleGenerator 
import logging

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
                self._confirm_and_start_new_puzzle() 
            self._update_ui_for_puzzle()
        except Exception as e:
            logging.exception("Error during initial game load or puzzle start.")
            QMessageBox.critical(self, "Initialization Error",
                                 f"An error occurred during loading or initialization: {e}\n"
                                 "Starting a fresh game state.")
            self.game_state = GameState() 
            self._confirm_and_start_new_puzzle()
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
            return

        self.check_button.setEnabled(True)
        self.reset_button.setEnabled(True)

        self.level_label.setText(f"Level: {puzzle.level + 1}")
        hints_left = self.game_state.max_hints_per_level - self.game_state.hints_used_this_level
        self.hints_label.setText(f"Hints Left: {hints_left}")
        self.hint_button.setEnabled(hints_left > 0)
        self.feedback_label.setText("")
        self.clues_text.clear()

        if isinstance(puzzle, Puzzle) and not puzzle.is_scenario:
            self.puzzle_type_label.setText("Type: Symbol Cipher")
            self.puzzle_title_label.setText("Symbols & Assignments")
            self.clues_title.setText("Alchemist's Notes (Clues)")
            self._create_symbol_puzzle_ui(puzzle)
            self._display_symbol_clues(puzzle)
        elif isinstance(puzzle, ScenarioPuzzle):
            puzzle_type_str = puzzle.puzzle_type.name.replace('_', ' ').title()
            self.puzzle_type_label.setText(f"Type: {puzzle_type_str}")
            self.puzzle_title_label.setText(f"Scenario: {puzzle_type_str}") 
            self.clues_title.setText("Scenario Information & Clues")
            self._create_scenario_puzzle_ui(puzzle)
            self._display_scenario_information(puzzle)
        else:
            self.puzzle_title_label.setText("Error")
            self.puzzle_content_layout.addWidget(QLabel("Error: Unknown puzzle type encountered."))
            logging.error(f"Unknown puzzle type in _update_ui_for_puzzle: {type(puzzle)}")

        self._apply_theme()
        self.puzzle_area_layout.activate()


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
                details = ", ".join(f"{k}: {v}" for k, v in char.items() if k != 'name' and k != 'state_history') 
                html_content += f"<li><b>{char.get('name', 'Unknown')}</b>: {details}</li>"
            html_content += "</ul>"

        if puzzle.setting and puzzle.setting.get('name') != "N/A":
             html_content += f"<h3>Setting:</h3><p>{puzzle.setting.get('name', '')} ({', '.join(puzzle.setting.get('details', []))})</p>"

        html_content += "<h3>Information & Clues:</h3>"
        if puzzle.information:
            html_content += "<ul>"
            for info in puzzle.information:
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

        assignments_grid = QGridLayout()
        symbols = puzzle.symbols
        letters_for_combo = [""] + sorted(puzzle.letters)
        num_cols = 3 

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

        if puzzle.puzzle_type == HumanScenarioType.LOGIC_GRID:
             self._create_logic_grid_ui(puzzle)
        elif puzzle.puzzle_type in [HumanScenarioType.SOCIAL_DEDUCTION,
                                     HumanScenarioType.COMMON_SENSE_GAP,
                                     HumanScenarioType.AGENT_SIMULATION]: 
            self.scenario_input_widget = self._create_line_edit_input(
                label_map.get(puzzle.puzzle_type, "Your Answer:")
            )
        elif puzzle.puzzle_type == HumanScenarioType.RELATIONSHIP_MAP:
            input_label = QLabel("Enter Pairs (one per line, e.g., 'Alice : Bob'):")
            self.scenario_input_widget = QTextEdit()
            self.scenario_input_widget.setPlaceholderText("Alice : Bob\nChloe : David\n...")
            self.scenario_input_widget.setFont(QFont("Arial", 11))
            self.scenario_input_widget.setFixedHeight(100) 
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
             for i in range(num_items):
                 table.setItem(i, 0, QTableWidgetItem(f"Position {i+1}")) 
             table.setVerticalHeaderLabels([str(i+1) for i in range(num_items)])
             table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
             for r in range(num_items):
                 combo = QComboBox()
                 combo.addItems([""] + sorted(items_to_order)) 
                 table.setCellWidget(r, 0, combo)

             self.scenario_input_widget = table 
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
                     combo.addItems(["", "✔️"]) 
                     combo.setFont(QFont("Arial", 12))
                     combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                     table.setCellWidget(r, c, combo)

             table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
             table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
             self.scenario_input_widget = table 
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
                 self.scenario_input_widget.addButton(radio_button, i) 
                 group_layout.addWidget(radio_button) 

             self.puzzle_content_layout.addWidget(group_box) 
        else:
             self.puzzle_content_layout.addWidget(QLabel(f"Input UI not implemented for type: {puzzle.puzzle_type.name}"))

        self.puzzle_content_layout.addStretch() 


    def _create_line_edit_input(self, label_text: str) -> QLineEdit:
        """Helper to create a label and line edit pair."""
        input_layout = QHBoxLayout()
        input_label = QLabel(label_text)
        line_edit = QLineEdit()
        line_edit.setFont(QFont("Arial", 11))
        input_layout.addWidget(input_label)
        input_layout.addWidget(line_edit)
        self.puzzle_content_layout.addLayout(input_layout) 
        return line_edit 


    def _create_logic_grid_ui(self, puzzle: ScenarioPuzzle):
        """Creates the QTableWidget UI for a Logic Grid scenario puzzle."""
        if not puzzle.elements or len(puzzle.elements) < 2:
            self.puzzle_content_layout.addWidget(QLabel("Error: Insufficient elements for logic grid."))
            return

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
                col_headers.append(f"{cat_name[:3]}:{element_name}") 
                col_category_map[flat_col_index] = (cat_name, element_name)
                flat_col_index += 1
        table.setHorizontalHeaderLabels(col_headers)
        self.scenario_input_widgets['logic_grid_col_map'] = col_category_map


        for r in range(num_rows):
            for c in range(num_cols):
                cell_combo = QComboBox()
                cell_combo.addItems(["", "✔️", "❌"]) 
                cell_combo.setFont(QFont("Arial", 12))
                table.setCellWidget(r, c, cell_combo)

        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch) 
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.resizeColumnsToContents()

        self.scenario_input_widget = table 
        self.puzzle_content_layout.addWidget(table)

        table.setMinimumHeight(num_rows * 40 + table.horizontalHeader().height())

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

            current_index = combo_box.findText(current_assignment)

            combo_box.clear()
            combo_box.addItem("") 

            for letter in sorted(puzzle.letters):
                combo_box.addItem(letter)
                item_index = combo_box.findText(letter)
                if item_index >= 0: 
                    item = combo_box.model().item(item_index)
                    if item:
                        is_assigned_elsewhere = (letter in assigned_letters and letter != current_assignment)
                        item.setEnabled(not is_assigned_elsewhere)

            if current_index != -1:
                 new_index = combo_box.findText(current_assignment)
                 if new_index != -1:
                     combo_box.setCurrentIndex(new_index)
                 else: 
                      combo_box.setCurrentIndex(0) 
            else:
                 combo_box.setCurrentIndex(0) 

            combo_box.blockSignals(False) 


    def _assign_letter(self, symbol: str, letter: str):
        """Handles the signal when a letter is assigned via ComboBox for Symbol Puzzles."""
        if not isinstance(self.game_state.current_puzzle, Puzzle) or self.game_state.current_puzzle.is_scenario:
            return 

        current_mapping = self.game_state.user_mapping

        existing_symbol_for_letter = None
        for s, l in current_mapping.items():
            if l == letter and s != symbol:
                existing_symbol_for_letter = s
                break

        if letter: 
            if existing_symbol_for_letter:
                current_mapping.pop(existing_symbol_for_letter, None)
                old_combo = self.assignment_widgets[existing_symbol_for_letter]['combo']
                old_combo.blockSignals(True)
                old_combo.setCurrentIndex(0) 
                old_combo.blockSignals(False)

            current_mapping[symbol] = letter 
        else: 
            current_mapping.pop(symbol, None)

        self._update_assignments_display() 


    def _use_hint(self):
        """Handles the 'Get Hint' button click."""
        hint_result = self.game_state.get_hint() 

        if not hint_result:
            self.feedback_label.setText("Internal error: Hint request failed.")
            return
        elif "No hints left" in hint_result or "No further hints" in hint_result or "No puzzle loaded" in hint_result:
             self.feedback_label.setText(hint_result)
             self.feedback_label.setStyleSheet("color: orange;")
             return

        self.feedback_label.setText(f"Hint: {hint_result}")
        self.feedback_label.setStyleSheet("color: #007bff;") 

        hints_left = self.game_state.max_hints_per_level - self.game_state.hints_used_this_level
        self.hints_label.setText(f"Hints Left: {hints_left}")
        self.hint_button.setEnabled(hints_left > 0)

        if isinstance(self.game_state.current_puzzle, Puzzle) and not self.game_state.current_puzzle.is_scenario:
            parts = hint_result.split("'")
            if len(parts) >= 5 and "maps to letter" in hint_result:
                 try:
                     symbol = parts[1]
                     letter = parts[3]
                     if symbol in self.assignment_widgets:
                          self._assign_letter(symbol, letter)
                          logging.info(f"Hint revealed mapping: {symbol} -> {letter}. UI updated.")
                 except IndexError:
                     logging.warning("Could not parse symbol/letter from hint text for UI update.")


    def _check_solution(self):
        """Handles the 'Check Solution' button click, retrieves UI solution, and gives feedback."""
        puzzle = self.game_state.current_puzzle
        if not puzzle: 
             self.feedback_label.setText("No puzzle active to check.")
             return

        user_solution_data = None
        is_correct = False

        try:
            if isinstance(puzzle, Puzzle) and not puzzle.is_scenario:
                 if len(self.game_state.user_mapping) < puzzle.num_elements:
                     self.feedback_label.setText("Please assign a letter to all symbols first.")
                     self.feedback_label.setStyleSheet("color: orange;")
                     return
                 is_correct = self.game_state.check_solution() 
            elif isinstance(puzzle, ScenarioPuzzle):
                 user_solution_data = self._get_scenario_solution_from_ui()
                 if user_solution_data is None:
                      self.feedback_label.setText("Please complete the puzzle input.")
                      self.feedback_label.setStyleSheet("color: orange;")
                      return
                 is_correct = self.game_state.check_solution(user_solution_data)
            else:
                 self.feedback_label.setText("Error: Cannot check unknown puzzle type.")
                 self.feedback_label.setStyleSheet("color: red;")
                 return

            if is_correct:
                self.feedback_label.setText(f"Correct! Level {puzzle.level + 1} Solved!")
                self.feedback_label.setStyleSheet("color: green;")
                self.game_state.puzzles_solved += 1

                feedback_title = "Puzzle Solved!"
                feedback_text = self._get_educational_feedback(puzzle)
                QMessageBox.information(self, feedback_title, feedback_text)

                unlocked_theme = self.game_state.check_unlockables()
                if unlocked_theme:
                    if self.game_state.unlock_theme(unlocked_theme):
                        QMessageBox.information(self, "Theme Unlocked!",
                            f"Congratulations!\nYou've unlocked the '{unlocked_theme}' theme!")
                        self._update_theme_menu() 

                if QMessageBox.question(self, "Next Level?",
                    "Proceed to the next level?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes) == QMessageBox.StandardButton.Yes:
                    self.game_state.current_level += 1
                    self._confirm_and_start_new_puzzle() 
                else:
                    self.check_button.setEnabled(False) 

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
            clue_types_used = getattr(puzzle, 'clue_types_used', set()) 
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
             scenario_type_name = puzzle.puzzle_type.name.replace('_', ' ').title()
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
                grid_solution = {} 
                solved_map = {} 
                rows = widget.rowCount()
                cols = widget.columnCount()
                row_headers = [widget.verticalHeaderItem(r).text() for r in range(rows)]
                col_map = self.scenario_input_widgets.get('logic_grid_col_map', {})
                if not col_map or len(col_map) != cols:
                     QMessageBox.critical(self, "Internal Error", "Logic grid column mapping is missing or incorrect.")
                     return None

                for entity in row_headers: solved_map[entity] = {}

                all_filled = True
                for r in range(rows):
                    entity_name = row_headers[r]
                    for c in range(cols):
                        cell_widget = widget.cellWidget(r, c)
                        if isinstance(cell_widget, QComboBox):
                             selection = cell_widget.currentText()
                             if not selection: 
                                 all_filled = False
                                 continue 

                             category_name, element_value = col_map[c]

                             if selection == "✔️": 
                                 if category_name in solved_map[entity_name] and solved_map[entity_name][category_name] != element_value:
                                      QMessageBox.warning(self, "Input Error", f"Contradiction found in grid for {entity_name}: Trying to assign {element_value} to {category_name}, but already has {solved_map[entity_name][category_name]}.")
                                      return None
                                 for other_entity, assignments in solved_map.items():
                                     if other_entity != entity_name and assignments.get(category_name) == element_value:
                                          QMessageBox.warning(self, "Input Error", f"Contradiction found in grid: {element_value} ({category_name}) is already assigned to {other_entity}, cannot also assign to {entity_name}.")
                                          return None

                                 solved_map[entity_name][category_name] = element_value
                             elif selection == "❌": 
                                  if solved_map.get(entity_name, {}).get(category_name) == element_value:
                                       QMessageBox.warning(self, "Input Error", f"Contradiction found in grid for {entity_name}: Marked 'No' for {element_value} ({category_name}), but it was previously marked 'Yes'.")
                                       return None

                        else:
                             logging.warning(f"Unexpected widget type in logic grid cell ({r},{c})")

                if not all_filled:
                     QMessageBox.information(self, "Input Incomplete", "Please make a selection (✔️ or ❌) for every cell in the logic grid.")
                     return None

                for entity, assignments in solved_map.items():
                    all_categories_present = True
                    for cat_name, _ in col_map.values(): 
                        if cat_name not in assignments:
                             all_categories_present = False; break
                    if not all_categories_present:
                         QMessageBox.warning(self, "Input Incomplete", f"Grid solution incomplete for {entity}. Ensure one ✔️ is selected for each category group.")
                         return None


                solution_dict = {"grid": solved_map} 

            elif isinstance(widget, QLineEdit) or isinstance(widget, QTextEdit):
                if isinstance(widget, QLineEdit):
                    answer = widget.text().strip()
                    if not answer:
                        QMessageBox.information(self, "Input Needed", "Please enter your answer.")
                        return None
                    solution_dict = {"answer": answer}
                elif isinstance(widget, QTextEdit) and puzzle.puzzle_type == HumanScenarioType.RELATIONSHIP_MAP:
                    raw_text = widget.toPlainText().strip()
                    solution_map = {}
                    if raw_text:
                        lines = raw_text.split('\n')
                        for i, line in enumerate(lines):
                            line = line.strip()
                            if not line: continue
                            parts = line.split(':', 1) 
                            if len(parts) == 2:
                                person1 = parts[0].strip()
                                person2 = parts[1].strip()
                                if person1 and person2:
                                    if person1 in solution_map or person2 in solution_map.values(): 
                                         QMessageBox.warning(self, "Input Error", f"Duplicate or conflicting entry found for '{person1}' or '{person2}' on line {i+1}. Each person should appear only once per side.")
                                         return None
                                    solution_map[person1] = person2
                                else:
                                    QMessageBox.warning(self, "Input Error", f"Invalid format on line {i+1}: '{line}'. Use 'Name1 : Name2'.")
                                    return None
                            else:
                                QMessageBox.warning(self, "Input Error", f"Invalid format on line {i+1}: '{line}'. Use 'Name1 : Name2'.")
                                return None
                    if len(solution_map) != len(puzzle.characters):
                         QMessageBox.information(self, "Input Incomplete", f"Please ensure all {len(puzzle.characters)} individuals are included in the pairs.")
                         return None

                    solution_dict = {"map": solution_map}

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
        puzzle = self.game_state.current_puzzle
        if not puzzle: return

        if QMessageBox.question(self, "Confirm Reset",
                              "Reset all your inputs for this puzzle?\n(Hints used will also be reset)",
                              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                              QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:

            self.game_state.hints_used_this_level = 0
            self.game_state.user_mapping = {}
            self.game_state.scenario_user_state = None 

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

                elif isinstance(widget, QButtonGroup): 
                    checked_button = widget.checkedButton()
                    if checked_button:
                         widget.setAutoExclusive(False)
                         checked_button.setChecked(False)
                         widget.setAutoExclusive(True)

            self.hints_label.setText(f"Hints Left: {self.game_state.max_hints_per_level}")
            self.hint_button.setEnabled(True)
            self.check_button.setEnabled(True) 
            self.feedback_label.setText("Puzzle reset.")
            self.feedback_label.setStyleSheet("") 


    def _confirm_and_start_new_puzzle(self, puzzle_type: Optional[Union[str, HumanScenarioType]] = None):
        """Unified method to confirm (if needed) and start a new puzzle."""
        progress_made = False
        puzzle = self.game_state.current_puzzle
        if puzzle:
             if isinstance(puzzle, Puzzle) and not puzzle.is_scenario and self.game_state.user_mapping:
                 progress_made = True
             elif isinstance(puzzle, ScenarioPuzzle) and self._get_scenario_solution_from_ui() is not None: 
                 progress_made = True 

        if progress_made:
             reply = QMessageBox.question(self, "Confirm New Puzzle",
                                          "Start a new puzzle? Your current progress will be lost.",
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                          QMessageBox.StandardButton.No)
             if reply == QMessageBox.StandardButton.No:
                 return 

        self.game_state.start_new_puzzle(puzzle_type)
        self._update_ui_for_puzzle()
        display_name = self._get_puzzle_type_display_name(self.game_state.current_puzzle)
        self.feedback_label.setText(f"New puzzle started: {display_name}")
        self.feedback_label.setStyleSheet("") 


    def _save_game(self):
        """Handles the 'Save Game' menu action."""
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
        for theme_name in THEMES:
            action = QAction(theme_name, self, checkable=True) 
            is_unlocked = theme_name in self.game_state.unlocked_themes
            is_current = theme_name == self.game_state.current_theme

            action.setEnabled(is_unlocked)
            action.setChecked(is_current and is_unlocked) 
            action.triggered.connect(lambda checked=False, name=theme_name: self._change_theme(name))
            self.theme_menu.addAction(action)

    def _change_theme(self, theme_name: str):
        """Changes the current theme if unlocked and applies it."""
        if theme_name in self.game_state.unlocked_themes:
            self.game_state.current_theme = theme_name
            self._apply_theme()
            self._update_theme_menu() 
            try:
                self.game_state.save_game() 
            except Exception as e:
                 logging.error(f"Could not save game after theme change: {e}")
                 QMessageBox.warning(self, "Save Error", f"Failed to save theme change: {e}")


    def _apply_theme(self):
        """Applies the current theme's stylesheet to the application."""
        theme_data = THEMES.get(self.game_state.current_theme)
        if theme_data:
            self.setStyleSheet(theme_data.stylesheet)
            self._update_assignments_display() 


    def _show_how_to_play(self):
        """Displays a scrollable dialog explaining gameplay mechanics for all types."""
        dialog = QDialog(self)
        dialog.setWindowTitle("How to Play")
        dialog.setMinimumSize(600, 500)
        layout = QVBoxLayout(dialog)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml("""
        <h1>The Alchemist's Cipher & Logic Puzzles</h1>

        <h2>1. Objective</h2>
        <p>Solve logic puzzles! Decode symbol-to-letter mappings using clues, or tackle various scenario-based logic challenges.</p>

        <h2>2. Interface</h2>
        <ul>
            <li><b>Top Bar:</b> Shows current level, puzzle type, and hints remaining.</li>
            <li><b>Left Area:</b> The main puzzle interaction area (symbol assignments, logic grids, etc.).</li>
            <li><b>Right Area:</b> Displays clues, scenario descriptions, goals, and other relevant information.</li>
            <li><b>Bottom Bar:</b> Buttons to Get Hint, Check Solution, and Reset the current puzzle.</li>
            <li><b>Feedback Area:</b> Shows messages about your progress, hints, and errors.</li>
            <li><b>Menu Bar:</b> Access Game options (New Puzzle, Select Type, Save, Exit), Options (Themes), and Help (Tutorial, How to Play, About).</li>
        </ul>

        <h2>3. Puzzle Types</h2>

        <h3>Symbol Cipher</h3>
        <ul>
            <li><b>Goal:</b> Figure out which letter corresponds to each unique symbol.</li>
            <li><b>Input:</b> Use the dropdown boxes next to each symbol to select a letter.</li>
            <li><b>Clues:</b> Various types help you deduce the mapping (Direct, Exclusion, Category, Relational, Positional, Logical).</li>
            <li><b>Strategy:</b> Start with direct clues. Use exclusion to narrow options. Combine clues. Use process of elimination.</li>
        </ul>

        <h3>Scenario Puzzles</h3>
        <p>These puzzles present a situation requiring logical deduction.</p>
        <ul>
            <li><b>Logic Grid:</b>
                <ul><li><b>Goal:</b> Match items across several categories (e.g., Person -> Job -> Pet).</li>
                    <li><b>Input:</b> Use the grid. Mark cells with ✔️ (Yes) or ❌ (No) using the dropdowns. A 'Yes' indicates a definite match between the row item and the column item (which represents an element from a specific category).</li>
                    <li><b>Strategy:</b> Fill the grid based on clues. Use 'No' to eliminate possibilities. Look for implications (if A is with B, and B is not with C, then A is not with C). Ensure each row item matches exactly one element from each column category group.</li></ul>
            </li>
            <li><b>Social Deduction:</b>
                <ul><li><b>Goal:</b> Identify a person based on statements, roles, or actions (e.g., who is lying, who did it).</li>
                    <li><b>Input:</b> Type the name or identifier into the text box.</li>
                    <li><b>Strategy:</b> Analyze statements for contradictions or consistency with known traits/facts. Look for motives or opportunities.</li></ul>
            </li>
            <li><b>Common Sense Gap:</b>
                <ul><li><b>Goal:</b> Identify a missing item, step, or piece of information needed for a task or process.</li>
                    <li><b>Input:</b> Type the missing item/concept into the text box.</li>
                    <li><b>Strategy:</b> Read the description carefully. Think about the logical steps or components required for the described activity. What is essential but not mentioned?</li></ul>
             <li><b>Relationship Map:</b>
                <ul><li><b>Goal:</b> Determine the pairs or connections between individuals in a group.</li>
                    <li><b>Input:</b> Enter pairs in the text area, one per line (e.g., "Name1 : Name2").</li>
                    <li><b>Strategy:</b> Use positive clues ("A works with B") and negative clues ("C does not work with D") to establish links and exclusions. Ensure everyone is paired correctly.</li></ul>
            </li>
             <li><b>Ordering:</b>
                <ul><li><b>Goal:</b> Determine the correct sequence of items or events.</li>
                    <li><b>Input:</b> Select the correct item for each position in the table using the dropdowns.</li>
                    <li><b>Strategy:</b> Use clues about relative order ("A is before B"), absolute position ("C is first"), or adjacency ("D is immediately after E").</li></ul>
            </li>
             <li><b>Scheduling:</b>
                <ul><li><b>Goal:</b> Determine the availability or booking status for individuals across time slots based on constraints.</li>
                    <li><b>Input:</b> Use the table. Select ✔️ (Booked) or leave blank (Available) in each cell using the dropdowns.</li>
                    <li><b>Strategy:</b> Apply constraints systematically. Mark 'unavailable' slots first. Resolve conflicts based on rules ('before', 'together', 'apart'). Ensure the final schedule satisfies all conditions.</li></ul>
            </li>
             <li><b>Dilemma:</b>
                <ul><li><b>Goal:</b> Choose the most appropriate course of action in a complex situation with potential trade-offs.</li>
                    <li><b>Input:</b> Select one of the radio button options.</li>
                    <li><b>Strategy:</b> Carefully read the scenario and the contextual information. Evaluate the potential consequences (short-term and long-term) of each option. Consider ethical implications and professional standards.</li></ul>
            </li>
             <li><b>Agent Simulation / Identify Rule:</b>
                <ul><li><b>Goal:</b> Deduce agent behavior, predict future states, identify traits, or uncover hidden rules based on observations of a simulated system.</li>
                    <li><b>Input:</b> Type the answer (location, trait, rule text) into the text box.</li>
                    <li><b>Strategy:</b> Analyze the provided observations (agent locations over time). Correlate movements with the known/observed rules. Look for patterns that suggest unstated rules or specific agent goals/traits.</li></ul>
            </li>
            </ul>

            <h2>4. Selecting Puzzle Types</h2>
            <ul>
            <li>Use the Game menu -> "Select Puzzle Type..."</li>
            <li>Choose "Symbol Cipher" or "Scenario Puzzle".</li>
            <li>If Scenario, you can choose a specific type or leave it as "Random Scenario" (currently default if 'Scenario Puzzle' radio is selected).</li>
            </ul>

            <h2>5. Hints & Solving</h2>
            <ul>
            <li>Use hints sparingly when stuck (limited per level).</li>
            <li>Check your solution when you think you've solved it.</li>
            <li>Reset the puzzle if you want to clear your inputs and start fresh.</li>
            <li>Solve puzzles to increase your level, gain bragging rights, and unlock new visual themes!</li>
            </ul>

            <h2>6. Saving</h2>
            <p>Your progress (current level, solved count, unlocked themes, and current puzzle state) is automatically saved when you close the game or start a new puzzle. You can also save manually via the Game menu.</p>
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
                         f"The Alchemist's Cipher & Logic Puzzles\nVersion 2.1\n\n" 
                         "A collection of logic puzzles including symbol ciphers and various human-centric scenarios.\n\n"
                         "Built with Python and PyQt6.\n"
                         f"(Save File Version: {self.game_state.SAVE_VERSION})")


    def _show_tutorial(self):
        """Shows the Logic Tutorial dialog window."""
        tutorial_dialog = TutorialDialog(self)
        tutorial_dialog.exec()


    def _show_practice_puzzle(self):
        """Shows the Practice Puzzle dialog window."""
        practice_dialog = PracticePuzzleDialog(self)
        practice_dialog.exec()


    def closeEvent(self, event):
        """Handles the main window close event, ensuring game is saved."""
        try:
            self._save_game() 
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
        puzzle_type_dialog = PuzzleTypeDialog(self)
        if puzzle_type_dialog.exec() == QDialog.DialogCode.Accepted:
            selected_type = puzzle_type_dialog.selected_type
            self._confirm_and_start_new_puzzle(selected_type)


    def _get_puzzle_type_display_name(self, puzzle_or_type: Union[Puzzle, ScenarioPuzzle, HumanScenarioType, str, None]) -> str:
        """Gets a user-friendly display name for a puzzle instance or type identifier."""
        if isinstance(puzzle_or_type, Puzzle) and not puzzle_or_type.is_scenario:
            return "Symbol Cipher"
        elif isinstance(puzzle_or_type, ScenarioPuzzle):
             return puzzle_or_type.puzzle_type.name.replace('_', ' ').title()
        elif isinstance(puzzle_or_type, HumanScenarioType):
             return puzzle_or_type.name.replace('_', ' ').title()
        elif isinstance(puzzle_or_type, str):
             if puzzle_or_type == "Symbol": return "Symbol Cipher"
             if puzzle_or_type == "Scenario": return "Scenario (Random)"
             return puzzle_or_type 
        elif puzzle_or_type is None:
             return "Random (Default)"
        else:
             return "Unknown Type"


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
        self.scenario_type_combo.addItem("Random Scenario", "Scenario") 
        for scenario_type in HumanScenarioType:
            display_name = scenario_type.name.replace('_', ' ').title()
            self.scenario_type_combo.addItem(display_name, scenario_type) 

        scenario_details_layout.addWidget(self.scenario_type_combo, stretch=1)
        layout.addWidget(self.scenario_details_box)

        self.scenario_radio.toggled.connect(self.scenario_type_combo.setEnabled) 
        self.scenario_type_combo.setEnabled(self.scenario_radio.isChecked()) 


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

        self.selected_type: Optional[Union[str, HumanScenarioType]] = "Symbol" 


    def accept(self):
        """Handles the 'Create Selected' button click."""
        if self.symbol_radio.isChecked():
            self.selected_type = "Symbol"
        elif self.scenario_radio.isChecked():
            self.selected_type = self.scenario_type_combo.currentData()
        super().accept()


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Alchemist Cipher Logic Puzzles")
    app.setOrganizationName("YourNameOrGroup") 
    app.setWindowIcon(QIcon.fromTheme("applications-education")) 

    window = SymbolCipherGame()
    window.show()
    sys.exit(app.exec())