from pwn import *

# Send a guess, get a result
def test(guess):
    conn.recvuntil(b'Your input: ')
    guess_hex = hex(guess)[2:]
    guess_hex = '0'*(32-len(guess_hex)) + guess_hex
    conn.sendline(guess_hex.encode())

    output = conn.recvline().decode() # Wrong! 4292837375 is not zero!
    
    if not output.startswith('Wrong!'):    
        return output
    
    result = int(output.split(' ')[1])
    return result

# Get the next guess based on the current guess and the result
def get_next_part(current_part, result_part):
    if result_part == 0:
        return current_part
    current_part += 1
    current_part &= 0xF
    return current_part

# Combine the pieces into one integer
def combine_parts(parts):
    parts_copy = parts.copy()
    sum = 0
    for i in range(4):
        for j in range(32):
            sum <<= 1
            sum |= parts_copy[j] & 1
            parts_copy[j] >>= 1
    return sum

# Get the bits of the result (in the right order)
def get_result_parts(result):
    result_parts = []
    for i in range(4):
        for j in range(8):
            # weird shift amount based on binary representation of integers
            shift = i * 8 + (7 - j)
            result_part = (result >> shift) & 1
            result_parts.append(result_part)
    return result_parts

conn = None

# Put the pieces together and solve
def solve():
    global conn

    # init connection
    context.log_level = 'error'
    conn = remote('compare-me.ctf.bsidestlv.com', 4545)

    current_parts = [0 for x in range(32)]

    # 20 attempts, but we only need 16
    for i in range(16):
        # Combine the parts
        combined = combine_parts(current_parts)
        
        # Guess and get the result
        result = test(combined)

        # The result is a string if the guess was correct
        if isinstance(result, str):
            print('Solved:', result)
            break

        # Get the parts from the result
        result_parts = get_result_parts(result)
        
        # Setup next guesses based on the result's parts
        for i in range(32):
            current_parts[i] = get_next_part(current_parts[i], result_parts[i])
    
    conn.recvall(2)

    # close connection
    conn.close()

if __name__ == '__main__':
    solve()