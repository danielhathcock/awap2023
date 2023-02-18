from typing import List, Tuple, Any

from src.game_constants import RobotType, Direction, Team, TileState, GameConstants
from src.game_state import GameState, GameInfo
from src.player import Player
from bots.aditya import *
from src.map import TileInfo, RobotInfo
import random

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
        self.mining_assignment = dict() # A dictionary mapping mines to a Mining_Logistics object
        self.charging_spots = []
        self.game_state = None
        return

    def no_collision(self, row, col):
        tile = self.game_state.get_map()[row][col]
        print((row, col))
        return tile.robot is None

    def initial_two_turns(self, game_state: GameState) -> None:
        ginfo = game_state.get_info()

        initial_mine_list = first_decision(ginfo.map)
        # move the robots
        robots = game_state.get_ally_robots()
        for rname, rob in robots.items():
            if rob.type == RobotType.MINER:
                for mine_info in initial_mine_list:
                    if (rob.row, rob.col) == mine_info['tt']:
                        move_dir = mine_info['td']
                        if game_state.can_move_robot(rname, move_dir):
                            game_state.move_robot(rname, move_dir)
            if game_state.can_robot_action(rname):
                game_state.robot_action(rname) # action the robots

        print(initial_mine_list)
        # spawn robots
        for mine_info in initial_mine_list:
            tt_coordinates = mine_info['tt']
            t_direction = mine_info['td'].value # From TT --> mining location
            m_direction = (-1 * t_direction[0], -1 * t_direction[1]) # From mining location --> TT
            mining_coordinates = (tt_coordinates[0] + t_direction[0], tt_coordinates[1] + t_direction[1])

            print(mine_info)
            if ginfo.map[mining_coordinates[0]][mining_coordinates[1]].state != TileState.MINING:
                raise Exception("why isn't this a mining tile??")

            if mining_coordinates not in self.mining_assignment.keys():
                self.mining_assignment[mining_coordinates] = Mining_Logistics(coordinates=mining_coordinates, direction=m_direction)

            if 2 >= mine_info['c'] > len(self.mining_assignment[mining_coordinates].miners):
                if game_state.can_spawn_robot(RobotType.MINER, tt_coordinates[0], tt_coordinates[1]): # spawn the robots
                    new_miner = game_state.spawn_robot(RobotType.MINER, tt_coordinates[0], tt_coordinates[1])
                    print(new_miner.name)
                    self.mining_assignment[mining_coordinates].mine2tt = (-1 * t_direction[0], -1 * t_direction[1])
                    self.mining_assignment[mining_coordinates].miners.append(new_miner.name)

        print(self.mining_assignment)


    def general_mining_turn(self, game_state: GameState, new_mines=None) -> list[tuple[Any, Any]]:
        ginfo = game_state.get_info()
        robots = game_state.get_ally_robots()

        #print(self.mining_assignment.keys())

        # moving, actioning, or recharging
        for mining_location in self.mining_assignment:
            logistics = self.mining_assignment[mining_location]
            these_robots = logistics.miners

            if 1 >= len(these_robots) > 0: # FIX!!!!!!!!!!
                print(these_robots)
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
                    #ginfo.map[miner_robot_object.row][miner_robot_object.col].terraform > 0:
                    #
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

        unfinished_mines = []
        # spawning
        if new_mines is None:
            new_mines = []

        for mining_location, mine2tt in new_mines:
            self.mining_assignment[mining_location] = Mining_Logistics(coordinates=mining_location, direction=mine2tt)
            row = self.mining_assignment[mining_location].tt_coordinates[0]
            col = self.mining_assignment[mining_location].tt_coordinates[1]

            if game_state.can_spawn_robot(RobotType.MINER, row, col):
                new_miner = game_state.spawn_robot(RobotType.MINER, row, col)
                self.mining_assignment[mining_location].miners.append(new_miner.name)
            else:
                unfinished_mines.append((mining_location, mine2tt))
                print("Couldn't spawn at " + str(mining_location))

        return unfinished_mines



    def terraforming_phase(self):
        ginfo = self.game_state.get_info()
        height, width = len(ginfo.map), len(ginfo.map[0])
        # Move and action the current terraform robots


        # Spawn new terra formers.
        for row in range(height):
            for col in range(width):
                tile = ginfo.map[row][col]
                if tile.terraform() > 0:
                    if self.game_state.can_spawn_robot(RobotType.TERRAFORMER, row, col):
                        self.game_state.spawn_robot(RobotType.TERRAFORMER, row, col)

        return


    def play_turn(self, game_state: GameState) -> None:

        # get info
        ginfo = game_state.get_info()
        self.game_state = game_state

        # Extract information

        if ginfo.turn <= 2:
            self.initial_two_turns(game_state)
        else:
            self.general_mining_turn(game_state)
            self.terraforming_phase()




