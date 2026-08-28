import json
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException

from utils import logger, GamePayload, PlayerState
from game_logic import compute_round_score, instantiate_active_players

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE_PATH = BASE_DIR / "data"

app = FastAPI()

###############################################################
# Actual code
###############################################################

# API endpoint to retrieve game data by game ID
@app.get("/games/{gameID}")
async def get_game_data(gameID: str):
    file_path = DATA_FILE_PATH / f"{gameID}.json"

    if not os.path.abspath(file_path).startswith(str(DATA_FILE_PATH)):
        raise HTTPException(status_code = 400, detail = "Invalid game ID.")

    if not os.path.exists(file_path):
        raise HTTPException(status_code = 404, detail = "Game data not found.")

    with open(file_path, "r") as file:
        data = json.load(file)

    return {
        "success": True,
        "message": "Game data retrieved successfully.",
        "gameData": data
    }


# API endpoint to update game data by game ID
@app.post("/games/{gameID}")
async def update_game_data(gameID: str, payload: GamePayload):
    file_path = DATA_FILE_PATH / f"{gameID}.json"

    logger.info(f"Received payload for game {gameID}: {payload}")

    if not os.path.abspath(file_path).startswith(str(DATA_FILE_PATH)):
        raise HTTPException(status_code = 400, detail = "Invalid game ID.")

    if not os.path.exists(file_path):
        raise HTTPException(status_code = 404, detail = "Game data not found.")

    # Load existing game data
    with open(file_path, "r") as file:
        existing_data = json.load(file)

    active_players = instantiate_active_players(payload.players, existing_data)
    logger.info(f"Working with these active players: {[(p.name, p.role) for p in active_players]}")
    round_scores = compute_round_score(active_players, payload.roundWonBy)
    
    logger.info(f"Computed round scores: {round_scores}")

    return {
        "success": True,
    }
