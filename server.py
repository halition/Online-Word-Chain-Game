"""
Exercise 10 - Online Word Chain Game 
SERVER  |  Python Socket Programming 
"""

import socket
import threading
import queue
import time
import json
import math
import datetime

# CONFIG 
HOST = "127.0.0.1"
PORT = 5000
TURN_TIME = 10          # seconds per turn
MAX_WORD_LEN = 45       # guard against over-long input 
MAX_BUFFER_LEN = 4096   # guard: max bytes buffered for one line with no '\n' yet
LOG_FILE = "game.log"
DICT_PATHS = ["words.txt", "/usr/share/dict/words"]   

msg_queue = queue.Queue()          # items: (player_id, raw_line | None)
log_lock = threading.Lock()

RULES_TEXT = (
    "WORD CHAIN RULES:\n"
    "  1) The word must be a real English word (checked against a dictionary).\n"
    "  2) No repeating a word already used by YOU or your OPPONENT.\n"
    "  3) The new word must start with the LAST LETTER of the previous word.\n"
    "  4) You have only 10 seconds to answer (the clock keeps running even after "
    "an invalid word).\n"
    "  5) Type '/surrender' or '/quit' to give up the CURRENT round (you lose it).\n"
    "     (Note: typing 'quit'/'surrender' WITHOUT the '/' counts as a normal word.)"
)


# LOGGING & JSON SEND/RECEIVE
def log_event(text):
    """Write one log line to the screen and file, with a timestamp."""
    line = "[%s] %s" % (
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), text)
    print(line)
    with log_lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def send_json(conn, mtype, data=None):
    """Send one JSON message (one line, ending with '\n') to a client."""
    obj = {"type": mtype, "data": data if data is not None else {}}
    try:
        conn.sendall((json.dumps(obj) + "\n").encode("utf-8"))
    except OSError:
        pass


def broadcast(conns, mtype, data=None):
    for c in conns:
        send_json(c, mtype, data)


def reader_thread(pid, conn):
    """Read the byte stream, split on '\n' (message framing for TCP), enqueue."""
    buffer = ""
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            buffer += data.decode("utf-8", errors="ignore")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if line.strip():
                    msg_queue.put((pid, line.strip()))
            # Guard: if a client keeps sending bytes with no '\n' at all,
            # 'buffer' would otherwise grow without bound. Cap it and treat
            # the connection as misbehaving rather than exhausting memory.
            if len(buffer) > MAX_BUFFER_LEN:
                log_event("Player %d exceeded max buffer size (no newline); "
                          "closing connection." % (pid + 1))
                break
    except OSError:
        pass
    finally:
        msg_queue.put((pid, None))   # signal a disconnect 


def parse_json(raw):
    """Return a dict if valid, None if the JSON is malformed."""
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


# DICTIONARY 
def load_dictionary():
    for path in DICT_PATHS:
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                words = {w.strip().lower() for w in f
                         if w.strip().isalpha()}
            if words:
                return words, path
        except OSError:
            continue
    return None, None


# RULE VALIDATION 
def validate_word(word, last_word, used_words, dictionary):
    """String token processing + rule checks. Returns (ok, reason)."""
    if not word:
        return False, "Empty word."
    if len(word) > MAX_WORD_LEN:
        return False, "Word is too long."
    if not word.isalpha() or not word.isascii():
        return False, "The word may contain letters a-z only."
    # Chain rule: first letter must match the last letter of the previous word.
    if last_word is not None and word[0] != last_word[-1]:
        return False, "The word must start with '%s'." % last_word[-1]
    # No duplicates (SET shared by BOTH players).
    if word in used_words:
        return False, "This word has already been used (no repeats)."
    # Dictionary/meaning check.
    if dictionary is not None and word not in dictionary:
        return False, "Not a valid English word."
    return True, ""


# PLAY ONE ROUND 
def run_one_round(conns, start_player, dictionary):
    """
    Returns a result dict:
      {"winner":pid, "loser":pid, "reason":str, "end_match":bool}
    end_match=True means end the whole match now (disconnect).
    """
    used_words = set()   # SET: dedup history shared by BOTH players this round 
    history = []         # LIST: keep (pid, word) in order 
    last_word = None
    current = start_player

    broadcast(conns, "ROUND_START", {"start_player": start_player + 1})

    while True:
        opponent = 1 - current
        need_char = last_word[-1] if last_word else None
        send_json(conns[current], "TURN",
                  {"time": TURN_TIME, "last_word": last_word,
                   "need_char": need_char})
        send_json(conns[opponent], "WAIT", {"msg": "Opponent is thinking..."})

        deadline = time.time() + TURN_TIME
        last_sec = None

        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                log_event("Player %d RAN OUT OF TIME." % (current + 1))
                return {"winner": opponent, "loser": current,
                        "reason": "Ran out of time (10s)", "end_match": False}

            # Emit a countdown tick whenever the (rounded) second changes.
            sec = int(math.ceil(remaining))
            if sec != last_sec:
                send_json(conns[current], "TIME", {"remaining": sec})
                last_sec = sec

            try:
                pid, raw = msg_queue.get(timeout=min(remaining, 0.2))
            except queue.Empty:
                continue

            # Disconnect
            if raw is None:
                log_event("Player %d DISCONNECTED." % (pid + 1))
                return {"winner": 1 - pid, "loser": pid,
                        "reason": "Opponent disconnected", "end_match": True}

            obj = parse_json(raw)
            if obj is None:
                send_json(conns[pid], "REJECT",
                          {"reason": "Invalid message (bad JSON)."})
                continue

            mtype = obj.get("type")

            # Surrender: handled no matter whose turn it is 
            if mtype in ("QUIT", "SURRENDER"):
                log_event("Player %d SURRENDERED this round." % (pid + 1))
                # Loses only the CURRENT round; we still ask to play again after.
                return {"winner": 1 - pid, "loser": pid,
                        "reason": "Opponent surrendered this round",
                        "end_match": False}

            # Message from the player whose turn it isn't -> ignore (clock runs).
            if pid != current:
                send_json(conns[pid], "REJECT", {"reason": "It is not your turn yet."})
                continue

            if mtype != "WORD":
                send_json(conns[current], "REJECT",
                          {"reason": "Waiting for you to enter a WORD."})
                continue

            word = str(obj.get("data", "")).strip().lower()
            ok, reason = validate_word(word, last_word, used_words, dictionary)
            if not ok:
                # Word rejected, but the clock KEEPS running (Rule #4).
                send_json(conns[current], "REJECT", {"reason": reason})
                log_event("Player %d rejected word '%s': %s"
                          % (current + 1, word, reason))
                continue

            # Valid -> update state and switch turns.
            used_words.add(word)
            history.append((current, word))
            last_word = word
            send_json(conns[current], "ACCEPT", {"word": word})
            send_json(conns[opponent], "OPP",
                      {"word": word, "need_char": word[-1]})
            log_event("Player %d played '%s' (OK). Chain='%s'"
                      % (current + 1, word, word[-1]))
            break

        current = opponent   # switch turns (turn management)


# ASK TO PLAY AGAIN
def ask_play_again(conns):
    broadcast(conns, "PLAY_AGAIN_ASK",
              {"msg": "Play another round? Type 'yes' or 'no'."})
    answers = {}
    while len(answers) < 2:
        pid, raw = msg_queue.get()
        if raw is None:                      # disconnect -> treated as 'no'
            answers[pid] = False
            answers.setdefault(1 - pid, False)
            break
        obj = parse_json(raw)
        if obj is None:
            send_json(conns[pid], "REJECT", {"reason": "Invalid answer."})
            continue
        t = obj.get("type")
        if t in ("QUIT", "SURRENDER"):
            answers[pid] = False
        elif t == "PLAY_AGAIN":
            answers[pid] = str(obj.get("data", "")).strip().lower() in (
                "yes", "y", "co", "ok")
        else:
            send_json(conns[pid], "REJECT", {"reason": "Waiting for a yes/no answer."})
    return answers.get(0, False), answers.get(1, False)


# WAIT FOR BOTH PLAYERS (READY -> GO)
def wait_for_ready(conns):
    """
    After sending the rules, wait for BOTH players to press READY, then
    announce GO at the same time.
    Returns False if a player leaves/surrenders before the match starts.
    """
    broadcast(conns, "READY_ASK",
              {"msg": "When you have read the rules, press READY."})
    ready = set()
    while len(ready) < 2:
        pid, raw = msg_queue.get()
        if raw is None:                        # disconnect before the match starts
            return False
        obj = parse_json(raw)
        if obj is None:
            send_json(conns[pid], "REJECT", {"reason": "Invalid message."})
            continue
        t = obj.get("type")
        if t in ("QUIT", "SURRENDER"):
            return False
        if t == "READY":
            if pid not in ready:
                ready.add(pid)
                log_event("Player %d is READY (%d/2)." % (pid + 1, len(ready)))
                send_json(conns[pid], "INFO",
                          {"msg": "You are ready. Waiting for your opponent..."})
                send_json(conns[1 - pid], "INFO",
                          {"msg": "Your opponent is ready..."})
        else:
            send_json(conns[pid], "REJECT", {"reason": "Please press READY to start."})
    broadcast(conns, "GO", {"msg": "GO!"})
    log_event("Both players are ready -> GO!")
    return True


# MATCH CONTROLLER
def game_controller(conns):
    dictionary, dict_path = load_dictionary()
    if dictionary:
        log_event("Dictionary loaded: %s (%d words)." % (dict_path, len(dictionary)))
    else:
        log_event("WARNING: no dictionary found; skipping the meaning check.")

    # (#9) Send the rules and assign player numbers BEFORE the match.
    send_json(conns[0], "ASSIGN", {"player": 1})
    send_json(conns[1], "ASSIGN", {"player": 2})
    broadcast(conns, "RULES", {"text": RULES_TEXT,
                               "dictionary_active": dictionary is not None})

    # (#9+) Let both read the rules & press READY, then announce GO together.
    if not wait_for_ready(conns):
        broadcast(conns, "GAME_OVER",
                  {"scores": [0, 0],
                   "final": "Match cancelled (a player left before it started)."})
        log_event("Match cancelled during the READY phase.")
        return

    scores = [0, 0]
    start_player = 0
    round_num = 0

    while True:
        round_num += 1
        broadcast(conns, "INFO", {"msg": "===== ROUND %d =====" % round_num})
        log_event("Starting round %d (first to move: player %d)."
                  % (round_num, start_player + 1))

        result = run_one_round(conns, start_player, dictionary)
        w, l = result["winner"], result["loser"]
        scores[w] += 1

        send_json(conns[w], "WIN",
                  {"reason": result["reason"], "scores": scores})
        send_json(conns[l], "LOSE",
                  {"reason": result["reason"], "scores": scores})
        broadcast(conns, "SCORE", {"p1": scores[0], "p2": scores[1]})
        log_event("Round %d result: Player %d wins (%s). Score %d-%d."
                  % (round_num, w + 1, result["reason"], scores[0], scores[1]))

        if result.get("end_match"):
            break

        again1, again2 = ask_play_again(conns)
        if not (again1 and again2):
            break
        start_player = 1 - start_player      # alternate the starting player

    broadcast(conns, "GAME_OVER",
              {"scores": scores,
               "final": "Final score: %d - %d" % (scores[0], scores[1])})
    log_event("MATCH OVER. Score %d-%d." % (scores[0], scores[1]))


# MAIN
def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(2)
    log_event("Server listening on %s:%d" % (HOST, PORT))

    conns = []
    while len(conns) < 2:
        conn, addr = server.accept()
        conns.append(conn)
        log_event("Player %d connected from %s" % (len(conns), addr))
        send_json(conn, "INFO", {"msg": "Connected successfully. Waiting for a player..."})

    for pid, conn in enumerate(conns):
        threading.Thread(target=reader_thread, args=(pid, conn),
                         daemon=True).start()

    try:
        game_controller(conns)
    finally:
        for c in conns:
            c.close()
        server.close()


if __name__ == "__main__":
    main()
