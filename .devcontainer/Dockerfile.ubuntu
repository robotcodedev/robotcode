FROM ubuntu:latest

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Berlin

# Update the repositories
RUN apt update --yes

RUN apt install --yes --no-install-recommends locales

RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8


RUN apt install --yes --no-install-recommends curl make build-essential \
        libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev \
        wget curl llvm libncursesw5-dev xz-utils tk-dev libxml2-dev \
        libxmlsec1-dev libffi-dev liblzma-dev pipx git less nano

RUN curl -fsSL https://deb.nodesource.com/setup_19.x | bash - && \
        apt install -y nodejs

RUN pipx install hatch

RUN curl https://pyenv.run | bash


RUN echo 'if [ -d "$HOME/.local/bin" ] ; then' >> ~/.profile
RUN echo '    PATH="$HOME/.local/bin:$PATH"' >> ~/.profile
RUN echo 'fi' >> ~/.profile

RUN echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.profile
RUN echo 'command -v pyenv >/dev/null || export PATH="$PATH:$PYENV_ROOT/bin"' >> ~/.profile
RUN echo 'eval "$(pyenv init -)"' >> ~/.profile


RUN . ~/.profile && pyenv install 3.8.16
RUN . ~/.profile && pyenv install 3.11.1
RUN . ~/.profile && pyenv global 3.11.1
