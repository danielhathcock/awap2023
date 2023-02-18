from src.game_constants import RobotType, Direction, Team, TileState
from src.game_state import GameState, GameInfo
from src.player import Player
from src.map import TileInfo, RobotInfo
from src.robot import Robot
import random
from collections import deque

class BotPlayer(Player):
    """
    Players will write a child class that implements (notably the play_turn method)
    """

    def __init__(self, team: Team):
        self.team = team
        self.game_state : GameState = None
        self.game_info : GameInfo = None
        self.width : int = 0
        self.height : int = 0
        return

    def get_tile_style(self, row, col) -> TileInfo :
        if row < 0 : return TileInfo(TileState.ILLEGAL, 0, 0, 0, 0, None)
        if row >= self.width : return TileInfo(TileState.ILLEGAL, 0, 0, 0, 0, None)
        if col < 0 : return TileInfo(TileState.ILLEGAL, 0, 0, 0, 0, None)
        if col >= self.height : return TileInfo(TileState.ILLEGAL, 0, 0, 0, 0, None)
        return self.tiles[row][col]

    def update_cache(self):
        '''Update global variables to save data'''
        self.game_info = self.game_state.get_info()
        self.height = len(self.game_info.map)
        self.width = len(self.game_info.map[0])
        self.total_tiles = self.height * self.width
        self.tiles = self.game_info.map

        # Stuff for exploration bot
        self.explore_prio = []
        for row in range(self.height):
            row_prio = []
            for col in range(self.width):
                row_prio.append(0.0)
            self.explore_prio.append(row_prio)

    def unexplored_bfs(self, row, col, threshold):
        if self.tiles[row][col] != None:
            return None
        retList = []
        vis = {(row,col)}
        queue = deque((row, col, 0))
        while(queue):
            qr, qc, m = queue.popleft()
            retList.append((qr,qc,m))
            if(m == threshold):
                continue
            for d in Direction:
                nr, nc = qr + d.value[0], qc + d.value[1]
                if vis.__contains__((nr,nc)):
                    continue
                if self.get_tile_style(nr,nc).state == TileState.ILLEGAL:
                    queue.append((nr,nc,m+1))
                    vis.add((nr,nc))
        return retList
        

    def add_prio(self, row, col, val):
        ratio = 0.5
        dist = 5
        updates = self.unexplored_bfs(row, col, dist)
        for cur in updates:
            r, c, d = cur
            self.explore_prio[r][c] += val * pow(ratio, d)
                

    def get_explorable_tiles(self, row, col) -> int:
        val : int = 0
        for d in Direction:
            if self.isvalid(row + d.value[0], col + d.value[1]):
                tile_info : TileInfo = self.game_info.map[row + d.value[0]][col + d.value[1]]
                if tile_info.state == TileState.ILLEGAL:
                    val += 1
        return val

    def explore_next(self, rname : str, robot : Robot) -> Direction:
        '''Perform the best move action for an explorer'''
        robot_info : RobotInfo = robot.info()
        robot_row = robot_info.row
        robot_col = robot_info.col
        val : int = 0
        d_options : list = []
        for d in Direction:
            if self.game_state.can_move_robot(rname, d):
                cur : int = self.get_explorable_tiles(robot_row + d.value[0], robot_col + d.value[1])
                if cur > val and self.game_state.get_map()[robot_row+d.value[0]][robot_col+d.value[1]].robot is None:
                    val = cur
                    d_options = []
                    d_options.append(d)
                    continue
                if cur == val and self.game_state.get_map()[robot_row+d.value[0]][robot_col+d.value[1]].robot is None:
                    d_options.append(d)
                    continue
        d_move = random.choice(d_options)
        self.game_state.move_robot(rname, d_move)
        if self.game_state.can_robot_action(rname):
            self.game_state.robot_action(rname)

    def explore_action(self, game_state: GameState) -> None:
        '''Perform one move/action sequence for each of the explore/terraform pairs'''
        print(self.et_pairs)
        for exp, ter in self.et_pairs:
            if exp.battery == 0:
                # Recharge sequence
                for d in Direction:
                    dest_row = ter.row + d.value[0]
                    dest_col = ter.col + d.value[1]
                    if game_state.can_move_robot(ter.name, d) and game_state.get_map()[dest_row][dest_col].robot is None:
                        game_state.move_robot(ter.name, d)
                        if game_state.can_robot_action(ter.name):
                            game_state.robot_action(ter.name)
                        game_state.move_robot(exp.name, Direction((ter.row - exp.row, ter.col - exp.col)))
                        break
            
            else:
                # Explore sequence
                old_exp_row, old_exp_col = (exp.row, exp.col)
                self.explore_next(exp.name, exp)

                # Move Terraformer to the previous location of the explorer
                game_state.move_robot(ter.name, Direction((old_exp_row - ter.row, old_exp_col - ter.col)))
                if game_state.can_robot_action(ter.name):
                    game_state.robot_action(ter.name)   

    def play_turn(self, game_state: GameState) -> None:
        self.game_state = game_state
        self.update_cache()

        # print info about the game
        print(f"Turn {self.game_info.turn}, team {self.game_info.team}")
        print("Map height", self.height)
        print("Map width", self.width)

        ally_tiles = []
        for row in range(self.height):
            for col in range(self.width):
                # get the tile at (row, col)
                tile = self.game_info.map[row][col]
                # skip fogged tiles
                if tile is not None: # ignore fogged tiles
                    if tile.robot is None: # ignore occupied tiles
                        if tile.terraform > 0: # ensure tile is ally-terraformed
                            ally_tiles += [tile]

        print(f"My metal {game_state.get_metal()}")
        robots = game_state.get_ally_robots()

        # Refresh RobotInfo objects in et_pairs.
        # TODO: check if any of our robots in here were destroyed
        for i in range(len(self.et_pairs)):
            exp, ter = self.et_pairs[i]
            self.et_pairs[i] = (robots[exp.name], robots[ter.name])

        if self.construct_state == 0:
            for spawn_loc in ally_tiles:
                if self.construct_state > 0:
                    break
                spawn_type = RobotType.EXPLORER
                if game_state.can_spawn_robot(spawn_type, spawn_loc.row, spawn_loc.col):
                    game_state.spawn_robot(spawn_type, spawn_loc.row, spawn_loc.col)
                    self.construct_state = 1

        elif self.construct_state == 1:
            exp_name, exp = list(robots.items())[0]
            self.explore_next(exp_name, exp)

            if game_state.can_spawn_robot(RobotType.TERRAFORMER, exp.row, exp.col):
                new_ter = game_state.spawn_robot(RobotType.TERRAFORMER, exp.row, exp.col)
                self.construct_state = 2
                self.et_pairs.append((exp, new_ter))

            print(self.et_pairs)
        else:
            self.explore_action(game_state)

        # iterate through dictionary of robots
        for rname, rob in game_state.get_ally_robots().items():
            print(f"Robot {rname} at {rob.row, rob.col}")
        return 
