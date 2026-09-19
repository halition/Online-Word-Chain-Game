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
- **Dictionary-backed validity check** against the bundled `words.txt`.
- **O(1) duplicate detection** via a shared `set`, plus a `list` for ordered history/logging.
- **READY / GO handshake** so both players start the match at the same instant.
- **Multi-round play** with a scoreboard and alternating starting player.
- **Surrender command** (`/surrender`, `/quit`, `/gg`, `/give`) to forfeit a stuck round.
- **Defensive handling** of malformed JSON, oversized input, non-ASCII tokens, unbounded input buffers, out-of-turn messages, and client disconnects.
- **Timestamped server logging** to `game.log` for every event (auto-generated on first run, not tracked in this repo).

## Requirements

- Python **3.7+** — standard library only (`socket`, `threading`, `queue`, `json`, `time`, `math`, `datetime`).
- A terminal with ANSI escape-code support for the colour countdown bar (falls back to plain text otherwise).

## Repository contents

```
.
├── README.md       # This file
├── server.py       # The referee: connections, turns, rules, timer, scoring, logging
├── client.py       # Terminal client: sends words, renders the countdown bar
└── words.txt       # Dictionary used for word-validity checks
```

`game.log` is created automatically the first time `server.py` runs — it is not part of this repo.

## Quick start

Runs entirely on `127.0.0.1` — no network setup needed, just three terminals, from a local clone of this repo:

```bash
git clone https://github.com/halition/Online-Word-Chain-Game.git
cd Online-Word-Chain-Game

# Terminal 1 — server
python3 server.py

# Terminal 2 — Player 1
python3 client.py

# Terminal 3 — Player 2
python3 client.py
```

Both players read the rules, type `ready`, and the match begins once both are ready.

> Want to play over a LAN? Set `HOST = "0.0.0.0"` in `server.py` and point `HOST` in `client.py` at the server's LAN IP (both machines must be on the same subnet with port `5000` open).

## How to play

| You type       | Effect                                                             |
|-----------------|---------------------------------------------------------------------|
| any word        | Submit that word for the current turn.                              |
| `ready`         | Signal you are ready to start (during the READY phase).             |
| `yes` / `no`    | Answer the "play again?" prompt after a round.                      |
| `/surrender`    | Forfeit the current round (aliases: `/quit`, `/gg`, `/give`).       |
| `Ctrl + C`      | Disconnect and end the whole match.                                 |

**Rules enforced by the server:**
1. The word must be a real English word (checked against `words.txt`).
2. It must not repeat any word already used by you or your opponent this round.
3. It must start with the last letter of the previous word.
4. You have 10 seconds per turn; the clock keeps running even after an invalid attempt.
5. Type `/surrender` (or `/quit`) to give up the current round.

## Protocol

Transport is **TCP**, encoding is **UTF-8**, and framing is one **JSON object per line**, terminated by `\n`:

```json
{"type": "MESSAGE_TYPE", "data": { ... }}
```

Full message-type tables (client→server, server→client) and design notes are documented as comments in `server.py` and `client.py`.

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
