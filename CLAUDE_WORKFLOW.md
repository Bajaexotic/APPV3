# MANDATORY CODE CHANGE WORKFLOW

**Claude must ALWAYS follow this workflow for EVERY code change. No exceptions.**

---

## BEFORE Making Any Code Changes

### 1. ASK FOR CLARIFICATION if there's ANY ambiguity

- Don't assume what the user means
- Ask specific questions about what should change
- Confirm understanding before touching code
- **Example**: If user says "change background to grey" → Ask "Which backgrounds? (main window, panels, graph, cells, all?)"

### 2. READ the relevant files FIRST

- Understand current implementation
- Identify what will be affected
- Map out dependencies
- Use Read tool to examine code before changing

### 3. EXPLAIN the plan to the user

- What files will change
- What specific lines/values will change
- What the impact will be
- **Get confirmation before proceeding**

---

## AFTER Making Code Changes

### 4. VALIDATE Syntax

- **ALWAYS** run `python3 -m py_compile` on ALL modified files
- Check for syntax errors before proceeding

### 5. RUN Comprehensive Error Scan

Check for:

- Missing THEME keys
- Broken imports
- Undefined variables
- Logic errors
- Hardcoded values that should use theme config

### 6. VERIFY the actual changes match intent

- Read the changed sections back
- Confirm the values are correct
- Check nothing else was accidentally changed
- Compare before/after if needed

### 7. TEST related functionality

- Will this break anything else?
- Are there side effects?
- Do related components need updates?
- Consider the ripple effects

### 8. COMMIT with clear message

Explain:

- What changed (specific files, lines, values)
- Why it changed (user request, bug fix, etc.)
- What the impact is (what it affects)

### 9. PUSH to remote

- Push changes to the designated branch
- Verify push succeeded

### 10. REPORT results to user

- Summary of what was changed
- Error scan results
- Pull command for user to get changes
- Any warnings or notes

---

## NEVER

- ❌ Make changes without asking for clarification
- ❌ Assume what the user means
- ❌ Skip the error scan
- ❌ Commit without validation
- ❌ Change code "just to try something"
- ❌ Batch multiple unrelated changes together
- ❌ Make changes to files you haven't read

---

## ALWAYS

- ✅ Ask questions if unclear
- ✅ Explain before changing
- ✅ Validate after changing
- ✅ Run error scans (automatic after code delivery)
- ✅ Report results
- ✅ Follow the standard error scan workflow
- ✅ Use TodoWrite to track multi-step changes

---

## Standard Error Scan (Run After Every Code Change)

```python
1. PYTHON SYNTAX VALIDATION
   - Run py_compile on all modified files

2. THEME KEY COMPLETENESS
   - Check all THEME.get() calls
   - Verify keys exist in BASE_STRUCTURE

3. IMPORT VALIDATION
   - Check for circular imports
   - Verify all imports resolve

4. LOGIC VALIDATION
   - Check for undefined variables
   - Verify function calls have all required parameters

5. CONSISTENCY CHECK
   - Hardcoded values should use THEME
   - Font sizes should use universal skeleton
   - Colors should use color coordination when applicable
```

---

## How to Use This Workflow

**At the start of each session**, tell Claude:

```
"Read CLAUDE_WORKFLOW.md and follow it for all code changes"
```

**During the session**, Claude will:

1. Ask clarifying questions BEFORE changing code
2. Explain what will change and get confirmation
3. Make the changes
4. Run comprehensive error scans
5. Report results

---

## Example of Correct Workflow

**User**: "Change the background to grey"

**Claude Should Do**:

1. ❓ Ask: "Which backgrounds do you want grey? (main window, panel containers, graph, cells, pills, or all?)"
2. 👂 Wait for user answer
3. 📖 Read relevant files to understand current implementation
4. 📋 Explain: "I will change `bg_primary`, `bg_panel`, `bg_secondary` from #000000 to #1F2937 in config/theme.py. This will affect Panel 1, 2, and 3 backgrounds. The graph is transparent so it will show the grey background through. Is this correct?"
5. 👂 Wait for confirmation
6. ✏️ Make changes
7. ✅ Run error scan
8. 📤 Commit and push
9. 📊 Report results

---

**This workflow ensures quality, prevents mistakes, and maintains clear communication.**

Last Updated: 2025-11-06
