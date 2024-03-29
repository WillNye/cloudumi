# Sysbox

- Sysbox can be installed from here: https://github.com/nestybox/sysbox
- Sysbox allows for more security in running docker in docker environments, which is perfect for our build system and those that might not have the right OS

## Use containers

- Sysbox containers are fully fledged init containers with systemd and docker pre-installed
- Use the ubunty_sysbox Dockerfile to set up your environment to mirror your user name, directory, etc, then mount into the countainer your cloudumi repo and bazel cache
- Customize:
- 1. Change ubunty_sysbox/Dockerfile and change all occurrences of "matt" to your user name
- 2. Build: `docker build -t local/ubuntu-focal-systemd-docker:latest`
- Then run the container: `docker run -v /home/matt/.cache/bazel:/home/matt/.cache/bazel -v $(pwd):/cloudumi --runtime=sysbox-runc -it --rm -P --hostname=syscont local/ubuntu-focal-systemd-docker:latest`

## How to run in sysbox

- Sysbox containers are fully fledged init containers with systemd and docker pre-installed
- Use the ubunty_sysbox Dockerfile to set up your environment to mirror your user name, directory, etc, then mount into the countainer your cloudumi repo and bazel cache
- Customize:
- 1. Change ubunty_sysbox/Dockerfile and change all occurrences of "matt" to your user name
- 2. Build: `docker build -t local/ubuntu-focal-systemd-docker:latest`
- Then run the container: `docker run -v /home/matt/.aws:/home/matt/.aws -v /home/matt/.cache/bazel:/home/matt/.cache/bazel -v $(pwd):/cloudumi --runtime=sysbox-runc -it --rm -P --hostname=syscont local/ubuntu-focal-systemd-docker:latest`
- OR! run the container using the `docker-compose` orchestration script, from the project root: `docker-compose -f dev_environment/docker-compose-ubunty-sysbox.yml up -d`
  - And attach: `docker attach dev_environment_ubunty-sysbox_1`
- Once in the container, install python: `pyenv install 3.9.7`.
