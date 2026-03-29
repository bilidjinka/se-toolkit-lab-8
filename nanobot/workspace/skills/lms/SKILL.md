---
name: lms
description: Use LMS MCP tools for live course data
always: true
---

# LMS Skill

You have access to LMS backend tools via MCP. Use them to answer questions about labs, scores, and student progress.

## Available Tools

- `lms_health` — Check if the LMS backend is healthy
- `lms_labs` — List all available labs
- `lms_pass_rates` — Get pass rates for a specific lab
- `lms_scores` — Get scores for a specific lab
- `lms_completion` — Get completion statistics for a specific lab
- `lms_groups` — Get student groups
- `lms_timeline` — Get timeline data for a specific lab
- `lms_top_learners` — Get top learners for a specific lab

## Strategy

### When user asks about labs, scores, pass rates, completion, groups, timeline, or top learners:

1. **If a lab is not specified**, first call `lms_labs` to get the list of available labs
2. **If multiple labs exist**, ask the user to choose one. Use the lab title as the label and the lab ID as the value for structured UI choices
3. **Once a lab is selected**, call the appropriate tool with the lab parameter

### Example flows:

**User: "Show me the scores"**
- Step 1: Call `lms_labs` to get available labs
- Step 2: If multiple labs, present a choice to the user
- Step 3: Call `lms_scores` with the selected lab

**User: "What labs are available?"**
- Call `lms_labs` and return the list

**User: "Is the backend healthy?"**
- Call `lms_health` and report the result

**User: "Which lab has the lowest pass rate?"**
- Call `lms_labs` to get all labs
- Call `lms_pass_rates` for each lab
- Compare and report the lowest

## Formatting

- Format percentages with one decimal place (e.g., "75.3%")
- Keep responses concise
- When showing lab lists, use the lab title from the API response
- If the API returns an error, explain what went wrong clearly

## When asked "What can you do?"

Explain that you can:
- Check LMS backend health
- List available labs
- Show scores, pass rates, and completion stats for specific labs
- Show student groups, timeline, and top learners
- Answer questions about course progress

Be honest about your current tools and limits.
