#!/bin/sh

# Inject notification listener authorization credentials into config.yml
sed -i "s/notification_auth/$notification_auth/g" /etc/docker/registry/config.yml

# this assumed a particular start-up for the container registry
# if the command changes in future versions, this will have to be updated too
/entrypoint.sh /etc/docker/registry/config.yml
