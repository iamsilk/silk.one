---
date: 2023-06-28
categories:
  - writeups
authors:
  - silk
tags:
  - misc
comments: true
---

# BSidesTLV 2023: compare_me writeup

**Prompt:**
> Can you guess a random 128-bit number?  
> If you do I have a flag for you!
> 
> `nc compare-me.ctf.bsidestlv.com 4545`

**Difficulty:** Medium

**Attachments:** [*challenge.zip*](./attachments/challenge.zip)

**Solution:** [*asd.py*](./attachments/asd.py)

## First Look

Firstly, we are given a .zip file containing the source code and Dockerfile of the application.

If we connect to the application through netcat, we get the following response:
```sh
$ nc compare-me.ctf.bsidestlv.com 4545
Welcome!
I have choosen a 128-bit random.
See if you can guess it with just 20 queries.
You can enter an empty line to exit.

(guess 1 out of 20) Your input: 
```

Let's try some input:
```sh
(guess 1 out of 20) Your input: 1
Bad input length 1 != 32

(guess 2 out of 20) Your input: 11111111111111111111111111111111
Wrong! 4294967287 is not zero!

(guess 3 out of 20) Your input: ^C
```

Jumping over to the source code (`compare_me.py`), we can get a better sense of what the program is doing.

First, it is setting up some `memcmp_all` function from the `memcmp_all.so` library. This library is probably compiled from the `memcmp_all.c` which we have yet to take a look at. 
```python
# memcmp_all to ensure constant time check
memcmp_all = CDLL('./memcmp_all.so').memcmp_all
memcmp_all.argtypes = [c_char_p, c_char_p, c_uint32]
memcmp_all.restype = c_uint32
```

We have the start of our main function, which loads the random number and the flag.
```python
def main():
    guess_me = os.urandom(16)
    flag = os.getenv("FLAG")
```

Some output text welcoming us and mentioning we only have 20 attempts.
```python
    print("Wellcome!")
    print("I have choosen a 128-bit random.")
    print("See if you can guess it with just 20 queries.")
    print("You can enter an empty line to exit.")
```

For each attempt, it verifies the input is 32. Then converts our input into a `bytes` object using the `fromhex` function.
```python
    for turn in range(20):
        req = input(f"\n(guess {turn+1} out of 20) Your input: ")
        if len(req) == 0:
            return
        if len(req) != 32:
            print(f'Bad input length {len(req)} != 32')
            continue
        guess = bytes.fromhex(req)
```

Our `guess` is then passed to the `memcmp_all` function. If `guess` matches `guess_me`, the return value will be zero and the flag will be printed.
```python
        ret = memcmp_all(guess_me, guess, 16)
        if ret == 0:
            print(f'Success! {flag}')
        else:
            print(f'Wrong! {ret} is not zero!')
    print("Too many attempts!")
```

Then the part of the script which calls `main`.
```python
if __name__ == "__main__":
    try:
        main()
        print("Bye!")
    except:
        print("Some error occured")
    sys.exit(0)
```

We can take a look at `memcmp_all.c` to get a better understanding of what the `memcmp_all` function is doing.

We can see `p1`, `p2`, and `compare_len` parameters corresponding to our `guess_me`, `guess`, `16` arguments in the Python script. 
```c
uint32_t memcmp_all(const void *p1, const void *p2, uint32_t compare_len) {
```

The parameters `p1` and `p2` are casted to a `uint32_t` pointer.
```c
  uint32_t result = 0;

  uint32_t *pDW1 = (uint32_t *)p1;
  uint32_t *pDW2 = (uint32_t *)p2;
  uint8_t *pByte1;
  uint8_t *pByte2;
```

While `compare_len` is greater than (or equal) to `sizeof(int)`, which is probably 4 (bytes), the loop runs.
```c
  while (compare_len >= sizeof(int)) {
  ```

The two `uint32_t` pointers are dereferenced, XORed together, then bitwise-ORed into `result`.
```c
    result |= (*pDW1 ^ *pDW2);
```

Then the pointers are incremented and `compare_len` is subtracted.
```c
    pDW1++;
    pDW2++;
    compare_len -= sizeof(int);
  }
```

The above loop is repeated, except with `uint8_t` to compare the final bytes, in case `compare_len` is not a multiple of 4. In our case, it is a multiple of 4 (16), so we do not need to worry about this loop.
```c
  pByte1 = (uint8_t *)pDW1;
  pByte2 = (uint8_t *)pDW2;

  while (compare_len > 0) {
    result |= (uint32_t)(*pByte1 ^ *pByte2);
    pByte1++;
    pByte2++;
    compare_len--;
  }
```

The result is then returned.
```
  return result;
}
```

## Solution

The solution depends on the fact we aren't simply told if `guess` and `guess_me` are equal, but instead we are given their comparison `result`. `result` tells us more information about what parts of `guess` and `guess_me` are and are not equal.

`guess` and `guess_me` are both 128 bits long, where as `result` is 32 bits long. The while loop in `memcmp_all` will loop 4 times. Therefore, `guess` and `guess_me` will be broken up into four separate `uint32_t` values, and then XORed together. The bits can be represented something like below:
```
guess ^ guess_me:
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

result:
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Each bit in the `result` above will be dependent on if the bits above it in `guess ^ guess_me` contain any 1s, as we know the `result` is the result of OR operations on these bits. For example:
```
guess ^ guess_me:
00xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
10xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
00xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
00xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

result:
10xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Then when all of `guess ^ guess_me` are zero, the result is zero, and `guess == guess_me` will be true. 

If each bit of the result is dependent on only four bits, then we don't have to guess a 128-bit integer. Instead, we need to guess 32 4-bit integers simultaneously. For each 4-bit integer, there are only 2^4=16 possibilities, which is less than our 20 tries.

Treating each column of the `guess ^ guess_me` representation as 4-bit integer, we can try each possible value (0, 1, 2, ... 15). Whenever the `result` bit for that column becomes 0, we know `guess` and `guess_me` match for that column, and we can stop guessing values for that column.

Now let's write some code to do that.

First, I wrote a function that takes in the current integer (representing the column) and the result's bit. If the result's bit is 0, the function returns the current guess. Otherwise, the function returns the next guess.
```python
def get_next_part(current_part, response_part):
    if response_part == 0:
        return current_part
    current_part += 1
    current_part &= 0xF
    return current_part
```

Next up, we need to be able to combine these parts into a single integer that can be passed to the application.
```python
def combine_parts(parts):
    parts_copy = parts.copy()
    sum = 0
    for i in range(4):
        for j in range(32):
            sum <<= 1
            sum |= parts_copy[j] & 1
            parts_copy[j] >>= 1
    return sum
```

We also need to be able to take the result from the server, and break it up into its bits. We need to make sure these bits line up with our parts. This was a little bit of a headache to figure out, but we just need to calculate the correct bit shift, which can be seen in the code.
```python
def get_result_parts(result):
    result_parts = []
    for i in range(4):
        for j in range(8):
            # weird shift amount based on binary representation of integers
            shift = i * 8 + (7 - j)
            result_part = (result >> shift) & 1
            result_parts.append(result_part)
    return result_parts
```

Now we need a way to communicate with the server, so let's create a `test` function which we pass a guess and receive the result. We also add a check for if the guess isn't wrong, we just return the output from the server.
```python
import pwn

conn = None # this will be set in our solve function

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
```

Now let's put all the pieces together. We start our solve function by setting up the connection.
```python
def solve():
    global conn

    # init connection
    context.log_level = 'debug'
    conn = remote('compare-me.ctf.bsidestlv.com', 4545)
```

Then we initialize our `current_parts` array that will contain each column from the `guess ^ guess_me` representation.
```python
    current_parts = [0 for x in range(32)]
```

Now we can loop by sending our guess, receiving the result, and setting up our next guess based on the result. If ever the result from `test` is a string, we know we have guessed correctly and we print the flag.
```python
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
```

Then we close our connection.
```python
    conn.recvall(2)

    # close connection
    conn.close()
```

And run our `solve` function.
```python
if __name__ == '__main__':
    solve()
```

Now if we run our script:
```
... bunch of debug logs
Solved: Success! BSidesTLV2023{c0mp4r1ng_c4n_c4u53_unc0mp4r4b13_1nf0_134k4g3}
```

We got the flag: `BSidesTLV2023{c0mp4r1ng_c4n_c4u53_unc0mp4r4b13_1nf0_134k4g3}`