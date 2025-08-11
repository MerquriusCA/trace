# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Trace is a Chrome Extension (Manifest V3) project with a simple popup interface. The extension currently displays a button that sends messages to the active tab.

## Architecture

The extension consists of:
- **manifest.json**: Chrome extension configuration (manifest v3) with side panel support
- **popup.html/js/css**: Extension popup interface (still available but side panel is primary)
- **sidepanel.html/js/css**: Side panel interface that displays on the side of the browser
- **background.js**: Background service worker for persistent functionality
- **content.js**: Content script that runs on all pages to extract page information
- **Icon files**: SVG format icons (16x16, 48x48, 128x128)
- **create_icons.html**: Utility page to generate PNG icons from canvas

## Key Technical Details

1. **Chrome Extension API**: Uses chrome.tabs API with activeTab permission
2. **Permissions**: storage, activeTab, scripting, sidePanel
3. **Message Passing**: Communication between popup/side panel, background script, and content scripts
4. **Icon Format Issue**: manifest.json references PNG icons but repository contains SVG files
5. **Side Panel**: Extension uses Chrome's side panel API for a persistent sidebar interface
6. **Toggle Feature**: Extension can be enabled/disabled with persistent state storage

## Development Commands

This is a vanilla JavaScript Chrome extension with no build process:

```bash
# No build/install commands needed
# To test the extension:
# 1. Open Chrome and navigate to chrome://extensions/
# 2. Enable "Developer mode"
# 3. Click "Load unpacked" and select this directory
```

## Important Notes

- **Icon Generation**: Use create_icons.html in a browser to generate PNG icons from canvas
- **Side Panel Access**: Click the extension icon to open the side panel on the right side of the browser
- **Page Title Display**: When enabled, the extension displays the current page title in the side panel
- **Manual Testing**: Test the extension by loading it unpacked in Chrome's developer mode
- **Chrome Version**: Side panel API requires Chrome 114 or later