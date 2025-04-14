from PyQt6.QtWidgets import QMenuBar, QMessageBox
from PyQt6.QtGui import QAction, QIcon
import logging

# Import necessary components from sibling modules or parent packages
# from .dialogs import AiSolverDialog # Example if you create this dialog
from themes import THEMES # Need access to themes for the menu

logger = logging.getLogger(__name__)

def create_menu_bar(main_window):
    """Creates the main menu bar and connects actions to main_window methods."""
    logger.debug("Creating menu bar...")
    menubar = main_window.menuBar() # Get the menu bar from the main window

    # --- Game Menu ---
    game_menu = menubar.addMenu("&Game")

    new_action = QAction(QIcon.fromTheme("document-new"), "&New Random Puzzle", main_window)
    new_action.setShortcut("Ctrl+N")
    # Connect to the main window's method using lambda to pass None for type
    new_action.triggered.connect(lambda: main_window._confirm_and_start_new_puzzle(None))
    game_menu.addAction(new_action)

    select_type_action = QAction(QIcon.fromTheme("preferences-system"), "Select Puzzle &Type...", main_window)
    select_type_action.setShortcut("Ctrl+T")
    select_type_action.triggered.connect(main_window._select_puzzle_type) # Connect to main window method
    game_menu.addAction(select_type_action)

    save_action = QAction(QIcon.fromTheme("document-save"), "&Save Game", main_window)
    save_action.setShortcut("Ctrl+S")
    save_action.triggered.connect(main_window._save_game) # Connect to main window method
    game_menu.addAction(save_action)

    game_menu.addSeparator()

    # AI Solver Actions (store references on main_window)
    main_window.run_ai_action = QAction(QIcon.fromTheme("system-run"), "Run AI Solver (Step-by-Step)", main_window)
    main_window.run_ai_action.triggered.connect(main_window._start_ai_solver)
    main_window.run_ai_action.setToolTip("Let the AI solve the current puzzle step-by-step")
    game_menu.addAction(main_window.run_ai_action)

    main_window.stop_ai_action = QAction(QIcon.fromTheme("process-stop"), "Stop AI Solver", main_window)
    main_window.stop_ai_action.triggered.connect(main_window._stop_ai_solver)
    main_window.stop_ai_action.setEnabled(False) # Initially disabled
    main_window.stop_ai_action.setToolTip("Stop the currently running AI solver")
    game_menu.addAction(main_window.stop_ai_action)

    game_menu.addSeparator()

    exit_action = QAction(QIcon.fromTheme("application-exit"), "E&xit", main_window)
    exit_action.setShortcut("Ctrl+Q")
    exit_action.triggered.connect(main_window.close) # Connect to main window's close method
    game_menu.addAction(exit_action)


    # --- Options Menu ---
    options_menu = menubar.addMenu("&Options")

    # Theme Submenu (store reference on main_window)
    main_window.theme_menu = options_menu.addMenu(QIcon.fromTheme("preferences-desktop-theme"), "&Themes")
    main_window._update_theme_menu() # Call main window's method to populate it initially


    # Placeholder for AI Solver Selection/Configuration Dialog
    # select_ai_action = QAction("Select AI Solver...", main_window)
    # select_ai_action.triggered.connect(lambda: _open_ai_solver_dialog(main_window)) # Example call
    # options_menu.addAction(select_ai_action)


    # --- Help Menu ---
    help_menu = menubar.addMenu("&Help")

    tutorial_action = QAction(QIcon.fromTheme("help-contents"), "Logic &Tutorial", main_window)
    tutorial_action.triggered.connect(main_window._show_tutorial)
    help_menu.addAction(tutorial_action)

    practice_action = QAction(QIcon.fromTheme("games-config-board"), "&Practice Puzzle", main_window)
    practice_action.triggered.connect(main_window._show_practice_puzzle)
    help_menu.addAction(practice_action)

    how_to_play = QAction(QIcon.fromTheme("help-faq"), "&How to Play", main_window)
    how_to_play.triggered.connect(main_window._show_how_to_play)
    help_menu.addAction(how_to_play)

    help_menu.addSeparator()

    about_action = QAction(QIcon.fromTheme("help-about"), "&About", main_window)
    about_action.triggered.connect(main_window._show_about)
    help_menu.addAction(about_action)

    logger.debug("Menu bar created.")
    # No need to return menubar, as it's attached to main_window


# Placeholder function for AI Dialog (if you implement it)
# def _open_ai_solver_dialog(parent_window):
#     logger.debug("Opening AI Solver Dialog...")
#     dialog = AiSolverDialog(parent_window.game_state, parent=parent_window) # Pass game state
#     dialog.exec()