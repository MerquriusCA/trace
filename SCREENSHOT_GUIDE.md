# Screenshot Guide for Chrome Web Store

Chrome Web Store requires **1280x800 or 640x400** screenshots. I recommend 1280x800 for best quality.

## Required Screenshots (3-5 total)

### Screenshot 1: Onboarding Flow
**Shows**: Initial user experience and personalization
**Capture**: The onboarding questions screen

### Screenshot 2: Summary in Action
**Shows**: AI summarization with key points and quotes
**Capture**: Side panel with a complete summary displayed

### Screenshot 3: Side Panel Interface
**Shows**: Main interface and "Trace This Page" button
**Capture**: Clean side panel view with welcome message

### Screenshot 4 (Optional): Settings
**Shows**: User preferences and customization options
**Capture**: Settings tab with reading profile options

### Screenshot 5 (Optional): Quote References
**Shows**: Expandable quotes feature
**Capture**: Summary with quotes section expanded

---

## How to Take 1280x800 Screenshots

### Method 1: Using Chrome DevTools (Recommended)

1. **Open the extension side panel**
   - Click the Trace extension icon

2. **Open Chrome DevTools**
   - Press `Cmd + Option + I` (Mac) or `F12` (Windows/Linux)
   - Or right-click → Inspect

3. **Enable Device Toolbar**
   - Press `Cmd + Shift + M` (Mac) or `Ctrl + Shift + M` (Windows/Linux)
   - Or click the device icon in DevTools toolbar

4. **Set Custom Dimensions**
   - Click "Responsive" dropdown at top
   - Select "Edit..."
   - Add custom device:
     - Device Name: `Chrome Web Store Screenshot`
     - Width: `1280`
     - Height: `800`
     - Device pixel ratio: `1`

5. **Take Screenshot**
   - With device toolbar active, click the three dots menu (⋮)
   - Select "Capture screenshot"
   - File will download as PNG

### Method 2: Using Browser Window Resize

1. **Resize your browser window to 1280x800**
   - Use a window resize extension like "Window Resizer"
   - Or manually resize (less precise)

2. **Take screenshot**
   - Mac: `Cmd + Shift + 4`, then press `Space`, click window
   - Windows: Use Snipping Tool
   - Linux: Use Screenshot utility

### Method 3: Using Online Tools

1. Go to https://www.screely.com or https://screenshots.cloud
2. Upload your extension screenshots
3. Set dimensions to 1280x800
4. Add browser mockup (optional but looks professional)

---

## Screenshot Checklist

### Before Taking Screenshots:

- [ ] **Use demo content**: Navigate to a good article (e.g., tech blog, news site)
- [ ] **Clear data**: Start fresh so UI looks clean
- [ ] **Sign in**: Make sure you're authenticated
- [ ] **Good lighting**: If using browser chrome, enable light theme for clarity

### What to Capture:

#### Screenshot 1: Onboarding (onboarding.html)
```bash
# Open onboarding manually
chrome-extension://<your-extension-id>/onboarding.html
```
- [ ] Capture the reader type question screen
- [ ] Or capture the reading level selection
- [ ] Make sure it looks welcoming and clear

#### Screenshot 2: Welcome/Empty State
- [ ] Open side panel (click extension icon)
- [ ] Show "Welcome" message with "Get Started" button
- [ ] Clean, uncluttered view

#### Screenshot 3: Summary with Key Points
- [ ] Navigate to a well-known article (e.g., TechCrunch, Medium, BBC)
- [ ] Click "Trace This Page"
- [ ] Wait for summary to load
- [ ] Show summary sentence + 2-3 bullet points
- [ ] **Make sure page title is visible at top**

#### Screenshot 4: Quotes Expanded
- [ ] Same as Screenshot 3
- [ ] Click "Show Quotes" on one bullet point
- [ ] Capture with quotes visible
- [ ] Shows the quote reference feature

#### Screenshot 5: Settings (optional)
- [ ] Click "Settings" tab
- [ ] Show reading profile preferences
- [ ] Displays customization options

---

## Quick Steps (Fastest Method)

1. **Set up DevTools device mode at 1280x800**
2. **Open extension and take 5 screenshots:**
   - Onboarding page
   - Welcome screen
   - Summary in action (on a real article)
   - Quotes expanded
   - Settings page

3. **Save screenshots as:**
   - `screenshot-1-onboarding.png`
   - `screenshot-2-welcome.png`
   - `screenshot-3-summary.png`
   - `screenshot-4-quotes.png`
   - `screenshot-5-settings.png`

---

## Pro Tips

### Make Screenshots Look Professional:

1. **Use a well-known website** for demo
   - TechCrunch, Medium, BBC, The Verge
   - Avoid controversial or sensitive content

2. **Choose good test content**
   - Article with clear structure
   - Generates good bullet points
   - Has quotable excerpts

3. **Clean UI**
   - No error messages visible
   - All loading complete
   - Proper spacing and alignment

4. **Highlight key features**
   - Show the AI summary clearly
   - Display quote references
   - Show personalization options

5. **Add annotations (optional)**
   - Use tools like Skitch or Snagit
   - Add arrows or highlights to key features
   - Keep it subtle and professional

---

## Recommended Test Pages for Screenshots

### Good Articles for Demo:
1. **TechCrunch** - https://techcrunch.com/latest
   - Pick a recent tech news article
   - Usually generates good summaries

2. **Medium** - https://medium.com/topics/technology
   - Well-structured articles
   - Clear key points

3. **The Verge** - https://www.theverge.com
   - Tech/science content
   - Professional appearance

4. **BBC News** - https://www.bbc.com/news
   - Reputable source
   - Diverse topics

---

## After Taking Screenshots

1. **Review each screenshot:**
   - [ ] Is resolution exactly 1280x800?
   - [ ] Is text readable?
   - [ ] Are there any UI glitches?
   - [ ] Does it showcase the feature well?

2. **Optimize file size (optional):**
   ```bash
   # Using ImageOptim (Mac)
   # Or use https://tinypng.com
   ```

3. **Name files clearly:**
   ```
   trace-screenshot-1-onboarding.png
   trace-screenshot-2-welcome.png
   trace-screenshot-3-summary.png
   trace-screenshot-4-quotes.png
   trace-screenshot-5-settings.png
   ```

4. **Store in project:**
   ```bash
   mkdir -p /Users/noojen/repos-hachoo/trace/store-assets
   mv trace-screenshot-*.png /Users/noojen/repos-hachoo/trace/store-assets/
   ```

---

## Chrome Web Store Upload

When uploading screenshots:
1. Go to Chrome Web Store Developer Dashboard
2. Your listing → Store listing
3. Scroll to "Screenshots"
4. Upload images in order (drag to reorder)
5. First screenshot is the primary one (most important!)

**Order matters:**
1. Most impressive feature first (Summary in action)
2. Then onboarding/setup
3. Then additional features
4. Settings last

---

## Need Help?

If you need me to:
- Adjust UI for better screenshots
- Create a demo mode
- Add screenshot borders/styling
- Generate mockups

Just let me know!
