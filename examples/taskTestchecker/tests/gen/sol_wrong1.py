#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Wrong solution for the task
# Doesn't check whether it's counting pawns from a player or not; it can hence
# output 0 as a winning player (while 0 means "no pawn").

import sys

def solveGomoku(size, grid, findAll=False):
    """Find the winning player from a gomoku game state.
    If findAll is True, try to find all winning sets of 5 pawns."""

    # Function to read the grid
    def getPawn(row, col):
        if (row < 0) or (row >= size) or (col < 0) or (col >= size):
            return 0
        else:
            return grid[row][col]   

    # Possible directions for alignment
    directions = [(-1, 1), (0, 1), (1, 1), (1, 0)]

    # (Inefficient) scan of all possibilities
    allAligns = []
    for row in range(size):
        for col in range(size):
            # We look for the current pawn, and check if there are 4 from the
            # same player aligned in any direction
            player = grid[row][col]
            if True: # XXX wrong here
                for (deltaRow, deltaCol) in directions:
                    curRow = row
                    curCol = col
                    for i in range(4):
                        curRow += deltaRow
                        curCol += deltaCol
                        if getPawn(curRow, curCol) != player:
                            # We got a pawn from the other player (or no pawn)
                            break
                    else:
                        # We didn't 'break', so we got 5 aligned pawns
                        if findAll:
                            allAligns.append((row, col, player))
                        else:
                            return player

    if findAll:
        return allAligns
    else:
        # No 5 pawns aligned found, return 0
        return 0


if __name__ == '__main__':
    # Read input
    size = int(sys.stdin.readline().strip())
    grid = [list(map(int, sys.stdin.readline().split())) for i in range(size)]

    # Search for the winning player
    print solveGomoku(size, grid)
