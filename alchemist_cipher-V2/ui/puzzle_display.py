from PyQt6.QtWidgets import (QLabel, QComboBox, QGridLayout, QWidget, QVBoxLayout,
                             QHBoxLayout, QTableWidget, QLineEdit, QRadioButton,
                             QButtonGroup, QTableWidgetItem, QHeaderView, QTextEdit,
                             QSizePolicy)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
import logging
from typing import Optional, Dict, Any, Union

# Import puzzle types and enums
from ..puzzle.puzzle_types import Puzzle, ScenarioPuzzle
from ..puzzle.common import HumanScenarioType, ClueType

logger = logging.getLogger(__name__)

# --- Helper Functions ---

def clear_layout(layout):
    """Removes all widgets and sub-layouts from a layout."""
    if layout is not None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                # logger.debug(f"Deleting widget: {widget}")
                widget.deleteLater() # Schedule for deletion
            else:
                sub_layout = item.layout()
                if sub_layout is not None:
                    # logger.debug(f"Clearing sub-layout: {sub_layout}")
                    clear_layout(sub_layout)
                    # Optional: Delete the sub-layout object itself? Usually not needed.
                    # sub_layout.deleteLater() # Might be risky if referenced elsewhere

def get_puzzle_type_display_name(puzzle_or_type: Union[Puzzle, ScenarioPuzzle, HumanScenarioType, str, None]) -> str:
    """Gets a user-friendly display name for a puzzle or type."""
    if isinstance(puzzle_or_type, Puzzle) and not puzzle_or_type.is_scenario:
        return "Symbol Cipher"
    elif isinstance(puzzle_or_type, ScenarioPuzzle):
        p_type = getattr(puzzle_or_type, 'puzzle_type', None)
        return p_type.name.replace('_', ' ').title() if isinstance(p_type, HumanScenarioType) else "Scenario (Unknown Type)"
    elif isinstance(puzzle_or_type, HumanScenarioType):
        return puzzle_or_type.name.replace('_', ' ').title()
    elif isinstance(puzzle_or_type, str):
         # Handle simple strings like "Symbol", "Scenario"
         if puzzle_or_type == "Symbol": return "Symbol Cipher"
         if puzzle_or_type == "Scenario": return "Scenario (Random)"
         # Try converting string to Enum name (assuming format like "LOGIC_GRID" or "Logic Grid")
         try:
             test_name = puzzle_or_type.replace(' ', '_').upper()
             enum_match = HumanScenarioType[test_name]
             return enum_match.name.replace('_', ' ').title()
         except KeyError:
             return puzzle_or_type # Return original string if no match
    elif puzzle_or_type is None:
         return "Random (Default)"
    else:
         logger.warning(f"Unknown type passed to get_puzzle_type_display_name: {type(puzzle_or_type)}")
         return "Unknown Type"

def get_clue_prefix(clue_type: ClueType) -> str:
    """Returns a visual prefix string for different clue types."""
    prefixes = {
        ClueType.DIRECT: "🔍 ",
        ClueType.EXCLUSION: "❌ ",
        ClueType.POSITIONAL: "📍 ",
        ClueType.RELATIONAL: "↔️ ",
        ClueType.CATEGORY: "📑 ",
        ClueType.LOGICAL: "🧠 ",
    }
    return prefixes.get(clue_type, "• ") # Default bullet point


# --- UI Creation for Puzzle Input Area ---

def create_symbol_puzzle_ui(puzzle: Puzzle, parent_layout: QVBoxLayout, main_window):
    """Creates the UI elements (labels, comboboxes) for a Symbol Cipher."""
    logger.debug("Creating Symbol Cipher UI...")
    # Clear previous widgets in parent_layout (should already be done by _update_ui_for_puzzle)
    # clear_layout(parent_layout)

    # Ensure necessary refs are available
    if puzzle is None or parent_layout is None or not hasattr(main_window, 'assignment_widgets'):
        logger.error(f"Cannot create symbol UI: Missing puzzle={puzzle is None}, layout={parent_layout is None}, or main_window.assignment_widgets={not hasattr(main_window, 'assignment_widgets')}.")
        return
        
    # Add debug logging
    logger.debug(f"Symbol UI check passed: puzzle={puzzle}, layout={parent_layout}, layout.count={parent_layout.count() if parent_layout else 'N/A'}")

    main_window.assignment_widgets = {} # Reset assignment widgets dict
    is_interactive = not main_window.is_ai_running

    assignments_grid = QGridLayout()
    assignments_grid.setSpacing(10) # Add spacing

    symbols = puzzle.symbols
    # Prepare letter options: blank + sorted unique letters
    letters_for_combo = [""] + sorted(list(set(puzzle.letters)))
    num_symbols = len(symbols)

    # Determine number of columns based on symbol count for better layout
    num_cols = 2 if num_symbols <= 6 else 3 if num_symbols <= 12 else 4

    for i, symbol in enumerate(symbols):
        row, col = divmod(i, num_cols)

        # Symbol Label
        symbol_label = QLabel(symbol)
        symbol_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        symbol_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        symbol_label.setMinimumWidth(40)
        assignments_grid.addWidget(symbol_label, row, col * 2) # Column 0, 2, 4...

        # Letter ComboBox
        letter_combo = QComboBox()
        letter_combo.addItems(letters_for_combo)
        letter_combo.setFont(QFont("Arial", 14))
        letter_combo.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        letter_combo.setMinimumWidth(60)
        letter_combo.setEnabled(is_interactive) # Set enabled state
        # Connect signal to main window's method, passing the symbol
        letter_combo.currentTextChanged.connect(lambda text, s=symbol: main_window._assign_letter(s, text))
        assignments_grid.addWidget(letter_combo, row, col * 2 + 1) # Column 1, 3, 5...

        # Store reference to the combo box for later updates
        main_window.assignment_widgets[symbol] = {'combo': letter_combo}

    parent_layout.addLayout(assignments_grid)
    # Call display update immediately after creation to set initial state/disable options
    update_symbol_assignments_display(main_window)
    logger.debug("Symbol Cipher UI created.")


def create_scenario_puzzle_ui(puzzle: ScenarioPuzzle, parent_layout: QVBoxLayout, main_window):
    """Creates the appropriate UI input elements for the given scenario puzzle type."""
    # Add check for valid parameters
    if puzzle is None or parent_layout is None:
        logger.error(f"Cannot create scenario UI: Missing puzzle={puzzle is None}, layout={parent_layout is None}")
        return
        
    logger.debug(f"Creating Scenario UI for type: {puzzle.puzzle_type.name}")
    # Add debug logging of the layout
    logger.debug(f"Scenario UI layout check: layout={parent_layout}, layout.count={parent_layout.count() if parent_layout else 'N/A'}")
    # Clear previous widgets (should be done already)
    # clear_layout(parent_layout)

    # Reset main scenario widget references
    main_window.scenario_input_widget = None
    main_window.scenario_input_widgets = {} # Clear helper dict too
    is_interactive = not main_window.is_ai_running

    # --- Create UI based on puzzle type ---
    puzzle_type = puzzle.puzzle_type

    if puzzle_type == HumanScenarioType.LOGIC_GRID:
        _create_logic_grid_ui(puzzle, parent_layout, main_window, is_interactive)

    elif puzzle_type == HumanScenarioType.RELATIONSHIP_MAP:
        _create_relationship_map_ui(puzzle, parent_layout, main_window, is_interactive)

    elif puzzle_type == HumanScenarioType.ORDERING:
        _create_ordering_ui(puzzle, parent_layout, main_window, is_interactive)

    elif puzzle_type == HumanScenarioType.SCHEDULING:
        _create_scheduling_ui(puzzle, parent_layout, main_window, is_interactive)

    elif puzzle_type == HumanScenarioType.DILEMMA:
        _create_dilemma_ui(puzzle, parent_layout, main_window, is_interactive)

    elif puzzle_type in [HumanScenarioType.SOCIAL_DEDUCTION,
                         HumanScenarioType.COMMON_SENSE_GAP,
                         HumanScenarioType.AGENT_SIMULATION]:
        # These types expect a single string answer
        label_map = {
            HumanScenarioType.SOCIAL_DEDUCTION: "Who is the deduced individual?",
            HumanScenarioType.COMMON_SENSE_GAP: "What essential item/tool is missing?",
            HumanScenarioType.AGENT_SIMULATION: "Enter your deduction (e.g., Name, Item, Rule):",
        }
        label_text = label_map.get(puzzle_type, "Enter your answer:")
        _create_line_edit_input(label_text, parent_layout, main_window, is_interactive)

    else:
        # Fallback for unimplemented types
        logger.warning(f"Input UI not implemented for scenario type: {puzzle_type.name}")
        parent_layout.addWidget(QLabel(f"Input UI not implemented for type: {puzzle_type.name}"))

    parent_layout.addStretch(1) # Add stretch at the bottom of the puzzle area
    logger.debug("Scenario UI creation complete.")


# --- Specific Scenario UI Creation Helpers ---

def _create_line_edit_input(label_text: str, parent_layout: QVBoxLayout, main_window, is_interactive: bool):
    """Creates a label and a QLineEdit for simple text answers."""
    input_layout = QHBoxLayout()
    input_label = QLabel(label_text)
    line_edit = QLineEdit()
    line_edit.setFont(QFont("Arial", 11))
    line_edit.setEnabled(is_interactive)
    line_edit.setPlaceholderText("Type your answer here")
    input_layout.addWidget(input_label)
    input_layout.addWidget(line_edit, stretch=1) # Allow line edit to stretch
    parent_layout.addLayout(input_layout)
    # Store reference to the line edit as the main input widget
    main_window.scenario_input_widget = line_edit


def _create_logic_grid_ui(puzzle: ScenarioPuzzle, parent_layout: QVBoxLayout, main_window, is_interactive: bool):
    """Creates the QTableWidget for logic grid puzzles."""
    if not puzzle.elements or not isinstance(puzzle.elements, dict) or len(puzzle.elements) < 2:
        parent_layout.addWidget(QLabel("Error: Invalid or insufficient elements data for Logic Grid."))
        logger.error("Invalid elements data for Logic Grid UI creation.")
        return

    categories = list(puzzle.elements.keys())
    row_category = categories[0] # Assume first category is rows
    col_categories = categories[1:]
    row_items = puzzle.elements[row_category]

    if not row_items or not col_categories:
         parent_layout.addWidget(QLabel("Error: Missing row or column categories for Logic Grid."))
         logger.error("Missing row/column categories for Logic Grid UI.")
         return

    num_rows = len(row_items)
    # Calculate total columns needed
    col_headers = []
    col_category_map = {} # Map flat column index -> (category_name, element_value)
    flat_col_index = 0
    for cat_name in col_categories:
        elements_in_cat = puzzle.elements.get(cat_name, [])
        if not elements_in_cat:
             logger.warning(f"No elements found for column category: {cat_name}")
             continue
        for element_name in elements_in_cat:
             # Create short header like "Col: Name"
             short_cat = cat_name[:3] # Abbreviate category name
             col_headers.append(f"{short_cat}:{element_name}")
             col_category_map[flat_col_index] = (cat_name, element_name)
             flat_col_index += 1

    num_cols = len(col_headers)
    if num_cols == 0:
        parent_layout.addWidget(QLabel("Error: No columns generated for Logic Grid."))
        logger.error("No columns generated for Logic Grid UI.")
        return

    # Create the table
    table = QTableWidget(num_rows, num_cols)
    table.setVerticalHeaderLabels(row_items)
    table.setHorizontalHeaderLabels(col_headers)
    main_window.scenario_input_widgets['logic_grid_col_map'] = col_category_map # Store mapping

    # Populate table with ComboBoxes
    for r in range(num_rows):
        for c in range(num_cols):
            cell_combo = QComboBox()
            cell_combo.addItems(["", "✔️", "❌"]) # Blank, Yes, No
            cell_combo.setFont(QFont("Arial", 12, QFont.Weight.Bold)) # Make symbols clearer
            cell_combo.setStyleSheet("combobox-popup: 0;") # Compact dropdown
            cell_combo.setMinimumWidth(40)
            cell_combo.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
            cell_combo.setEnabled(is_interactive)
            table.setCellWidget(r, c, cell_combo)

    # Configure table appearance
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    # table.horizontalHeader().setStretchLastSection(True) # Stretch last column? Maybe not needed.
    table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    table.setAlternatingRowColors(True) # Improve readability

    # Store table reference and add to layout
    main_window.scenario_input_widget = table
    table.setEnabled(is_interactive) # Enable/disable the whole table
    parent_layout.addWidget(table)

    # Adjust minimum height based on content
    header_height = table.horizontalHeader().height()
    row_height_estimate = 40 # Estimate height per row
    table.setMinimumHeight(num_rows * row_height_estimate + header_height + 10) # Add padding

def _create_relationship_map_ui(puzzle: ScenarioPuzzle, parent_layout: QVBoxLayout, main_window, is_interactive: bool):
    """Creates a QTextEdit for relationship map input."""
    input_label = QLabel("Enter relationships (one per line, e.g., 'Alice : Bob'):")
    text_edit = QTextEdit()
    text_edit.setPlaceholderText("Alice : Bob\nChloe : David\n...")
    text_edit.setFont(QFont("Arial", 11))
    text_edit.setFixedHeight(150) # Set a fixed height? Or allow expansion?
    text_edit.setEnabled(is_interactive)

    parent_layout.addWidget(input_label)
    parent_layout.addWidget(text_edit)
    main_window.scenario_input_widget = text_edit


def _create_ordering_ui(puzzle: ScenarioPuzzle, parent_layout: QVBoxLayout, main_window, is_interactive: bool):
    """Creates a QTableWidget with ComboBoxes for ordering puzzles."""
    input_label = QLabel("Select the item for each position in the sequence (Top = First):")
    parent_layout.addWidget(input_label)

    # Get items to order - ideally from puzzle elements if available, otherwise from solution
    items_to_order = []
    if puzzle.elements and isinstance(puzzle.elements, dict):
        # Assume elements might store the items under a key like 'items' or the primary category
        items_key = list(puzzle.elements.keys())[0] if puzzle.elements else None
        if items_key: items_to_order = puzzle.elements[items_key]
    if not items_to_order and puzzle.solution and 'order' in puzzle.solution:
         # Fallback to using items from the solution if elements aren't structured for this
         items_to_order = puzzle.solution['order']
    if not items_to_order or not isinstance(items_to_order, list):
         parent_layout.addWidget(QLabel("Error: Could not determine items to order."))
         logger.error("Could not determine items for Ordering UI.")
         return

    num_items = len(items_to_order)
    table = QTableWidget(num_items, 1)
    table.setHorizontalHeaderLabels(["Item in Sequence"])
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

    combo_options = [""] + sorted(items_to_order) # Blank option + sorted items
    for r in range(num_items):
        combo = QComboBox()
        combo.addItems(combo_options)
        combo.setEnabled(is_interactive)
        combo.setFont(QFont("Arial", 11))
        table.setCellWidget(r, 0, combo)
        table.setVerticalHeaderItem(r, QTableWidgetItem(f"Position {r+1}"))

    main_window.scenario_input_widget = table
    table.setEnabled(is_interactive)
    parent_layout.addWidget(table)
    # Adjust height
    header_height = table.horizontalHeader().height()
    row_height_estimate = 35
    table.setMinimumHeight(num_items * row_height_estimate + header_height + 10)


def _create_scheduling_ui(puzzle: ScenarioPuzzle, parent_layout: QVBoxLayout, main_window, is_interactive: bool):
    """Creates a QTableWidget for scheduling puzzles."""
    input_label = QLabel("Mark scheduled appointments (✔️ = Booked, leave blank = Available):")
    parent_layout.addWidget(input_label)

    # Determine people (rows) and slots (columns) from solution structure or elements
    schedule_data = puzzle.solution.get('schedule', {})
    people = []
    time_slots = []

    if schedule_data and isinstance(schedule_data, dict):
        people = sorted(list(schedule_data.keys()))
        if people:
            # Try to get consistent slots from the first person's schedule
            time_slots = sorted(list(schedule_data.get(people[0], {}).keys()))

    # Fallback or alternative: use puzzle.characters and puzzle.setting['details']?
    if not people and puzzle.characters:
        people = sorted([c.get('name', f'Person{i+1}') for i, c in enumerate(puzzle.characters)])
    if not time_slots and puzzle.setting and isinstance(puzzle.setting.get('details'), list):
         time_slots = sorted(puzzle.setting['details'])

    if not people or not time_slots:
         parent_layout.addWidget(QLabel("Error: Could not determine people or time slots for scheduling grid."))
         logger.error("Could not determine people/slots for Scheduling UI.")
         return

    table = QTableWidget(len(people), len(time_slots))
    table.setVerticalHeaderLabels(people)
    table.setHorizontalHeaderLabels(time_slots)

    for r in range(len(people)):
        for c in range(len(time_slots)):
            combo = QComboBox()
            combo.addItems(["", "✔️"]) # Available (blank), Booked (check)
            combo.setFont(QFont("Arial", 12))
            combo.setStyleSheet("combobox-popup: 0;")
            combo.setMinimumWidth(50)
            combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding) # Expand to fill cell
            combo.setEnabled(is_interactive)
            table.setCellWidget(r, c, combo)

    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.setAlternatingRowColors(True)

    main_window.scenario_input_widget = table
    table.setEnabled(is_interactive)
    parent_layout.addWidget(table)
    # Adjust height
    header_height = table.horizontalHeader().height()
    row_height_estimate = 35
    table.setMinimumHeight(len(people) * row_height_estimate + header_height + 10)


def _create_dilemma_ui(puzzle: ScenarioPuzzle, parent_layout: QVBoxLayout, main_window, is_interactive: bool):
    """Creates RadioButtons within a ButtonGroup for dilemma choices."""
    input_label = QLabel("Select the most appropriate action:")
    input_label.setWordWrap(True)
    parent_layout.addWidget(input_label)

    # Use a QWidget as a container for layout purposes if needed, or just add buttons directly
    # group_box = QWidget()
    # group_layout = QVBoxLayout(group_box)
    # group_layout.setContentsMargins(5, 5, 5, 5)
    # group_layout.setSpacing(10)

    button_group = QButtonGroup(main_window) # Parent is main window for lifetime management
    main_window.scenario_input_widget = button_group # Store the QButtonGroup

    options_to_display = getattr(puzzle, 'options', [])
    if not options_to_display or not isinstance(options_to_display, list):
         parent_layout.addWidget(QLabel("Error: No valid options found for this dilemma."))
         logger.error("No valid options found for Dilemma UI.")
         return

    for i, option_text in enumerate(options_to_display):
        radio_button = QRadioButton(option_text)
        radio_button.setFont(QFont("Arial", 11))
        radio_button.setEnabled(is_interactive)
        radio_button.setWordWrap(True) # Allow options to wrap
        radio_button.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Preferred)
        button_group.addButton(radio_button, i) # Add button to group with an ID (index)
        parent_layout.addWidget(radio_button) # Add directly to parent layout

    # parent_layout.addWidget(group_box) # Add the container if used
    # group_box.setEnabled(is_interactive) # Enable/disable container? Button group doesn't have setEnabled


# --- UI State Retrieval ---

def get_scenario_solution_from_ui(main_window, check_completeness=True) -> Optional[Dict[str, Any]]:
    """Retrieves the current user solution from the scenario input UI elements."""
    puzzle = main_window.game_state.current_puzzle
    widget = main_window.scenario_input_widget

    if not isinstance(puzzle, ScenarioPuzzle):
        logger.error("Attempted to get scenario solution when puzzle is not a ScenarioPuzzle.")
        return None
    if not widget:
         logger.error("Attempted to get scenario solution, but scenario_input_widget is None.")
         main_window._set_feedback("Internal UI Error: Input widget not found.", "red")
         return None

    logger.debug(f"Getting scenario solution from UI for type: {puzzle.puzzle_type.name}")
    solution_dict = {}

    try:
        # --- Logic Grid ---
        if puzzle.puzzle_type == HumanScenarioType.LOGIC_GRID:
             if not isinstance(widget, QTableWidget):
                 main_window._set_feedback("Internal UI Error: Expected QTableWidget for Logic Grid.", "red")
                 return None
             solved_map = {}
             rows = widget.rowCount()
             cols = widget.columnCount()
             try:
                 row_headers = [widget.verticalHeaderItem(r).text() for r in range(rows)]
                 col_map = main_window.scenario_input_widgets.get('logic_grid_col_map', {})
             except AttributeError:
                  main_window._set_feedback("Internal UI Error: Grid headers/mapping missing.", "red")
                  return None

             if not col_map or len(col_map) != cols:
                 main_window._set_feedback("Internal UI Error: Grid column mapping error.", "red")
                 return None

             # Initialize map for all entities
             for entity in row_headers: solved_map[entity] = {}

             # Validate input: Ensure no contradictions and all cells filled (if checking completeness)
             all_cells_filled = True
             validation_passed = True
             temp_validation_map = {entity: {} for entity in row_headers} # Track 'Yes' assignments for validation

             for r in range(rows):
                 if not validation_passed: break
                 entity_name = row_headers[r]
                 yes_in_row_for_cat = {} # Track yes counts per category for this row

                 for c in range(cols):
                      cell_widget = widget.cellWidget(r, c)
                      if isinstance(cell_widget, QComboBox):
                           selection = cell_widget.currentText()
                           category_name, element_value = col_map[c]

                           if check_completeness and selection == "":
                                all_cells_filled = False
                                continue # Skip blanks if checking completeness

                           if selection == "✔️":
                                # Check Row Constraint: Only one 'Yes' per category group in a row
                                if category_name in temp_validation_map[entity_name] and temp_validation_map[entity_name][category_name] != element_value:
                                     main_window._set_feedback(f"Input Error: Grid contradiction in row '{entity_name}' for category '{category_name}'.", "orange")
                                     validation_passed = False; break
                                # Check Column Constraint: Only one 'Yes' per value across all entities
                                for other_entity, assignments in temp_validation_map.items():
                                     if other_entity != entity_name and assignments.get(category_name) == element_value:
                                          main_window._set_feedback(f"Input Error: Grid contradiction in column for '{element_value}' ({category_name}).", "orange")
                                          validation_passed = False; break
                                if not validation_passed: break
                                # Tentatively assign 'Yes' for validation
                                temp_validation_map[entity_name][category_name] = element_value

                           elif selection == "❌":
                                # Check against tentative 'Yes' assignment
                                if temp_validation_map.get(entity_name, {}).get(category_name) == element_value:
                                     main_window._set_feedback(f"Input Error: Grid contradiction - Cannot mark 'No' where 'Yes' is implied for '{entity_name}' / '{element_value}'.", "orange")
                                     validation_passed = False; break
                      else:
                           logger.warning(f"Non-ComboBox widget found in logic grid cell ({r},{c}).")
                           validation_passed = False # Treat unexpected widget as error
                           break # Stop checking this row
                 if not validation_passed: break # Stop checking rows

             if not validation_passed: return None # Contradiction found

             if check_completeness and not all_cells_filled:
                  main_window._set_feedback("Input Incomplete: Please mark every cell in the grid (✔️ or ❌).", "orange")
                  return None

             # If validation passes (and complete if checked), build the final solution map from 'Yes' marks
             final_solved_map = {entity: {} for entity in row_headers}
             for r in range(rows):
                  entity_name = row_headers[r]
                  for c in range(cols):
                      cell_widget = widget.cellWidget(r,c)
                      if isinstance(cell_widget, QComboBox) and cell_widget.currentText() == "✔️":
                           category_name, element_value = col_map[c]
                           final_solved_map[entity_name][category_name] = element_value
             solution_dict = {"grid": final_solved_map}

        # --- Simple Text Input ---
        elif isinstance(widget, QLineEdit):
            answer = widget.text().strip()
            if check_completeness and not answer:
                main_window._set_feedback("Input Needed: Please enter your answer.", "orange")
                return None
            solution_dict = {"answer": answer}

        # --- Relationship Map (TextEdit) ---
        elif isinstance(widget, QTextEdit) and puzzle.puzzle_type == HumanScenarioType.RELATIONSHIP_MAP:
             raw_text = widget.toPlainText().strip()
             user_map_input = {}
             expected_pair_count = len(puzzle.characters) // 2 if puzzle.characters else 0
             puzzle_char_names = {str(char.get('name','')) for char in puzzle.characters} if puzzle.characters else set() # Ensure names are strings

             if raw_text:
                  lines = raw_text.split('\n')
                  processed_people = set()
                  line_num = 0
                  for line in lines:
                       line_num += 1
                       line = line.strip()
                       if not line or line.startswith('#'): continue # Ignore empty lines and comments

                       parts = line.split(':', 1)
                       if len(parts) == 2:
                            person1_raw = parts[0].strip()
                            person2_raw = parts[1].strip()
                            person1 = str(person1_raw) # Ensure string
                            person2 = str(person2_raw)

                            if person1 and person2:
                                 # Validate names against puzzle characters
                                 if person1 not in puzzle_char_names:
                                     main_window._set_feedback(f"Input Error (Line {line_num}): Name '{person1}' not recognized in this puzzle.", "orange"); return None
                                 if person2 not in puzzle_char_names:
                                      main_window._set_feedback(f"Input Error (Line {line_num}): Name '{person2}' not recognized in this puzzle.", "orange"); return None
                                 # Validate constraints
                                 if person1 == person2:
                                     main_window._set_feedback(f"Input Error (Line {line_num}): Cannot pair '{person1}' with themselves.", "orange"); return None
                                 if person1 in processed_people or person2 in processed_people:
                                     main_window._set_feedback(f"Input Error (Line {line_num}): Person '{person1 if person1 in processed_people else person2}' mentioned in multiple pairs.", "orange"); return None

                                 user_map_input[person1] = person2
                                 processed_people.add(person1)
                                 processed_people.add(person2)
                            else:
                                main_window._set_feedback(f"Input Error (Line {line_num}): Invalid format - missing name before or after colon.", "orange"); return None
                       else:
                            main_window._set_feedback(f"Input Error (Line {line_num}): Invalid format - expected 'Name : Name'.", "orange"); return None

             # Check completeness only if required
             if check_completeness and len(processed_people) != len(puzzle.characters):
                  main_window._set_feedback(f"Input Incomplete: Expected {expected_pair_count} pairs involving all {len(puzzle.characters)} individuals. Found {len(user_map_input)} pairs.", "orange")
                  return None

             solution_dict = {"map": user_map_input}

        # --- Ordering (Table) ---
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
                            if check_completeness: all_selected = False; break # Stop if checking and found blank
                            else: ordered_items.append(None); continue # Allow blanks if not checking
                       if item in seen_items:
                            main_window._set_feedback(f"Input Error: Item '{item}' appears multiple times in the sequence.", "orange")
                            return None
                       ordered_items.append(item)
                       seen_items.add(item)
                  else:
                       logger.warning("Non-ComboBox found in ordering table UI.")
                       main_window._set_feedback("Internal UI Error: Ordering table setup incorrect.", "red")
                       return None

             if check_completeness and not all_selected:
                  main_window._set_feedback("Input Incomplete: Please select an item for each position in the sequence.", "orange")
                  return None
             # Replace None with empty string or handle as needed if incompleteness allowed
             solution_dict = {"order": [item if item is not None else "" for item in ordered_items]}

        # --- Scheduling (Table) ---
        elif isinstance(widget, QTableWidget) and puzzle.puzzle_type == HumanScenarioType.SCHEDULING:
             rows = widget.rowCount()
             cols = widget.columnCount()
             schedule_map = {}
             try:
                 people = [widget.verticalHeaderItem(r).text() for r in range(rows)]
                 time_slots = [widget.horizontalHeaderItem(c).text() for c in range(cols)]
             except AttributeError:
                  main_window._set_feedback("Internal UI Error: Scheduling grid headers missing.", "red")
                  return None

             for r, person in enumerate(people):
                  schedule_map[person] = {}
                  for c, slot in enumerate(time_slots):
                       cell_widget = widget.cellWidget(r, c)
                       if isinstance(cell_widget, QComboBox):
                            selection = cell_widget.currentText()
                            status = "Booked" if selection == "✔️" else "Available"
                            schedule_map[person][slot] = status
                       else:
                            logger.warning("Non-ComboBox found in scheduling table UI.")
                            main_window._set_feedback("Internal UI Error: Scheduling table setup incorrect.", "red")
                            return None
             solution_dict = {"schedule": schedule_map}

        # --- Dilemma (ButtonGroup) ---
        elif isinstance(widget, QButtonGroup) and puzzle.puzzle_type == HumanScenarioType.DILEMMA:
             checked_button = widget.checkedButton()
             if checked_button:
                 solution_dict = {"choice": checked_button.text()}
             elif check_completeness:
                  main_window._set_feedback("Input Needed: Please select one of the options.", "orange")
                  return None
             else: # Not checking completeness, allow no selection
                  solution_dict = {"choice": None} # Or empty string? None seems better.

        else:
            # Type not handled or widget mismatch
            logger.error(f"Cannot get UI solution for {puzzle.puzzle_type.name}: Widget type mismatch or type not handled. Widget is {type(widget)}.")
            main_window._set_feedback(f"Internal UI Error: Cannot read input for {get_puzzle_type_display_name(puzzle)}.", "red")
            return None

    except Exception as e:
        logger.exception("Error getting solution from UI.")
        main_window._set_feedback(f"Internal Error reading solution: {e}", "red")
        return None

    logger.debug(f"Retrieved scenario solution from UI: {solution_dict}")
    return solution_dict


# --- UI State Update ---

def update_symbol_assignments_display(main_window):
    """Updates symbol combo boxes - disables letters already assigned elsewhere."""
    if not isinstance(main_window.game_state.current_puzzle, Puzzle) or main_window.game_state.current_puzzle.is_scenario:
        return # Only for symbol puzzles

    puzzle = main_window.game_state.current_puzzle
    current_mapping = main_window.game_state.user_mapping
    assigned_letters = set(current_mapping.values()) # Set of letters currently assigned
    symbols_in_ui = list(main_window.assignment_widgets.keys())

    # logger.debug(f"Updating assignments display. Mapping: {current_mapping}, Assigned: {assigned_letters}")

    for symbol in symbols_in_ui:
        widget_dict = main_window.assignment_widgets.get(symbol)
        if not widget_dict or 'combo' not in widget_dict: continue # Skip if widget missing

        combo_box: QComboBox = widget_dict['combo']
        current_assignment_for_this_symbol = current_mapping.get(symbol, "") # Get current assignment for *this* combo

        combo_box.blockSignals(True) # Prevent signals during update

        # --- Rebuild items if necessary (e.g., letters changed - unlikely) ---
        # For now, assume items are fixed ["", "A", "B", ...]

        # --- Enable/Disable items based on assignment ---
        for i in range(combo_box.count()):
            letter = combo_box.itemText(i)
            item = combo_box.model().item(i)
            if item: # Check item exists
                if not letter: # Always enable the blank option
                    item.setEnabled(True)
                else:
                    # Disable if letter is assigned to a *different* symbol
                    is_assigned_elsewhere = (letter in assigned_letters and letter != current_assignment_for_this_symbol)
                    item.setEnabled(not is_assigned_elsewhere)

        # --- Ensure current selection is correct ---
        # (This should ideally be handled by _assign_letter, but double-check here)
        current_text_in_combo = combo_box.currentText()
        if current_text_in_combo != current_assignment_for_this_symbol:
             index = combo_box.findText(current_assignment_for_this_symbol)
             if index >= 0:
                  combo_box.setCurrentIndex(index)
             else: # Fallback to blank if assigned letter somehow invalid
                  combo_box.setCurrentIndex(0)

        combo_box.blockSignals(False) # Re-enable signals

# --- Clue Display ---

def display_symbol_clues(puzzle: Puzzle, text_widget: QTextEdit):
    """Displays formatted clues for a symbol puzzle in the QTextEdit."""
    if not text_widget: return
    clue_html = "<style> li { margin-bottom: 6px; } </style><ul>" # Add some spacing
    if puzzle.clues:
        for clue_text, clue_type in puzzle.clues:
            prefix = get_clue_prefix(clue_type)
            # Escape potential HTML in clue_text? Or assume it's safe plain text.
            # import html
            # escaped_text = html.escape(clue_text)
            escaped_text = clue_text # Assume safe for now
            clue_html += f"<li>{prefix}{escaped_text}</li>"
    else:
        clue_html += "<li>No specific clues provided for this puzzle.</li>"
    clue_html += "</ul>"
    text_widget.setHtml(clue_html)


def display_scenario_information(puzzle: ScenarioPuzzle, text_widget: QTextEdit):
    """Displays formatted information/clues for a scenario puzzle."""
    if not text_widget: return
    html_content = ""

    # --- Description ---
    if puzzle.description:
         html_content += f"<h3>Description:</h3><p>{puzzle.description}</p>"
    # --- Goal ---
    if puzzle.goal:
         html_content += f"<h3>Goal:</h3><p>{puzzle.goal}</p><hr>"
    # --- Characters/Entities ---
    if puzzle.characters:
        html_content += "<h3>Characters/Entities Involved:</h3><ul>"
        for char in puzzle.characters:
            name = char.get('name', 'Unknown')
            details_list = []
            # Add known attributes like trait, occupation
            if 'trait' in char: details_list.append(f"trait: {char['trait']}")
            if 'occupation' in char: details_list.append(f"occupation: {char['occupation']}")
            # Add other simple key-value pairs excluding complex ones
            for k, v in char.items():
                if k not in ['name', 'trait', 'occupation', 'state_history', 'details'] and isinstance(v, (str, int, float, bool)):
                    details_list.append(f"{k}: {v}")
            # Handle 'details' field specially
            extra_details = char.get('details')
            if isinstance(extra_details, str) and extra_details != "N/A": details_list.append(f"info: {extra_details}")
            elif isinstance(extra_details, list) and extra_details: details_list.append(f"info: {', '.join(map(str,extra_details))}")

            details_str = "; ".join(details_list)
            html_content += f"<li><b>{name}</b>{f' ({details_str})' if details_str else ''}</li>"
        html_content += "</ul>"
    # --- Setting ---
    if puzzle.setting and puzzle.setting.get('name') != "N/A":
         setting_name = puzzle.setting.get('name', 'Unknown Setting')
         setting_details_list = puzzle.setting.get('details', [])
         details_str = ""
         if isinstance(setting_details_list, list) and setting_details_list: details_str = f" ({', '.join(map(str, setting_details_list))})"
         elif isinstance(setting_details_list, str) and setting_details_list: details_str = f" ({setting_details_list})"
         html_content += f"<h3>Setting:</h3><p>{setting_name}{details_str}</p>"
    # --- Rules (if applicable) ---
    if puzzle.rules:
        html_content += "<h3>Rules:</h3><ul>"
        for rule in puzzle.rules: html_content += f"<li>{rule}</li>"
        html_content += "</ul>"
     # --- Options (for Dilemma) ---
    if puzzle.options and puzzle.puzzle_type == HumanScenarioType.DILEMMA:
        html_content += "<h3>Options to Consider:</h3><ul>"
        for option in puzzle.options: html_content += f"<li>{option}</li>"
        html_content += "</ul>"
    # --- Information/Clues ---
    html_content += "<h3>Information & Clues:</h3>"
    if puzzle.information:
        html_content += "<style> li { margin-bottom: 5px; } </style><ul>" # Add spacing
        for info in puzzle.information:
            if not isinstance(info, str): info = str(info) # Ensure string
            # Add specific styling for hints or rules if they appear here
            if info.lower().startswith("hint:"):
                html_content += f"<li style='font-style: italic; color: #555;'>{info}</li>"
            elif info.lower().startswith("rule observed:"):
                 html_content += f"<li style='color: #007bff;'><i>{info}</i></li>" # Blue italic
            else:
                html_content += f"<li>{info}</li>"
        html_content += "</ul>"
    else:
        html_content += "<p>No specific information provided beyond the description.</p>"

    text_widget.setHtml(html_content)