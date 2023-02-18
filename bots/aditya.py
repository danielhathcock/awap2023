from src.game_constants import RobotType, Direction, Team, TileState, GameConstants
from src.game_state import GameState, GameInfo
from src.player import Player
from src.map import TileInfo, RobotInfo


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

    T = self.assigned_terra.copy()

    def get_terra_tile(mine):
        """ Returns a dictionary with keys (tt, td) = (adjacent terra tile, directions FROM the terra tile) """
        x, y = mine.row, mine.col
        D, terras = {}, []
        for t in Direction:
            p, q = t.value
            nx, ny = x - p, y - q
            if 0 <= nx < height and 0 <= ny < width and map[nx][ny] and map[nx][ny].state == TileState.TERRAFORMABLE:
                terras.append( ( (nx,ny) , t) )

        if not terras: return {}
        for i,t in terras:
            if i not in T:
                T.add(i)
                D['tt'], D['td'] = i, t
                break
        if not D: D['tt'], D['td'] = terras[0]
        return D

    M = self.sorted_mines(map)
    decision_list = []  # This is a list of dictionaries with keys tt,td,c : Terra Tile, Terra_to_mine Direction, Count

    if not M:
        return {}

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
    T = self.assigned_terra.copy()

    def get_terra_tile(mine):
        """ Returns a dictionary with keys (tt, td) = (adjacent terra tile, directions FROM the terra tile) """
        x, y = mine.row, mine.col
        D, terras = {}, []
        for t in Direction:
            p, q = t.value
            nx, ny = x - p, y - q
            if 0 <= nx < height and 0 <= ny < width and map[nx][ny] and map[nx][ny].state == TileState.TERRAFORMABLE:
                terras.append(((nx, ny), t))

        if not terras: return {}
        for i, t in terras:
            if i not in T:
                T.add(i)
                D['tt'], D['td'] = i, t
                break
        if not D: D['tt'], D['td'] = terras[0]
        return D

    New_mines = []
    New_decisions = []
    for row in map:
        for tile in row:
            if tile and tile.state == TileState.MINING and ((tile.row, tile.col) not in S):
                New_mines.append(tile)

    New_mines.sort(key=lambda x: -x.mining)
    for mine in New_mines:
        D = get_terra_tile(mine)
        if D:
            D['c'] = 1
            New_decisions.append(D)
    return New_decisions