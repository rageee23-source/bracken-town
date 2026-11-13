"""Create a dedicated Solana receive address; Windows protects the signing seed."""
import os
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption
import win32crypt

def address(raw):
    alphabet='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    n=int.from_bytes(raw,'big')
    out=''
    while n:
        n,i=divmod(n,58)
        out=alphabet[i]+out
    return '1'*(len(raw)-len(raw.lstrip(b'\0')))+out

if __name__=='__main__':
    root=Path(os.environ['LOCALAPPDATA'])/'BrackenTown'
    root.mkdir(exist_ok=True)
    path=root/'town-wallet.dpapi'
    if not path.exists():
        key=Ed25519PrivateKey.generate()
        raw=key.private_bytes(Encoding.Raw,PrivateFormat.Raw,NoEncryption())
        sealed=win32crypt.CryptProtectData(raw,'Bracken Solana wallet',None,None,None,1)
        with path.open('xb') as f: f.write(sealed)
    raw=win32crypt.CryptUnprotectData(path.read_bytes(),None,None,None,1)[1]
    pub=Ed25519PrivateKey.from_private_bytes(raw).public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)
    print(address(pub))
