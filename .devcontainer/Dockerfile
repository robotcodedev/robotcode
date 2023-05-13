FROM	 archlinux:latest

# Update the repositories
RUN	 pacman -Syy

RUN /bin/sh -c echo '[multilib]' >> /etc/pacman.conf && \
    pacman --noconfirm -Syyu && \
    pacman --noconfirm -S base-devel git git-lfs && \
    useradd -m -r -s /bin/bash aur && \
    passwd -d aur && \
    echo 'aur ALL=(ALL) ALL' > /etc/sudoers.d/aur && \
    mkdir -p /home/aur/.gnupg && \
    echo 'standard-resolver' > /home/aur/.gnupg/dirmngr.conf && \
    chown -R aur:aur /home/aur && \
    mkdir /build && \
    chown -R aur:aur /build && \
    cd /build && \
    sudo -u aur git clone --depth 1 https://aur.archlinux.org/yay.git && \
    cd yay && \
    sudo -u aur makepkg --noconfirm -si

# install yay
RUN sudo -u aur yay --cleanafter --removemake --save && \
    pacman -Qtdq | xargs -r pacman --noconfirm -Rcns && \
    rm -rf /home/aur/.cache && \
    rm -rf /build

# configure zsh
RUN sudo -u aur yay -S --needed --noconfirm zsh easy-zsh-config

RUN echo '' >> /etc/skel/.zshrc \
    && sed -i -r "s/^(PATH_OF_THE_THEME=).*/\1\/usr\/share\/oh-my-posh\/themes\/stelbent\.minimal\.omp\.json/" /etc/skel/.zshrc

RUN sudo -u aur yay -S --needed --noconfirm openssh python python-pip python-setuptools python-pipenv python-pipx nodejs npm npm-check-updates

# configure python
RUN sudo -u aur yay -S --needed --noconfirm python38 python39 python310

RUN echo '' >> /etc/skel/.zshrc \
    && echo 'if [ -d "$HOME/.local/bin" ] ; then' >> /etc/skel/.zshrc \
    && echo '    PATH="$HOME/.local/bin:$PATH"' >> /etc/skel/.zshrc \
    && echo 'fi' >> /etc/skel/.zshrc

# create vscode user
RUN useradd -l -u 33333 -G wheel -md /home/vscode -s /bin/zsh -p vscode vscode
USER vscode

RUN pipx install hatch
RUN pipx install python-semantic-release
RUN pipx install pre-commit

RUN hatch config set dirs.env.virtual ".hatch"

ENV SHELL=/usr/bin/zsh