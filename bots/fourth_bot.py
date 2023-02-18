from typing import List, Tuple, Any
from collections import deque
import random

from src.game_constants import RobotType, Direction, Team, TileState, GameConstants
from src.game_state import GameState, GameInfo
from src.player import Player
from src.map import TileInfo, RobotInfo
from src.robot import Robot


class SpawnRequest:
    def __init__(self, status):
        self.name = None
        self.status = status
        # self.status = -1 -- failed
        # self.status = 0  -- waiting
        # self.status = 1  -- success


class Mining_Logistics:
    def __init__(self, coordinates, direction=None, robots=None):
        self.mining_coordinates = coordinates
        if robots is None:
            self.miners = []  # should just be a list of names
        else:
            self.miners = robots
        self.mine2tt = direction  # Vector mining location --> terraforming tile direction

        self.tt2mine = (-1 * self.mine2tt[0], -1 * self.mine2tt[1])
        self.tt_coordinates = (
        self.mining_coordinates[0] + self.mine2tt[0], self.mining_coordinates[1] + self.mine2tt[1])


class BotPlayer(Player):
    """
    Players will write a child class that implements (notably the play_turn method)
    """

    def __init__(self, team: Team):
        self.team = team
        self.game_state: GameState = None
        self.ginfo: GameInfo = None
        self.initial_setup = False
        self.width: int = 0
        self.height: int = 0
        self.metal: int = 0

        self.robots = None
        self.ally_tiles = []

        # Spawning stuff
        self.spawn_queue = set()
        self.spawn_complete = set()
        self.spawn_requests = 0

        # exploring stuff
        self.et_pairs: list[tuple[RobotInfo, RobotInfo]] = []
        self.construct_state = 0
        self.new_exp = None

        # Moving stuff
        self.bot_move_queues = dict

        # Mining stuff
        self.mining_assignment = dict()  # A dictionary mapping mines to a Mining_Logistics object
        self.assigned_mines = set()
        self.assigned_terra = set()

        return

    # Precomputations and runtime updates
    def update_vars(self):
        '''Update global variables to save data'''
        self.ginfo = self.game_state.get_info()
        self.tiles = self.ginfo.map
        self.metal = self.ginfo.metal
        self.robots = self.game_state.get_ally_robots()

        self.ally_tiles = []
        for row in range(self.height):
            for col in range(self.width):
                # get the tile at (row, col)
                tile = self.tiles[row][col]
                # skip fogged tiles
                if tile is not None:  # ignore fogged tiles
                    if tile.terraform > 0:  # ensure tile is ally-terraformed
                        self.ally_tiles.append(tile)

    def init_vars(self):
        '''Varianles that need to be updated one time'''
        if self.initial_setup: return
        self.initial_setup = True
        self.ginfo = self.game_state.get_info()

        self.height = len(self.ginfo.map)
        self.width = len(self.ginfo.map[0])
        self.total_tiles = self.height * self.width




    # Helper functions
    def get_tile_info(self, row, col) -> TileInfo:
        if row < 0: return TileInfo(TileState.IMPASSABLE, 0, 0, 0, 0, None)
        if row >= self.width: return TileInfo(TileState.IMPASSABLE, 0, 0, 0, 0, None)
        if col < 0: return TileInfo(TileState.IMPASSABLE, 0, 0, 0, 0, None)
        if col >= self.height: return TileInfo(TileState.IMPASSABLE, 0, 0, 0, 0, None)
        if self.tiles[row][col] == None: return TileInfo(TileState.ILLEGAL, 0, 0, 0, 0, None)
        return self.tiles[row][col]






    # Exploration
    def get_explorable_tiles(self, row, col) -> int:
        val: int = 0
        for d in Direction:
            tile_info = self.get_tile_info(row + d.value[0], col + d.value[1])
            if tile_info.state == TileState.ILLEGAL:
                val += 1
        return val

    def explore_next(self, rname: str, robot_info: RobotInfo) -> None:
        '''Perform the best move action for an explorer'''
        robot_row = robot_info.row
        robot_col = robot_info.col
        val: int = 0
        d_options: list = []
        for d in Direction:
            if self.game_state.can_move_robot(rname, d) and self.game_state.get_map()[robot_row + d.value[0]][robot_col + d.value[1]].robot is None:
                cur: int = self.get_explorable_tiles(robot_row + d.value[0], robot_col + d.value[1])
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
            if self.game_state.can_move_robot(rname, d_move):
                self.game_state.move_robot(rname, d_move)
                if self.game_state.can_robot_action(rname):
                    self.game_state.robot_action(rname)

    def explore_action(self) -> None:
        '''Perform one move/action sequence for each of the explore/terraform pairs'''
        for exp, ter in self.et_pairs:
            # print(f'et pair: {exp, ter}')
            if exp.battery == 0:
                # Recharge sequence
                # print('Recharge')
                for d in Direction:
                    dest_row = ter.row + d.value[0]
                    dest_col = ter.col + d.value[1]
                    if self.game_state.can_move_robot(ter.name, d) and self.game_state.get_map()[dest_row][dest_col].robot is None:
                        self.game_state.move_robot(ter.name, d)
                        if self.game_state.can_robot_action(ter.name):
                            self.game_state.robot_action(ter.name)
                        self.game_state.move_robot(exp.name, Direction((ter.row - exp.row, ter.col - exp.col))) # Check this lol
                        break

            else:
                # Explore sequence
                # print('Explore')
                old_exp_row, old_exp_col = (exp.row, exp.col)
                self.explore_next(exp.name, exp)

                # Move Terraformer to the previous location of the explorer
                d = Direction((old_exp_row - ter.row, old_exp_col - ter.col))
                if self.game_state.can_move_robot(ter.name, d) and self.game_state.get_map()[old_exp_row][old_exp_col].robot is None:
                    self.game_state.move_robot(ter.name, d)
                if self.game_state.can_robot_action(ter.name):
                    self.game_state.robot_action(ter.name)

    def exploration_phase(self, to_spawn=False):
        # Refresh RobotInfo objects in et_pairs.
        # TODO: check if any of our robots in here were destroyed
        updated_et_pairs = []
        robots = self.game_state.get_ally_robots()
        for exp, ter in self.et_pairs:
            if exp.name in robots and ter.name in robots:
                updated_et_pairs.append((robots[exp.name], robots[ter.name]))
        self.et_pairs = updated_et_pairs

        # print(self.ally_tiles)
        # print('Explore action:')
        self.explore_action()

        if to_spawn:
            # print('spawn?')
            if self.construct_state == 0 and self.game_state.get_metal() >= 100:
                for spawn_loc in self.ally_tiles:
                    if self.construct_state > 0:
                        break
                    spawn_type = RobotType.EXPLORER
                    if self.game_state.can_spawn_robot(spawn_type, spawn_loc.row, spawn_loc.col):
                        # print('spawn exp')
                        self.new_exp = self.game_state.spawn_robot(spawn_type, spawn_loc.row, spawn_loc.col)
                        self.construct_state = 1

            elif self.construct_state == 1:
                exp_name, exp = self.new_exp.name, self.new_exp
                self.explore_next(exp_name, exp)

                if self.game_state.can_spawn_robot(RobotType.TERRAFORMER, exp.row, exp.col):
                    # print('spawn ter')
                    new_ter = self.game_state.spawn_robot(RobotType.TERRAFORMER, exp.row, exp.col)
                    self.construct_state = 0
                    self.et_pairs.append((exp, new_ter))

                # print(self.et_pairs)
            









    # Mining stuff
    def no_collision(self, row, col):
        tile = self.game_state.get_map()[row][col]
        return tile.robot is None

    def no_allied_collision(self, row, col):
        tile = self.game_state.get_map()[row][col]
        return tile.robot is None or tile.robot.team != self.team


    def next_decision(self, map):
        """ Input is new map and already assigned mines. Returns priority queue of new miners to make"""
        S = self.assigned_mines
        height, width = len(map), len(map[0])
        T = self.assigned_terra.copy()

        def get_terra_tile(mine):
            """ Returns a dictionary with keys (tt, td) = (adjacent terra tile, directions FROM the terra tile) """
            x, y = mine.row, mine.col
            D, terras = {}, []
            for t in Direction:
                p, q = t.value
                nx, ny = x - p, y - q
                if 0 <= nx < height and 0 <= ny < width and map[nx][ny] and map[nx][ny].terraform > 0:
                    terras.append(((nx, ny), t))

            if not terras: return {}
            for i, t in terras:
                if i not in T:
                    T.add(i)
                    D['tt'], D['td'] = i, t
                    break
            if not D: D['tt'], D['td'] = terras[0]
            return D

        new_mines = []
        new_decisions = []
        for row in map:
            for tile in row:
                if tile and tile.state == TileState.MINING and ((tile.row, tile.col) not in S):
                    new_mines.append(tile)

        # print(new_mines)
        new_mines.sort(key=lambda x: -x.mining)
        for mine in new_mines:
            D = get_terra_tile(mine)
            # print(f'({mine.row}, {mine.col}), Mining: {mine.mining}, {D}')
            if D and mine.mining > 0:
                D['c'] = 1
                new_decisions.append(D)
        return new_decisions



    def general_mining_turn(self, game_state: GameState):
        robots = game_state.get_ally_robots()

        # moving, actioning, or recharging
        for mining_location in list(self.mining_assignment.keys()):
            logistics = self.mining_assignment[mining_location]
            these_robots = logistics.miners

            if len(these_robots) == 1: 
                miner = these_robots[0]
                
                if miner not in robots:
                    # Try to rebuild our miner!!
                    row, col = logistics.tt_coordinates
                    if game_state.get_map()[row][col].terraform > 0:
                        if game_state.can_spawn_robot(RobotType.TERRAFORMER, row, col):
                            new_rob = game_state.spawn_robot(RobotType.TERRAFORMER, row, col)
                            logistics.miners = [new_rob.name]
                    else:
                        # Kill this logistics object
                        del self.mining_assignment[mining_location]
                        self.assigned_mines.remove(mining_location)

                else:
                    miner_robot_object = robots[miner]
                    if (miner_robot_object.row, miner_robot_object.col) == mining_location:
                        # print("MINING: " + str(ginfo.turn))
                        # print("BATTERY: " + str(miner_robot_object.battery))
                        # print()
                        if miner_robot_object.battery >= GameConstants.MINER_ACTION_COST:
                            game_state.robot_action(miner)
                        else:
                            if self.no_collision(*logistics.tt_coordinates):
                                game_state.move_robot(miner, Direction(logistics.mine2tt))
                    elif (miner_robot_object.row, miner_robot_object.col) == logistics.tt_coordinates:
                        #ginfo.map[miner_robot_object.row][miner_robot_object.col].terraform > 0:
                        #
                        # print("CHARGING: " + str(ginfo.turn))
                        if miner_robot_object.battery == GameConstants.INIT_BATTERY:
                            if self.no_collision(*logistics.mining_coordinates):
                                game_state.move_robot(miner, Direction(logistics.tt2mine))
                    else:
                        raise Exception("Miners aren't in the right place!!")
            elif len(these_robots) > 1:
                # print(len(these_robots))
                raise Exception("Way too many robots here...")
        
        # Spawn new miners
        # print(f'next decision {self.next_decision(self.game_state.get_map())}')
        for mine_info in self.next_decision(self.game_state.get_map()):
            # print(f'mine info: {mine_info}')
            if self.game_state.get_metal() >= 50:

                tt_coordinates = mine_info['tt']
                t_direction = mine_info['td'].value # From TT --> mining location
                m_direction = (-1 * t_direction[0], -1 * t_direction[1]) # From mining location --> TT
                mining_coordinates = (tt_coordinates[0] + t_direction[0], tt_coordinates[1] + t_direction[1])
                print(f'Trying to spawn for {mining_coordinates}')

                self.mining_assignment[mining_coordinates] = Mining_Logistics(coordinates=mining_coordinates, direction=m_direction)
                row = self.mining_assignment[mining_coordinates].tt_coordinates[0]
                col = self.mining_assignment[mining_coordinates].tt_coordinates[1]

                if game_state.can_spawn_robot(RobotType.MINER, row, col):
                    new_miner = game_state.spawn_robot(RobotType.MINER, row, col)
                    self.mining_assignment[mining_coordinates].miners.append(new_miner.name)
                    # print(f'{row, col} mining at {mining_coordinates}')
                    # print(self.assigned_mines)
                    
                    self.assigned_mines.add(mining_coordinates)
                    self.assigned_terra.add(tt_coordinates)
                # else:
                    # raise Exception('We couldnt spawn the miner!!!')
            else:
                print(f'no metal: {self.game_state.get_metal()}')
                break







    # Terraforming stuff
    def terraforming_phase2(self):
        ginfo = self.game_state.get_info()
        height, width = len(ginfo.map), len(ginfo.map[0])
        # Move and action the current terraform robots
        robots = self.game_state.get_ally_robots()

        # Move and Action
        print("TERRA: FIND A DIRECTION TO MOVE")
        for rname, rob in robots.items():
            if rob.type == RobotType.TERRAFORMER:

                move_dir = None
                potential_dir = []
                #aggressive_dir = None
                for dir in Direction:
                    loc = (rob.row + dir.value[0], rob.col + dir.value[1])
                    if self.game_state.can_move_robot(rname, dir) and self.no_allied_collision(*loc) and loc not in self.assigned_mines and loc not in self.assigned_terra:
                        potential_dir.append(dir)
                        #if ginfo.map[loc[0]][loc[1]].robot is not None and ginfo.map[loc[0]][loc[1]].robot != self.team:
                            #aggressive_dir = dir
                            #An opportunity to write ADVERSERIAL CODE!!
               #if aggressive_dir is not None and ginfo.turn >= 100:
                    #print("MWUHAHAHAHHAHAHAH!")
                    #move_dir = aggressive_dir
                if len(potential_dir) > 0:
                    move_dir = random.choice(potential_dir)

                if move_dir is not None:
                    self.game_state.move_robot(rname, move_dir)
                #action
                if self.game_state.can_robot_action(rname):
                    self.game_state.robot_action(rname)

        # Spawn new terra formers.
        print("TERRA: Find Allied Tiles")
        ally_tiles = []
        for row in range(height):
            for col in range(width):
                # get the tile at (row, col)
                tile = ginfo.map[row][col]
                # skip fogged tiles
                if tile is not None:  # ignore fogged tiles
                    if tile.robot is None:  # ignore occupied tiles
                        if tile.terraform > 0:  # ensure tile is ally-terraformed
                            ally_tiles += [tile]

        print("TERRA: Pick a random allied tile")
        # pick a several random ally tiles to spawn on, while we have the budget to do so
        if len(ally_tiles) > 0:
            num_new_bots = int(ginfo.metal * 0.8 / GameConstants.ROBOT_SPAWN_COST)
            spawn_locs = random.sample(ally_tiles, num_new_bots)
            for spawn_loc in spawn_locs:
                # spawn the robot
                # check if we can spawn here (checks if we can afford, tile is empty, and tile is ours)
                if self.game_state.can_spawn_robot(RobotType.TERRAFORMER, spawn_loc.row, spawn_loc.col):
                    self.game_state.spawn_robot(RobotType.TERRAFORMER, spawn_loc.row, spawn_loc.col)
        print("TERRA: done")
        return


    def play_turn(self, game_state: GameState) -> None:
        # get info
        self.game_state = game_state
        self.init_vars()
        self.update_vars()

        # print info about the game
        print(f"Turn {self.ginfo.turn}, team {self.ginfo.team}")
        # print("Map height", self.height)
        # print("Map width", self.width)
        # print(f"My metal {game_state.get_metal()}")
        # Extract information

        if self.ginfo.turn <= 20:
            self.exploration_phase(to_spawn=True)
        else:
            print('Begin explore phase')
            self.exploration_phase()
            print('End explore, begin mine')
            try:
                self.general_mining_turn(game_state)
            except KeyError:
                print('yo yo yo')
            print('End mine, begin terra')
            self.terraforming_phase2()
            print('End terra')
        if self.ginfo.turn == 200:
            print(len(self.ginfo.ally_robots))

        # iterate through dictionary of robots
        # for rname, rob in game_state.get_ally_robots().items():
        #     print(f"Robot {rname} at {rob.row, rob.col}")
        return

