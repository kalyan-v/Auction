# Scheduled Workflow Troubleshooting Guide

## Issue: Scheduled Workflow Not Running

### Problem Statement
The scheduled workflow `scrape_wpl.yml` works fine when triggered manually (via workflow_dispatch) but does not run automatically on the scheduled times (cron triggers).

### Root Cause
**GitHub Actions scheduled workflows only run on the default branch (`main`)**. This is a fundamental limitation of GitHub Actions.

- ✅ Manual triggers (`workflow_dispatch`) can be executed from any branch
- ❌ Scheduled triggers (`schedule`/`cron`) only execute on the default branch

### Solution
To enable scheduled workflow runs, the workflow file must exist on the default branch (`main`). Once this PR is merged to `main`, the scheduled workflow will start running automatically.

### Current Workflow Configuration
The workflow is configured to run:
1. **Every 5 minutes**: `cron: '*/5 * * * *'` (UTC)
2. **Daily at 6:30 PM UTC**: `cron: '30 18 * * *'`

### Verification Steps
After merging to `main`, you can verify the scheduled runs are working by:

1. **Check Actions Tab**: Go to the Actions tab in your GitHub repository
2. **Look for Scheduled Runs**: Look for workflow runs with event type `schedule` (not `workflow_dispatch`)
3. **Wait for First Run**: It may take up to 5 minutes for the first scheduled run to appear

### Important Notes

1. **First Run Delay**: After merging to `main`, there may be a delay before the first scheduled run. GitHub sometimes requires a few minutes to register the schedule.

2. **Repository Activity**: For public repositories, if there's been no activity for 60 days, GitHub automatically suspends scheduled workflows. A new push will reactivate them.

3. **Permissions**: The workflow has `contents: write` permission, which allows it to commit and push changes to the repository.

4. **Cron Timing**: All cron schedules use UTC time zone. Make sure to convert your local time to UTC when setting schedules.

5. **Testing**: To test changes without waiting for the schedule:
   - Use the "Run workflow" button in the Actions tab
   - Select the branch you want to test
   - Click "Run workflow"

### Additional Resources
- [GitHub Actions Events - Schedule](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule)
- [Cron Syntax Help](https://crontab.guru/)
- [GitHub Actions Troubleshooting](https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows)

## Summary
✅ **The workflow file is correctly configured**  
✅ **Manual dispatch works perfectly**  
⚠️ **Scheduled runs require the workflow to be on the `main` branch**  
🔄 **Action Required: Merge this PR to `main` to enable scheduled runs**
