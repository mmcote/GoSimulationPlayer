EMPTY = 0
BLACK = 1
WHITE = 2
BORDER = 3
FLOODFILL = 4
import numpy as np
from pattern import pat3set
import sys
import random

class GoBoardUtil(object):
    
    @staticmethod       
    def playGame(board, color, **kwargs):
        komi = kwargs.pop('komi', 0)
        limit = kwargs.pop('limit', 1000)
        check_selfatari = kwargs.pop('selfatari', True)
        pattern = kwargs.pop('pattern', True)
        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)
        numPass = 0
        for _ in range(limit):
            move = GoBoardUtil.generate_move_with_filter(board,pattern,check_selfatari)
            if move != None:
                # print("move ", move,type(move), "color  ",  color,type(color), '\n')
                isLegalMove = board.move(move,color)
                assert isLegalMove
                numPass = 0
            else:
                board.move(move,color)
                numPass += 1
                if numPass == 2:
                    break
            color = GoBoardUtil.opponent(color)
        winner = board.get_winner(komi)
        return winner
    
    @staticmethod
    def generate_legal_moves(board, color):
        """
        generate a list of legal moves

        Arguments
        ---------
        board : np.array
            a SIZExSIZE array representing the board
        color : {'b','w'}
            the color to generate the move for.
        """
        empty = board.get_empty_points()
        legal_moves = []
        for move in empty:
            if board.check_legal(move, color):
                legal_moves.append(move)
        return legal_moves

    @staticmethod
    def sorted_point_string(points, ns):
        result = []
        if isinstance(points[0], list):
            points = points[0]

        for point in points:
            if point is None:
                continue
            x, y = GoBoardUtil.point_to_coord(point, ns)
            result.append(GoBoardUtil.format_point((x, y)))
        return ' '.join(sorted(result))

    @staticmethod
    def generate_pattern_moves(board):
        color = board.current_player
        pattern_checking_set = board.last_moves_empty_neighbors()
        moves = []
        for p in pattern_checking_set:
            if (board.neighborhood_33(p) in pat3set):
                assert p not in moves
                assert board.board[p] == EMPTY
                moves.append(p)
        return moves
        
    @staticmethod
    def generate_all_policy_moves(board,pattern,check_selfatari):
        """
            generate a list of policy moves on board for board.current_player.
            Use in UI only. For playing, use generate_move_with_filter
            which is more efficient
        """
        atari_capture_move = GoBoardUtil.captures_atari(board,board.last_move, board.current_player)
        if atari_capture_move:
            return [atari_capture_move], "AtariCapture"
        atari_defense_move = GoBoardUtil.defends_atari(board, board.current_player)
        # print(type(atari_defense_move))
        if len(atari_defense_move)!=1 or atari_defense_move[0]!=None:
            return atari_defense_move, "AtariDefense"

        pattern_moves = GoBoardUtil.generate_pattern_moves(board)
        pattern_moves = GoBoardUtil.filter_moves(board, pattern_moves, check_selfatari)
        if len(pattern_moves) > 0:
            return pattern_moves, "Pattern"
        return GoBoardUtil.generate_random_moves(board), "Random"

    @staticmethod
    def generate_random_moves(board):
        empty_points = board.get_empty_points()
        color = board.current_player
        moves = []
        for move in empty_points:
            if board.check_legal(move, color) and not board.is_eye(move, color):
                moves.append(move)
        return moves

    @staticmethod
    def generate_random_move(board):
        color = board.current_player
        moves = board.get_empty_points()
        while len(moves) > 0:
            index = random.randint(0,len(moves) - 1)
            move = moves[index]
            if board.check_legal(move, color) and not board.is_eye(move, color):
                return move
            else:
                # delete moves[index] by overwriting with last in list
                lastIndex = len(moves) - 1
                if index < lastIndex:
                    moves[index] = moves[lastIndex]
                moves.pop()
        return None

    @staticmethod
    def filter_moves(board, moves, check_selfatari):
        color = board.current_player
        good_moves = []
        for move in moves:
            if not GoBoardUtil.filter(board,move,color,check_selfatari):
                good_moves.append(move)
        return good_moves

    # return True if move should be filtered
    @staticmethod
    def filleye_filter(board, move, color):
        assert move != None
        return not board.check_legal(move, color) or board.is_eye(move, color)
    
    # return True if move should be filtered
    @staticmethod
    def selfatari_filter(board, move, color):
        return (  GoBoardUtil.filleye_filter(board, move, color)
               or GoBoardUtil.selfatari(board, move, color)
               )

    # return True if move should be filtered
    @staticmethod
    def filter(board, move, color, check_selfatari):
        if check_selfatari:
            return GoBoardUtil.selfatari_filter(board, move, color)
        else:
            return GoBoardUtil.filleye_filter(board, move, color)

    def captures_atari(board, to_capture, color):
        # print("board is  ", board, type(board), '\n')
        # print('to_capture is ', to_capture, type(to_capture), '\n')
        # print('color is ', color, type(color), '\n')
        if to_capture is None:
            return None
        num_libs, position = board.num_liberties_and_positions(to_capture, GoBoardUtil.opponent(color))

        if num_libs == 1:
            if not GoBoardUtil.selfatari_filter(board, position[0], color):
                return position[0]
        return None

    def captures_atari_new(board, previous_move, color):
        num_libs, position, points_explored = board.num_liberties_and_positions_and_checked_positions(previous_move, GoBoardUtil.opponent(color))

        if num_libs == 1:
            if not GoBoardUtil.selfatari_filter(board, position[0], color):
                return position[0], None
        return None, points_explored

    def defends_atari(board, color):
        
        if board.last_move is None:
            return [None]
        possible_move_list=list()
        # get list of neghbouring points ot last move
        points = board._neighbors(board.last_move)
        # Collector for our points
        player_points = []
        # print(str(points))
        for point in points:
            # If neigbour is our color and if it's in atari
            if board.board[point] == color and GoBoardUtil.captures_atari(board, point, GoBoardUtil.opponent(color)):
                player_points.append(point)
        #print(str(player_points))
        if len(player_points) > 0:
            first_atari = player_points[0]
            # Return only point we can play
            move = GoBoardUtil.captures_atari(board, first_atari, GoBoardUtil.opponent(color))
            #Simulate the next move
            simul_board = board.copy()
            # See if we move to that point
            legal = board.check_legal(move, color)
            simul_board.move(move, color)
            # can opponent capture that point then
            opponent_capture_point = GoBoardUtil.captures_atari(simul_board, simul_board.last_move, GoBoardUtil.opponent(color))
            # If opponent can't capture point, it's a runaway
            if not opponent_capture_point and legal:
            #     # print("Option 01 Taken")
                possible_move_list.append(move)
            
            # print("Option 02 Taken")
            # Captures enemies last move or returns None
            capture_move = GoBoardUtil.find_capture_point(board, first_atari, color)
            possible_move_list.append(capture_move)
            # print("move is ", move, type(move), '\n')
            return possible_move_list
        return [None]



    def find_capture_point(board, point, color):
        # set of opponent points that do have been checked
        opponentPointsChecked = set()
        # which of our own points are to be explored next
        toExplore = board._neighbors(point)
        # points of our own which have been explored
        explored = []
        while len(toExplore) > 0:
            # pop the next to explore
            currentPosition = toExplore.pop()
            # is it your own team? and has it been explored?
            if board.board[currentPosition] == color and currentPosition not in explored:
                toExplore = toExplore + board._neighbors(point)
                explored.append(currentPosition)
            elif board.board[currentPosition] == GoBoardUtil.opponent(color) and currentPosition not in opponentPointsChecked:
                # simulate capturing block
                simul_board = board.copy()
                atariPoint, pointsChecked = GoBoardUtil.captures_atari_new(simul_board, currentPosition, color)
                if atariPoint:
                    return atariPoint
                else:
                    opponentPointsChecked.add(currentPosition)
                    opponentPointsChecked.union(pointsChecked)
        return None
            
        def find_north_south_opponent(board, point, direction, color):
            current_point = point
            #content of board at current point
            content = board[current_point]
            opponent = GoBoardUtil.opponent(color)
            while(content != BORDER or content != opponent):
                current_point = current_point + (direction * board.size)
                content = board[current_point]
            # If we've reached a board, we can't capture borders
            if(content == BORDER):
                return None
            else:
                return current_point
                
        def find_east_west_opponent(board, point, direction, color):
            current_point = point
            #content of board at current point
            content = board[current_point]
            opponent = GoBoardUtil.opponent(color)
            # Travel in direction until we reach board or find opponent
            while(content != BORDER or content != opponent):
                current_point = current_point + (direction * 1)
                content = board[current_point]
            # If we've reached a board, we can't capture borders
            if(content == BORDER):
                return None
            else:
                return current_point
            
    @staticmethod 
    def filter_moves_and_generate(board, moves, check_selfatari):
        color = board.current_player
        while len(moves) > 0:
            candidate = random.choice(moves)
            if GoBoardUtil.filter(board, candidate, color, check_selfatari):
                moves.remove(candidate)
            else:
                return candidate
        return None
        
    @staticmethod
    def generate_move_with_filter(board, use_pattern, check_selfatari):
        """
            Arguments
            ---------
            check_selfatari: filter selfatari moves?
                Note that even if True, this filter only applies to pattern moves
            use_pattern: Use pattern policy?
        """
        move = None
        

        atari_capture_move = GoBoardUtil.captures_atari(board,board.last_move, board.current_player)
        if atari_capture_move:
            return atari_capture_move
        atari_defense_move = GoBoardUtil.defends_atari(board, board.current_player)
        if len(atari_defense_move)!=1 or atari_defense_move[0]!=None:
            return atari_defense_move



        if use_pattern:
            moves = GoBoardUtil.generate_pattern_moves(board)
            move = GoBoardUtil.filter_moves_and_generate(board, moves, 
                                                         check_selfatari)
        if move == None:
            move = GoBoardUtil.generate_random_move(board)
        return move 

        
        
        



    
    @staticmethod
    def selfatari(board, move, color):
        max_old_liberty = GoBoardUtil.blocks_max_liberty(board, move, color, 2)
        if max_old_liberty > 2:
            return False
        cboard = board.copy()
        # swap out true board for simulation board, and try to play the move
        isLegal = cboard.move(move, color) 
        if isLegal:               
            new_liberty = cboard._liberty(move,color)
            if new_liberty==1:
                return True 
        return False

    @staticmethod
    def blocks_max_liberty(board, point, color, limit):
        assert board.board[point] == EMPTY
        max_lib = -1 # will return this value if this point is a new block
        neighbors = board._neighbors(point)
        for n in neighbors:
            if board.board[n] == color:
                num_lib = board._liberty(n,color) 
                if num_lib > limit:
                    return num_lib
                if num_lib > max_lib:
                    max_lib = num_lib
        return max_lib
        
    @staticmethod
    def format_point(move):
        """
        Return coordinates as a string like 'a1', or 'pass'.

        Arguments
        ---------
        move : (row, col), or None for pass

        Returns
        -------
        The move converted from a tuple to a Go position (e.g. d4)
        """
        column_letters = "abcdefghjklmnopqrstuvwxyz"
        if move is None or move == 'pass':
            return "pass"
        row, col = move
        if not 0 <= row < 25 or not 0 <= col < 25:
            raise ValueError
        return    column_letters[col - 1] + str(row) 
        
    @staticmethod
    def move_to_coord(point, board_size):
        """
        Interpret a string representing a point, as specified by GTP.

        Arguments
        ---------
        point : str
            the point to convert to a tuple
        board_size : int
            size of the board

        Returns
        -------
        a pair of coordinates (row, col) in range(1, board_size+1)

        Raises
        ------
        ValueError : 'point' isn't a valid GTP point specification for a board of size 'board_size'.
        """
        if not 0 < board_size <= 25:
            raise ValueError("board_size out of range")
        try:
            s = point.lower()
        except Exception:
            raise ValueError("invalid point")
        if s == "pass":
            return None
        try:
            col_c = s[0]
            if (not "a" <= col_c <= "z") or col_c == "i":
                raise ValueError
            if col_c > "i":
                col = ord(col_c) - ord("a")
            else:
                col = ord(col_c) - ord("a") + 1
            row = int(s[1:])
            if row < 1:
                raise ValueError
        except (IndexError, ValueError):
            raise ValueError("wrong coordinate")
        if not (col <= board_size and row <= board_size):
            raise ValueError("wrong coordinate")
        return row, col
    
    @staticmethod
    def opponent(color):
        opponent = {WHITE:BLACK, BLACK:WHITE} 
        try:
            return opponent[color]    
        except:
            raise ValueError("Wrong color provided for opponent function")
            
    @staticmethod
    def color_to_int(c):
        """convert character representing player color to the appropriate number"""
        color_to_int = {"b": BLACK , "w": WHITE, "e":EMPTY, "BORDER":BORDER, "FLOODFILL":FLOODFILL}
        try:
           return color_to_int[c] 
        except:
            raise ValueError("wrong color")
    
    @staticmethod
    def int_to_color(i):
        """convert number representing player color to the appropriate character """
        int_to_color = {BLACK:"b", WHITE:"w", EMPTY:"e", BORDER:"BORDER", FLOODFILL:"FLOODFILL"}
        try:
           return int_to_color[i] 
        except:
            raise ValueError("Provided integer value for color is invalid")
         
    @staticmethod
    def copyb2b(board, copy_board):
        """Return an independent copy of this Board."""
        copy_board.board = np.copy(board.board)
        copy_board.suicide = board.suicide  # checking for suicide move
        copy_board.winner = board.winner 
        copy_board.NS = board.NS
        copy_board.WE = board.WE
        copy_board._is_empty = board._is_empty
        copy_board.passes_black = board.passes_black
        copy_board.passes_white = board.passes_white
        copy_board.current_player = board.current_player
        copy_board.ko_constraint =  board.ko_constraint 
        copy_board.white_captures = board.white_captures
        copy_board.black_captures = board.black_captures 

        
    @staticmethod
    def point_to_coord(point, ns):
        """
        Transform one dimensional point presentation to two dimensional.

        Arguments
        ---------
        point

        Returns
        -------
        x , y : int
                coordinates of the point  1 <= x, y <= size
        """
        # result_list = list()
        # if isinstance(point, list):
        #     for item in point:
        #         if point is None:
        #             pass


        if point is None:
            return 'pass'
        # printpoint ", point, type(point), '\n')
        row, col = divmod(point, ns)
        return row,col

