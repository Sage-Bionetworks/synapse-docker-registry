#
# Generate a self-signed cert'
#
# from
# https://stackoverflow.com/questions/27164354/create-a-self-signed-x509-certificate-in-python
#
from OpenSSL import crypto, SSL

#
# returns a dict containing the private key and certificate as strings
#
#
def cert_gen(
    emailAddress="emailAddress",
    commonName="commonName",
    countryName="NT",
    localityName="localityName",
    stateOrProvinceName="stateOrProvinceName",
    organizationName="organizationName",
    organizationUnitName="organizationUnitName",
    serialNumber=0,
    validityStartInSeconds=0,
    validityEndInSeconds=10*365*24*60*60):
    #can look at generated file using openssl:
    #openssl x509 -inform pem -in selfsigned.crt -noout -text
    # create a key pair
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 4096)
    # create a self-signed cert
    cert = crypto.X509()
    cert.get_subject().C = countryName
    cert.get_subject().ST = stateOrProvinceName
    cert.get_subject().L = localityName
    cert.get_subject().O = organizationName
    cert.get_subject().OU = organizationUnitName
    cert.get_subject().CN = commonName
    cert.get_subject().emailAddress = emailAddress
    cert.set_serial_number(serialNumber)
    cert.gmtime_adj_notBefore(validityStartInSeconds)
    cert.gmtime_adj_notAfter(validityEndInSeconds)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha512')
    return {'private_key':crypto.dump_privatekey(crypto.FILETYPE_PEM, k).decode("utf-8"), 
    	'certificate':crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode("utf-8")}

        
if __name__ == '__main__':
	result = cert_gen()
	print(f"private_key:\n{result['private_key']}\n\ncert:\n{result['certificate']}")
