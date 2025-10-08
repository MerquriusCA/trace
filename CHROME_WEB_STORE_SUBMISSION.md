# Chrome Web Store Submission Guide for Trace

## Pre-Submission Checklist

### 1. Required Assets

#### Icons (Already have these ✓)
- [x] 16x16 icon
- [x] 48x48 icon
- [x] 128x128 icon

#### Screenshots (NEED TO CREATE)
- [ ] **1280x800 or 640x400** screenshots (required, 1-5 images)
- [ ] Show key features: onboarding, summarization, side panel
- [ ] Recommended: 3-5 high-quality screenshots

#### Promotional Images (OPTIONAL but recommended)
- [ ] **Small tile**: 440x280 (shown in search results)
- [ ] **Marquee**: 1400x560 (featured placement)

### 2. Store Listing Information

**Name**: Trace

**Summary** (132 chars max):
```
AI-powered reading assistant that summarizes articles and web pages with personalized insights based on your reading style.
```

**Detailed Description** (suggested):
```
Trace is your intelligent reading companion that helps you understand web content faster and more effectively.

KEY FEATURES:
• AI-Powered Summarization: Get concise, accurate summaries of articles and web pages
• Personalized Insights: Summaries adapted to your reading level and preferences
• Quote References: See exact quotes from the source to verify key points
• Side Panel Interface: Non-intrusive reading assistance alongside your browsing
• Reading Profiles: Customize your experience with different reading levels (Simple, Balanced, Detailed, Technical)

HOW IT WORKS:
1. Sign in with your Google account
2. Complete quick onboarding to set your reading preferences
3. Navigate to any article or web page
4. Click "Trace This Page" to get an instant summary
5. Review key points with supporting quotes from the article

PERFECT FOR:
• Students researching topics
• Professionals staying informed
• Casual readers wanting to save time
• Anyone looking to understand complex content more easily

SUBSCRIPTION:
Trace offers a Pro subscription ($9.99/month) for unlimited AI-powered summaries. Currently available by invitation during beta testing.

PRIVACY:
We take your privacy seriously. Trace only processes page content you explicitly request to summarize. Your reading preferences are stored securely.
```

**Category**: Productivity

**Language**: English

### 3. Privacy & Compliance

#### Privacy Policy (REQUIRED)
- [ ] Create and host a privacy policy (required for extensions using OAuth or collecting data)
- [ ] URL must be publicly accessible
- [ ] Should cover:
  - What data you collect (email, page content, reading preferences)
  - How you use it (summarization, personalization)
  - How you store it (database, encryption)
  - Third-party services (OpenAI, Google OAuth, Stripe)
  - User rights (data deletion, opt-out)

**Suggested Privacy Policy URL**:
- Host at: `https://trace-production-79d5.up.railway.app/privacy`
- Or use a dedicated page on your domain

#### Permissions Justification
Be prepared to explain each permission:
- **storage**: Save user preferences and reading profiles
- **activeTab**: Access current page content for summarization
- **tabs**: Manage side panel and page title display
- **scripting**: Inject content scripts for page analysis
- **sidePanel**: Display reading assistance interface
- **identity**: Google OAuth for user authentication

### 4. Package Your Extension

```bash
cd /Users/noojen/repos-hachoo/trace

# Create a clean directory with only necessary files
mkdir trace-release
cp -r *.js *.html *.css *.png *.json trace-release/
cd trace-release

# Remove any development files
rm -f .git* README.md CLAUDE.md

# Create ZIP file
zip -r trace-v1.0.0.zip .
```

### 5. OAuth Configuration

⚠️ **IMPORTANT**: Update Google OAuth consent screen
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials/consent)
2. Update OAuth consent screen:
   - Add Chrome Web Store item ID (will get this after first submission)
   - Set Publishing status to "In Production" (requires verification)
   - Add authorized domains

### 6. Submission Process

1. **Go to Chrome Web Store Developer Dashboard**
   - https://chrome.google.com/webstore/devconsole
   - Pay $5 one-time developer fee if not already paid

2. **Create New Item**
   - Click "New Item"
   - Upload `trace-v1.0.0.zip`

3. **Fill Out Store Listing**
   - Upload screenshots (1280x800 recommended)
   - Add detailed description
   - Select category: Productivity
   - Add privacy policy URL

4. **Set Distribution**
   - **Visibility**: Public, Unlisted, or Private
   - For beta: Choose "Unlisted" (only people with link can install)
   - For public launch: Choose "Public"

5. **Pricing & Distribution**
   - Free extension with in-app purchases (Stripe subscription)
   - Select regions (all or specific countries)

6. **Submit for Review**
   - Review process takes 1-5 business days
   - May request changes or clarifications

### 7. Post-Submission

**After Approval:**
1. Note your extension ID (looks like: `abcdefghijklmnopqrstuvwxyz123456`)
2. Update OAuth consent screen with extension ID
3. Test installation from Chrome Web Store
4. Monitor user reviews and feedback

**Updating Extension:**
- Increment version number (e.g., 1.0.0 → 1.0.1)
- Create new ZIP
- Upload to existing listing
- Each update goes through review

### 8. Common Rejection Reasons to Avoid

- [ ] Using broad host permissions unnecessarily (we use `<all_urls>`)
- [ ] Missing privacy policy
- [ ] OAuth not properly configured
- [ ] Unclear permission justifications
- [ ] Poor quality screenshots
- [ ] Violating Google's policies on content or functionality

### 9. Chrome Web Store Policies to Review

**Must comply with:**
- [Developer Program Policies](https://developer.chrome.com/docs/webstore/program-policies/)
- User data privacy requirements
- Minimum functionality requirements
- Metadata quality guidelines

### 10. Beta Testing (Optional but Recommended)

Before public release:
1. Set visibility to "Unlisted"
2. Share direct link with beta testers
3. Collect feedback
4. Fix issues
5. Update to "Public" when ready

## Quick Start Commands

```bash
# Create release package
cd /Users/noojen/repos-hachoo/trace
zip -r trace-v1.0.0.zip . -x "*.git*" -x "node_modules/*" -x "*.md" -x ".DS_Store"

# Verify package contents
unzip -l trace-v1.0.0.zip
```

## Resources

- [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole)
- [Publication Guide](https://developer.chrome.com/docs/webstore/publish/)
- [Program Policies](https://developer.chrome.com/docs/webstore/program-policies/)
- [Best Practices](https://developer.chrome.com/docs/webstore/best-practices/)

## Timeline

- **Preparation**: 1-2 days (create assets, privacy policy)
- **First Submission**: ~30 minutes
- **Review**: 1-5 business days
- **Total**: ~1 week for first approval

## Current Status

- [x] Manifest updated for production
- [ ] Create screenshots
- [ ] Create privacy policy page
- [ ] Create promotional images (optional)
- [ ] Package extension
- [ ] Submit to Chrome Web Store
