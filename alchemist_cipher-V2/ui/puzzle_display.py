from PyQt6.QtWidgets import (QLabel, QComboBox, QGridLayout, QWidget, QVBoxLayout,
                             QHBoxLayout, QTableWidget, QLineEdit, QRadioButton,
                             QButtonGroup, QTableWidgetItem, QHeaderView, QTextEdit,
                             QSizePolicy)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
import logging
from typing import Optional, Dict, Any, Union

# Import puzzle types and enums
from puzzle.puzzle_types import Puzzle, ScenarioPuzzle
from puzzle.common import HumanScenarioType, ClueType

logger = logging.getLogger(__name__)

# --- Visual Feedback Styles ---
ERROR_STYLE = "border: 2px solid red; background-color: #FFDDDD;" # Example: Red border, light red background
WARNING_STYLE = "border: 2px solid orange; background-color: #FFFFAA;" # Example: Orange border, light yellow background
# CORRECT_STYLE = "border: 2px solid green; background-color: #DDFFDD;" # Optional: Green for correct
DEFAULT_STYLE = "" # Default empty style sheet

# --- Visual Feedback Helper Functions ---

def apply_visual_feedback(widget: QWidget, feedback_type: str):
    """Applies a visual style to a widget based on feedback type."""
    if not widget: return # Safety check
    style = DEFAULT_STYLE
    tooltip = ""
    if feedback_type == 'error':
        style = ERROR_STYLE
        tooltip = "Incorrect or conflicting input." 
    elif feedback_type == 'warning':
        style = WARNING_STYLE
        tooltip = "Potential issue or contradiction."
    # Add more types like 'correct' if desired
        
    # Store original style might be complex if widgets already have styles. Clearing is safer.
    widget.setStyleSheet(style)
    widget.setToolTip(tooltip) # Set tooltip for explanation
    # logger.debug(f"Applied {feedback_type} style to {widget}")

def clear_visual_feedback(widget: QWidget):
    """Clears any custom visual feedback style from a widget."""
    if not widget: return # Safety check
    widget.setStyleSheet(DEFAULT_STYLE) 
    widget.setToolTip("") # Clear tooltip
    # logger.debug(f"Cleared style from {widget}")


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
             # Limit element name length in header
             element_name_short = (element_name[:8] + '...') if len(element_name) > 11 else element_name 
             col_headers.append(f"{short_cat}:{element_name_short}")
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
    table.setFont(QFont("Arial", 10)) # Adjust font if needed
    table.setEnabled(is_interactive)

    # --- Styling and Item Creation ---
    option_items = ["", "✓", "X"] # Blank, True, False representation

    for r in range(num_rows):
        for c in range(num_cols):
            # Use QComboBox in each cell for consistent input
            cell_widget = QComboBox() 
            cell_widget.addItems(option_items)
            cell_widget.setFont(QFont("Arial", 11))
            cell_widget.setEnabled(is_interactive)
            
            # Apply fixed size policy to prevent excessive stretching
            cell_widget.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
            cell_widget.setMinimumWidth(40) # Ensure minimum clickable width
            
            # Center the combobox within the cell using a container widget
            cell_container = QWidget() 
            cell_layout = QHBoxLayout(cell_container)
            cell_layout.addWidget(cell_widget)
            cell_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell_layout.setContentsMargins(1, 1, 1, 1) # Minimal margins
            cell_container.setLayout(cell_layout) # Explicitly set layout
            
            table.setCellWidget(r, c, cell_container) # Add container with combobox

            # Optional: Connect signal here if immediate feedback per cell change is needed
            # cell_widget.currentTextChanged.connect(lambda text, r=r, c=c: main_window._logic_grid_cell_changed(r, c, text))


    # Adjust header resize modes AFTER setting cell widgets maybe?
    table.resizeColumnsToContents()
    table.resizeRowsToContents()
    # Use Interactive resize mode or Stretch based on preference/column count
    # table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive) 
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    # table.horizontalHeader().setStretchLastSection(True) # Optional: stretch last column
    table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    # table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    
    # --- Important: Store the table and the column map ---
    main_window.scenario_input_widget = table # Store the table itself as the main input
    main_window.scenario_input_widgets['column_map'] = col_category_map # Store the helper map

    parent_layout.addWidget(table)
    logger.debug("Logic Grid UI created with QComboBox cells.")


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
    """Extracts the current solution attempt from the UI widgets."""
    puzzle = main_window.game_state.current_puzzle
    if not puzzle or not puzzle.is_scenario:
        logger.error("Attempted to get scenario solution with no active scenario puzzle.")
        return None

    solution_data: Dict[str, Any] = {"type": puzzle.puzzle_type}
    widget = main_window.scenario_input_widget
    puzzle_type = puzzle.puzzle_type
    is_complete = True # Assume complete initially

    try:
        if puzzle_type == HumanScenarioType.LOGIC_GRID:
            if not isinstance(widget, QTableWidget):
                logger.error(f"Expected QTableWidget for Logic Grid, found {type(widget)}")
                main_window._set_feedback("Internal Error: UI component mismatch for Logic Grid.", "red")
                return None

            grid_solution: Dict[str, Dict[str, Optional[bool]]] = {}
            table: QTableWidget = widget
            row_labels = [table.verticalHeaderItem(r).text() for r in range(table.rowCount())]
            col_map = main_window.scenario_input_widgets.get('column_map', {}) # {flat_idx: (cat, item)}
            
            if not col_map:
                 logger.error("Logic Grid column map is missing from scenario_input_widgets.")
                 main_window._set_feedback("Internal Error: Logic Grid configuration missing.", "red")
                 return None

            # --- Basic UI Validation (Example: Check for uniqueness within categories if applicable) ---
            # This depends heavily on the specific logic grid rules (e.g., match Person to Job)
            # We could add checks here to ensure only one '✓' per row/column *within a related group*.
            # For a generic grid, the core verifier handles logical contradictions.
            # We can check for completeness here.

            for r, row_item in enumerate(row_labels):
                grid_solution[row_item] = {}
                row_has_positive = False # Example check: Ensure each row has at least one '✓'? (Depends on puzzle)
                
                for c in range(table.columnCount()):
                    col_info = col_map.get(c)
                    if not col_info:
                         logger.warning(f"Missing column info for column index {c}")
                         continue # Skip column if map is broken
                    col_cat, col_item = col_info

                    cell_container = table.cellWidget(r, c)
                    combo_box = cell_container.findChild(QComboBox) if cell_container else None

                    if not combo_box:
                        logger.error(f"Could not find QComboBox in cell ({r}, {c})")
                        main_window._set_feedback(f"Internal Error: UI element missing at {row_item}, Col {c}.", "red")
                        return None # Critical UI error

                    value_str = combo_box.currentText()
                    cell_value: Optional[bool] = None
                    if value_str == "✓":
                        cell_value = True
                        row_has_positive = True
                    elif value_str == "X":
                        cell_value = False
                    else: # Blank
                        if check_completeness:
                            is_complete = False
                            # Optional: Apply visual feedback directly? Needs care.
                            # apply_visual_feedback(combo_box, 'warning') # Indicate incompleteness

                    grid_solution[row_item][col_item] = cell_value
            
            solution_data['grid'] = grid_solution
            
            # --- Completeness Check ---
            if check_completeness and not is_complete:
                 main_window._set_feedback("Please fill in all cells in the logic grid ('✓' or 'X').", "orange")
                 logger.warning("Logic grid check failed: Incomplete.")
                 # Optional: Add visual cues to empty cells here if desired.
                 return None # Don't proceed with check if incomplete

            # --- Add more UI-level validation if needed (e.g., duplicate '✓' in unique groups) ---
            # Example: If categories[1] and categories[2] must have a unique pairing for each row_item
            # validation_passed, error_cells = _validate_logic_grid_ui_constraints(table, col_map)
            # if not validation_passed:
            #    main_window._set_feedback("Invalid input: Check highlighted cells for conflicts.", "orange")
            #    for r_err, c_err in error_cells: # Apply visual feedback to error cells
            #        cell_container = table.cellWidget(r_err, c_err)
            #        combo = cell_container.findChild(QComboBox) if cell_container else None
            #        if combo: apply_visual_feedback(combo, 'warning')
            #    return None


        elif puzzle_type == HumanScenarioType.RELATIONSHIP_MAP:
            # ... (logic for Relationship Map - potentially complex grid/combos) ...
             # Ensure completeness check if needed
            pass # Placeholder

        elif puzzle_type == HumanScenarioType.ORDERING:
            if not isinstance(widget, QTableWidget):
                 logger.error(f"Expected QTableWidget for Ordering, found {type(widget)}")
                 return None
            table: QTableWidget = widget
            ordered_items = []
            positions = []
            for r in range(table.rowCount()):
                item_widget = table.item(r, 0) # Item name is in non-editable column 0
                combo_box_container = table.cellWidget(r, 1) # Combo box is in column 1
                combo_box = combo_box_container.findChild(QComboBox) if combo_box_container else None
                
                if not item_widget or not combo_box:
                     logger.error(f"Missing item or combobox in ordering table row {r}")
                     return None
                     
                item_name = item_widget.text()
                position_str = combo_box.currentText()
                
                if not position_str: # Blank selection
                     if check_completeness:
                         is_complete = False
                         # apply_visual_feedback(combo_box, 'warning')
                else:
                     position = int(position_str)
                     if position in positions: # Check for duplicate positions selected
                          if check_completeness: # Only fail completeness check if duplicates found
                             main_window._set_feedback(f"Invalid input: Position '{position}' assigned multiple times.", "orange")
                             # Apply visual feedback to conflicting comboboxes? Harder to track pairs.
                             # apply_visual_feedback(combo_box, 'warning')
                             return None # Treat as incomplete/invalid for check
                     positions.append(position)
                     ordered_items.append((position, item_name)) # Store as (pos, item)

            if check_completeness and not is_complete:
                 main_window._set_feedback("Please assign a unique position to all items.", "orange")
                 return None
            
            # Sort by position and extract item names
            ordered_items.sort()
            solution_data['ordered_items'] = [item for pos, item in ordered_items]


        elif puzzle_type == HumanScenarioType.SCHEDULING:
            if not isinstance(widget, QTableWidget):
                 logger.error(f"Expected QTableWidget for Scheduling, found {type(widget)}")
                 return None
            table: QTableWidget = widget
            schedule: Dict[str, Dict[str, Optional[str]]] = {} # {time_slot: {category: item}}
            time_slots = [table.verticalHeaderItem(r).text() for r in range(table.rowCount())]
            categories = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
            
            selected_items = set() # For checking duplicates if needed

            for r, time_slot in enumerate(time_slots):
                 schedule[time_slot] = {}
                 for c, category in enumerate(categories):
                     cell_container = table.cellWidget(r, c)
                     combo_box = cell_container.findChild(QComboBox) if cell_container else None
                     if not combo_box:
                         logger.error(f"Could not find QComboBox in scheduling cell ({r}, {c})")
                         return None
                         
                     item_name = combo_box.currentText()
                     if not item_name: # Blank selection
                         if check_completeness:
                             is_complete = False
                             # apply_visual_feedback(combo_box, 'warning')
                         schedule[time_slot][category] = None
                     else:
                         schedule[time_slot][category] = item_name
                         # Check for duplicates across the whole schedule if that's a rule
                         # if item_name in selected_items:
                         #     is_valid = False # Or handle based on specific puzzle rules
                         # selected_items.add(item_name)

            if check_completeness and not is_complete:
                 main_window._set_feedback("Please make a selection for all time slots and categories.", "orange")
                 return None
                 
            # Add validation for schedule rules if needed (e.g., item used only once)
                 
            solution_data['schedule'] = schedule


        elif puzzle_type == HumanScenarioType.DILEMMA:
            if not isinstance(widget, QButtonGroup):
                 logger.error(f"Expected QButtonGroup for Dilemma, found {type(widget)}")
                 return None
            button_group: QButtonGroup = widget
            checked_button = button_group.checkedButton()
            if not checked_button:
                 if check_completeness:
                     main_window._set_feedback("Please choose one option for the dilemma.", "orange")
                     # Apply visual feedback to the groupbox?
                     return None
                 solution_data['choice'] = None
            else:
                 solution_data['choice'] = checked_button.text()


        elif puzzle_type in [HumanScenarioType.SOCIAL_DEDUCTION,
                             HumanScenarioType.COMMON_SENSE_GAP,
                             HumanScenarioType.AGENT_SIMULATION]:
            if not isinstance(widget, QLineEdit):
                 logger.error(f"Expected QLineEdit for {puzzle_type.name}, found {type(widget)}")
                 return None
            line_edit: QLineEdit = widget
            answer = line_edit.text().strip()
            if not answer:
                 if check_completeness:
                     main_window._set_feedback("Please enter your answer.", "orange")
                     # apply_visual_feedback(line_edit, 'warning')
                     return None
                 solution_data['answer'] = None
            else:
                 solution_data['answer'] = answer

        else:
             logger.warning(f"Solution extraction not implemented for scenario type: {puzzle_type.name}")
             main_window._set_feedback(f"Cannot check solution for type: {puzzle_type.name}", "orange")
             return None

    except Exception as e:
        logger.exception(f"Error getting solution from UI for puzzle type {puzzle_type.name}")
        main_window._set_feedback(f"Error reading UI state: {e}", "red")
        return None

    logger.debug(f"Extracted solution data from UI: {solution_data}")
    return solution_data


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