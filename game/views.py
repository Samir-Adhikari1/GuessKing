import random
from django.shortcuts import render, redirect

# -------------------------
# Word Lists (Tech Theme) — 7 Levels
# -------------------------

EASY_WORDS      = ["mouse", "coder", "logic", "input", "print", "paste", "bytes", "click", "email", "files"]
MEDIUM_WORDS    = ["array", "stack", "queue", "linux", "pixel", "flask", "query", "class", "value", "index"]
HARD_WORDS      = ["cache", "debug", "token", "cloud", "block", "build", "scope", "parse", "shell", "fetch"]
EXPERT_WORDS    = ["async", "spawn", "proxy", "mutex", "yield", "trait", "macro", "regex", "tuple", "slice"]
MASTER_WORDS    = ["bitwise", "kernel", "branch", "shader", "cipher", "neural", "socket", "vector"]
ELITE_WORDS     = ["malloc", "offset", "pragma", "signal", "thread", "buffer", "struct", "daemon"]
LEGENDARY_WORDS = ["bitflip", "entropy", "latency", "syscall", "sandbox", "payload", "runtime", "pointer"]

# Cap all words to 5 letters (master/elite/legendary use 5-letter picks)
MASTER_WORDS    = ["heap", "mutex", "yield", "inode", "chmod", "shebang"[:5], "vnode", "inode"[:5], "pager", "shard"]
ELITE_WORDS     = ["xmmap", "ptrace", "splice", "ioctl", "sysfs"[:5], "ramfs", "tmpfs", "audit", "trace", "probe"]
LEGENDARY_WORDS = ["mlock", "brk", "dmesg"[:5], "swapd"[:5], "iommu"[:5], "dmesg", "kprobe"[:5], "ebpf"[:4]+"s", "vmalloc"[:5], "cgroup"[:5]]

DIFFICULTY_CONFIG = {
    "easy":      {"words": EASY_WORDS,      "multiplier": 1, "attempts": 8,  "label": "Easy",      "preview_time": 3000},
    "medium":    {"words": MEDIUM_WORDS,    "multiplier": 2, "attempts": 7,  "label": "Medium",    "preview_time": 2500},
    "hard":      {"words": HARD_WORDS,      "multiplier": 3, "attempts": 6,  "label": "Hard",      "preview_time": 2000},
    "expert":    {"words": EXPERT_WORDS,    "multiplier": 4, "attempts": 5,  "label": "Expert",    "preview_time": 1500},
    "master":    {"words": MASTER_WORDS,    "multiplier": 5, "attempts": 5,  "label": "Master",    "preview_time": 1000},
    "elite":     {"words": ELITE_WORDS,     "multiplier": 7, "attempts": 4,  "label": "Elite",     "preview_time": 700},
    "legendary": {"words": LEGENDARY_WORDS, "multiplier": 10,"attempts": 3,  "label": "Legendary", "preview_time": 500},
}

MAX_ATTEMPTS = 6


# -------------------------
# Start Game View
# -------------------------

def start_game(request):
    if request.method == "POST":
        difficulty = request.POST.get("difficulty", "easy")
        config = DIFFICULTY_CONFIG.get(difficulty, DIFFICULTY_CONFIG["easy"])

        word_list   = [w for w in config["words"] if len(w) == 5]
        secret_word = random.choice(word_list)

        request.session["secret_word"]    = secret_word
        request.session["attempts"]       = config["attempts"]
        request.session["max_attempts"]   = config["attempts"]
        request.session["multiplier"]     = config["multiplier"]
        request.session["word_list"]      = word_list
        request.session["feedback"]       = []
        request.session["preview_shown"]  = False
        request.session["difficulty"]     = difficulty
        request.session["preview_time"]   = config["preview_time"]

        return redirect("rules")

    return render(request, "game/start.html", {"difficulties": DIFFICULTY_CONFIG})


# -------------------------
# Word Evaluation Logic
# -------------------------

def evaluate_guess(secret_word, guess):
    result      = []
    secret_list = list(secret_word)
    guess_list  = list(guess)
    statuses    = ["absent"] * 5

    # First pass: correct positions
    for i in range(5):
        if guess_list[i] == secret_list[i]:
            statuses[i]    = "correct"
            secret_list[i] = None
            guess_list[i]  = None

    # Second pass: present letters
    for i in range(5):
        if guess_list[i] is not None:
            if guess_list[i] in secret_list:
                statuses[i] = "present"
                secret_list[secret_list.index(guess_list[i])] = None

    for i, status in enumerate(statuses):
        result.append((status, guess[i]))

    return result


# -------------------------
# Play Game View
# -------------------------

def play_game(request):
    secret_word   = request.session.get("secret_word")
    attempts      = request.session.get("attempts")
    max_attempts  = request.session.get("max_attempts", 6)
    multiplier    = request.session.get("multiplier", 1)
    word_list     = request.session.get("word_list", [])
    feedback      = request.session.get("feedback", [])
    difficulty    = request.session.get("difficulty", "easy")
    preview_time  = request.session.get("preview_time", 2500)

    if not secret_word:
        return redirect("start")

    preview_shown = request.session.get("preview_shown", False)
    if not preview_shown:
        request.session["preview_shown"] = True

    error = None

    if request.method == "POST":
        guess = request.POST.get("guess", "").lower().strip()

        if len(guess) != 5:
            error = "Please enter exactly 5 letters."
        elif not guess.isalpha():
            error = "Only letters allowed."
        else:
            result = evaluate_guess(secret_word, guess)
            feedback.append(result)
            request.session["feedback"] = feedback

            if guess == secret_word:
                score = attempts * 10 * multiplier
                request.session.flush()
                return render(request, "game/result.html", {
                    "win": True, "word": secret_word, "score": score,
                    "difficulty": difficulty,
                })

            attempts -= 1
            request.session["attempts"] = attempts

            if attempts == 0:
                request.session.flush()
                return render(request, "game/result.html", {
                    "win": False, "word": secret_word,
                    "difficulty": difficulty,
                })

    # Build empty rows for remaining guesses (Wordle grid style)
    used_rows   = len(feedback)
    empty_rows  = max_attempts - used_rows
    empty_cells = [("empty", "") for _ in range(5)]
    empty_row_list = [empty_cells for _ in range(max(0, empty_rows))]

    return render(request, "game/play.html", {
        "attempts":      attempts,
        "max_attempts":  max_attempts,
        "multiplier":    multiplier,
        "feedback":      feedback,
        "empty_rows":    empty_row_list,
        "word_list":     word_list,
        "show_preview":  not preview_shown,
        "difficulty":    difficulty,
        "preview_time":  preview_time,
        "error":         error,
    })


# -------------------------
# Rules Page
# -------------------------

def rules_page(request):
    if not request.session.get("secret_word"):
        return redirect("start")
    difficulty = request.session.get("difficulty", "easy")
    config     = DIFFICULTY_CONFIG.get(difficulty, DIFFICULTY_CONFIG["easy"])
    return render(request, "game/rules.html", {
        "attempts":   config["attempts"],
        "difficulty": config["label"],
        "multiplier": config["multiplier"],
    })