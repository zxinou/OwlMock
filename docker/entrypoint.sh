#!/bin/sh
set -eu

data_dir="${OWLMOCK_DATA_DIR:-/data}"

case "$data_dir" in
    /data|/data/*) ;;
    *)
        echo "OWLMOCK_DATA_DIR must be within /data for this production image." >&2
        exit 64
        ;;
esac

mkdir -p "$data_dir"
chown owlmock:owlmock "$data_dir"
chmod 0750 "$data_dir"

exec setpriv --reuid=owlmock --regid=owlmock --init-groups -- "$@"
