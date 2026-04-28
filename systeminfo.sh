#!/usr/bin/env bash
# sysinfo.sh — raw system stats to stdout

# ── CPU usage (compare two /proc/stat snapshots 1s apart) ──────────────────
get_cpu() {
  read -r _ u1 n1 s1 i1 _ < /proc/stat
  sleep 1
  read -r _ u2 n2 s2 i2 _ < /proc/stat
  total1=$((u1 + n1 + s1 + i1))
  total2=$((u2 + n2 + s2 + i2))
  idle_delta=$((i2 - i1))
  total_delta=$((total2 - total1))
  cpu_used=$(( (total_delta - idle_delta) * 100 / total_delta ))
  echo "CPU: ${cpu_used}%"
}

# ── Memory ──────────────────────────────────────────────────────────────────
get_mem() {
  total=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
  avail=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
  used=$(( (total - avail) * 100 / total ))
  echo "RAM: $((total/1024))MB total, $((avail/1024))MB free (${used}% used)"
}

# ── Disk ────────────────────────────────────────────────────────────────────
get_disk() {
  df -h / | awk 'NR==2 {printf "Disk (/): %s used of %s (%s)\n", $3, $2, $5}'
}

# ── Top 5 processes by CPU ──────────────────────────────────────────────────
get_procs() {
  echo "Top processes:"
  ps aux --sort=-%cpu | awk 'NR>1 && NR<=6 {printf "  %-20s CPU: %s%%  MEM: %s%%\n", $11, $3, $4}'
}

# ── Network ─────────────────────────────────────────────────────────────────
get_net() {
  iface=$(ip route | awk '/default/ {print $5; exit}')
  rx=$(awk -v iface="$iface" '$1 ~ iface {print $2}' /proc/net/dev)
  tx=$(awk -v iface="$iface" '$1 ~ iface {print $10}' /proc/net/dev)
  echo "Net ($iface): RX $((rx/1024/1024))MB  TX $((tx/1024/1024))MB"
}

echo "=== System Health @ $(date '+%H:%M:%S') ==="
get_cpu
get_mem
get_disk
get_procs
get_net