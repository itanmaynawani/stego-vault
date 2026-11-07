# Vault: steganographic image vault

Hides AES-256-GCM encrypted text inside image pixels (least significant bits).
The key (via scrypt) encrypts the text *and* decides which pixels carry it.

## Run
```
cd backend && pip install -r requirements.txt && python app.py
cd frontend && npm install && npm run dev      # open http://localhost:5173
```
Sealed images are PNG only: lossy formats (JPEG, most chat apps) wipe the hidden bits.
