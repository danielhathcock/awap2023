from src.game_constants import RobotType, Direction, Team, TileState
from src.game_state import GameState, GameInfo
from src.player import Player
from src.map import TileInfo, RobotInfo
from src.robot import Robot
import random

class BotPlayer(Player):
    """
    Players will write a child class that implements (notably the play_turn method)
    """

    game_state : GameState = None
    game_info : GameInfo = None
    map_width : int = 0
    map_height : int = 0
    one_constructed = False

    def __init__(self, team: Team):
        self.team = team
        return

    def isvalid(self, row, col):
        if row < 0 : return False
        if row >= self.map_width : return False
        if col < 0 : return False
        if col >= self.map_height : return False
        return True

    def get_explorable_tiles(self, row, col) -> int:
        val : int = 0
        for d in Direction:
            if self.isvalid(row + d.value[0], col + d.value[1]):
                tile_info : TileInfo = self.game_info.map[row + d.value[0]][col + d.value[1]]
                if tile_info.state == TileState.ILLEGAL:
                    val += 1
        return val

    def explore_next(self, rname : str, robot : Robot) -> Direction:
        robot_info : RobotInfo = robot.info()
        robot_row = robot_info.row
        robot_col = robot_info.col
        val : int = 0
        d_options : list = []
        for d in Direction:
            if self.game_state.can_move_robot(rname, d):
                cur : int = self.get_explorable_tiles(robot_row + d.value[0], robot_col + d.value[1])
                if cur > val:
                    val = cur
                    d_options = []
                    d_options.append(d)
                    continue
                if cur == val:
                    d_options.append(d)
                    continue
        d_move = random.choice(d_options)
        self.game_state.move_robot(rname, d_move)

    def play_turn(self, game_state: GameState) -> None:
        self.game_state = game_state
        self.game_info = game_state.get_info()
        self.map_width = len(self.game_info.map)
        self.map_height = len(self.game_info.map[0])

        ally_tiles = []
        for row in range(map_height):
            for col in range(map_width):
                # get the tile at (row, col)
                tile = self.game_info.map[row][col]
                # skip fogged tiles
                if tile is not None: # ignore fogged tiles
                    if tile.robot is None: # ignore occupied tiles
                        if tile.terraform > 0: # ensure tile is ally-terraformed
                            ally_tiles += [tile]

        for spawn_loc in ally_tiles:
            if self.one_constructed:
                break
            spawn_type = RobotType.EXPLORER
            if game_state.can_spawn_robot(spawn_type, spawn_loc.row, spawn_loc.col):
                game_state.spawn_robot(spawn_type, spawn_loc.row, spawn_loc.col)
                self.one_constructed = True
        return 
