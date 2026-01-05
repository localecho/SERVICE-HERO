---
name: sheets_tracker
description: Google Sheets integration for sprint tracking and executive dashboards
triggers:
  - update sheet
  - sync to sheets
  - sprint dashboard
---

# Skill: Google Sheets Sprint Tracker

Automatically sync sprint progress to Google Sheets for manager visibility.

## Quick Setup

```bash
/sheets init --name "Project Sprint Tracker"
```

## Features

- Real-time sprint event logging
- Executive dashboard with KPIs
- Historical trend tracking
- Skills inventory

## Sheet Structure

| Tab | Purpose |
|-----|---------|
| Sprint Log | Raw event data |
| Dashboard | Aggregated metrics |
| Trends | Weekly/monthly charts |
| Skills | Capability inventory |

## Configuration

```yaml
sheets:
  enabled: true
  spreadsheet_id: $GOOGLE_SHEET_ID
  sync:
    mode: real_time
    on_events:
      - issue_completed
      - pr_merged
      - sprint_completed
```

*Real-time visibility into agent progress for stakeholders.*
