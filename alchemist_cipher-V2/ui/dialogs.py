from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QRadioButton, QButtonGroup, QFrame, QComboBox)
from typing import Optional, Union

# Import puzzle enums if needed for type hints or data
from puzzle.common import HumanScenarioType

class PuzzleTypeDialog(QDialog):
    """Dialog for selecting the type of puzzle to generate."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Puzzle Type")
        self.setMinimumWidth(450)
        self.selected_type: Optional[Union[str, HumanScenarioType]] = None # Stores the result

        layout = QVBoxLayout(self)
        layout.setSpacing(15) # Add more spacing

        desc_label = QLabel("Choose the type of puzzle you want to generate:")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # --- Main Type Selection (Radio Buttons) ---
        main_type_box = QFrame()
        main_type_box.setFrameShape(QFrame.Shape.StyledPanel)
        main_type_layout = QVBoxLayout(main_type_box)
        self.type_group = QButtonGroup(self) # Group for mutual exclusion

        # Symbol Cipher Option
        self.symbol_radio = QRadioButton("&Symbol Cipher")
        self.symbol_radio.setChecked(True) # Default selection
        self.type_group.addButton(self.symbol_radio)
        main_type_layout.addWidget(self.symbol_radio)
        symbol_desc = QLabel("    Decode symbols into letters using logical clues.")
        symbol_desc.setStyleSheet("padding-left: 15px; color: #555;") # Indent and style desc
        symbol_desc.setWordWrap(True)
        main_type_layout.addWidget(symbol_desc)

        # Scenario Puzzle Option
        self.scenario_radio = QRadioButton("S&cenario Puzzle")
        self.type_group.addButton(self.scenario_radio)
        main_type_layout.addWidget(self.scenario_radio)
        scenario_desc = QLabel("    Solve a logic puzzle based on a descriptive scenario.")
        scenario_desc.setStyleSheet("padding-left: 15px; color: #555;")
        scenario_desc.setWordWrap(True)
        main_type_layout.addWidget(scenario_desc)

        layout.addWidget(main_type_box)

        # --- Scenario Details (ComboBox, enabled only if Scenario selected) ---
        self.scenario_details_box = QFrame()
        self.scenario_details_box.setFrameShape(QFrame.Shape.StyledPanel)
        scenario_details_layout = QHBoxLayout(self.scenario_details_box)
        scenario_type_label = QLabel("Specific Scenario Type:")
        scenario_details_layout.addWidget(scenario_type_label)

        self.scenario_type_combo = QComboBox()
        self.scenario_type_combo.addItem("Random Scenario", "Scenario") # Special value for random
        # Populate with actual HumanScenarioType enum values
        for scenario_type in HumanScenarioType:
            display_name = scenario_type.name.replace('_', ' ').title()
            self.scenario_type_combo.addItem(display_name, scenario_type) # Store Enum member as data
        scenario_details_layout.addWidget(self.scenario_type_combo, stretch=1)
        layout.addWidget(self.scenario_details_box)

        # Connect toggle signal to enable/disable the combo box
        self.scenario_radio.toggled.connect(self.scenario_details_box.setEnabled)
        self.scenario_details_box.setEnabled(self.scenario_radio.isChecked()) # Initial state


        # --- Dialog Buttons ---
        layout.addStretch() # Push buttons to bottom
        button_layout = QHBoxLayout()
        button_layout.addStretch() # Push buttons right

        self.ok_button = QPushButton("&Create Selected")
        self.ok_button.setDefault(True)
        self.ok_button.clicked.connect(self.accept) # Use built-in accept
        button_layout.addWidget(self.ok_button)

        self.cancel_button = QPushButton("&Cancel")
        self.cancel_button.clicked.connect(self.reject) # Use built-in reject
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)


    def accept(self):
        """Overrides accept to store the selected type before closing."""
        if self.symbol_radio.isChecked():
            self.selected_type = "Symbol"
        elif self.scenario_radio.isChecked():
            # Get the data associated with the selected item (Enum member or "Scenario" string)
            self.selected_type = self.scenario_type_combo.currentData()
        # logger.debug(f"PuzzleTypeDialog accepted. Selected type: {self.selected_type}")
        super().accept() # Call the default accept method


# --- Placeholder for AiSolverDialog ---
# class AiSolverDialog(QDialog):
#     def __init__(self, game_state, parent=None):
#         super().__init__(parent)
#         self.game_state = game_state
#         # ... Setup UI for selecting AI, entering API keys etc. ...
#         self.setWindowTitle("AI Solver Configuration")
#         # ...