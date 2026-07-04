FROM nixos/nix:2.24.11
RUN mkdir -p /etc/nix && printf 'experimental-features = nix-command flakes
' > /etc/nix/nix.conf
WORKDIR /runtime
COPY conductor-config.yaml /runtime/conductor-config.yaml
COPY entrypoint.sh /usr/local/bin/prometheus-holochain-entrypoint
RUN chmod +x /usr/local/bin/prometheus-holochain-entrypoint && mkdir -p /var/lib/holochain
EXPOSE 65000 65001
ENTRYPOINT ["/usr/local/bin/prometheus-holochain-entrypoint"]
