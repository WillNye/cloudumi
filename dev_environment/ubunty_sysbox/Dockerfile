FROM nestybox/ubuntu-focal-systemd-docker:latest

# TODO: figure out how to pass in the username via an env var; apparently docker run does not support this
RUN usermod -l matt admin \ 
 && groupmod -n matt admin \
 && mv /home/admin /home/matt \
 && usermod -d /home/matt matt \
 && apt-get update -y \
 && apt-get install -y vim wget libedit-dev git build-essential python-dev python3-dev make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev \
 && git clone https://github.com/pyenv/pyenv.git /home/matt/.pyenv \
 && sed -Ei -e '/^([^#]|$)/ {a export PYENV_ROOT="$HOME/.pyenv" a export PATH="$PYENV_ROOT/bin:$PATH" a ' -e ':a' -e '$!{n;ba};}' /home/matt/.profile \
 && echo 'eval "$(pyenv init --path)"' >> /home/matt/.profile \
 && echo 'eval "$(pyenv init -)"' >> /home/matt/.bashrc \
 && echo 'PATH=/home/matt/.pyenv/bin:$PATH' >> /home/matt/.bashrc \
 && mkdir -p /home/matt/bin \
 && mkdir -p /home/matt/.cache \
 && chown matt.matt /home/matt/bin \
 && chown matt.matt /home/matt/.cache \
 && chown matt.matt /home/matt/.pyenv \
 && wget https://github.com/bazelbuild/bazelisk/releases/download/v1.11.0/bazelisk-linux-amd64 \
 && mv bazelisk-linux-amd64 /home/matt/bin \
 && ln -s /home/matt/bin/bazelisk-linux-amd64 /home/matt/bin/bazelisk \
 && ln -s /home/matt/bin/bazelisk-linux-amd64 /home/matt/bin/bazel \
 && chmod +x /home/matt/bin/bazelisk-linux-amd64
