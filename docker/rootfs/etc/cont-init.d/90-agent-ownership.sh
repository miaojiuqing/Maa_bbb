#!/bin/sh
set -eu

# The GUI service runs with the configurable USER_ID/GROUP_ID, while MFW
# rewrites embedded Agent sources in place.
chown -R "${USER_ID}:${GROUP_ID}" /opt/maa-bbb/agent
chmod -R u+rwX /opt/maa-bbb/agent
