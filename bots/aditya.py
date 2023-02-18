def sorted_mines(map):
    """ Input is map object list(list[TileInfo]) """
    height, width = len(map), len(map[0])
    mines = []
    for row in map:
        for tile in row:
            if tile.state == TileState.TERRAFORMABLE:
                mines.append(tile)
    mines.sort(key = lambda x: - x.mining)
    # mines is sorted in decreasing order of capacity
    return mines

def first_decision(map):
    """ Decide how many miners to start with, and where to place them.
     Returns list of dictionaries, sorted by capacity """
    height, width = len(map), len(map[0])
    gmt = 15    #Good Mine Threshold
    def get_terra_tile(mine):
        """ Returns a dictionary with keys (tt, td) = (adjacent terra tile, directions FROM the terra tile) """
        x, y = mine.row, mine.column
        D = {}
        for t in Direction:
            p, q = t.value()
            nx, ny = x - p , y - q
            if 0 <= nx < height and 0 <= ny < width and map[nx][ny].state == TileState.TERRAFORMABLE:
                D['tt'], D['td'] = (nx, ny), t
        return D

    M = self.sorted_mines(map)
    decision_list = [] #This is a list of dictionaries with keys tt,td,c : Terra Tile, Terra_to_mine Direction, Count

    if len(M)==1:
        D = get_terra_tile(M[0])
        D['c'] = 2
        decision_list.append(D)

    elif len(M)==2:
        [m1, m2] = M
        D1, D2 = get_terra_tile(m1), get_terra_tile(m2)
        p1, p2 = m1.mining, m2.mining
        c1, c2 = 1 if p1 < gmt else 2, 1 if p2 < gmt else 2
        D1['c'], D2['c'] = c1, c2
        decision_list.append(D1)
        decision_list.append(D2)

    elif len(M)==3:
        [m1, m2, m3] = M
        D1, D2, D3 = get_terra_tile(m1), get_terra_tile(m2), get_terra_tile(m3)
        p1, p2, p3 = m1.mining, m2.mining, m3.mining
        if p2 < gmt :
            if 0.4 * p1 >= 0.6 * p2 : c1, c2, c3 = 2, 0, 0
            else: c1, c2, c3 = 1, 1, 0
        else:
            if 0.4 * p2 >= 0.6 * p3 : c1, c2, c3 = 2, 2, 0
            else: c1, c2, c3 = 2, 1, 1
        D1['c'], D2['c'], D3['c'] = c1, c2, c3
        if c1: decision_list.append(D1)
        if c2: decision_list.append(D2)
        if c3: decision_list.append(D3)

    else:
        [m1, m2, m3, m4] = M[:4]
        D1, D2, D3, D4 = get_terra_tile(m1), get_terra_tile(m2), get_terra_tile(m3), get_terra_tile(m4)
        p1, p2, p3, p4 = m1.mining, m2.mining, m3.mining, m4.mining
        if p2 < gmt :
            if 0.4 * p1 >= 0.6 * p2 : c1, c2, c3, c4 = 2, 0, 0, 0
            else : c1, c2, c3, c4 = 1, 1, 0, 0
        else:
            if 0.4 * p2 >= o.6 * p3 : c1, c2, c3, c4 = 2, 2, 0, 0
            elif 0.4 * p1 < 0.6 * p4 : c1, c2, c3, c4 = 1, 1, 1, 1
            else: c1, c2, c3, c4 = 2, 1, 1, 0
        D1['c'], D2['c'], D3['c'], D4['c'] = c1, c2, c3, c4
        if c1: decision_list.append(D1)
        if c2: decision_list.append(D2)
        if c3: decision_list.append(D3)
        if c4: decision_list.append(D4)

    return decision_list
