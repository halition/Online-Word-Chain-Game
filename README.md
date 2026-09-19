# Online Word Chain Game

A two-player online word-chain game built with **Python socket programming**.
Two clients connect to a central server over **TCP**; the server acts as the
referee that manages turns, enforces the rules, times each move, and keeps score.

> **Exercise 10 — Computer Networks**
> Architecture: **2 Clients – 1 Server (TCP)**
> Key focus: string token processing, word-history tracking (Set/List), turn management.

---

## 1. Gameplay

Two players take turns submitting English words. Each new word must **begin with
the last letter of the previous word** (e.g. `apple → elephant → tiger → ...`).
A player who cannot supply a valid word within **10 seconds** loses the round.

---

## 2. Features

- **Client–server over TCP** with two players and one authoritative server.
- **JSON message protocol** — every message is a single line of JSON terminated
  by `\n` (newline-based framing over the TCP byte stream).
- **Server-side 10-second timer** — the server is the single source of truth for
  timing; it streams a `TIME` tick every second so the client can show a live
  countdown.
- **Live countdown bar** — the client renders a fixed 10-cell horizontal bar that
  shrinks each second and changes colour (green → yellow → red).
- **Dictionary check** — submitted words must be real English words. The server
  loads a word list from `words.txt` (if present) or the system dictionary
  `/usr/share/dict/words`.
- **Word-history tracking** — a shared `set` prevents any word already played by
  *either* player from being reused within a round; a `list` preserves order.
- **READY / GO handshake** — after the rules are shown, both players press
  `ready`; only when both are ready does the server broadcast `GO` and start.
- **Multiple rounds with a scoreboard** — after each round the players are asked
  whether to play again; the starting player alternates for fairness.
- **Surrender** — a player who is stuck can forfeit the current round with the
  `/surrender` command (the round is lost, then a new round can be started).
- **Robust error handling** — invalid JSON, over-length input, out-of-turn
  messages, and client disconnects are all handled gracefully.
- **Server logging** — every event is written to `game.log` with a timestamp.

---

## 3. Requirements

- **Python 3.7+** (uses only the standard library: `socket`, `threading`,
  `queue`, `json`, `time`, `math`, `datetime`, `sys`).
- No third-party packages and **no GUI toolkit** — everything runs in a terminal.
- A terminal that supports ANSI escape codes (macOS Terminal, the VS Code
  integrated terminal, or most Linux terminals). If output is not a terminal,
  the client automatically falls back to a plain single-line countdown.

---

## 4. Files

| File         | Description                                             |
|--------------|---------------------------------------------------------|
| `server.py`  | The referee: connections, turns, rules, timer, scoring. |
| `client.py`  | A terminal client: sends words, shows the countdown bar.|
| `game.log`   | Auto-generated event log (created on first run).        |
| `README.md`  | This file.                                              |

---

## 5. How to run

Everything runs on a single machine using the loopback address `127.0.0.1`, so
**you do not need two computers** — you just need three terminal windows.

1. **Terminal 1 — start the server:**

   ```bash
   python3 server.py
   ```

   Wait until it prints `Server listening on 127.0.0.1:5000`.

2. **Terminal 2 — first player:**

   ```bash
   python3 client.py
   ```

3. **Terminal 3 — second player:**

   ```bash
   python3 client.py
   ```

Once both clients are connected, the server sends the rules to each player.

> **Optional — play across two machines on the same LAN:**
> change `HOST` in `client.py` to the server machine's IP address, make sure the
> server's port `5000` is reachable, and run one client on each machine.

---

## 6. How to play

1. Read the rules that appear on screen.
2. Type `ready` and press Enter. When **both** players are ready, `GO!` appears
   and the first round begins.
3. On your turn a countdown bar appears above the input line:

   ```
   >>> YOUR TURN! The word must start with 'e'.
   [███████░░░]  7s
   Enter a word (then Enter): elep_
   ```

4. Type a valid word and press Enter. If the word is rejected, the clock keeps
   running — try again before it reaches zero.
5. When a round ends, the score is shown and you are asked whether to play again.
   Type `yes` or `no`.

### Commands

| You type       | Effect                                                        |
|----------------|---------------------------------------------------------------|
| any word       | Submit that word for the current turn.                        |
| `ready`        | Signal you are ready to start (during the READY phase).       |
| `yes` / `no`   | Answer the "play again?" prompt after a round.                |
| `/surrender`   | Forfeit the **current round** (aliases: `/quit`, `/gg`, `/give`). |
| `Ctrl + C`     | Disconnect and end the whole match.                           |

> **Note:** the surrender command needs the leading slash. Typing `surrender`
> or `quit` **without** the slash is treated as an ordinary word, so those words
> can still be played legitimately in the chain.

---

## 7. Game rules (enforced by the server)

1. The word must be a **real English word** (checked against the dictionary).
2. It must **not repeat** any word already used by you *or* your opponent in the
   current round.
3. It must **start with the last letter** of the previous word.
4. You have **10 seconds** per turn; the clock keeps running even after an
   invalid attempt.
5. Type `/surrender` (or `/quit`) to give up the current round.

---

## 8. Protocol specification

Transport: **TCP**. Encoding: **UTF-8**. Framing: one **JSON object per line**,
terminated by `\n`. Every message has the shape:

```json
{"type": "MESSAGE_TYPE", "data": { ... }}
```

### Client → Server

| Type          | `data`                    | Meaning                                  |
|---------------|---------------------------|------------------------------------------|
| `WORD`        | `"<word>"`                | Submit a word for the current turn.      |
| `READY`       | `{}`                      | The player is ready to start.            |
| `PLAY_AGAIN`  | `"yes"` / `"no"`          | Answer the play-again prompt.            |
| `QUIT`        | `{}`                      | Forfeit the current round (surrender).   |

### Server → Client

| Type             | `data`                              | Meaning                                    |
|------------------|-------------------------------------|--------------------------------------------|
| `ASSIGN`         | `{"player": 1\|2}`                  | Tells the client its player number.        |
| `RULES`          | `{"text","dictionary_active"}`      | The rules text, sent before the match.     |
| `READY_ASK`      | `{"msg"}`                           | Prompt the player to press ready.          |
| `GO`             | `{"msg"}`                           | Both are ready; the match starts.          |
| `INFO`           | `{"msg"}`                           | General status message.                    |
| `ROUND_START`    | `{"start_player"}`                  | A new round begins.                        |
| `TURN`           | `{"time","last_word","need_char"}`  | It is this player's turn.                  |
| `WAIT`           | `{"msg"}`                           | Waiting for the opponent's move.           |
| `TIME`           | `{"remaining"}`                     | One-per-second countdown tick.             |
| `ACCEPT`         | `{"word"}`                          | Your word was accepted.                    |
| `OPP`            | `{"word","need_char"}`              | The opponent's accepted word.              |
| `REJECT`         | `{"reason"}`                        | Your word was rejected; try again.         |
| `WIN` / `LOSE`   | `{"reason","scores"}`               | Round result for this player.              |
| `SCORE`          | `{"p1","p2"}`                       | Current cumulative score.                  |
| `PLAY_AGAIN_ASK` | `{"msg"}`                           | Ask whether to start a new round.          |
| `GAME_OVER`      | `{"scores","final"}`                | The match is over.                         |

### Typical message flow

```
Server                         Client 1                 Client 2
  |-- ASSIGN/RULES/READY_ASK ---> |                        |
  |-- ASSIGN/RULES/READY_ASK ----|----------------------> |
  |<-- READY --------------------|                        |
  |<-- READY --------------------|------------------------|
  |-- GO -----------------------> |  (broadcast)           |
  |-- ROUND_START --------------> |                        |
  |-- TURN --------------------->  |                        |
  |-- TIME (x10, one per second)-> |                        |
  |<-- WORD "apple" -------------- |                        |
  |-- ACCEPT "apple" -----------> |                        |
  |-- OPP "apple" ---------------|----------------------> |
  |               ... turns alternate ...                  |
  |-- WIN / LOSE + SCORE -------> |  and -----------------> |
  |-- PLAY_AGAIN_ASK -----------> |  and -----------------> |
```

---

## 9. Design notes

- **String token processing.** The server normalises each word (trim +
  lowercase) and chains rounds by comparing `word[0]` with `last_word[-1]`.
- **Word-history tracking (Set / List).** A `set` gives O(1) duplicate detection
  shared by both players within a round; a parallel `list` records play order for
  logging and history.
- **Turn management.** The server tracks the current player and flips
  `current ↔ opponent` after every accepted word.
- **Authoritative timer.** The 10-second limit lives on the server, implemented
  with `queue.Queue.get(timeout=...)`, so the game never trusts the client for
  rule enforcement. The server also emits one `TIME` tick per second purely for
  display.
- **Concurrency.** The server runs one reader thread per client that pushes
  incoming lines into a shared queue; a single controller loop consumes the
  queue, which keeps game state changes serialised and race-free.
- **Command vs. data.** Control actions use a `/` prefix (`/surrender`) so they
  can never be confused with a legitimate word such as "quit" or "surrender" —
  a small illustration of separating protocol commands from payload.

---

## 10. Troubleshooting

- **`Address already in use`** — a previous server is still bound to port 5000.
  Wait a moment or stop the old process; the server sets `SO_REUSEADDR` to make
  restarts easier.
- **Client prints `Could not connect to the server`** — start `server.py` first,
  then the clients.
- **Countdown bar looks broken** — your terminal font may not render the block
  characters. Replace `█` and `░` in `render_bar()` (in `client.py`) with `#`
  and `-`.
- **Words are never rejected as "not a real word"** — no dictionary was found.
  Put a `words.txt` word list next to the scripts, or run on a system that has
  `/usr/share/dict/words`.

---

## 11. Possible extensions

- A GUI client (e.g. tkinter) for a richer countdown and buttons.
- A lobby that pairs many players into separate matches.
- Best-of-N match format and persistent high scores.
- Command-line arguments for host/port instead of hard-coded values.
