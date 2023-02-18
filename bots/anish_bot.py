from src.game_constants import RobotType, Direction, Team, TileState
from src.game_state import GameState, GameInfo
from src.player import Player
from src.map import TileInfo, RobotInfo
from src.robot import Robot
import random
from collections import deque

class SpawnRequest:
    def __init__(self, status):
        self.name = None
        self.status = status
        # self.status = -1 -- failed
        # self.status = 0  -- waiting
        # self.status = 1  -- success

class BotPlayer(Player):
    """
    Players will write a child class that implements (notably the play_turn method)
    """

    def __init__(self, team: Team):
        self.team = team
        self.game_state : GameState = None
        self.game_info : GameInfo = None
        self.initial_setup = False
        self.width : int = 0
        self.height : int = 0
        self.metal : int = 0

        # Spawning stuff
        self.spawn_queue = set()
        self.spawn_complete = set()
        self.spawn_requests = 0

        # Moving stuff
        self.bot_move_queues = dict 
        return

    # Helper functions
    def get_tile_info(self, row, col) -> TileInfo :
        if row < 0 : return TileInfo(TileState.IMPASSABLE, 0, 0, 0, 0, None)
        if row >= self.width : return TileInfo(TileState.IMPASSABLE, 0, 0, 0, 0, None)
        if col < 0 : return TileInfo(TileState.IMPASSABLE, 0, 0, 0, 0, None)
        if col >= self.height : return TileInfo(TileState.IMPASSABLE, 0, 0, 0, 0, None)
        if self.tiles[row][col] == None: return TileInfo(TileState.ILLEGAL, 0, 0, 0, 0, None)
        return self.tiles[row][col]

    def request_spawn(self, row, col, rtype : RobotType) -> SpawnRequest:
        if self.get_tile_info(row,col).terraform < 1:
            return SpawnRequest(-1)
        req = SpawnRequest(0)
        self.spawn_queue.add((self.spawn_requests, row, col, rtype, req))
        self.spawn_requests += 1
        return req

    def try_spawn(self) -> None:
        for spawn_req in self.spawn_queue:
            if self.metal < 50:
                break
            if self.game_state.can_spawn_robot(spawn_req[3], spawn_req[1], spawn_req[2]) :
                spawn_req[4].name = self.game_state.spawn_robot(spawn_req[3], spawn_req[1], spawn_req[2]).name
                spawn_req[4].status = 1
                self.spawn_complete.add(spawn_req)
                self.spawn_queue.pop(spawn_req)

    def request_move(self, rname, rinfo : RobotInfo, )

    # Precomputations and runtime updates
    def update_cache(self):
        '''Update global variables to save data'''
        self.game_info = self.game_state.get_info()
        self.tiles = self.game_info.map
        self.metal = self.game_info.metalt 


    def initial_cache(self):
        '''Varianles that need to be updated one time'''
        if self.initial_setup: return
        self.initial_setup = True

        self.height = len(self.game_info.map)
        self.width = len(self.game_info.map[0])
        self.total_tiles = self.height * self.width
