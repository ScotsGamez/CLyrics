# 🎵 Transparent Live Lyrics Overlay

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?style=for-the-badge&logo=windows)](https://github.com/ScotsGamez/transparent-lyrics-overlay)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://pypi.org/project/PySide6/)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

A lightweight, hardware-independent, **100% transparent live lyrics overlay** for Windows. It floats directly above your games, desktop, or workspace, streaming synchronized lyrics in real time from whatever song is currently playing on Spotify, YouTube, Apple Music, or Windows Media.

---

## ✨ Features

- **100% True Translucent Background**: Zero window borders, titlebars, background boxes, or dark rectangles. Only the pure floating text glyphs are rendered on your screen.
- **3-Line Continuous Smooth Scrolling Karaoke View**:
  - **Previous Line**: Dimmed context line.
  - **Active Line**: Prominent, high-opacity, emphasized text.
  - **Next Line**: Dimmed upcoming preview line.
- **Jitter-Free Continuous 60 FPS Interpolation**: Float-based lyric index position tracker with monotonic time smoothing and index hysteresis, eliminating timeline bouncing and boundary stutter.
- **Album Cover Art (Left / Right / Off)**:
  - Toggle live album artwork directly on the left or right of the floating lyrics.
  - Automatically widens window aspect ratio to guarantee spacious, uncompressed typography.
  - Smooth rounded corners and graceful cross-fades when changing tracks.
- **Window Resizing & Presets**:
  - Resize directly from the System Tray or right-click menu (**Compact**, **Standard**, **Large**, **Wide**, **Ultra-Wide**, or **Custom Dimensions**).
  - Drag-to-resize by grabbing the bottom-right corner when unlocked.
- **Always-on-Top Floating Window**: Stays visible above active apps, browsers, and borderless games.
- **Hardware-Level Click-Through**:
  - **Unlocked Mode**: Click and drag the lyrics anywhere to reposition. Right-click opens the context menu.
  - **Locked Mode**: Uses native Windows Win32 API (`WS_EX_TRANSPARENT`) so clicks pass seamlessly through to windows and games underneath.
- **System Tray Recovery Controller**: A persistent taskbar notification tray icon lets you lock, unlock, resize, toggle album art, switch themes, or exit at any time—even while clicks are passing through.
- **Intelligent Song Lifecycle**:
  - Automatically queries Windows GSMTC (Global System Media Transport Controls).
  - Fast synchronized `.lrc` lyrics fetching with in-memory caching.
  - Automatic `(Intro)` and `(Instrumental)` interlude detection.
  - Graceful notification and fade-out if no synchronized lyrics exist for a track.
- **Extensible Theme System**: Switch between built-in themes on the fly:
  - 🤍 **Minimalist** (Default): Crisp pure white typography with subtle silver context.
  - 🩵 **Cyberpunk**: Vibrant neon cyan monospace aesthetic.
  - 🧡 **Sunset**: Warm amber and peach glow.
  - 💚 **Emerald**: Sleek electric green and dark mint.

---

## 🚀 Quickstart

### Prerequisites

- **OS**: Windows 10 or 11 (64-bit)
- **Python**: Python 3.10+ installed and added to `PATH`
- **Supported Players**: Spotify, YouTube (via Edge/Chrome/Firefox), Apple Music, Windows Media Player, or any app supporting Windows Media Transport Controls.

### 1. Clone & Setup

```powershell
git clone https://github.com/ScotsGamez/transparent-lyrics-overlay.git
cd transparent-lyrics-overlay
```

Double-click **`setup.bat`**:
- Installs all dependencies (`pip install -r requirements.txt`).
- Automatically creates a sleek **Transparent Live Lyrics** shortcut directly on your Windows Desktop!

### 2. Launching

- **From Desktop**: Double-click the **Transparent Live Lyrics** desktop shortcut.
- **From Folder**: Double-click `Launch_Transparent_Lyrics.bat` (runs silently with zero command prompt box).
- **Via Terminal**:
  ```powershell
  python run.py
  ```

---

## 🎮 Controls & Usage

| Action | How to Trigger |
| :--- | :--- |
| **Move Overlay** | Left-click and drag the lyrics anywhere across your monitors (when unlocked). |
| **Resize by Dragging** | Click and drag the bottom-right corner of the overlay (when unlocked). |
| **Window Size Presets** | Right-click lyrics or System Tray Icon > **Window Size** > select preset or **Custom Dimensions...** |
| **Album Cover Art** | Right-click lyrics or System Tray Icon > **Album Cover** > select **Off**, **Left Side**, or **Right Side**. |
| **Open Menu** | Right-click directly on the lyrics text (when unlocked). |
| **Lock Click-Through** | Right-click lyrics > **Lock (Click-Through)**, or right-click the taskbar tray icon > **Lock**. |
| **Unlock / Reposition** | Right-click the **System Tray Icon** in your Windows taskbar notification area > uncheck **Lock**. |
| **Center on Screen** | Right-click > **Center on Screen**. |
| **Change Theme** | Right-click > **Themes** > select your preferred palette. |
| **Exit** | Right-click lyrics or System Tray Icon > **Exit**. |

---

## 🏛️ Architecture

```mermaid
flowchart TD
    subgraph Windows_OS [Windows Media Subsystem]
        GSMTC["Windows Media Control (Spotify, YouTube, Apple Music)"]
    end

    subgraph Data_Layer [Data & Synchronization Engine]
        MR["media_reader.ps1 (WinRT Daemon)"]
        SL["syncedlyrics (Thread Pool Worker)"]
        Cache[("LRC Lyrics Memory Cache")]
    end

    subgraph UI_Layer [PySide6 Transparent Overlay]
        Tray["QSystemTrayIcon (Taskbar Tray Menu)"]
        Window["OverlayWindow (Frameless, Translucent, AlwaysOnTop, Win32 Click-Through)"]
        Renderer["LyricsRenderer (3-Line Eased Slide & Pure Glyphs)"]
    end

    GSMTC -->|WinRT Query (150ms)| MR
    MR -->|JSON Telemetry: Title, Artist, Pos, Dur| Window
    Window -->|Track Changed Event| SL
    SL --> Cache
    Cache -->|Parsed Timestamped Lines| Window
    Window --> Renderer
    Tray -->|Toggle Lock / Unlock / Exit| Window
```

### Directory Structure

```
transparent-lyrics-overlay/
├── .gitignore
├── Launch_Transparent_Lyrics.bat    # Zero-console Windows batch launcher
├── README.md
├── requirements.txt
├── run.py                           # Application entry point
├── scripts/
│   └── media_reader.ps1             # WinRT Windows Media daemon
├── tests/
│   ├── test_config.py
│   ├── test_integration.py
│   ├── test_lyrics_service.py
│   └── test_themes.py
└── transparent_lyrics/
    ├── __init__.py
    ├── app.py                       # Master controller & lifecycle coordinator
    ├── config.py                    # Persistent settings (window position & theme)
    ├── lyrics_service.py            # Asynchronous LRC fetching & matching
    ├── media_service.py             # GSMTC background worker process
    ├── overlay_window.py            # Translucent window & Win32 click-through handler
    ├── renderer.py                  # 3-line animated smooth-scrolling painter
    ├── themes.py                    # Color palettes and typography presets
    └── tray.py                      # Taskbar system tray icon & context menu
```

---

## 🧪 Running Tests

A full suite of unit and automated integration tests is included:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
