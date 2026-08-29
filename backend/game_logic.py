from datetime import datetime
import json
from pathlib import Path
from utils import Role, Winners, PlayerState, logger, Player
from typing import Dict, List


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
        if winners == Winners.FOLLE:
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


def update_save_file(file_path: Path, score_deltas: Dict[str, float], winner: int):

    with open(file_path, "r") as file:
        data = json.load(file)

    # Update the round count
    data["rounds"] += 1
    current_round = data["rounds"]

    # Update player scores with delta and total points
    for player in data["players"]:
        pid = player["id"]
        if pid in score_deltas:
            player["points"] = round(player["points"] + score_deltas[pid], 4)
            player["delta"] = round(score_deltas[pid], 4)
        else:
            player["delta"] = 0.0  # Delta = 0 for inactive players

    # Add new entry to score history for the current round
    history_entry = {
        "round": current_round,
        "scores": {p["id"]: p["points"] for p in data["players"]},
        "deltas": {p["id"]: p.get("delta", 0.0) for p in data["players"]},
        "winner": str(Winners(winner).name),
        "date": datetime.now().isoformat()
    }
    data["scoreHistory"].append(history_entry)

    # Write data
    with open(file_path, "w") as file:
        json.dump(data, file, indent = 4)



def create_new_game(file_path: Path, game_id: str, player_names: List[str]) -> dict:
    '''
    Init new game with the specified player names.
    Raises FileExistsError if the game already exists.
    '''

    if file_path.exists():
        raise FileExistsError(f"Game {game_id} already exists.")

    file_path.parent.mkdir(parents = True, exist_ok = True)

    initial_data = {
        "id": game_id,
        "annotations": None,
        "players": [
            {
                "id": name,
                "points": 0.0,
                "delta": 0.0,
            } for name in player_names
        ],
        "rounds": 0,
        "scoreHistory": [
            {
                "round": 0,
                "winner": None
            }
        ]
    }

    with open(file_path, "w") as file:
        json.dump(initial_data, file, indent = 4)
        
    return initial_data


def add_new_player(file_path: Path, player_name: str) -> dict:
    '''
    Add a new player to an existing game.
    Raises FileNotFoundError if the game does not exist.
    Raises ValueError if the player already exists.
    '''

    if not file_path.exists():
        raise FileNotFoundError(f"Game data for {file_path.stem} not found.")

    with open(file_path, "r") as file:
        data = json.load(file)

    # Check if player already exists
    if any(player["id"] == player_name for player in data["players"]):
        raise ValueError(f"Player {player_name} already exists in the game.")

    # Add new player
    new_player = {
        "id": player_name,
        "points": 0.0,
        "delta": 0.0,
    }
    data["players"].append(new_player)

    # Write updated data back to file
    with open(file_path, "w") as file:
        json.dump(data, file, indent = 4)

    return new_player