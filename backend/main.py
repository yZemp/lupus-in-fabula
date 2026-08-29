import json
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException

from utils import Winners, logger, GamePayload, NewGamePayload, NewPlayerPayload
from game_logic import compute_round_score, instantiate_players, create_new_game, update_save_file, add_new_player

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

    active_players = instantiate_players(payload.players, existing_data)
    logger.info(f"Working with these active players: {[(p.name, p.role) for p in active_players]}")
    round_scores, alpha = compute_round_score(active_players, payload.roundWonBy)
    
    logger.info(f"Computed round scores: {round_scores}")
    logger.info(f"Computed alpha: {alpha}")
    logger.info(f"Writing data to {file_path} with winner: {Winners(payload.roundWonBy).name}")

    update_save_file(file_path, round_scores, payload.roundWonBy, payload.players, alpha)

    return {
        "success": True,
        "message": "Game data updated successfully."
    }


# API endpoint to create a new game by game ID
@app.post("/games/{gameID}/create")
async def create_game(gameID: str, payload: NewGamePayload):
    file_path = DATA_FILE_PATH / f"{gameID}.json"
    
    try:
        create_new_game(file_path, gameID, payload.playerNames)
        return {"success": True, "message": f"New game {gameID} created."}
    except FileExistsError as e:
        raise HTTPException(status_code = 409, detail = str(e))



# API endpoint to add a new player to an existing game by game ID
@app.post("/games/{gameID}/add_player")
async def api_add_player(gameID: str, payload: NewPlayerPayload):
    file_path = DATA_FILE_PATH / f"{gameID}.json"

    if not os.path.abspath(file_path).startswith(str(DATA_FILE_PATH)):
        raise HTTPException(status_code = 400, detail = "Invalid game ID.")

    if not os.path.exists(file_path):
        raise HTTPException(status_code = 404, detail = "Game data not found.")

    try:
        add_new_player(file_path, payload.playerName, active = True)
        return {"success": True, "message": f"New player {payload.playerName} added to game {gameID}."}
    except FileExistsError as e:
        raise HTTPException(status_code = 409, detail = str(e))