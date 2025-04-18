from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, 
                           QHBoxLayout, QTextEdit, QFrame,
                           QGridLayout, QComboBox, QSizePolicy, QTextBrowser)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from ..puzzle import PuzzleGenerator, Puzzle, ClueType
from typing import Optional
import os
import sys # Import sys
import logging

# from utils import resource_path # Removed import
from ..ui.puzzle_display import (create_symbol_puzzle_ui, display_symbol_clues,
                             update_symbol_assignments_display, clear_layout)

logger = logging.getLogger(__name__)

class TutorialDialog(QDialog):
    """Shows the tutorial content from an HTML file."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Logic Puzzle Tutorial")
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout(self)

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True) # Allow opening links
        layout.addWidget(self.browser)

        # Load HTML content using inline path logic
        try:
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath(".")
        html_path = os.path.join(base_path, "tutorial_content.html")
        check_icon_path = os.path.join(base_path, "icons/check.png")

        logger.info(f"Attempting to load tutorial HTML from: {html_path}")
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            # Replace placeholder for icon path
            icon_path_placeholder = "{{CHECK_ICON_PATH}}"
            # Ensure forward slashes for HTML/CSS compatibility
            check_icon_html_path = check_icon_path.replace("\\", "/")
            html_content = html_content.replace(icon_path_placeholder, check_icon_html_path)

            self.browser.setHtml(html_content)
            logger.info("Successfully loaded and set tutorial HTML content.")
        except FileNotFoundError:
            logger.error(f"Tutorial HTML file not found at: {html_path}")
            self.browser.setPlainText("Error: Tutorial content not found. Please ensure 'tutorial_content.html' exists.")
        except Exception as e:
            logger.exception(f"An error occurred loading or processing tutorial HTML: {e}")
            self.browser.setPlainText(f"An unexpected error occurred loading tutorial content: {e}")

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignCenter)

class PracticePuzzleDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Practice Puzzle")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Practice Your Logic Skills")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel("""
        Try solving this practice puzzle. Each step will teach you a different logical reasoning technique.
        Take your time to understand each clue and how it helps you solve the puzzle.
        """)
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Practice puzzle area
        self.puzzle_frame = QFrame()
        self.puzzle_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Plain)
        puzzle_layout = QHBoxLayout(self.puzzle_frame)
        
        # --- Left Side: Puzzle Input --- 
        input_area = QVBoxLayout()
        self.assignment_widgets = {}
        self.practice_puzzle = self._generate_practice_puzzle()

        if self.practice_puzzle:
            puzzle_title = QLabel("Symbols & Assignments")
            puzzle_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            input_area.addWidget(puzzle_title)

            assignments_grid = QGridLayout()
            symbols = self.practice_puzzle.symbols
            letters = [""] + sorted(self.practice_puzzle.letters) 
            num_cols = 2 

            for i, symbol in enumerate(symbols):
                row, col = divmod(i, num_cols)
                symbol_label = QLabel(symbol)
                symbol_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
                symbol_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                assignments_grid.addWidget(symbol_label, row, col * 2)

                letter_combo = QComboBox()
                letter_combo.addItems(letters)
                letter_combo.setFont(QFont("Arial", 12))
                letter_combo.setMinimumWidth(60) 
                letter_combo.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                assignments_grid.addWidget(letter_combo, row, col * 2 + 1)
                self.assignment_widgets[symbol] = letter_combo

            input_area.addLayout(assignments_grid)
            input_area.addStretch()
        else:
            input_area.addWidget(QLabel("Could not generate practice puzzle."))

        puzzle_layout.addLayout(input_area, stretch=1)

        # --- Right Side: Clues --- 
        clue_area = QVBoxLayout()
        clues_title = QLabel("Clues")
        clues_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        clue_area.addWidget(clues_title)

        clues_text = QTextEdit()
        clues_text.setReadOnly(True)
        if self.practice_puzzle:
             for clue_text, clue_type in self.practice_puzzle.clues:
                 clues_text.append(f"• {clue_text}\n")
        clues_text.setFont(QFont("Arial", 11))
        clue_area.addWidget(clues_text)

        puzzle_layout.addLayout(clue_area, stretch=1)

        layout.addWidget(self.puzzle_frame)
        
        # Navigation buttons
        button_layout = QHBoxLayout()

        self.feedback_label = QLabel("") 
        layout.addWidget(self.feedback_label)
        check_button = QPushButton("Check Solution")
        check_button.clicked.connect(self._check_practice_solution)
        button_layout.addWidget(check_button)

        button_layout.addStretch()

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

    def _generate_practice_puzzle(self) -> Optional[Puzzle]:
        try:
            generator = PuzzleGenerator(min_elements=3, max_elements=4, max_tries=500)
            puzzle: Optional[Puzzle] = None
            attempts = 0
            max_attempts = 10 

            while attempts < max_attempts:
                puzzle = generator.generate_puzzle(level=0) 
                if isinstance(puzzle, Puzzle) and puzzle.is_verified:
                    break 
                attempts += 1

            if isinstance(puzzle, Puzzle) and puzzle.is_verified:
                 print("Generated practice puzzle:", puzzle.symbols, puzzle.letters, puzzle.solution_mapping)
                 return puzzle
            else:
                 print(f"Failed to generate a verifiable practice symbol puzzle after {max_attempts} attempts.")
                 print("Falling back to hardcoded practice puzzle.")
                 symbols = ["α", "β", "γ", "δ"]
                 letters = ["A", "B", "C", "D"]
                 solution = {"α": "A", "β": "B", "γ": "C", "δ": "D"}
                 clues = [
                     ("'α' directly represents the letter 'A'.", ClueType.DIRECT),
                     ("The symbol 'β' does not represent the letter 'C'.", ClueType.EXCLUSION),
                     ("The symbol 'γ' represents a consonant.", ClueType.CATEGORY),
                     ("The letter for 'δ' comes later in the alphabet than the letter for 'γ'.", ClueType.RELATIONAL)
                 ]
                 return Puzzle(level=0, symbols=symbols, letters=letters, solution_mapping=solution, clues=clues, is_verified=True) 

        except Exception as e:
            print(f"Error generating practice puzzle: {e}")
            return None 

    def _check_practice_solution(self):
        if not self.practice_puzzle:
            self.feedback_label.setText("Error: No practice puzzle loaded.")
            return

        user_mapping = {}
        complete = True
        for symbol, combo in self.assignment_widgets.items():
            letter = combo.currentText()
            if letter:
                user_mapping[symbol] = letter
            else:
                complete = False

        if not complete:
            self.feedback_label.setText("Please assign a letter to all symbols.")
            return

        is_correct = self.practice_puzzle.check_solution(user_mapping)
        if is_correct:
            self.feedback_label.setText("Correct! Well done.")
            self.feedback_label.setStyleSheet("color: green")
        else:
            self.feedback_label.setText("Not quite right. Check the clues again.")
            self.feedback_label.setStyleSheet("color: red")

# Example usage (if running tutorial.py directly)
if __name__ == '__main__':
    pass 
    # Example: You could instantiate and show the dialog here for testing
    # import sys
    # from PyQt6.QtWidgets import QApplication
    # app = QApplication(sys.argv)
    # dialog = PracticePuzzleDialog()
    # dialog.show()
    # sys.exit(app.exec()) 