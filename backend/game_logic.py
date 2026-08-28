from utils import Role, Winners, PlayerState, logger, Player
from typing import Dict


def instantiate_active_players(incoming_payload: Dict[str, PlayerState], saved_data: dict) -> list[Player]:
    '''
    Instantiate active players based on the incoming payload and saved data.
    '''
    # Create a mapping of saved players for quick lookup
    saved_players_map = {p["id"]: p for p in saved_data.get("players", [])}
    
    active_players = []
    
    # Iterate through the incoming payload to instantiate active players
    for name, state in incoming_payload.items():
        if not state.active:
            continue
            
        # Retrieve saved player info if available
        saved_info = saved_players_map.get(name, {})
        
        # Key mapping for class constructor
        kwargs = {
            "name": name,
            "role": state.role,
            "score": saved_info.get("points", 0.0), # mapping 'points' -> 'score'
            "rank": saved_info.get("rank", -1)
        }
        
        active_players.append(Player(kwargs))
        
    return active_players


def compute_round_score(players: list[Player], winners: int) -> dict[str, float]:

    # Constants
    k = 2.2 # Empirical estimate of (lupo / buono) power ratio 
    N = len(players)
    V = sum([1 for p in players if p.role == Role.BUONO])
    L = sum([1 for p in players if p.role == Role.LUPO])
    alpha = (L * k) / V # Lupi advantage factor

    logger.info(f"Alpha: {alpha} - (the lesser the stronger is the Buoni)")

    criceto_bitten = True if any(p.role == Role.CRIC_CONVERTITO for p in players) else False

    # If alpha < 1: Lupi should be theoretically weaker than Buoni
    # If alpha ~1: Lupi and Buoni should be theoretically balanced
    # If alpha > 1: Lupi should be theoretically stronger than Buoni
    
    raw_scores = {}

    # Compute raw scores based on the winner and player roles
    for p in players:
        if winners == 2:  # Folle wins
            raw_scores[p.name] = (N / 3) if p.role == Role.FOLLE else -1.0
            continue

        # Else (Buoni vs Lupi)
        if p.role == Role.FOLLE:
            raw_scores[p.name] = -1.0
            continue

        if p.role == Role.CRIC_NON_CONVERTITO or p.role == Role.CRIC_CONVERTITO:
            if not criceto_bitten and winners == Winners.BUONI:
                raw_scores[p.name] = 2 * alpha
            elif criceto_bitten and winners == Winners.LUPI:
                raw_scores[p.name] = 1 / alpha
            else:
                raw_scores[p.name] = - (1 / k) if winners == Winners.LUPI else -k 
            continue

        if winners == Winners.BUONI:
            raw_scores[p.name] = alpha if p.role == Role.BUONO else -k
        elif winners == Winners.LUPI:
            raw_scores[p.name] = (1 / alpha) if p.role == Role.LUPO else -(1 / k)

    # Normalize scores to a zero-sum distribution
    total_raw = sum(raw_scores.values())
    shift = total_raw / N
    
    final_scores = {name: score - shift for name, score in raw_scores.items()}

    return final_scores