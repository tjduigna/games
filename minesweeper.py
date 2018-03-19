# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# Copyright (c) 2018, Thomas J. Duignan
# Distributed under the terms of the Apache License 2.0
"""A minesweeper clone by Thomas J. Duignan."""

import curses
from random import randint

class Cell(object):
    """A plot of land in a mine field.
    
    Args
        d (int): dimension of the full board.
        i (int): the i'th row in the board. 
        j (int): the j'th column in the board.
        value (int): number of adjacent mines. (default=0)
        view (str): the display value of the cell. (default='O')
    """

    def update_view(self, mark=False):
        """Update the display value of the cell."""
        if mark: 
            self.view = 'M'
        elif self.value == 'M': 
            return
        elif self.value < 0:
            self.view = 'X'
            return False
        elif self.value: 
            self.view = self.value 
        elif self.view:
            self.view = ''
            return True

    def __str__(self):
        return '{:^3}'.format(self.view)

    def __init__(self, d, i, j, value=0, view='O'):
        self.view = view 
        self.value = value
        self.ir = 1 if i == d - 1 else bool(i) - 1 
        self.jr = 1 if j == d - 1 else bool(j) - 1


class Board(object):
    """A collection of mine field cells. 

    Args 
        d (int): dimension of the grid.
        diff (int): difficulty from 0-2."""

    _ranges = {-1: range(0, 2), 
                0: range(-1, 2), 
                1: range(-1, 1)}

    @property 
    def shape(self):
        """Shape of the board including grid padding."""
        return (self.d * 4 + 1, 2 * self.d + 2)

    def won(self):
        """Return True if all mines are flagged."""
        cnt = len([cell for cell in self.values()
                   if cell.value < 0 
                   and cell.view == 'M'])
        if cnt == self.bomb: return True

    def update_view(self, tup, mark=None):
        """Update the view of the grid based on user input."""
        cell = self[tup]
        old = cell.view 
        save = cell.update_view(mark)
        new = cell.view 
        if save is not None and not save:
            return False
        if new == 'M' and old != 'M':
            self.left -= 1
        elif old == 'M' and new != 'M':
            self.left += 1
        if save:
            self._traverse_empty(tup)
        return self.won()

    def _traverse_empty(self, tup):
        """Recursively reveal empty neighbor cells."""
        cache = []
        for ij in self._iter_neighbors(tup): 
            save = self[ij].update_view()
            if save: cache.append(ij)
        for adj in cache: self._traverse_empty(adj)

    def _iter_neighbors(self, tup):
        """Given a cell, iterate over all neighbor cells."""
        i, j = tup
        for k in self._ranges[self[tup].ir]:
            for l in self._ranges[self[tup].jr]:
                x = i + k
                y = j + l
                if (self[(x, y)].value < 0
                    or (i, j) == (x, y)): 
                    continue
                yield (x, y)

    def _increment(self, tup):
        """Count neighboring mines."""
        for xy in self._iter_neighbors(tup):
            self[xy].value += 1

    def values(self): return self.grid.values()
    def items(self): return self.grid.items()
    def __getitem__(self, tup): 
        return self.grid.__getitem__(tup)
    def __setitem__(self, tup, val): 
        return self.grid.__setitem__(tup, val)

    def __str__(self):
        f = '{:^3}'
        fmt = f.format
        s = fmt('') 
        r = range(self.d)
        hdr = s + ((' ' + f) * self.d + '\n').format(*r)
        lbrk = s + '-' * (self.shape[0]) + '\n'
        ret = hdr + lbrk
        for i in range(self.d):
            pos = fmt(i)
            ret += ('|'.join([pos] + [str(self[(i, j)]) 
                    for j in range(self.d)] + [pos + '\n'])
                    + lbrk)
        return ret + hdr

    def __init__(self, d, diff=0):
        self.d = d
        self.diff = diff
        self.grid = {(i, j): Cell(d, i, j) 
                     for i in range(d) 
                     for j in range(d)}
        modes = {0: 8, 1: 6, 2: 4}
        self.bomb = d ** 2 // modes[diff]
        self.left = self.bomb 
        mines = set()
        while len(mines) < self.bomb:
            tup = (randint(0, d - 1), 
                   randint(0, d - 1))
            if tup in mines: continue 
            mines.add(tup)
            self[tup].value = -1 
            self._increment(tup)


def curses_driver(scr, board):
    """A gameplay interface using curses."""

    def _scr_to_grid(b, ax, ay):
        """Generate a dictionary of all cursor tuples 
        that correspond to cell positions."""
        mapr = {}
        cy = ay
        for i in range(b.d):
            cx = ax
            cy += 1
            for j in range(b.d):
                cx += 1
                for k in range(3):
                    mapr[(cx + k, cy)] = (i, j)
                cx += 3
            cy += 1
        return mapr

    def _draw_board(scr, ax, ay, lbrk, board):
        """Draw the board with color highlighting 
        corresponding to cell views."""
        cy = ay
        for i in range(board.d):
            cx = ax 
            scr.addstr(cy, cx, lbrk)
            cy += 1
            for j in range(board.d):
                cell = board[(i, j)]
                scr.addstr(cy, cx, '|')
                cx += 1
                if cell.view == 'X': clr = 9
                elif cell.view == 'O': clr = 10
                elif cell.view == 'M': clr = 11
                else: clr = cell.value
                scr.attron(curses.color_pair(clr))
                scr.addstr(cy, cx, str(cell))
                scr.attroff(curses.color_pair(clr))
                cx += 3
            scr.addstr(cy, cx, '|')
            cy += 1
        cx = ax
        scr.addstr(cy, cx, lbrk)

    # Init
    k = 0
    bx, by = board.shape
    lbrk = '-' * bx
    reset = set([78, 110]) # 'n', 'N'
    marks = set([77, 109]) # 'm', 'M'
    revls = set([10, 32])  # 'enter', 'space'
    both = marks.union(revls)
    ph, pw = None, None
    won, lost = False, False

    # Curses setup
    scr.clear()
    scr.refresh()
    curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_WHITE)
    curses.init_pair(2, curses.COLOR_GREEN,curses.COLOR_WHITE)
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_WHITE)
    curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_WHITE)
    curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_WHITE)
    curses.init_pair(6, curses.COLOR_YELLOW, curses.COLOR_WHITE)
    curses.init_pair(7, curses.COLOR_GREEN, curses.COLOR_WHITE)
    curses.init_pair(8, curses.COLOR_RED, curses.COLOR_WHITE)
    curses.init_pair(9, curses.COLOR_WHITE, curses.COLOR_RED)
    curses.init_pair(10, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(11, curses.COLOR_WHITE, curses.COLOR_YELLOW)
    curses.init_pair(12, curses.COLOR_BLACK, curses.COLOR_WHITE)

    # User input loop
    while (k != ord('q')):
        scr.clear()
        h, w = scr.getmaxyx()
        ax = (w - bx) // 2
        ay = (h - by) // 2

        # Cache _scr_to_grid mapr so we don't need to
        # re-make the mapr unless the screen resizes.
        if ph is None:
            cx = ax - 1
            cy = ay - 1
            mapr = _scr_to_grid(board, ax, ay)
            ph, pw = h, w
        else:
            if h < bx + 2 or w < by + 2:
                raise Exception("Terminal was resized "
                                "too small for game.")
            if ph != h or pw != w:
                mapr = _scr_to_grid(board, ax, ay)
                ph, pw = h, w

        # Move the cursor with the directional-pad
        if k == curses.KEY_DOWN: cy = cy + 1
        elif k == curses.KEY_UP: cy = cy - 1
        elif k == curses.KEY_RIGHT: cx = cx + 1
        elif k == curses.KEY_LEFT: cx = cx - 1

        # Keep the cursor in bounds and draw the board
        cx = min(w - 1, max(0, cx))
        cy = min(h - 1, max(0, cy))
        _draw_board(scr, ax, ay, lbrk, board)

        # The `heads-up display` interface
        rules = ["| 'enter' or 'space' to reveal",
                 "| 'm' or 'M' to mark k={}".format(k),
                 "| 'q' to quit",
                 "| {} mines remaining".format(board.left)]
        if lost: rules.append("| Game over!")
        elif won: rules.append("| You win!")
        if len(rules) == 5: 
            rules.append("| 'n' to reset board")
        pad = max([len(rule) for rule in rules])
        scr.attron(curses.color_pair(12))
        for i, rule in enumerate(rules):
            padded = ' ' * (pad - len(rule) + 2) + '|'
            scr.addstr(i, 0, rule + padded)
        scr.attroff(curses.color_pair(12))

        # Update cursor and accept input
        scr.move(cy, cx)
        scr.refresh()
        k = scr.getch()

        # Check for win condition // reset
        if (cx, cy) in mapr and k in both:
            kws = {} if k in revls else {'mark': True}
            chk = board.update_view(mapr[(cx, cy)], **kws)
            if (chk is not None and not chk) or lost: lost = True
            if chk and not lost: won = True
        elif k in reset:
            board = Board(board.d, board.diff)
            lost, won = False, False
            bx, by = board.shape
            lbrk = '-' * bx
            _draw_board(scr, ax, ay, lbrk, board)


def command_line_driver(b):
    """Simple gameplay interface using stdout."""
    prompt = '''\
Enter a grid position: row,col[M to mark] 
(marks remaining in top left).'''
    lose = 'You stepped on a mine! GG.'
    win = 'You correctly identified all the mines! GG.'

    while True:
        print(b)
        tup, mark = interact(prompt, typ=tuple)
        chk = b.update_view(tup, mark)
        if chk is not None:
            print(b)
            print(win if chk else lose)
            exit()


def interact(prompt, typ=None):
    """Wait for valid input and parse appropriately."""
    while True:
        value = input(prompt)
        if value in ['q', 'exit', 'quit']:
            exit()
        if typ is not None:
            if typ == tuple:
                try:
                    return (typ([int(i) 
                                for i in value.lower()
                                .replace('m', '')
                                .split(',')]), 
                            'm' in value.lower())
                except:
                    print('Did not understand.')
                    continue
            try: 
                return typ(value)
            except:
                print('Did not understand.')
                continue 
        else:
            return value


def main():
    """Initialize configuration for the game."""
    dims = interact('''Hello, Welcome to Minesweeper. 
Please enter a grid size. [5-20]''', typ=int)
    dims = min(20, max(5, dims))
    diff = interact('''Please select a difficulty. 
0: Easy    1: Medium    2: Hard''', typ=int)
    diff = min(2, max(0, diff))
    board = Board(dims, diff) 
    drvr = interact('''\
Launch with curses? [Y/n]''', typ=str)
    if 'y' in drvr.lower(): 
        curses.wrapper(curses_driver, board)
    else: 
        command_line_driver(board)


if __name__ == '__main__': main()
