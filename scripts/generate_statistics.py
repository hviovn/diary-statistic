import os
import subprocess
import sys

def run_script(script_name):
    print(f"\n>>> Running {script_name}...")
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script_name)
    result = subprocess.run([sys.executable, script_path], capture_output=False)
    if result.returncode != 0:
        print(f"Error running {script_name}")
        return False
    return True

def main():
    steps = [
        "step1_link_discovery.py",
        "step2_content_extraction.py",
        "step3_analysis.py",
        "step4_generate_heatmap.py"
    ]

    for step in steps:
        if not run_script(step):
            print(f"Pipeline failed at {step}")
            sys.exit(1)

    print("\nPipeline completed successfully!")

if __name__ == "__main__":
    main()
