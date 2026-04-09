import json
import os
import sys
import subprocess
import platform

try:
    import msvcrt
except Exception:
    msvcrt = None
try:
    import tty
    import termios
except Exception:
    tty = None
    termios = None

def _getch():
    if msvcrt:
        return msvcrt.getch()
    else:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
            return ch.encode()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def interactive_menu(options, title=None):
    idx = 0
    selected = [True] * len(options)
    while True:
        # clear screen
        if os.name == 'nt':
            os.system('cls')
        else:
            os.system('clear')

        if title:
            print(title)
        print('Use Up/Down arrows to navigate, Space to toggle, Enter to confirm. Ctrl-C to cancel.\n')
        for i, option in enumerate(options):
            prefix = '=> ' if i == idx else '   '
            mark = '[x]' if selected[i] else '[ ]'
            print(f"{prefix}{mark} {option['label']}")

        try:
            ch = _getch()
        except Exception:
            print('\nInput error; falling back to all selected.')
            return [True] * len(options)

        # Windows msvcrt
        if msvcrt:
            if ch in (b'\r', b'\n'):
                return selected
            if ch == b' ':
                selected[idx] = not selected[idx]
            if ch in (b'\x00', b'\xe0'):
                ch2 = msvcrt.getch()
                if ch2 == b'H': # Up
                    idx = (idx - 1) % len(options)
                elif ch2 == b'P': # Down
                    idx = (idx + 1) % len(options)
        else:
            # Unix
            if ch == b'\n' or ch == b'\r':
                return selected
            if ch == b' ':
                selected[idx] = not selected[idx]
            if ch == b'\x1b':
                # read two more
                try:
                    import fcntl
                    fd = sys.stdin.fileno()
                    old_flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                    fcntl.fcntl(fd, fcntl.F_SETFL, old_flags | os.O_NONBLOCK)
                    rest = sys.stdin.read(2)
                    fcntl.fcntl(fd, fcntl.F_SETFL, old_flags)
                    if rest == '[A':
                        idx = (idx - 1) % len(options)
                    elif rest == '[B':
                        idx = (idx + 1) % len(options)
                except:
                    pass

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sources_file = os.path.join(script_dir, "sources.json")

    if not os.path.exists(sources_file):
        print(f"Error: {sources_file} not found.")
        return

    with open(sources_file, 'r', encoding='utf-8') as f:
        sources = json.load(f)

    options = []
    # Step 1 options
    for s in sources:
        name = s.get('name', s['type'])
        url = s['url']
        options.append({
            'step': 1,
            'source_name': name,
            'label': f"Step 1: Create sources [x] {name} ({url})"
        })

    # Step 2 options
    for s in sources:
        name = s.get('name', s['type'])
        url = s['url']
        options.append({
            'step': 2,
            'source_name': name,
            'label': f"Step 2: Parse sources [x] {name} ({url})"
        })

    # Step 3
    options.append({
        'step': 3,
        'label': "Step 3: Parse content [x]"
    })

    # Step 4
    options.append({
        'step': 4,
        'label': "Step 4: Create heatmap [x]"
    })

    selection = interactive_menu(options, title="Diary Statistics Pipeline Generation")

    if not any(selection):
        print("No steps selected. Exiting.")
        return

    # Execute selected steps

    # Step 1 execution
    step1_sources = []
    for i, opt in enumerate(options):
        if opt['step'] == 1 and selection[i]:
            step1_sources.append(opt['source_name'])

    if step1_sources:
        print("\n--- Executing Step 1: Create sources ---")
        cmd = [sys.executable, os.path.join(script_dir, "1_create_sources.py")] + step1_sources
        subprocess.run(cmd)

    # Step 2 execution
    step2_sources = []
    for i, opt in enumerate(options):
        if opt['step'] == 2 and selection[i]:
            step2_sources.append(opt['source_name'])

    if step2_sources:
        print("\n--- Executing Step 2: Parse sources ---")
        cmd = [sys.executable, os.path.join(script_dir, "2_parse_sources.py")] + step2_sources
        subprocess.run(cmd)

    # Step 3 execution
    step3_selected = False
    for i, opt in enumerate(options):
        if opt['step'] == 3 and selection[i]:
            step3_selected = True
            break

    if step3_selected:
        print("\n--- Executing Step 3: Parse content ---")
        cmd = [sys.executable, os.path.join(script_dir, "3_parse_content.py")]
        subprocess.run(cmd)

    # Step 4 execution
    step4_selected = False
    for i, opt in enumerate(options):
        if opt['step'] == 4 and selection[i]:
            step4_selected = True
            break

    if step4_selected:
        print("\n--- Executing Step 4: Create heatmap ---")
        cmd = [sys.executable, os.path.join(script_dir, "4_create_heatmap.py")]
        subprocess.run(cmd)

    print("\nAll selected steps completed.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled by user.")
