from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, 
                           QHBoxLayout, QTextEdit, QFrame,
                           QGridLayout, QComboBox, QSizePolicy)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from .puzzle import PuzzleGenerator, Puzzle, ClueType
from typing import Optional
import os

class TutorialDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Logic Tutorial")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Logic Puzzle Tutorial")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Content - Load from external file
        content = QTextEdit()
        content.setReadOnly(True)
        content.setFont(QFont("Arial", 12))

        try:
            base_path = os.path.dirname(__file__)
            content_path = os.path.join(base_path, "tutorial_content.html")
            with open(content_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            content.setHtml(html_content)
        except FileNotFoundError:
            content.setHtml("<h2>Error</h2><p>Could not load tutorial content from tutorial_content.html.</p>")
        except Exception as e:
            content.setHtml(f"<h2>Error</h2><p>An error occurred loading tutorial content: {e}</p>")
            
        layout.addWidget(content)
        
        # Navigation buttons
        button_layout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

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