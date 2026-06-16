import os
import sys

# 1. CRITICAL AUDIO ENVIRONMENT VARIABLE OVERRIDE
# This instructs Qt to use the modern Windows Media Foundation backend framework.
# This MUST execute at the absolute top of the stack before any PyQt5 modules are loaded!
os.environ['QT_MULTIMEDIA_PREFERRED_PLUGINS'] = 'windowsmediafoundation'

from PyQt5.QtWidgets import QApplication
from server import run_server
from companion import CompanionApp

if __name__ == "__main__":
    print("===================================================")
    print("      Initializing Desktop Companion V1.0 Core     ")
    print("===================================================")
    
    # 2. LAUNCH FLASK BACKGROUND ENVIRONMENT GATES
    # This fires up your Admin Dashboard web layout panels seamlessly.
    run_server()
    
    # 3. CONSTRUCT INTERFACE ENGINE PIPELINES
    app = QApplication(sys.argv)
    
    print("[SYSTEM] Waking up desktop avatar...")
    pet = CompanionApp()
    
    # 4. EXECUTE APPLICATION RUNTIME LOOP
    sys.exit(app.exec_())