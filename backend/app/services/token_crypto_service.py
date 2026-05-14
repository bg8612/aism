from __future__ import annotations

import base64


class TokenCryptoService:
    # MVP placeholder: isolated reversible encoding so storage mechanism can be replaced later.
    def encrypt(self, token: str) -> str:
        return base64.b64encode(token.encode("utf-8")).decode("ascii")

    def decrypt(self, token_encrypted: str) -> str:
        return base64.b64decode(token_encrypted.encode("ascii")).decode("utf-8")
