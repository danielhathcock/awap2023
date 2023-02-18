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
        self.initial_setup = False
        self.width : int = 0
        self.height : int = 0
        self.et_pairs : list[tuple[RobotInfo, RobotInfo]] = []
        self.construct_state = 0

        # Exploration stuff
        self.default_explore_val = 10
        self.default_explore_threshold = 50
        self.explore_prio = []
        
        # Charging stuff
        self.ally_tiles = set()
        self.ally_distance = []
        self.ally_distance_vis = set()

        # Spawning stuff
        self.spawn_queue = set()
        self.spawn_requests = 0

        # Moving stuff
        self.bot_move_queues = dict 
        return

    def get_tile_info(self, row, col) -> TileInfo :
        if row < 0 : return TileInfo(TileState.IMPASSABLE, 0, 0, 0, 0, None)
        if row >= self.width : return TileInfo(TileState.IMPASSABLE, 0, 0, 0, 0, None)
        if col < 0 : return TileInfo(TileState.IMPASSABLE, 0, 0, 0, 0, None)
        if col >= self.height : return TileInfo(TileState.IMPASSABLE, 0, 0, 0, 0, None)
        if self.tiles[row][col] == None: return TileInfo(TileState.ILLEGAL, 0, 0, 0, 0, None)
        return self.tiles[row][col]


    # Precomputations and runtime updates
    def update_cache(self):
        '''Update global variables to save data'''
        self.game_info = self.game_state.get_info()
        self.tiles = self.game_info.map


    def initial_cache(self):
        '''Varianles that need to be updated one time'''
        if self.initial_setup: return
        self.initial_setup = True

        self.height = len(self.game_info.map)
        self.width = len(self.game_info.map[0])
        self.total_tiles = self.height * self.width

        # Stuff for exploration bot
        for row in range(self.height):
            row_prio = []
            for col in range(self.width):
                row_prio.append(0.0)
            self.explore_prio.append(row_prio)
        
        for row in range(self.height):
            for col in range(self.width):
                # get the tile at (row, col)
                tile = self.game_info.map[row][col]
                # skip fogged tiles
                if tile is not None: # ignore fogged tiles
                    if tile.terraform > 0: # ensure tile is ally-terraformed
                        self.ally_tiles.add(tile)

        for row in range(self.height):
            row_ally_dist = []
            for col in range(self.width):
                row_ally_dist.append(None)
            self.ally_distance.append(row_ally_dist)

        for tile in self.ally_tiles:
            self.ally_bfs(tile.row, tile.col)

    # Helper functions
    def request_spawn(self, row, col, rtype : RobotType):
        if self.get_tile_info(row,col).terraform < 1:
            return False
        self.spawn_queue.add((self.spawn_requests, row, col, rtype))
        self.spawn_requests += 1
        return True

    def unexplored_bfs(self, row, col, threshold):
        if self.get_tile_info(row,col).state != TileInfo.ILLEGAL:
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
                if self.get_tile_info(nr,nc).state == TileState.ILLEGAL:
                    queue.append((nr,nc,m+1))
                    vis.add((nr,nc))
        return retList

    def ally_bfs(self, row, col):
        tile_info = self.get_tile_info(row,col)
        if tile_info.state == TileState.ILLEGAL or tile_info.state == TileState.IMPASSABLE:
            return None
        if tile_info.terraform > 0:
            self.ally_distance[row][col] = (0,row,col)
        else:
            return None

        vis = {(row,col)}
        queue = deque((row, col, 0))
        while(queue):
            qr, qc, m = queue.popleft()
            for d in Direction:
                nr, nc = qr + d.value[0], qc + d.value[1]
                state = self.get_tile_info(nr,nc).state
                if vis.__contains__((nr,nc)) or state == TileState.ILLEGAL or state == TileState.IMPASSABLE:
                    continue
                if(m+1 == self.ally_distance[nr][nc][0]):
                    continue
                queue.append((nr,nc,m+1))
                vis.add((nr,nc))
                self.ally_distance[qr][qc] = (m+1,row,col)

    def update_ally_distance(self, row, col):
        tile_info = self.get_tile_info(row,col)
        if tile_info.state == TileState.ILLEGAL or tile_info.state == TileState.IMPASSABLE:
            return None
        if self.ally_distance[row][col] != None:
            _, ar, ac = self.ally_distance[row][col]
            if self.tiles[ar][ac].terraform > 0:
                return self.ally_distance[row][col]
        self.ally_distance_vis.clear()
        self.ally_distance_vis.add((row,col))
        self.ally_distance[row][col] = (100000,-1,-1)
        for d in Direction:
            nr, nc = row + d.value[0], col + d.value[1]
            state = self.get_tile_info(nr,nc).state
            if vis.__contains__((nr,nc)) or state == TileState.ILLEGAL or state == TileState.IMPASSABLE:
                continue
            if self.update_ally_distance(nr,nc):
                continue
            m,ar,ac = self.update_ally_distance(nr,nc)
            if m + 1 < self.ally_distance[row][col] :
                self.ally_distance[row][col] = (m+1,ar,ac)
        if self.ally_distance[row][col][0] == 100000:
            self.ally_distance[row][col] = None
        return self.ally_distance[row][col]

    # Exploration
    def add_prio(self, row, col, val):
        ratio = 0.9
        dist = 12
        updates = self.unexplored_bfs(row, col, dist)
        for cur in updates:
            r, c, d = cur
            self.explore_prio[r][c] += val * pow(ratio, d)

    # Wrappers for traditional functions
    def execute_explore(rname : str, rinfo : RobotInfo):
        if rinfo.type != RobotType.EXPLORER: return False
        rrow = rinfo.row
        rcol = rinfo.col
        if self.game_state.can_robot_action(rname):
            self.game_state.robot_action(rname)
            for d in Direction:
                nr, nc = rrow + d.value[0], rcol + d.value[1]
                if self.get_tile_info(nr,nc).state == TileState.ILLEGAL:
                    self.add_prio(nr,nc,self.default_explore_val)
                    self.explore_prio[nr][nc] = 0
                    self.update_ally_distance(nr,nc)
        return True

    # Strategies
    # Explore
    def explore_score(self, row, col):
        return self.explore_prio[row][col]

    def explore_strategy(self, threshold):
        self.pos_to_explore = deque()
        for row in range(self.height):
            for col in range(self.width):
                score = self.explore_score(row,col)
                if score > threshold:
                    pos_to_explore.append((score,row, col))
        pos_to_explore = sorted(pos_to_explore)
        pos_to_explore.reverse()
        for ps,pr,pc in pos_to_explore:
            if self.explore_score(row,col) < self.default_explore_threshold:
                continue;
            if not self.request_explore(pr,pc):
                break

    def get_explorable_tiles(self, row, col) -> int:
        val : int = 0
        for d in Direction:
            tile_info = self.get_tile_info(row + d.value[0], col + d.value[1])
            if tile_info.state == TileState.ILLEGAL:
                val += 1
        return val

    def explore_alone(self, rname : str, robot_info : RobotInfo) -> None:
        '''Alone Exploration Code'''
        rr = robot_info.row
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
        self.execute_explore(rname)

    def explore_pair(self, rname : str, robot_info : RobotInfo) -> None:
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
        if self.game_state.can_robot_action(rname):
            self.game_state.robot_action(rname)
            for d in Direction:
                nr, nc = robot_row + d.value[0], robot_col + d.value[1]
                if self.get_tile_info(nr,nc).state == TileState.ILLEGAL:
                    self.add_prio(nr,nc,self.default_explore_val)
                    self.explore_prio[nr][nc] = 0


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


        print(f"My metal {game_state.get_metal()}")
        robots = game_state.get_ally_robots()

        # Refresh RobotInfo objects in et_pairs.
        # TODO: check if any of our robots in here were destroyed
        for i in range(len(self.et_pairs)):
            exp, ter = self.et_pairs[i]
            self.et_pairs[i] = (robots[exp.name], robots[ter.name])

        if self.construct_state == 0:
            for spawn_loc in self.ally_tiles:
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
