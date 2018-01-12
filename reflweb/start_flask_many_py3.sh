#!/bin/bash

UMASK="$(umask)"

for (( c=0; c<$2; c++))
do
    p=$(($1+$c));
    uwsgi --umask "$UMASK" --socket "127.0.0.1:$p" --manage-script-name --mount /=server_flask:app --plugins-dir /usr/lib/uwsgi/plugins/ --plugin python3 -d /dev/null
done

