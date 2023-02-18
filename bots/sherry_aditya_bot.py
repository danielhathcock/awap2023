from src.game_constants import RobotType, Direction, Team, TileState, GameConstants
from src.game_state import GameState, GameInfo
from src.player import Player
from src.map import TileInfo, RobotInfo
import random

class Mining_Logistics:
  def __init__(self, coordinates, direction=None, robots=[]):
    self.mining_coordinates = coordinates
    self.miners = robots # should just be a list of names
    self.mine2tt = direction # Vector mining location --> terraforming tile direction
    self.tt2mine = (-1 * self.mine2tt[0], -1* self.mine2tt[1])


class BotPlayer(Player):
    """
    Players will write a child class that implements (notably the play_turn method)
    """

    def __init__(self, team: Team):
        self.team = team
        self.mining_assignment = dict() # A dictionary mapping mines to a Mining_Logistics object
        return

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
                        if game_state.can_move_robot(rname, move_dir):
                            game_state.move_robot(rname, move_dir)
            if game_state.can_robot_action(rname):
                game_state.robot_action(rname) # action the robots


        # spawn robots
        for mine_info in initial_mine_list:
            tt_coordinates = mine_info['tt']
            t_direction = mine_info['td'].value() # From TT --> mining location
            mining_coordinates = (tt_coordinates[0] + t_direction[0], tt_coordinates[1] + t_direction[1])

            if 2 >= mine_info['c'] > len(self.mining_assignment[mining_coordinates]):
                if game_state.can_spawn_robot(RobotType.MINER, tt_coordinates[0], tt_coordinates[1]): # spawn the robots
                    new_miner = game_state.spawn_robot(RobotType.MINER, tt_coordinates[0], tt_coordinates[1])

                    self.mining_assignment[mining_coordinates].mine2tt = (-1 * t_direction[0], -1 * t_direction[1])
                    self.mining_assignment[mining_coordinates].miners.add(new_miner)
            else:
                raise Exception("Number of robots for a single mine can't be larger than 2!")


    def general_mining_turn(self, game_state: GameState, new_mines=[]) -> None:
        ginfo = game_state.get_info()
        robots = game_state.get_ally_robots()

        # moving, actioning, or recharging
        for mining_location in self.mining_assignment.keys():
            logistics = self.mining_assignment[mining_location]
            these_robots = logistics.miners

            if len(these_robots) <= 2: # FIX!!!!!!!!!!
                miner = robots[0]
                if (miner.row, miner.col) == mining_location:
                    if miner.battery >= GameConstants.MINER_ACTION_COST:
                        game_state.robot_action(miner)
                    else:
                        game_state.move_robot(miner, Direction(logistics.mine2tt))
                elif (miner.row, miner.col) == (mining_location[0] + logistics.mine2tt[0], mining_location[1] + logistics.mine2tt[1]):
                    if miner.battery == GameConstants.INIT_BATTERY:
                        game_state.move_robot(miner, Direction(logistics.tt2mine))
                else:
                    raise Exception("Miners aren't in the right place!!")
            elif len(these_robots) == 2:
                1 + 1
            else:
                raise Exception("Way too  many robots here...")

        # spawning
        #for mining_location in new_mines:




    def play_turn(self, game_state: GameState) -> None:

        # get info
        ginfo = game_state.get_info()

        # Extract information
        current_map = ginfo.map
        for x in range(len(current_map)):
            for y in range(len(current_map[0])):
                if current_map[x][y] == TileState.MINING and (x, y) not in self.mining_assignment.keys():
                    self.mining_assignment[(x, y)] = Mining_Logistics(coordinates=(x, y))

        if ginfo.turn < 2:
            self.initial_two_turns(game_state)
        else:
            self.general_mining_turn()



