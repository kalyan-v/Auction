"""
Fantasy Points Calculator

Calculates fantasy points based on the scoring rules provided.
"""

from typing import Any, Dict, List, Tuple


class FantasyPointsCalculator:
    """Calculate fantasy points for cricket players based on match performance."""

    # ==================== BATTING POINTS ====================
    POINTS_PER_RUN: int = 1
    FOUR_BONUS: int = 4
    SIX_BONUS: int = 6
    RUNS_25_BONUS: int = 4
    RUNS_50_BONUS: int = 8
    RUNS_75_BONUS: int = 12
    RUNS_100_BONUS: int = 16
    DUCK_PENALTY: int = -2  # Excluding bowlers

    # Strike Rate bonuses/penalties (min 20 runs OR 10 balls)
    # Using exclusive upper bound approach: min <= value < max (except for last threshold)
    STRIKE_RATE_THRESHOLDS: List[Tuple[float, float, int]] = [
        (170, float('inf'), 6),    # 170+ : +6
        (150, 170, 4),             # 150-169.99 : +4
        (130, 150, 2),             # 130-149.99 : +2
        (70, 130, 0),              # 70-129.99 : 0
        (60, 70, -2),              # 60-69.99 : -2
        (50, 60, -4),              # 50-59.99 : -4
        (0, 50, -6),               # <50 : -6
    ]

    # ==================== BOWLING POINTS ====================
    DOT_BALL_BONUS: int = 1
    WICKET_POINTS: int = 30  # Except run-out
    MAIDEN_OVER_BONUS: int = 12
    LBW_BOWLED_BONUS: int = 8
    WICKET_3_HAUL_BONUS: int = 4
    WICKET_4_HAUL_BONUS: int = 8
    WICKET_5_HAUL_BONUS: int = 12

    # Economy Rate bonuses/penalties (min 2 overs)
    # Using exclusive upper bound approach: min <= value < max (except for last threshold)
    ECONOMY_RATE_THRESHOLDS: List[Tuple[float, float, int]] = [
        (0, 5, 6),                 # <5 : +6
        (5, 6, 4),                 # 5-5.99 : +4
        (6, 7, 2),                 # 6-6.99 : +2
        (7, 10, 0),                # 7-9.99 : 0
        (10, 11, -2),              # 10-10.99 : -2
        (11, 12, -4),              # 11-11.99 : -4
        (12, float('inf'), -6),    # 12+ : -6
    ]

    # ==================== FIELDING POINTS ====================
    CATCH_POINTS: int = 8
    CATCH_3_BONUS: int = 4
    STUMPING_POINTS: int = 12
    RUN_OUT_DIRECT_POINTS: int = 12
    RUN_OUT_INDIRECT_POINTS: int = 6  # Multiple players involved

    # ==================== OTHER POINTS ====================
    PLAYING_XI_BONUS: int = 4

    def __init__(self) -> None:
        """Initialize the calculator."""
        pass

    def calculate_batting_points(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate batting fantasy points.

        Args:
            stats: dict with keys:
                - runs: int
                - fours: int
                - sixes: int
                - balls_faced: int
                - is_out: bool
                - position: str (player position - Batter/Bowler/Allrounder/Keeper)

        Returns:
            dict with total_points and breakdown
        """
        points = 0
        breakdown: List[str] = []

        runs = stats.get('runs', 0)
        fours = stats.get('fours', 0)
        sixes = stats.get('sixes', 0)
        balls_faced = stats.get('balls_faced', 0)
        is_out = stats.get('is_out', False)
        position = stats.get('position', '').lower()

        # Base run points
        if runs > 0:
            points += runs * self.POINTS_PER_RUN
            breakdown.append(f"Runs ({runs}): {runs * self.POINTS_PER_RUN} pts")

        # Four bonus
        if fours > 0:
            four_points = fours * self.FOUR_BONUS
            points += four_points
            breakdown.append(f"Fours ({fours}): {four_points} pts")

        # Six bonus
        if sixes > 0:
            six_points = sixes * self.SIX_BONUS
            points += six_points
            breakdown.append(f"Sixes ({sixes}): {six_points} pts")

        # Milestone bonuses (cumulative - only highest applies)
        if runs >= 100:
            points += self.RUNS_100_BONUS
            breakdown.append(f"100 runs bonus: {self.RUNS_100_BONUS} pts")
        elif runs >= 75:
            points += self.RUNS_75_BONUS
            breakdown.append(f"75 runs bonus: {self.RUNS_75_BONUS} pts")
        elif runs >= 50:
            points += self.RUNS_50_BONUS
            breakdown.append(f"50 runs bonus: {self.RUNS_50_BONUS} pts")
        elif runs >= 25:
            points += self.RUNS_25_BONUS
            breakdown.append(f"25 runs bonus: {self.RUNS_25_BONUS} pts")

        # Duck penalty (excluding bowlers)
        if runs == 0 and is_out and position != 'bowler':
            points += self.DUCK_PENALTY
            breakdown.append(f"Duck: {self.DUCK_PENALTY} pts")

        # Strike rate bonus/penalty (min 20 runs OR 10 balls)
        if runs >= 20 or balls_faced >= 10:
            if balls_faced > 0:
                strike_rate = (runs / balls_faced) * 100
                sr_points = self._get_strike_rate_points(strike_rate)
                if sr_points != 0:
                    points += sr_points
                    breakdown.append(f"Strike rate ({strike_rate:.2f}): {sr_points:+d} pts")

        return {'points': points, 'breakdown': breakdown}

    def calculate_bowling_points(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate bowling fantasy points.

        Args:
            stats: dict with keys:
                - wickets: int
                - dot_balls: int
                - maidens: int
                - overs: float (e.g., 4.0 for 4 overs)
                - runs_conceded: int
                - lbw_bowled: int (wickets via LBW or bowled)

        Returns:
            dict with total_points and breakdown
        """
        points = 0
        breakdown: List[str] = []

        wickets = stats.get('wickets', 0)
        dot_balls = stats.get('dot_balls', 0)
        maidens = stats.get('maidens', 0)
        overs = stats.get('overs', 0)
        runs_conceded = stats.get('runs_conceded', 0)
        lbw_bowled = stats.get('lbw_bowled', 0)

        # Wicket points
        if wickets > 0:
            wicket_points = wickets * self.WICKET_POINTS
            points += wicket_points
            breakdown.append(f"Wickets ({wickets}): {wicket_points} pts")

        # Dot ball bonus
        if dot_balls > 0:
            dot_points = dot_balls * self.DOT_BALL_BONUS
            points += dot_points
            breakdown.append(f"Dot balls ({dot_balls}): {dot_points} pts")

        # Maiden over bonus
        if maidens > 0:
            maiden_points = maidens * self.MAIDEN_OVER_BONUS
            points += maiden_points
            breakdown.append(f"Maidens ({maidens}): {maiden_points} pts")

        # LBW/Bowled bonus
        if lbw_bowled > 0:
            lbw_points = lbw_bowled * self.LBW_BOWLED_BONUS
            points += lbw_points
            breakdown.append(f"LBW/Bowled ({lbw_bowled}): {lbw_points} pts")

        # Wicket haul bonuses
        if wickets >= 5:
            points += self.WICKET_5_HAUL_BONUS
            breakdown.append(f"5-wicket haul bonus: {self.WICKET_5_HAUL_BONUS} pts")
        elif wickets >= 4:
            points += self.WICKET_4_HAUL_BONUS
            breakdown.append(f"4-wicket haul bonus: {self.WICKET_4_HAUL_BONUS} pts")
        elif wickets >= 3:
            points += self.WICKET_3_HAUL_BONUS
            breakdown.append(f"3-wicket haul bonus: {self.WICKET_3_HAUL_BONUS} pts")

        # Economy rate bonus/penalty (min 2 overs)
        if overs >= 2:
            economy = runs_conceded / overs if overs > 0 else 0
            econ_points = self._get_economy_rate_points(economy)
            if econ_points != 0:
                points += econ_points
                breakdown.append(f"Economy rate ({economy:.2f}): {econ_points:+d} pts")

        return {'points': points, 'breakdown': breakdown}

    def calculate_fielding_points(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate fielding fantasy points.

        Args:
            stats: dict with keys:
                - catches: int
                - stumpings: int
                - run_outs_direct: int
                - run_outs_indirect: int

        Returns:
            dict with total_points and breakdown
        """
        points = 0
        breakdown: List[str] = []

        catches = stats.get('catches', 0)
        stumpings = stats.get('stumpings', 0)
        run_outs_direct = stats.get('run_outs_direct', 0)
        run_outs_indirect = stats.get('run_outs_indirect', 0)

        # Catch points
        if catches > 0:
            catch_points = catches * self.CATCH_POINTS
            points += catch_points
            breakdown.append(f"Catches ({catches}): {catch_points} pts")

            # 3 catch bonus
            if catches >= 3:
                points += self.CATCH_3_BONUS
                breakdown.append(f"3+ catches bonus: {self.CATCH_3_BONUS} pts")

        # Stumping points
        if stumpings > 0:
            stumping_points = stumpings * self.STUMPING_POINTS
            points += stumping_points
            breakdown.append(f"Stumpings ({stumpings}): {stumping_points} pts")

        # Run out points (direct)
        if run_outs_direct > 0:
            ro_direct_points = run_outs_direct * self.RUN_OUT_DIRECT_POINTS
            points += ro_direct_points
            breakdown.append(f"Run outs direct ({run_outs_direct}): {ro_direct_points} pts")

        # Run out points (indirect/assist)
        if run_outs_indirect > 0:
            ro_indirect_points = run_outs_indirect * self.RUN_OUT_INDIRECT_POINTS
            points += ro_indirect_points
            breakdown.append(f"Run outs assist ({run_outs_indirect}): {ro_indirect_points} pts")

        return {'points': points, 'breakdown': breakdown}

    def calculate_total_points(
        self,
        player_stats: Dict[str, Any],
        played: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate total fantasy points for a player.

        Args:
            player_stats: dict with all batting, bowling, and fielding stats
            played: bool - if player was in Playing XI

        Returns:
            dict with total_points, breakdown, and component scores
        """
        total_points = 0
        all_breakdown: List[str] = []

        # Playing XI bonus
        if played:
            total_points += self.PLAYING_XI_BONUS
            all_breakdown.append(f"Playing XI bonus: {self.PLAYING_XI_BONUS} pts")

        # Batting points
        batting = self.calculate_batting_points(player_stats)
        total_points += batting['points']
        all_breakdown.extend(batting['breakdown'])

        # Bowling points
        bowling = self.calculate_bowling_points(player_stats)
        total_points += bowling['points']
        all_breakdown.extend(bowling['breakdown'])

        # Fielding points
        fielding = self.calculate_fielding_points(player_stats)
        total_points += fielding['points']
        all_breakdown.extend(fielding['breakdown'])

        return {
            'total_points': total_points,
            'breakdown': all_breakdown,
            'batting_points': batting['points'],
            'bowling_points': bowling['points'],
            'fielding_points': fielding['points']
        }

    def _get_strike_rate_points(self, strike_rate: float) -> int:
        """Get points for strike rate."""
        for min_sr, max_sr, points in self.STRIKE_RATE_THRESHOLDS:
            # Use exclusive upper bound (min <= value < max) except for infinity
            if max_sr == float('inf'):
                if strike_rate >= min_sr:
                    return points
            elif min_sr <= strike_rate < max_sr:
                return points
        return 0

    def _get_economy_rate_points(self, economy: float) -> int:
        """Get points for economy rate."""
        for min_econ, max_econ, points in self.ECONOMY_RATE_THRESHOLDS:
            # Use exclusive upper bound (min <= value < max) except for infinity
            if max_econ == float('inf'):
                if economy >= min_econ:
                    return points
            elif min_econ <= economy < max_econ:
                return points
        return 0


# Create a singleton instance
calculator = FantasyPointsCalculator()


def calculate_fantasy_points(
    player_stats: Dict[str, Any],
    played: bool = True
) -> Dict[str, Any]:
    """Convenience function to calculate fantasy points."""
    return calculator.calculate_total_points(player_stats, played)
