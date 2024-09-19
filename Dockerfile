#
# Creates a configuration of the open source Docker registry
# suitable for using with Synapse
#
#
FROM registry:v2
# stack is dev or prod
ARG stack=dev

# switches between 'dev' and 'prod'
COPY resources/${stack}/config.yml /etc/docker/registry/config.yml
COPY resources/${stack}/token_signing_key_public_cert.pem /etc/docker/registry/token_signing_key_public_cert.pem
# the self-signed cert' and private key should be generated before running 'docker build'
# see the github workflow for an example of how to do this
COPY privatekey.pem /etc/docker/registry/ssl/privatekey.pem
COPY certificate.pem /etc/docker/registry/ssl/certificate.pem

ENTRYPOINT ...
CMD ...

COPY startup.sh /startup.sh

CMD /startup.sh
