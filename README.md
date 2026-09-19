# 🔤 Online Word Chain Game

A two-player, real-time word-chain game built with **pure Python socket programming** — no external dependencies, no GUI framework, just TCP sockets, threads, and a shared queue.

> **Exercise 10 — Network and Communication Technology**
> National Economics University · College of Technology · Faculty of Data Science and Artificial Intelligence
> Group 01 — Class DS67B · Instructor: Dr. Tran Duc Minh

---

## What it is

Two players take turns typing English words over the network. Each new word must **begin with the last letter of the previous word** (`cat → tan → nut → toe → ...`). A player who can't answer within **10 seconds** loses the round. The server is the single source of truth: it validates every word, runs the clock, and keeps score across rounds.

```
Client 1 (Player 1)  <──TCP/JSON──>  Server (referee)  <──TCP/JSON──>  Client 2 (Player 2)
```

## Features

- **Authoritative TCP server** — one server, two clients, no client-side rule enforcement.
- **Line-delimited JSON protocol** over TCP for all communication.
- **Server-side 10-second timer** with a live per-second countdown streamed to the client.
- **Colour-changing countdown bar** in the terminal (green → yellow → red), accurately reflecting real remaining time even after a rejected word.
- **Dictionary-backed validity check** against a local `words.txt` (or system dictionary).
- **O(1) duplicate detection** via a shared `set`, plus a `list` for ordered history/logging.
- **READY / GO handshake** so both players start the match at the same instant.
- **Multi-round play** with a scoreboard and alternating starting player.
- **Surrender command** (`/surrender`, `/quit`, `/gg`, `/give`) to forfeit a stuck round.
- **Defensive handling** of malformed JSON, oversized input, non-ASCII tokens, unbounded input buffers, out-of-turn messages, and client disconnects.
- **Timestamped server logging** to `game.log` for every event.

## Requirements

- Python **3.7+** — standard library only (`socket`, `threading`, `queue`, `json`, `time`, `math`, `datetime`).
- A terminal with ANSI escape-code support for the colour countdown bar (falls back to plain text otherwise).

## Project structure

```
.
├── server.py       # The referee: connections, turns, rules, timer, scoring, logging
├── client.py       # Terminal client: sends words, renders the countdown bar
├── words.txt       # Dictionary used for word-validity checks (optional)
├── game.log         # Auto-generated event log (created on first run)
└── README.md       # Full protocol & usage documentation
```

## Quick start

Runs entirely on `127.0.0.1` — no network setup needed, just three terminals:

```bash
# Terminal 1 — server
python3 server.py

# Terminal 2 — Player 1
python3 client.py

# Terminal 3 — Player 2
python3 client.py
```

Both players read the rules, type `ready`, and the match begins once both are ready.

> Want to play over a LAN? Set `HOST = "0.0.0.0"` in `server.py` and point `HOST` in `client.py` at the server's LAN IP. Full details in [`README.md`](./README.md).

## Documentation

- [`README.md`](./README.md) — full protocol specification (message types, flow diagrams), design notes, and troubleshooting.
- **Full project report (PDF)** — architecture rationale, protocol design, implementation details, and executed test cases with captured terminal output: *link here*

## Testing

All 10 functional/defensive test cases described in the report (valid chaining, rule violations, timeouts, surrender, disconnects, malformed input, dictionary checks, multi-round continuation, oversized input) were executed against the running server and verified against `game.log` output — see the report's Test Cases section for full evidence.

## Authors

**Group 01 — Class DS67B**
- Do Thao Vy — 11259019
- Nguyen Ha Linh — 11254520
- Nguyen Ha Phuong — 11256968

Instructor: **Dr. Tran Duc Minh**

## References

- Kurose, J. F., & Ross, K. W. *Computer Networking: A Top-Down Approach*. Pearson.
- Course lecture notes — *Network and Communication Technology*, National Economics University.
- [Python 3 Standard Library Documentation](https://docs.python.org/3/library/) — `socket`, `threading`, `queue`, `json`.
