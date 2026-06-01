"""Entry point for the PyInstaller-bundled TalkTrace AI base application."""
import multiprocessing

# Required on Windows so that child processes spawned by uvicorn/shiny
# do not re-execute the frozen entry point (which would loop).
multiprocessing.freeze_support()

from talktrace_ai.app import main

if __name__ == "__main__":
    main()
