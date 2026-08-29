from datetime import datetime
import json
import math
from pathlib import Path
from utils import Role, Winners, PlayerState, logger, Player
from typing import Dict, List


def instantiate_players(incoming_payload: Dict[str, PlayerState], saved_data: dict) -> list[Player]:
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



def compute_round_score(players: list[Player], winner: int) -> tuple[dict[str, float], float]:

    # Constants
    k = 2.8 # Empirical estimate of (lupo / buono) power ratio k = 2.8
    P = 10 # Base points
     
    N = len(players)
    V = sum(1 for p in players if p.role == Role.BUONO)
    L = sum(1 for p in players if p.role == Role.LUPO)
    alpha = (L * k) / V  # Theoretical power ratio of Lupi to Buoni
    logger.info(f"Alpha: {alpha} - (the lesser the stronger is the Buoni)")

    # If alpha < 1: Lupi should be theoretically weaker than Buoni
    # If alpha ~1: Lupi and Buoni should be theoretically balanced
    # If alpha > 1: Lupi should be theoretically stronger than Buoni

    # Probabilities of winning for Buoni and Lupi based on alpha and k
    deltas = {}

    for player in players:
        if winner == Winners.PATTA:
            deltas[player.name] = 0.0
            continue

        if winner == Winners.BUONI:
            if player.role == Role.BUONO or player.role == Role.CRIC_NON_CONVERTITO:
                deltas[player.name] = P * alpha
            elif player.role == Role.LUPO or player.role == Role.CRIC_CONVERTITO:
                deltas[player.name] = - P * alpha
            elif player.role == Role.FOLLE:
                deltas[player.name] = - P / 10

            # Bonus points for Cric non convertito if Buoni win
            if player.role == Role.CRIC_NON_CONVERTITO:
                deltas[player.name] = deltas[player.name] + P / 2

        if winner == Winners.LUPI:
            if player.role == Role.LUPO or player.role == Role.CRIC_CONVERTITO:
                deltas[player.name] = P / alpha
            elif player.role == Role.BUONO or player.role == Role.CRIC_NON_CONVERTITO:
                deltas[player.name] = - P / alpha
            elif player.role == Role.FOLLE:
                deltas[player.name] = - P / 10

        if winner == Winners.FOLLE:
            if player.role == Role.FOLLE:
                deltas[player.name] = 2 * P * math.log(N)
            else:
                deltas[player.name] = - P / 2

    return (deltas, alpha)


def update_save_file(file_path: Path, score_deltas: Dict[str, float], winner: int, payload_players: Dict[str, PlayerState], alpha: float):
    with open(file_path, "r") as file:
        data = json.load(file)

    # Update the round count
    data["rounds"] += 1
    current_round = data["rounds"]

    # Mapping saved players for O(1) lookup
    saved_players_map = {p["id"]: p for p in data["players"]}

    # Upsert players based on the incoming payload
    for pid, state in payload_players.items():
        if pid not in saved_players_map:
            raise ValueError(f"Player {pid} not found in saved data. This should not happen. You fucked up somewhere.")
        else:
            # Correct: update active status
            saved_players_map[pid]["active"] = state.active

    # Update all player scores with delta and total points
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
        "alpha": alpha,
        "scores": {p["id"]: p["points"] for p in data["players"]},
        "deltas": {p["id"]: p.get("delta", 0.0) for p in data["players"]},
        "winner": str(Winners(winner).name),
        "date": datetime.now().isoformat(),
        "active": {p["id"]: p.get("active", False) for p in data["players"]},
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
                "active": True,
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


def add_new_player(file_path: Path, player_name: str, active: bool) -> dict:
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

    # Add new player with initial score = median score of existing players or 0 if no players exist
    if data["players"]:
        existing_scores = [player["points"] for player in data["players"]]
        median_score = sorted(existing_scores)[len(existing_scores) // 2]
    else:
        median_score = 0.0

    new_player = {
        "id": player_name,
        "points": median_score,
        "delta": 0.0,
        "active": active
    }
    data["players"].append(new_player)

    # Write updated data back to file
    with open(file_path, "w") as file:
        json.dump(data, file, indent = 4)

    return new_player