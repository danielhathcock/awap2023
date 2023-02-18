from src.game_constants import RobotType, Direction, Team, TileState
from src.game_state import GameState, GameInfo
from src.player import Player
from src.map import TileInfo, RobotInfo
import random

class BotPlayer(Player):
    """
    Players will write a child class that implements (notably the play_turn method)
    """

    def __init__(self, team: Team):
        self.team = team

        self.game_state = None
        self.game_info = None
        self.map_width = None
        self.map_height = None

        self.et_pairs : list[tuple[RobotInfo, RobotInfo]] = []
        self.creating_pair = 0

        self.assigned_mines = set()

        self.new_exp = None

        return



    def no_collision(self, row, col):
        return self.game_state.get_map()[row][col].robot is None

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
                if tile_info is None:
                    val += 1
        return val

    def explore_next(self, rname : str, robot_info : RobotInfo) -> Direction:
        '''Perform the best move action for an explorer'''
        robot_row = robot_info.row
        robot_col = robot_info.col
        val : int = 0
        d_options : list = []
        for d in Direction:
            if self.game_state.can_move_robot(rname, d) and self.no_collision(robot_row+d.value[0], robot_col+d.value[1]):
                cur : int = self.get_explorable_tiles(robot_row + d.value[0], robot_col + d.value[1])
                if cur > val:
                    val = cur
                    d_options = []
                    d_options.append(d)
                    continue
                if cur == val:
                    d_options.append(d)
                    continue
        if len(d_options) > 0:
            d_move = random.choice(d_options)
            self.game_state.move_robot(rname, d_move)
            if self.game_state.can_robot_action(rname):
                self.game_state.robot_action(rname)
            return d_move


    def explore_action(self, game_state: GameState) -> None:
        '''Perform one move/action sequence for each of the explore/terraform pairs'''
        # print(self.et_pairs)
        for exp, ter in self.et_pairs:
            if exp.battery == 0:
                # Recharge sequence
                for d in Direction:
                    dest_row = ter.row + d.value[0]
                    dest_col = ter.col + d.value[1]
                    if game_state.can_move_robot(ter.name, d) and self.no_collision(dest_row,dest_col):
                        game_state.move_robot(ter.name, d)
                        if game_state.can_robot_action(ter.name):
                            game_state.robot_action(ter.name)
                        game_state.move_robot(exp.name, Direction((ter.row - exp.row, ter.col - exp.col)))
                        break
            
            else:
                # Explore sequence
                old_exp_row, old_exp_col = (exp.row, exp.col)
                d_move = self.explore_next(exp.name, exp)

                # Move Terraformer to the previous location of the explorer
                if d_move is not None:
                    game_state.move_robot(ter.name, Direction((old_exp_row - ter.row, old_exp_col - ter.col)))
                if game_state.can_robot_action(ter.name):
                    game_state.robot_action(ter.name)   


    def nearest_terr_tile(self, row, col):
        '''get nearest terraformed tile (dummy)'''
        return (0, 0)

    def create_et_pair(self, row, col):
        '''Create a pair nearest to row, col'''
        if self.creating_pair == 0:
            self.creating_pair = 1

        if self.creating_pair == 1 and self.game_state.get_metal() >= 50:
            nearest = self.nearest_terr_tile(row, col)
            



    def play_turn(self, game_state: GameState) -> None:

        self.game_state = game_state
        self.game_info = game_state.get_info()
        self.map_width = len(self.game_info.map)
        self.map_height = len(self.game_info.map[0])

        # get info
        ginfo = game_state.get_info()

        # get turn/team info
        height, width = len(ginfo.map), len(ginfo.map[0])

        # print info about the game
        print(f"Turn {ginfo.turn}, team {ginfo.team}")
        print("Map height", height)
        print("Map width", width)

        # find un-occupied ally tile
        ally_tiles = []
        for row in range(height):
            for col in range(width):
                # get the tile at (row, col)
                tile = ginfo.map[row][col]
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

        self.explore_action(game_state)

        
        if self.creating_pair != 0:
            self.create_et_pair()
        
        
        if self.construct_state == 0 and self.game_info.metal >= 100:
            for spawn_loc in ally_tiles:
                if self.construct_state > 0:
                    break
                spawn_type = RobotType.EXPLORER
                if game_state.can_spawn_robot(spawn_type, spawn_loc.row, spawn_loc.col):
                    self.new_exp = game_state.spawn_robot(spawn_type, spawn_loc.row, spawn_loc.col)
                    self.construct_state = 1

        elif self.construct_state == 1:
            exp_name, exp = self.new_exp.name, robots[self.new_exp.name]
            self.explore_next(exp_name, exp)

            if game_state.can_spawn_robot(RobotType.TERRAFORMER, exp.row, exp.col):
                new_ter = game_state.spawn_robot(RobotType.TERRAFORMER, exp.row, exp.col)
                self.construct_state = 0
                self.et_pairs.append((exp, new_ter))
        

        # iterate through dictionary of robots
        for rname, rob in game_state.get_ally_robots().items():
            print(f"Robot {rname} at {rob.row, rob.col}")