#!/bin/bash -e
#
# Copyright 2021 ScyllaDB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

docker build -f Dockerfile_deb . -t scylladb/packer-builder-deb

DOCKER_ID=$(docker run -d  -v `pwd`/../..:/scylla-machine-image scylladb/packer-builder-deb /bin/bash -c "cd /scylla-machine-image/azure/image; ./build_azure_image.sh $*")

kill_it() {
    if [[ -n "$DOCKER_ID" ]]; then
        docker rm -f "$DOCKER_ID" > /dev/null 2>&1
        container=
    fi
}

trap kill_it SIGTERM SIGINT SIGHUP EXIT

docker logs "$DOCKER_ID" -f

if [[ -n "$DOCKER_ID" ]]; then
    exitcode="$(docker wait "$DOCKER_ID")"
else
    exitcode=99
fi

echo "Docker exitcode: $exitcode"

kill_it

trap - SIGTERM SIGINT SIGHUP EXIT

# after "docker kill", docker wait will not print anything
[[ -z "$exitcode" ]] && exitcode=1

docker run --rm \
    --entrypoint /bin/sh \
    -e HOST_UID=`id -u` \
    -v `pwd`:/azure \
    scylladb/packer-builder-deb \
    -c "chown -R `stat -c \"%u:%g\" $(pwd)` /azure/" || true

exit "$exitcode"
