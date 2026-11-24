# Setting Up a macOS Finder Quick Action

With macOS Quick Actions, you can right-click any CSV, JSON, or text file containing social media handles in Finder and scrape them with one click.

---

## Option 1: Using the Apple Shortcuts App (Recommended on macOS 12+)

1. Open the **Shortcuts** app on your Mac (`Applications/Shortcuts.app`).
2. Click the **+** (Create Shortcut) button.
3. In the right sidebar, search for **Run Shell Script** and drag it into the canvas.
4. Set the shortcut options in the right pane:
   - Check **Use as Quick Action**
   - Under *Services Receive*, select **Files and Folders** in **Finder**
5. Configure the **Run Shell Script** action:
   - **Shell**: `/bin/zsh`
   - **Pass input**: `as arguments`
   - **Script content**:
     ```bash
     PROJECT_DIR="$HOME/.gemini/antigravity/scratch/bulk-social-scraper-macos"
     for f in "$@"; do
         "$PROJECT_DIR/run_macos.command" --file "$f"
     done
     ```
6. Name the Shortcut **"Scrape Social Media"** and choose a custom icon.
7. Now in **Finder**, right-click any `.csv` or `.txt` file &rarr; **Quick Actions** &rarr; **Scrape Social Media**!

---

## Option 2: Using Automator.app

1. Open **Automator.app** (`Applications/Utilities/Automator.app`).
2. Choose **Quick Action** as the document type.
3. At the top of the workflow:
   - "Workflow receives current": **files or folders** in **Finder.app**
4. From the Library, drag **Run Shell Script** to the right:
   - Shell: `/bin/bash`
   - Pass input: `as arguments`
   - Code:
     ```bash
     PROJECT_DIR="$HOME/.gemini/antigravity/scratch/bulk-social-scraper-macos"
     cd "$PROJECT_DIR"
     if [ -f .venv/bin/activate ]; then source .venv/bin/activate; fi
     python3 -m scraper.cli --file "$1" --export csv,json,sqlite,html
     ```
5. Save the Quick Action as `Bulk Scrape File`.
6. Right-click any file in Finder and select `Quick Actions > Bulk Scrape File`.
