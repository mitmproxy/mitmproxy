# SpecStory Artifacts Directory
    
This directory is automatically created and maintained by the SpecStory extension to preserve your AI chat history.
    
## What's Here?
    
- `.specstory/history`: Contains auto-saved markdown files of your AI coding sessions
    - Each file represents a separate AI chat session
    - If you enable auto-save, files are automatically updated as you work
    - You can enable/disable the auto-save feature in the SpecStory settings, it is disabled by default
- `.specstory/.project.json`: Contains the persistent project identity for the current workspace
    - This file is only present if you enable AI rules derivation
    - This is used to provide consistent project identity of your project, even as the workspace is moved or renamed
- `.specstory/ai_rules_backups`: Contains backups of the `.cursor/rules/derived-cursor-rules.mdc` or the `.github/copilot-instructions.md` file
    - Backups are automatically created each time the `.cursor/rules/derived-cursor-rules.mdc` or the `.github/copilot-instructions.md` file is updated
    - You can enable/disable the AI Rules derivation feature in the SpecStory settings, it is disabled by default
- `.specstory/.gitignore`: Contains directives to exclude non-essential contents of the `.specstory` directory from version control
    - Add `/history` to exclude the auto-saved chat history from version control

## Valuable Uses
    
- Capture: Keep your context window up-to-date when starting new Chat/Composer sessions via @ references
- Search: For previous prompts and code snippets 
- Learn: Meta-analyze your patterns and learn from your past experiences
- Derive: Keep the AI on course with your past decisions by automatically deriving rules from your AI interactions
    
## Version Control
    
We recommend keeping this directory under version control to maintain a history of your AI interactions. However, if you prefer not to version these files, you can exclude them by adding this to your `.gitignore`:
    
```
.specstory/**
```

We recommend __not__ keeping the `.specstory/ai_rules_backups` directory under version control if you are already using git to version your AI rules, and committing regularly. You can exclude it by adding this to your `.gitignore`:

```
.specstory/ai_rules_backups
```

## Searching Your Codebase
    
When searching your codebase, search results may include your previous AI coding interactions. To focus solely on your actual code files, you can exclude the AI interaction history from search results.
    
To exclude AI interaction history:
    
1. Open the "Find in Files" search in Cursor or VSCode (Cmd/Ctrl + Shift + F)
2. Navigate to the "files to exclude" section
3. Add the following pattern:
    
```
.specstory/*
```
    
This will ensure your searches only return results from your working codebase files.

## Notes

- Auto-save only works when Cursor or VSCode flushes sqlite database data to disk. This results in a small delay after the AI response is complete before SpecStory can save the history.

## Settings
    
You can control auto-saving behavior in Cursor or VSCode:
    
1. Open Cursor/Code → Settings → VS Code Settings (Cmd/Ctrl + ,)
2. Search for "SpecStory"
3. Find "Auto Save" setting to enable/disable
    
Auto-save occurs when changes are detected in the sqlite database, or every 2 minutes as a safety net.