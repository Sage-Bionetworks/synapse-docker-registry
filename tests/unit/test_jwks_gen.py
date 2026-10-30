import json
from docker_fargate.generate_jwks import jwks_gen

#
# Check that the JWK Set publishes the token signing key under the libtrust key ID
# that Synapse puts in the 'kid' header of its bearer tokens
#
def test_jwks_gen():
    expected_kids = {
        "dev": "CC4F:YEUW:NYJE:6XDF:XG7U:DBOB:4P6E:PFZU:UXFA:JCPC:7EVP:IAMY",
        "prod": "2MTZ:QH2X:J57H:MV5O:62AZ:QNI3:OMW3:FZVO:KDD6:CQMC:TO6H:64SW"
    }
    for stack, kid in expected_kids.items():
        with open(f"resources/{stack}/token_signing_key_public_cert.pem", "rb") as f:
            jwks = json.loads(jwks_gen(f.read()))
        assert len(jwks["keys"]) == 1
        key = jwks["keys"][0]
        assert key["kid"] == kid
        assert key["kty"] == "EC" and key["crv"] == "P-256" and key["alg"] == "ES256"
