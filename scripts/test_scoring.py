"""Quick test: compare WPL vs IPL scoring for the same player stats."""
from app.fantasy_calculator import calculate_fantasy_points

# Virat Kohli: 69 runs, 5 fours, 5 sixes, 38 balls, not out, 1 catch
stats = {
    'runs': 69, 'fours': 5, 'sixes': 5, 'balls_faced': 38,
    'is_out': False, 'position': 'Batter',
    'wickets': 0, 'dot_balls': 0, 'maidens': 0,
    'overs': 0, 'runs_conceded': 0, 'lbw_bowled': 0,
    'catches': 1, 'stumpings': 0,
    'run_outs_direct': 0, 'run_outs_indirect': 0,
}

for league in ['wpl', 'ipl']:
    result = calculate_fantasy_points(stats, played=True, league=league)
    print(f"=== {league.upper()} Scoring ===")
    print(f"Total: {result['total_points']} pts")
    for b in result['breakdown']:
        print(f"  {b}")
    print()

# Bowler: Jacob Duffy: 3 wickets, 4 overs, 22 runs conceded, 13 dots
bowler_stats = {
    'runs': 0, 'fours': 0, 'sixes': 0, 'balls_faced': 0,
    'is_out': False, 'position': 'Bowler',
    'wickets': 3, 'dot_balls': 13, 'maidens': 0,
    'overs': 4, 'runs_conceded': 22, 'lbw_bowled': 1,
    'catches': 0, 'stumpings': 0,
    'run_outs_direct': 0, 'run_outs_indirect': 0,
}

for league in ['wpl', 'ipl']:
    result = calculate_fantasy_points(bowler_stats, played=True, league=league)
    print(f"=== {league.upper()} Scoring (Bowler) ===")
    print(f"Total: {result['total_points']} pts")
    for b in result['breakdown']:
        print(f"  {b}")
    print()
