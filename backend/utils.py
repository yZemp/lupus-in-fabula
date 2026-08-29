from typing import Dict
from pydantic import BaseModel
from enum import Enum
import logging
import sys

KONST = 2.8 # Empirical estimate of (lupo / buono) power ratio k = 2.8
BASE_POINTS = 10 # Base points

class Role(int, Enum):
    BUONO = 0
    LUPO = 1
    FOLLE = 2
    CRIC_NON_CONVERTITO = 3
    CRIC_CONVERTITO = 4

class Winners(int, Enum):
    BUONI = 0
    LUPI = 1
    FOLLE = 2
    PATTA = 3

class NewGamePayload(BaseModel):
    playerNames: list[str]

class NewPlayerPayload(BaseModel):
    playerName: str

class PlayerState(BaseModel):
    active: bool
    role: int
    
class GamePayload(BaseModel):
    players: Dict[str, PlayerState]
    roundWonBy: int

class Player:
    '''
    Represents a player in the game with a name, role, and score.
    NOTE: Only active players in the round are supposed to be instantiated.
    '''
    def __init__(self, kwargs):
        self.name = kwargs.get("name", "")
        self.role = kwargs.get("role", -1)
        self.score = kwargs.get("score", 0.)
        self.rank = kwargs.get("rank", -1)


# Logger config
logging.basicConfig(
    stream = sys.stdout,
    level = logging.INFO,
    format = "%(levelname)s:\t  %(message)s"
)
logger = logging.getLogger(__name__)
logger.info("Logger initialized and writing to stdout.")

