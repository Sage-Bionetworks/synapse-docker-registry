#
# Generate a JWK Set from Synapse's token signing certificate
#
# Synapse puts a libtrust-style key ID in the 'kid' header of the bearer tokens it
# issues. registry:3 no longer derives that ID from a 'rootcertbundle', so instead we
# give it a JWK Set ('jwks' in config.yml) that publishes the same public key under
# that 'kid'.
#
import base64
import hashlib
import json

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

#
# The libtrust key ID: the first 240 bits of the SHA-256 of the DER encoded public key,
# base32 encoded and split into colon separated groups of four characters
#
# Note: The important thing about this key ID is that it's exactly what Synapse uses.
# In Synapse the libtrust algorithm is implemented in Java in
# org.sagebionetworks.repo.manager.KeyPairUtil.computeKeyId()
#
#
def libtrust_key_id(public_key):
    der = public_key.public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    b32 = base64.b32encode(hashlib.sha256(der).digest()[:30]).decode("utf-8")
    return ":".join(b32[i:i+4] for i in range(0, len(b32), 4))


def _base64url_uint(value, length):
    return base64.urlsafe_b64encode(value.to_bytes(length, "big")).decode("utf-8").rstrip("=")

#
# returns the JWK Set, as a string, for the EC P-256 public key in the given PEM certificate
#
def jwks_gen(certificate_pem):
    public_key = x509.load_pem_x509_certificate(certificate_pem).public_key()
    if not isinstance(public_key, ec.EllipticCurvePublicKey) or not isinstance(public_key.curve, ec.SECP256R1):
        raise ValueError("Token signing certificate must contain an EC P-256 public key")
    numbers = public_key.public_numbers()
    jwk = {
        "kty": "EC",
        "crv": "P-256",
        "x": _base64url_uint(numbers.x, 32),
        "y": _base64url_uint(numbers.y, 32),
        "kid": libtrust_key_id(public_key),
        "use": "sig",
        "alg": "ES256"
    }
    return json.dumps({"keys": [jwk]}, indent=2) + "\n"


if __name__ == '__main__':
    import sys
    with open(sys.argv[1], "rb") as f:
        print(jwks_gen(f.read()), end="")
