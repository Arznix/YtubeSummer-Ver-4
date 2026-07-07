import os
from pathlib import Path

os.chdir(Path(__file__).parent)

import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agent_orchestrator import main

if __name__ == "__main__":
    main()
