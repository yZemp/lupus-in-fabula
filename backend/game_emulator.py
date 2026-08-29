import asyncio
import numpy as np
import random
from matplotlib import pyplot as plt
import matplotlib.colors as mcolors

from utils import KONST, Role, Winners, PlayerState, logger, Player

from utils import GamePayload, NewGamePayload, PlayerState
from main import create_game, update_game_data, get_game_data

GAME_ID = "toy"
NUMBER_OF_PLAYERS = 15

async def emulate_game(gameID: str, game_len: int, player_number: int, seed: int | None = None):
    '''
    Emulate an entire game of game_len rounds with the specified players.
    '''

    if seed is not None:
        random.seed(seed)

    # Create a new game with the specified players
    player_names = [f"Player {i + 1}" for i in range(player_number)]
    newGamePayload = NewGamePayload(playerNames = player_names)
    await create_game(gameID = gameID, payload = newGamePayload)

    for round_num in range(game_len):
        # Set roles for each players following these constraints:
        # - 1 FOLLE
        # - 1 CRIC_NON_CONVERTITO or 1 CRIC_CONVERTITO
        # - V BUONI and L LUPI, where V + L = player_number - 2, and V, L minimize abs(alpha - 1)
        roles = [Role.FOLLE]
        if random.choice([True, False]):
            roles.append(Role.CRIC_NON_CONVERTITO)
        else:
            roles.append(Role.CRIC_CONVERTITO)
        V, L = optimize_parameters(player_number)
        roles.extend([Role.BUONO] * V)
        roles.extend([Role.LUPO] * L)

        random.shuffle(roles)
        players = {name: PlayerState(active = True, role = role.value) for name, role in zip(player_names, roles)}

        # Randomly determine the winner of the round with the following probabilities:
        # - If alpha < 1: Buoni have a higher chance of winning
        # - If alpha ~ 1: Buoni and Lupi have an equal chance of winning
        # - If alpha > 1: Lupi have a higher chance of winning
        # - Folle always has 5% chance of winning, regardless of alpha
        # - Every game has a 5% chance of ending in PATTA, regardless of alpha

        alpha = (L * KONST) / V
        logger.info(f"Round {round_num + 1}: V = {V}, L = {L}, alpha = {alpha}")

        winner = random.choices(
            population = [Winners.BUONI, Winners.LUPI, Winners.FOLLE, Winners.PATTA],
            weights = [0.475 if alpha < 1 else 0.25, 0.475 if alpha > 1 else 0.25, 0.05, 0.05],
            k = 1
        )[0]

        # Update the game data for this round
        payload = GamePayload(players = players, roundWonBy = winner.value)
        await update_game_data(gameID = gameID, payload = payload)


def optimize_parameters(N: int) -> tuple[int, int]:
    '''
    Compute V, L so to minimize abs(alpha - 1) given N players, where V + L = N - 2 and alpha = (L * k) / V.
    '''

    V_ideal = (KONST * (N - 2)) / (KONST + 1)    
    V = round(V_ideal)
    
    if V == 0:
        V = 1
        
    L = (N - 2) - V
    
    return V, L

def analyze_game(gameID: str):
    '''
    Analyze the game data for the specified game ID and print the results.
    '''

    # Retrieve the game data
    game_data = asyncio.run(get_game_data(gameID = gameID))
    
    if not game_data["success"]:
        logger.error(f"Failed to retrieve game data for {gameID}: {game_data['message']}")
        return

    data = game_data["gameData"]

    total_delta = sum([r["mean_delta"] for r in data["scoreHistory"]])
    total_mean_delta = total_delta / data["rounds"] if data["rounds"] > 0 else 0.0

    logger.info(f"Game {gameID} analysis:")
    logger.info(f"Total delta and mean delta: {total_delta, total_mean_delta}")

    # Plot score averages over rounds
    rs = np.arange(0, data["rounds"] + 1)
    avgs = [sum(r["scores"].values()) / len(r["scores"]) if len(r["scores"]) > 0 else 0.0 for r in data["scoreHistory"]]
    maxs = [max(r["scores"].values()) if len(r["scores"]) > 0 else 0.0 for r in data["scoreHistory"]]
    mins = [min(r["scores"].values()) if len(r["scores"]) > 0 else 0.0 for r in data["scoreHistory"]]

    logger.info(f"Rounds: {len(rs)}, Averages: {len(avgs)}, Maxs: {len(maxs)}, Mins: {len(mins)}")

    cmap = plt.get_cmap("managua")
    norm = mcolors.Normalize(vmin = min(rs), vmax = max(rs))

    plt.figure(figsize = (10, 6))

    for i in range(len(rs) - 1):
        color = cmap(norm(rs[i]))
        plt.plot(rs[i:i+2], avgs[i:i+2], color = color, linewidth = 2)
        plt.fill_between(rs[i:i+2], mins[i:i+2], maxs[i:i+2], color = color, alpha = 0.3)

    plt.title(f"Analysis - $\\alpha = {data["scoreHistory"][-1]["alpha"]:.3f}$, number of players = {len(data["players"])}")

    plt.grid(True, which = "both", linestyle = "--", linewidth = 0.5)
    plt.xlabel("Round")
    plt.ylabel("Average Score")

    plt.savefig(f"data/game_{gameID}_analysis.png")


def emulate(gameID: str, game_len: int, player_number: int, seed: int | None = None):
    asyncio.run(emulate_game(gameID = gameID, game_len = game_len, player_number = player_number, seed = seed))
    
def analyze(gameID: str):
    analyze_game(gameID = gameID)


if __name__ == "__main__":
    for player_number in range(12, 21):    
        game_len = 100
        seed = 0
        gameID = GAME_ID + "" + str(player_number) + "_" + str(game_len)
        emulate(gameID = gameID, game_len = game_len, player_number = player_number, seed = 0)
        analyze(gameID = gameID)