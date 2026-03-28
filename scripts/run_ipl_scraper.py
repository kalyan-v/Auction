"""Run IPL scraper and display all player fantasy points."""
from app.scrapers import get_scraper, ScraperType
from app.fantasy_calculator import calculate_fantasy_points

scraper = get_scraper(ScraperType.IPL)
urls = scraper.get_all_match_urls()
print("Completed matches:", urls.get("count", 0))

for match in urls.get("matches", []):
    print(f"\n{'='*60}")
    print(f"Match: {match['match_name']}")
    print(f"Date:  {match['date']}")

    result = scraper.scrape_match_scorecard(match["url"])
    if not result.success:
        print("FAILED:", result.error)
        continue

    mi = result.match_info
    print(f"Teams: {mi.home_team} vs {mi.away_team}")
    print(f"{'='*60}\n")

    # Calculate and sort by fantasy points
    player_results = []
    for name, stats in result.player_stats.items():
        sd = stats.to_dict()
        fp = calculate_fantasy_points(sd, played=True, league="ipl")
        player_results.append((name, fp["total_points"], sd, fp["breakdown"]))

    player_results.sort(key=lambda x: x[1], reverse=True)

    print(f"{'Player':<25} {'Pts':>5}  Performance")
    print(f"{'-'*25} {'---':>5}  {'-'*35}")

    for name, pts, sd, breakdown in player_results:
        parts = []
        r = sd.get("runs", 0)
        b = sd.get("balls_faced", 0)
        if r > 0 or b > 0:
            out = "" if not sd.get("is_out") else ""
            not_out = "*" if not sd.get("is_out") and b > 0 else ""
            parts.append(f"{r}{not_out}({b}b)")
            f4 = sd.get("fours", 0)
            f6 = sd.get("sixes", 0)
            if f4 or f6:
                parts.append(f"{f4}x4 {f6}x6")

        w = sd.get("wickets", 0)
        o = sd.get("overs", 0)
        rc = sd.get("runs_conceded", 0)
        if w > 0 or o > 0:
            parts.append(f"{w}/{rc} ({o}ov)")

        c = sd.get("catches", 0)
        if c > 0:
            parts.append(f"{c}ct")
        st = sd.get("stumpings", 0)
        if st > 0:
            parts.append(f"{st}st")
        rod = sd.get("run_outs_direct", 0)
        roi = sd.get("run_outs_indirect", 0)
        if rod > 0:
            parts.append(f"{rod}ro(d)")
        if roi > 0:
            parts.append(f"{roi}ro(i)")
        lbw = sd.get("lbw_bowled", 0)
        if lbw > 0:
            parts.append(f"{lbw}lbw/b")

        perf = ", ".join(parts)
        print(f"{name:<25} {pts:>5}  {perf}")

    print(f"\n{'Player':<25} {'Pts':>5}  Points Breakdown")
    print(f"{'-'*25} {'---':>5}  {'-'*35}")
    for name, pts, sd, breakdown in player_results:
        bd = " | ".join(breakdown)
        print(f"{name:<25} {pts:>5}  {bd}")
