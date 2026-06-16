import subprocess
import sys
import os

def install_libraries():
    print("--- Checking and Installing Libraries ---")
    req_file = 'requirements.txt'
    
    if not os.path.exists(req_file):
        print(f"Error: {req_file} not found in this folder.")
        return

    try:
        # Upgrade pip first to avoid dependency errors
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        # Install libraries
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file])
        print("\nSuccess: All libraries installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"\nError occurred during installation: {e}")

if __name__ == "__main__":
    install_libraries()
    input("\nPress Enter to close...")