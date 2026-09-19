"""
Exercise 10 - Online Word Chain Game 
CLIENT  |  Python Socket Programming
"""

import socket
import threading
import json
import sys

HOST = "127.0.0.1"
PORT = 5000

# Current input mode: "word" | "ready" | "again" | "idle"
input_mode = "idle"
bar_active = False              # whether the countdown bar is currently shown
last_remaining = 10              # last TIME value received from the server this turn
USE_ANSI = sys.stdout.isatty()  # only use ANSI codes on a real terminal

# ANSI colour codes
GREEN, YELLOW, RED, RESET = "\033[92m", "\033[93m", "\033[91m", "\033[0m"
PROMPT = "Enter a word (then Enter): "


def send_json(sock, mtype, data=None):
    obj = {"type": mtype, "data": data if data is not None else {}}
    try:
        sock.sendall((json.dumps(obj) + "\n").encode("utf-8"))
    except OSError:
        pass


def render_bar(remaining):
    """Build the 10-cell bar string for the remaining seconds."""
    filled = max(0, min(10, remaining))
    bar = "\u2588" * filled + "\u2591" * (10 - filled)   # 'block' and 'shade'
    if USE_ANSI:
        color = RED if remaining <= 3 else YELLOW if remaining <= 5 else GREEN
        return "%s[%s]%s %2ds" % (color, bar, RESET, remaining)
    return "[%s] %2ds" % (bar, remaining)


def start_bar_region(remaining=10):
    """Draw the bar line + the input prompt line. Cursor ends after the prompt.

    'remaining' lets a caller redraw the bar at the actual time left (e.g.
    after a REJECT) instead of always snapping back to a full 10s bar, since
    the server's clock never resets on an invalid word (Rule #4)."""
    global bar_active
    if USE_ANSI:
        # Line 1: the bar.  Line 2: the input field.
        sys.stdout.write(render_bar(remaining) + "\n" + PROMPT)
    else:
        sys.stdout.write("\r" + render_bar(remaining) + "  " + PROMPT)
    sys.stdout.flush()
    bar_active = True


def update_bar(remaining):
    """Update the bar in place without disturbing the input field."""
    if not bar_active:
        return
    if USE_ANSI:
        sys.stdout.write(
            "\0337"          # save the cursor position (currently in the input field)
            "\033[1A"        # move up 1 line -> the bar line
            "\r\033[2K"      # go to column 0 + clear the whole line
            + render_bar(remaining) +
            "\0338"          # restore the cursor to the input field
        )
    else:
        sys.stdout.write("\r" + render_bar(remaining) + "  " + PROMPT)
    sys.stdout.flush()


def handle_message(msg):
    """Interpret one JSON message from the server and display it."""
    global input_mode, bar_active, last_remaining
    mtype = msg.get("type")
    data = msg.get("data", {})

    if mtype == "ASSIGN":
        print("\n>>> You are PLAYER %d." % data.get("player"))
    elif mtype == "RULES":
        print("\n" + "=" * 50)
        print(data.get("text", ""))
        if not data.get("dictionary_active", True):
            print("  (*) No dictionary available -> meaning check disabled.")
        print("=" * 50)
    elif mtype == "INFO":
        print("\n[i] " + data.get("msg", ""))
    elif mtype == "READY_ASK":
        input_mode = "ready"
        print("\n" + data.get("msg", ""))
        print(">>> Type 'ready' (then Enter) when you have finished reading the rules.")
    elif mtype == "GO":
        input_mode = "idle"
        print("\n" + "=" * 20 + " GO! " + "=" * 20)
    elif mtype == "ROUND_START":
        print("\n--- New round. First to move: PLAYER %d ---"
              % data.get("start_player"))
    elif mtype == "TURN":
        input_mode = "word"
        nc = data.get("need_char")
        if nc:
            print("\n>>> YOUR TURN! The word must start with '%s'." % nc)
        else:
            print("\n>>> YOUR TURN! Enter any word to start.")
        last_remaining = 10
        start_bar_region(last_remaining)   # set up the bar + input field
    elif mtype == "WAIT":
        input_mode = "idle"
        bar_active = False
        print("\n... " + data.get("msg", "Waiting for opponent..."))
    elif mtype == "TIME":
        last_remaining = data.get("remaining", 0)
        update_bar(last_remaining)
    elif mtype == "ACCEPT":
        bar_active = False
        print("\n[OK] Word '%s' accepted." % data.get("word"))
    elif mtype == "OPP":
        bar_active = False
        print("\n[Opponent played]: %s   (your next word must start with '%s')"
              % (data.get("word"), data.get("need_char")))
    elif mtype == "REJECT":
        print("\n[X] Rejected: %s  (try again, the clock is still running!)"
              % data.get("reason"))
        if input_mode == "word":
            # Redraw at the actual remaining time (not a full bar): the
            # server's clock keeps running on a rejected word (Rule #4), so
            # the bar must not visually reset to 10s here.
            start_bar_region(last_remaining)
    elif mtype == "WIN":
        bar_active = False
        s = data.get("scores", [0, 0])
        print("\n*** YOU WIN THIS ROUND! (%s)  Score: %d - %d ***"
              % (data.get("reason"), s[0], s[1]))
    elif mtype == "LOSE":
        bar_active = False
        s = data.get("scores", [0, 0])
        print("\n--- You lose this round (%s).  Score: %d - %d ---"
              % (data.get("reason"), s[0], s[1]))
    elif mtype == "SCORE":
        print("[SCOREBOARD] Player 1: %d  |  Player 2: %d"
              % (data.get("p1", 0), data.get("p2", 0)))
    elif mtype == "PLAY_AGAIN_ASK":
        input_mode = "again"
        bar_active = False
        print("\n" + data.get("msg", "Play again? (yes/no)"))
    elif mtype == "GAME_OVER":
        bar_active = False
        print("\n===== MATCH OVER =====")
        print(data.get("final", ""))
        import os
        os._exit(0)
    else:
        print(msg)


def receiver(sock):
    buffer = ""
    while True:
        try:
            data = sock.recv(1024)
        except OSError:
            break
        if not data:
            print("\n[!] Lost connection to the server.")
            import os
            os._exit(0)
        buffer += data.decode("utf-8", errors="ignore")
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue
            try:
                handle_message(json.loads(line))
            except json.JSONDecodeError:
                print("\n[!] Received a malformed message from the server.")


def main():
    global bar_active
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PORT))
    except OSError as e:
        print("Could not connect to the server: %s" % e)
        return
    print("Connected to the server %s:%d" % (HOST, PORT))

    threading.Thread(target=receiver, args=(sock,), daemon=True).start()

    try:
        while True:
            text = input().strip()
            bar_active = False      # user just pressed Enter -> pause drawing the bar
            if not text:
                continue
            low = text.lower()
            # Surrender must use a leading '/' so it isn't confused with a valid word.
            if low in ("/quit", "/surrender", "/gg", "/give"):
                send_json(sock, "QUIT")
                continue
            if input_mode == "ready":
                send_json(sock, "READY")
                continue
            if input_mode == "again":
                send_json(sock, "PLAY_AGAIN", text)
            else:
                # 'quit'/'surrender' without '/' -> sent as a normal word.
                send_json(sock, "WORD", text)
    except (KeyboardInterrupt, EOFError):
        # Closing the socket -> the server treats it as a disconnect and ends the match.
        pass
    finally:
        sock.close()


if __name__ == "__main__":
    main()
