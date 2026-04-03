# CLIC — Cooler Lite IDE for Commandline

A super lightweight, modern, customizable terminal IDE for Windows.
Think Obsidian meets Cursor, but for the command line.

Built with [Textual](https://textual.textualize.io/) — runs inside your terminal, stays close to the CLI, but adds modern IDE features.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

Is super buggy for now so, yk...

## Features

| Feature | Description |
|---------|-------------|
| **Multi-tab terminals** | Open multiple terminal tabs (`Ctrl+T`), close with `Ctrl+W` |
| **File browser** | Clickable directory tree with Nerd Font icons, click to `cd` or preview files |
| **Markdown viewer** | Built-in `.md` rendering with syntax highlighting |
| **Command history** | Searchable history with timestamps and exit codes, arrow-key navigation |
| **Command palette** | `Ctrl+P` to fuzzy-search commands and custom shortcuts |
| **5 built-in themes** | Default, Dracula, Catppuccin, Gruvbox, Nord — cycle with palette |
| **Sound effects** | Typing clicks, ambient loops, UI sounds — fully configurable |
| **Customizable** | Everything in one `config.yaml` — theme, shell, shortcuts, sounds, etc. |
| **Status bar** | Shows current path, git branch, theme, clock |

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Install a Nerd Font (recommended)

CLIC uses [Nerd Font](https://www.nerdfonts.com/) icons. Install one and set it in your terminal:

- **JetBrainsMono Nerd Font** (recommended)
- FiraCode Nerd Font
- CaskaydiaCove Nerd Font

### 3. Run

1) Basic Python running:
```bash
python run.py
```

2) Windows Bash
Simply double click the run.bat 

3) To run the ide externally from other apps you can point them at the run_external.bat

#### CLI options

```bash
python run.py --dir ~/projects        # Start in a specific directory
python run.py --theme dracula         # Start with a theme
python run.py --config my_config.yaml # Use a custom config
python run.py --no-sound              # Disable sounds
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+T` | New terminal tab |
| `Ctrl+W` | Close current tab |
| `Ctrl+E` | Toggle file browser |
| `Ctrl+H` | Toggle history panel |
| `Ctrl+M` | Toggle markdown viewer |
| `Ctrl+P` | Open command palette |
| `F5` | Refresh file browser |
| `Escape` | Focus terminal input |
| `↑` / `↓` | Navigate command history |

---

## Project Structure

```
CLIC/
├── run.py                  # Entry point — run this
├── config.yaml             # User configuration (edit this!)
├── requirements.txt        # Python dependencies
│
├── clic/
│   ├── __init__.py         # Package init, version
│   ├── app.py              # Main Textual app — layout, bindings, orchestration
│   ├── config.py           # Config loader — reads config.yaml, provides defaults
│   ├── history.py          # Command history — persistence, search, navigation
│   ├── sounds.py           # Sound manager — typing, ambient, effects via pygame
│   │
│   ├── widgets/
│   │   ├── terminal.py     # Terminal widget — shell execution, prompt, cd handling
│   │   ├── file_browser.py # File tree — clickable dirs/files with Nerd Font icons
│   │   ├── markdown_viewer.py  # Markdown renderer panel
│   │   ├── history_panel.py    # Searchable history list panel
│   │   └── command_palette.py  # Ctrl+P fuzzy command search overlay
│   │
│   └── themes/
│       ├── default.tcss    # Default dark theme (GitHub Dark inspired)
│       ├── dracula.tcss    # Dracula theme
│       ├── catppuccin.tcss # Catppuccin Mocha theme
│       ├── gruvbox.tcss    # Gruvbox Dark theme
│       └── nord.tcss       # Nord theme
│
└── sounds/                 # Sound files — add your own!
    ├── typing/             # Keypress sounds (.wav/.ogg/.mp3)
    ├── ambient/            # Background loop sounds
    └── effects/            # UI sounds (run, success, error, cd, etc.)
```

---

## Configuration

All settings live in `config.yaml`. Here's what you can customize:

### Theme

```yaml
# Built-in: "default", "dracula", "catppuccin", "gruvbox", "nord"
# Or point to a custom .tcss file: "path/to/mytheme.tcss"
theme: "catppuccin"
```

### Shell

```yaml
shell: "powershell"   # Options: "powershell", "cmd", "bash", "wsl"
```

### Sounds

```yaml
sounds:
  enabled: true
  master_volume: 0.5

  typing:
    enabled: true
    volume: 0.3
    directory: "sounds/typing"    # Drop .wav files here

  ambient:
    enabled: false
    volume: 0.2
    file: "sounds/ambient/ambient.wav"

  effects:
    enabled: true
    volume: 0.4
    mapping:
      command_run: "sounds/effects/run.wav"
      command_success: "sounds/effects/success.wav"
      command_error: "sounds/effects/error.wav"
      tab_switch: "sounds/effects/tab.wav"
      cd: "sounds/effects/cd.wav"
      startup: "sounds/effects/startup.wav"
```

### Custom Commands

Add your own commands to the palette (`Ctrl+P`):

```yaml
custom_commands:
  " Git Status": "git status"
  " Docker PS": "docker ps"
  " My Script": "python scripts/deploy.py"
```

### File Browser

```yaml
file_browser:
  show_hidden: false
  show_icons: true
  show_sizes: true
  max_depth: 3
  exclude: ["__pycache__", "node_modules", ".git"]
```

---

## Creating Custom Themes

Themes are [TCSS](https://textual.textualize.io/css_types/) files (Textual CSS). Copy an existing theme and modify colors:

```bash
cp clic/themes/default.tcss clic/themes/mytheme.tcss
```

Then set in config:

```yaml
theme: "mytheme"
# or absolute path:
theme: "C:/Users/you/themes/mytheme.tcss"
```

Key CSS selectors to customize:

| Selector | What it styles |
|----------|---------------|
| `Screen` | Main background/text color |
| `#terminal-output` | Command output area |
| `#prompt-label` | Shell prompt line |
| `#command-input` | Input field |
| `#file-browser` | File browser panel |
| `#status-bar` | Bottom status bar |
| `.panel-title` | Panel header bars |
| `MarkdownH1`, `MarkdownH2` | Markdown heading colors |
| `Tab.-active` | Active tab styling |

---

## Adding Sounds

CLIC supports three types of sounds:

### Typing sounds

Drop `.wav`, `.ogg`, or `.mp3` files into `sounds/typing/`. CLIC picks a random one on each keypress for a natural feel. Use short clicks (50–150ms).

### Ambient sounds

Place a single loop file at `sounds/ambient/ambient.wav`. Toggle via the command palette. Good for rain, lo-fi, coffee shop vibes.

### Effect sounds

Map action names to files in `config.yaml` under `sounds.effects.mapping`. Available actions:

- `command_run` — when a command is executed
- `command_success` — when a command exits 0
- `command_error` — when a command exits non-zero
- `tab_switch` — tab created/closed
- `file_open` — file clicked in browser
- `cd` — directory changed
- `startup` — app launch

---

## Built-in Commands

These commands work directly in the terminal (no shell needed):

| Command | Action |
|---------|--------|
| `cd <path>` | Change directory (also updates file browser) |
| `clear` / `cls` | Clear terminal output |
| `exit` | Quit CLIC |

---

## Tech Stack

- **[Textual](https://textual.textualize.io/)** — Modern TUI framework for Python
- **[Rich](https://rich.readthedocs.io/)** — Beautiful terminal formatting (bundled with Textual)
- **[PyYAML](https://pyyaml.org/)** — Configuration parsing
- **[Pygame](https://www.pygame.org/)** — Audio playback for sounds
- **Python 3.11+** — Type hints, modern syntax

---

## License

MIT
