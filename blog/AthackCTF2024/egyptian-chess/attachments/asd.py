from pwn import *

#context.log_level = 'debug'

REMOTE_HOST = '192.168.20.87'
REMOTE_PORT = 12345

ENGINE_PATH = './Pikafish.2023-12-03/Linux/pikafish-sse41-popcnt'
NNUE_PATH = './Pikafish.2023-12-03/pikafish.nnue'

conn = remote(REMOTE_HOST, REMOTE_PORT)

# skip the banner
conn.recvuntil(b'>>> Press enter to start.')
conn.sendline()

# start the pikafish engine
engine = process(ENGINE_PATH)
engine.recvline()
engine.sendline(f'setoption name EvalFile value {NNUE_PATH}'.encode())

def read_player_move():
    # "Black to play", "White to play"
    player_move_line = conn.recvline().decode()
    player_move = player_move_line[0].lower()
    return player_move # returns 'w' or 'b'

def read_board_text():
    board_text = b'\n'.join(conn.recvlines(19)) # read 19 lines
    board_text = board_text.decode() # decode to string
    return board_text

def parse_board_text(board_text):
    non_pieces = ['┼', '┬', '┴', '┤', '├', '┌', '┐', '└', '┘']
    translation = {
        '将': 'k', '士': 'a', '象': 'b', '馬': 'n', '車': 'r', '砲': 'c', '卒': 'p',
        '帅': 'K', '仕': 'A', '相': 'B', '马': 'N', '车': 'R', '炮': 'C', '兵': 'P',
        '┼': None, '┬': None, '┴': None, '┤': None, '├': None, '┌': None, '┐': None, '└': None, '┘': None
    }
    board = []
    for line in board_text.splitlines():
        # split the line by the horizontal line character
        # and only keep non-empty pieces
        pieces = [x for x in line.split('─') if len(x) > 0]
        if len(pieces) != 9:
            continue
        # replace non-piece characters with None
        pieces = [(None if x in non_pieces else translation[x]) for x in pieces]
        board.append(pieces)
    return board

def convert_board_to_fen(board, player_move):
    board_fen = ''
    for line in board:
        spaces = 0
        # iterate over pieces in line
        for piece in line:
            # increment spaces
            if piece == None:
                spaces += 1
                continue
            # append spaces and reset spaces
            elif spaces > 0:
                board_fen += str(spaces)
                spaces = 0
            # append piece
            board_fen += piece
        # append remaining spaces
        if spaces > 0:
            board_fen += str(spaces)
            spaces = 0
        # add line separator
        board_fen += '/'

    board_fen = board_fen[:-1] # trim last /
    board_fen += ' ' + player_move + ' - - 0 1'

    return board_fen

def get_best_move(board_fen):
    engine.sendline(f'position fen "{board_fen}"'.encode())
    engine.sendline(b'go depth 20')
    engine.recvuntil(b'bestmove ')
    move = engine.recvline().decode().split()[0]
    # convert 0-based to 1-based: a0a2 -> a1a3
    move = move[0] + str(int(move[1])+1) + move[2] + str(int(move[3])+1)
    return move

for i in range(3):
    player_move = read_player_move()
    print('Player move:', player_move)

    board_text = read_board_text()
    board = parse_board_text(board_text)

    board_fen = convert_board_to_fen(board, player_move)
    print('Board:', board_fen)

    best_move = get_best_move(board_fen)
    print('Best move:', best_move)
    conn.sendline(best_move.encode())
    
    result = conn.recvline().decode()
    print(result)

conn.interactive()