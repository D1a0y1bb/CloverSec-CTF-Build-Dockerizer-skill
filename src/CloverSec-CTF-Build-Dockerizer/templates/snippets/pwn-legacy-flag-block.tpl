if [[ -d /home/ctf ]]; then
  cp /flag /home/ctf/flag 2>/dev/null || true
  chmod 444 /home/ctf/flag 2>/dev/null || true
fi
