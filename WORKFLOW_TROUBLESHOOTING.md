# Scheduled Workflow Fix

## Issue: Scheduled Workflow Not Running

### Problem Statement
The scheduled workflow `scrape_wpl.yml` works fine when triggered manually (via workflow_dispatch) but does not run automatically on the scheduled times (cron triggers).

### Root Causes & Fixes Applied

**1. GitHub Actions Scheduled Workflows Only Run on Default Branch**
- ✅ **Manual triggers** (`workflow_dispatch`) can be executed from any branch
- ❌ **Scheduled triggers** (`schedule`/`cron`) only execute on the default branch (`main`)
- **Fix**: This PR must be merged to `main` to activate scheduled runs

**2. Aggressive Schedule Can Be Throttled**
- ❌ **Previous**: Every 5 minutes (`*/5 * * * *`) - Too aggressive, may be throttled by GitHub
- ✅ **Fixed**: Daily at 6:30 PM UTC (`30 18 * * *`) - Reasonable schedule that won't be throttled
- **Reason**: GitHub may disable workflows with very frequent schedules to conserve resources

**3. Improved Error Handling**
- ✅ **Fixed**: Better conditional logic for git commit/push
- ✅ **Added**: Explicit message when no changes need to be committed
- **Benefit**: Prevents push failures when there are no database changes

### Changes Made

1. **Removed aggressive 5-minute schedule** - Kept only the daily 6:30 PM UTC schedule
2. **Improved commit logic** - Better error handling to prevent workflow failures
3. **Added documentation** - Comprehensive troubleshooting guide

### Updated Workflow Configuration
The workflow now runs:
- **Daily at 6:30 PM UTC**: `cron: '30 18 * * *'`
- **Manual trigger**: Available anytime via Actions tab

### Verification Steps
After merging to `main`, verify scheduled runs are working:

1. **Check Actions Tab**: Go to the Actions tab in your GitHub repository
2. **Wait for First Run**: First scheduled run will occur at 6:30 PM UTC
3. **Look for Scheduled Runs**: Look for workflow runs with event type `schedule` (not `workflow_dispatch`)

### Important Notes

1. **First Run**: After merging to `main`, the first scheduled run will occur at the next 6:30 PM UTC

2. **Repository Activity**: For public repositories, if there's been no activity for 60 days, GitHub automatically suspends scheduled workflows. A new push will reactivate them.

3. **Schedule Timing**: All cron schedules use UTC time zone. 6:30 PM UTC converts to:
   - 12:00 AM IST (India Standard Time)
   - 10:30 AM PST / 1:30 PM EST (US)

4. **Testing**: To test changes without waiting for the schedule:
   - Use the "Run workflow" button in the Actions tab
   - Select the branch you want to test
   - Click "Run workflow"

5. **Why Not Every 5 Minutes**: Very frequent schedules can:
   - Be throttled or disabled by GitHub
   - Consume excessive Actions minutes
   - Create unnecessary commits
   - Not align with WPL match schedules

### Additional Resources
- [GitHub Actions Events - Schedule](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule)
- [Cron Syntax Help](https://crontab.guru/)
- [GitHub Actions Best Practices](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)

## Summary
✅ **Removed aggressive 5-minute schedule that could be throttled**  
✅ **Improved error handling in commit/push step**  
✅ **Kept reasonable daily schedule at 6:30 PM UTC**  
⚠️ **Scheduled runs require the workflow to be on the `main` branch**  
🔄 **Action Required: Merge this PR to `main` to enable scheduled runs**
