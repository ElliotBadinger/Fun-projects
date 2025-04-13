from PyQt6.QtGui import QColor

class Theme:
    def __init__(self, name, colors):
        self.name = name
        self.colors = colors

    @property
    def stylesheet(self):
        """Generate Qt stylesheet for the theme."""
        return f"""
            QMainWindow, QDialog {{
                background-color: {self.colors['bg']};
                color: {self.colors['fg']};
            }}
            
            QPushButton {{
                background-color: {self.colors['accent']};
                color: {self.colors['fg']};
                border: none;
                padding: 8px;
                border-radius: 4px;
            }}
            
            QPushButton:hover {{
                background-color: {self.colors['accent_hover']};
            }}
            
            QPushButton:disabled {{
                background-color: {self.colors['accent_disabled']};
            }}
            
            QComboBox {{
                background-color: {self.colors['symbol_bg']};
                color: {self.colors['fg']};
                border: 1px solid {self.colors['accent']};
                border-radius: 4px;
                padding: 4px;
            }}
            
            QComboBox:disabled {{
                background-color: {self.colors['symbol_bg_disabled']};
            }}
            
            QTextEdit {{
                background-color: {self.colors['symbol_bg']};
                color: {self.colors['fg']};
                border: 1px solid {self.colors['accent']};
                border-radius: 4px;
            }}
            
            QLabel {{
                color: {self.colors['fg']};
            }}
            
            QMenuBar {{
                background-color: {self.colors['bg']};
                color: {self.colors['fg']};
            }}
            
            QMenuBar::item:selected {{
                background-color: {self.colors['accent']};
            }}
            
            QMenu {{
                background-color: {self.colors['bg']};
                color: {self.colors['fg']};
            }}
            
            QMenu::item:selected {{
                background-color: {self.colors['accent']};
            }}
        """

# Define available themes
THEMES = {
    "Default": Theme("Default", {
        'bg': '#ECECEC',
        'fg': '#333333',
        'accent': '#4CAF50',
        'accent_hover': '#45a049',
        'accent_disabled': '#a5d6a7',
        'symbol_bg': '#FFFFFF',
        'symbol_bg_disabled': '#F5F5F5',
        'correct': '#DFF0D8',
        'incorrect': '#F2DEDE',
    }),
    
    "Arcane Library": Theme("Arcane Library", {
        'bg': '#F5F5DC',
        'fg': '#5D4037',
        'accent': '#8D6E63',
        'accent_hover': '#795548',
        'accent_disabled': '#BCAAA4',
        'symbol_bg': '#FFF8DC',
        'symbol_bg_disabled': '#F5F5DC',
        'correct': '#A5D6A7',
        'incorrect': '#EF9A9A',
    }),
    
    "Midnight Lab": Theme("Midnight Lab", {
        'bg': '#263238',
        'fg': '#ECEFF1',
        'accent': '#00ACC1',
        'accent_hover': '#0097A7',
        'accent_disabled': '#4DD0E1',
        'symbol_bg': '#37474F',
        'symbol_bg_disabled': '#455A64',
        'correct': '#1B5E20',
        'incorrect': '#B71C1C',
    })
} 