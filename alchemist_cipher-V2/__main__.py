# Allows running with `python -m alchemist_cipher`
import sys
from .ui.main_window import main

if __name__ == "__main__":
    # It's good practice to handle potential exceptions here
    try:
        main()
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        # Potentially log the exception traceback here
        sys.exit(1)