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
        self.tt_coordinates = (self.mining_coordinates[0] + self.mine2tt[0], self.mining_coordinates[1] + self.mine2tt[1])


class BotPlayer(Player):
    """
    Players will write a child class that implements (notably the play_turn method)
    """

    def __init__(self, team: Team):
        self.team = team
        self.game_state : GameState = None
        self.ginfo : GameInfo = None
        self.initial_setup = False
        self.width : int = 0
        self.height : int = 0
        self.metal : int = 0

        self.robots = None
        self.ally_tiles = []

        # Spawning stuff
        self.spawn_queue = set()
        self.spawn_complete = set()
        self.spawn_requests = 0

        # exploring stuff
        self.et_pairs : list[tuple[RobotInfo, RobotInfo]] = []
        self.construct_state = 0

        # Moving stuff
        self.bot_move_queues = dict 

        # Mining stuff
        self.mining_assignment = dict() # A dictionary mapping mines to a Mining_Logistics object
        self.assigned_mines = set()
        self.charging_spots = []
        return

    # Precomputations and runtime updates
    def update_vars(self):
        '''Update global variables to save data'''
        self.ginfo = self.game_state.get_info()
        self.tiles = self.ginfo.map
        self.metal = self.ginfo.metal
        self.robots = self.game_state.get_ally_robots()

        for row in range(self.height):
            for col in range(self.width):
                # get the tile at (row, col)
                tile = self.tiles[row][col]
                # skip fogged tiles
                if tile is not None: # ignore fogged tiles
                    if tile.terraform > 0 : # ensure tile is ally-terraformed
                        self.ally_tiles += [tile]


    def init_vars(self):
        '''Varianles that need to be updated one time'''
        if self.initial_setup: return
        self.initial_setup = True

        self.height = len(self.ginfo.map)
        self.width = len(self.ginfo.map[0])
        self.total_tiles = self.height * self.width


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
                self.metal -= 50

    # Exploration
    def get_explorable_tiles(self, row, col) -> int:
        val : int = 0
        for d in Direction:
            tile_info = self.get_tile_info(row + d.value[0], col + d.value[1])
            if tile_info.state == TileState.ILLEGAL:
                val += 1
        return val

    def explore_next(self, rname : str, robot_info : RobotInfo) -> None:
        '''Perform the best move action for an explorer'''
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
        if self.game_state.can_move_robot(rname,d_move):
            self.game_state.move_robot(rname, d_move)
            if self.game_state.can_robot_action(rname):
                self.game_state.robot_action(rname)


    def explore_action(self) -> None:
        '''Perform one move/action sequence for each of the explore/terraform pairs'''
        print(self.et_pairs)
        for exp, ter in self.et_pairs:
            if exp.battery == 0:
                # Recharge sequence
                for d in Direction:
                    dest_row = ter.row + d.value[0]
                    dest_col = ter.col + d.value[1]
                    if self.game_state.can_move_robot(ter.name, d) and self.game_state.get_map()[dest_row][dest_col].robot is None:
                        self.game_state.move_robot(ter.name, d)
                        if self.game_state.can_robot_action(ter.name):
                            self.game_state.robot_action(ter.name)
                        self.game_state.move_robot(exp.name, Direction((ter.row - exp.row, ter.col - exp.col)))
                        break
            
            else:
                # Explore sequence
                old_exp_row, old_exp_col = (exp.row, exp.col)
                self.explore_next(exp.name, exp)

                # Move Terraformer to the previous location of the explorer
                self.game_state.move_robot(ter.name, Direction((old_exp_row - ter.row, old_exp_col - ter.col)))
                if self.game_state.can_robot_action(ter.name):
                    self.game_state.robot_action(ter.name)   

    def exploration_phase(self):
        # Refresh RobotInfo objects in et_pairs.
        # TODO: check if any of our robots in here were destroyed
        for i in range(len(self.et_pairs)):
            exp, ter = self.et_pairs[i]
            self.et_pairs[i] = (self.robots[exp.name], self.robots[ter.name])

        print(self.ally_tiles)

        if self.construct_state == 0:
            for spawn_loc in self.ally_tiles:
                if self.construct_state > 0:
                    break
                spawn_type = RobotType.EXPLORER
                if self.game_state.can_spawn_robot(spawn_type, spawn_loc.row, spawn_loc.col):
                    self.game_state.spawn_robot(spawn_type, spawn_loc.row, spawn_loc.col)
                    self.construct_state = 1

        elif self.construct_state == 1:
            exp_name, exp = list(self.robots.items())[0]
            self.explore_next(exp_name, exp)

            if self.game_state.can_spawn_robot(RobotType.TERRAFORMER, exp.row, exp.col):
                new_ter = self.game_state.spawn_robot(RobotType.TERRAFORMER, exp.row, exp.col)
                self.construct_state = 2
                self.et_pairs.append((exp, new_ter))

            print(self.et_pairs)
        else:
            self.explore_action()

    # Mining stuff
    def no_collision(self, row, col):
        tile = self.game_state.get_map()[row][col]
        return tile.robot is None

    def sorted_mines(self, map):
        """ Input is map object list(list[TileInfo]) """
        height, width = len(map), len(map[0])
        mines = []
        for row in map:
            for tile in row:
                if tile and tile.state == TileState.MINING:
                    mines.append(tile)
        mines.sort(key=lambda x: - x.mining)
        # mines is sorted in decreasing order of capacity
        return mines

    def first_decision(self, map):
        """ Decide how many miners to start with, and where to place them.
         Returns list of dictionaries, sorted by capacity """
        height, width = len(map), len(map[0])
        gmt = 15  # Good Mine Threshold

        def get_terra_tile(mine):
            """ Returns a dictionary with keys (tt, td) = (adjacent terra tile, directions FROM the terra tile) """
            x, y = mine.row, mine.col
            D = {}
            for t in Direction:
                p, q = t.value
                nx, ny = x - p, y - q
                if 0 <= nx < height and 0 <= ny < width and map[nx][ny] and map[nx][
                    ny].state == TileState.TERRAFORMABLE:
                    D['tt'], D['td'] = (nx, ny), t
            return D

        M = self.sorted_mines(map)
        decision_list = []  # This is a list of dictionaries with keys tt,td,c : Terra Tile, Terra_to_mine Direction, Count

        if len(M) == 1:
            D = get_terra_tile(M[0])
            D['c'] = 2
            decision_list.append(D)

        elif len(M) == 2:
            [m1, m2] = M
            D1, D2 = get_terra_tile(m1), get_terra_tile(m2)
            p1, p2 = m1.mining, m2.mining
            c1, c2 = 1 if p1 < gmt else 2, 1 if p2 < gmt else 2
            D1['c'], D2['c'] = c1, c2
            decision_list.append(D1)
            decision_list.append(D2)

        elif len(M) == 3:
            [m1, m2, m3] = M
            D1, D2, D3 = get_terra_tile(m1), get_terra_tile(m2), get_terra_tile(m3)
            p1, p2, p3 = m1.mining, m2.mining, m3.mining
            if p2 < gmt:
                if 0.4 * p1 >= 0.6 * p2:
                    c1, c2, c3 = 2, 0, 0
                else:
                    c1, c2, c3 = 1, 1, 0
            else:
                if 0.4 * p2 >= 0.6 * p3:
                    c1, c2, c3 = 2, 2, 0
                else:
                    c1, c2, c3 = 2, 1, 1
            D1['c'], D2['c'], D3['c'] = c1, c2, c3
            if c1: decision_list.append(D1)
            if c2: decision_list.append(D2)
            if c3: decision_list.append(D3)

        else:
            [m1, m2, m3, m4] = M[:4]
            D1, D2, D3, D4 = get_terra_tile(m1), get_terra_tile(m2), get_terra_tile(m3), get_terra_tile(m4)
            p1, p2, p3, p4 = m1.mining, m2.mining, m3.mining, m4.mining
            if p2 < gmt:
                if 0.4 * p1 >= 0.6 * p2:
                    c1, c2, c3, c4 = 2, 0, 0, 0
                else:
                    c1, c2, c3, c4 = 1, 1, 0, 0
            else:
                if 0.4 * p2 >= 0.6 * p3:
                    c1, c2, c3, c4 = 2, 2, 0, 0
                elif 0.4 * p1 < 0.6 * p4:
                    c1, c2, c3, c4 = 1, 1, 1, 1
                else:
                    c1, c2, c3, c4 = 2, 1, 1, 0
            D1['c'], D2['c'], D3['c'], D4['c'] = c1, c2, c3, c4
            if c1: decision_list.append(D1)
            if c2: decision_list.append(D2)
            if c3: decision_list.append(D3)
            if c4: decision_list.append(D4)

        return decision_list

    def next_decision(self, map):
        """ Input is new map and already assigned mines. Returns priority queue of new miners to make"""
        S = self.assigned_mines
        height, width = len(map), len(map[0])
        def get_terra_tile(mine):
            """ Returns a dictionary with keys (tt, td) = (adjacent terra tile, directions FROM the terra tile) """
            x, y = mine.row, mine.col
            D = {}
            for t in Direction:
                p, q = t.value
                nx, ny = x - p , y - q
                if 0 <= nx < height and 0 <= ny < width and map[nx][ny] and map[nx][ny].state == TileState.TERRAFORMABLE:
                    D['tt'], D['td'] = (nx, ny), t
            return D

        New_mines = []
        New_decisions = []
        for row in map:
            for tile in row:
                if tile and tile.state == TileState.MINING and ((tile.row, tile.col) not in S):
                    New_mines.append(tile)
        # print(S)
        # print(New_mines)

        New_mines.sort(key = lambda x: -x.mining)
        for mine in New_mines:
            D = get_terra_tile(mine)
            if D:
                # S.add((mine.row, mine.col))
                D['c'] = 1
                New_decisions.append(D)
        # self.assigned_mines = S
        return New_decisions

    def initial_two_turns(self, game_state: GameState) -> None:
        ginfo = game_state.get_info()

        initial_mine_list = self.first_decision(ginfo.map)
        # move the robots
        robots = game_state.get_ally_robots()
        for rname, rob in robots.items():
            if rob.type == RobotType.MINER:
                for mine_info in initial_mine_list:
                    if (rob.row, rob.col) == mine_info['tt']:
                        move_dir = mine_info['td']
                        if game_state.can_move_robot(rname, move_dir) and self.no_collision(rob.row + move_dir[0], rob.col + move_dir[1]):
                            game_state.move_robot(rname, move_dir)
            if game_state.can_robot_action(rname):
                game_state.robot_action(rname) # action the robots

        #print(initial_mine_list)
        # spawn robots
        for mine_info in initial_mine_list:
            tt_coordinates = mine_info['tt']
            t_direction = mine_info['td'].value # From TT --> mining location
            m_direction = (-1 * t_direction[0], -1 * t_direction[1]) # From mining location --> TT
            mining_coordinates = (tt_coordinates[0] + t_direction[0], tt_coordinates[1] + t_direction[1])

            #print(mine_info)
            if ginfo.map[mining_coordinates[0]][mining_coordinates[1]].state != TileState.MINING:
                raise Exception("why isn't this a mining tile??")

            if mining_coordinates not in self.mining_assignment.keys():
                self.mining_assignment[mining_coordinates] = Mining_Logistics(coordinates=mining_coordinates, direction=m_direction)

            if 2 >= mine_info['c'] > len(self.mining_assignment[mining_coordinates].miners):
                if game_state.can_spawn_robot(RobotType.MINER, tt_coordinates[0], tt_coordinates[1]): # spawn the robots
                    new_miner = game_state.spawn_robot(RobotType.MINER, tt_coordinates[0], tt_coordinates[1])
                    #print(new_miner.name)
                    self.mining_assignment[mining_coordinates].mine2tt = (-1 * t_direction[0], -1 * t_direction[1])
                    self.mining_assignment[mining_coordinates].miners.append(new_miner.name)

        #print(self.mining_assignment)


    def general_mining_turn(self, game_state: GameState):
        ginfo = game_state.get_info()
        robots = game_state.get_ally_robots()

        # moving, actioning, or recharging
        for mining_location in self.mining_assignment:
            logistics = self.mining_assignment[mining_location]
            these_robots = logistics.miners

            if 1 >= len(these_robots) > 0: # FIX!!!!!!!!!!
                print(these_robots[0])
                miner = these_robots[0]
                miner_robot_object = robots[miner]
                if (miner_robot_object.row, miner_robot_object.col) == mining_location:
                    print("MINING: " + str(ginfo.turn))
                    print("BATTERY: " + str(miner_robot_object.battery))
                    print()
                    if miner_robot_object.battery >= GameConstants.MINER_ACTION_COST:
                        game_state.robot_action(miner)
                    else:
                        if self.no_collision(*logistics.tt_coordinates):
                            game_state.move_robot(miner, Direction(logistics.mine2tt))
                elif (miner_robot_object.row, miner_robot_object.col) == logistics.tt_coordinates:
                    print("CHARGING: " + str(ginfo.turn))
                    if miner_robot_object.battery == GameConstants.INIT_BATTERY:
                        if self.no_collision(*logistics.mining_coordinates):
                            game_state.move_robot(miner, Direction(logistics.tt2mine))
                else:
                    raise Exception("Miners aren't in the right place!!")
            elif len(these_robots) == 2:
                continue
            elif len(these_robots) > 2:
                print(len(these_robots))
                raise Exception("Way too  many robots here...")
        
        # Spawn new miners
        print(f'next decision {self.next_decision(self.game_state.get_map())}')
        for mine_info in self.next_decision(self.game_state.get_map()):
            if self.game_state.get_metal() > 50:
                tt_coordinates = mine_info['tt']
                t_direction = mine_info['td'].value # From TT --> mining location
                m_direction = (-1 * t_direction[0], -1 * t_direction[1]) # From mining location --> TT
                mining_coordinates = (tt_coordinates[0] + t_direction[0], tt_coordinates[1] + t_direction[1])

                self.mining_assignment[mining_coordinates] = Mining_Logistics(coordinates=mining_coordinates, direction=m_direction)
                row = self.mining_assignment[mining_coordinates].tt_coordinates[0]
                col = self.mining_assignment[mining_coordinates].tt_coordinates[1]

                if game_state.can_spawn_robot(RobotType.MINER, row, col):
                    new_miner = game_state.spawn_robot(RobotType.MINER, row, col)
                    self.mining_assignment[mining_coordinates].miners.append(new_miner.name)
                    
                    # self.assigned_mines.add(mining_coordinates)
            else:
                break

    def terraforming_phase(self):
        ginfo = self.game_state.get_info()
        height, width = len(ginfo.map), len(ginfo.map[0])
        # Move and action the current terraform robots
        robots = self.game_state.get_ally_robots()

        # iterate through dictionary of robots
        for rname, rob in robots.items():
            if rob.type == RobotType.TERRAFORMER:

                all_dirs = [dir for dir in Direction] # find a good direction
                move_dir = Direction.DOWN_RIGHT
                for dir in all_dirs:
                    if self.game_state.can_move_robot(rname, dir) and self.no_collision(rob.row + dir.value[0], rob.col + dir.value[1]):
                        move_dir = dir

                # check if we can move in this direction
                if self.game_state.can_move_robot(rname, move_dir):
                    # try to not collide into robots from our team
                    dest_loc = (rob.row + move_dir.value[0], rob.col + move_dir.value[1])
                    dest_tile = self.game_state.get_map()[dest_loc[0]][dest_loc[1]]
                    if dest_tile.robot is None or dest_tile.robot.team != self.team:
                        print("here")
                        self.game_state.move_robot(rname, move_dir)
                        if self.game_state.can_robot_action(rname):
                            self.game_state.robot_action(rname)

        # Spawn new terra formers.
        for row in range(height):
            for col in range(width):
                tile = ginfo.map[row][col]
                if tile is not None and tile.terraform > 0:
                    if self.game_state.can_spawn_robot(RobotType.TERRAFORMER, row, col):
                        self.game_state.spawn_robot(RobotType.TERRAFORMER, row, col)

        return

    def play_turn(self, game_state: GameState) -> None:
        # get info
        self.game_state = game_state
        self.update_vars()
        self.init_vars()

        # print info about the game
        print(f"Turn {self.ginfo.turn}, team {self.ginfo.team}")
        print("Map height", self.height)
        print("Map width", self.width)
        print(f"My metal {game_state.get_metal()}")
        # Extract information

        if self.ginfo.turn <= 10:
            self.exploration_phase()
        elif self.ginfo.turn <= 20:
            1+1
        elif self.ginfo.turn <=22:
            self.initial_two_turns(game_state)
        else:
            self.exploration_phase()
            self.general_mining_turn(game_state)
            self.terraforming_phase()
        if self.ginfo.turn == 200:
            print(len(self.ginfo.ally_robots))


        # iterate through dictionary of robots
        for rname, rob in game_state.get_ally_robots().items():
            print(f"Robot {rname} at {rob.row, rob.col}")
        return 

