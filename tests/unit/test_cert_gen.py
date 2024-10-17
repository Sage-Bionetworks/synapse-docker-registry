from docker_fargate.generate_ssl_cert import cert_gen
import aws_cdk.assertions as assertions
from OpenSSL.crypto import (load_privatekey, load_certificate, FILETYPE_PEM)

#
# Check that the self-signed-cert code returns a valid private key
# and certificate
#
def test_cert_gen():
    key_and_cert = cert_gen()
    load_privatekey(FILETYPE_PEM, key_and_cert["private_key"])
    load_certificate(FILETYPE_PEM, key_and_cert["certificate"])
