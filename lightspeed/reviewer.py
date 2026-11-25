import json
from pathlib import Path

from aqt.qt import QTimer
from aqt import mw
from aqt.sound import av_player
from aqt.reviewer import Reviewer

SAVE_PATH = Path(__file__).parent / "resume.json"

BOTTOM_BAR = """
<style>
.ls { display:flex; align-items:center; justify-content:center; padding:6px 16px; gap:14px; font-size:13px }
.ls button { padding:5px 16px; border-radius:5px; border:1px solid #ccc; background:#f0f0f0; cursor:pointer; font-size:13px }
.ls button:hover { background:#e0e0e0 }
.ls button:disabled { opacity:.35; cursor:default }
.ls .progress { color:#888; min-width:60px; text-align:center; font-size:12px; cursor:pointer; text-decoration:underline dotted }
</style>
<div class="ls">
  <button id="prev" onclick="pycmd('ls:prev')">&#9664; Prev</button>
  <select id="mode" onchange="pycmd('ls:mode:'+this.value)">
    <option value="front" selected>Front</option>
    <option value="back">Back</option>
  </select>
  <label><input type="checkbox" id="auto" onchange="pycmd('ls:auto:'+this.checked)"> Auto</label>
  <input type="number" id="speed" min="0.1" max="30" step="0.1" value="1" style="width:50px"
         onchange="pycmd('ls:speed:'+this.value)">s
  <label><input type="checkbox" id="audio" onchange="pycmd('ls:audio:'+this.checked)"> Wait audio</label>
  <span class="progress" id="progress" onclick="pycmd('ls:jump')"></span>
  <button id="next" onclick="pycmd('ls:next')">Next &#9654;</button>
  <button onclick="pycmd('ls:close')" style="margin-left:8px">Close</button>
</div>
<script>
document.addEventListener('keydown', e => {
    if (e.key === 'ArrowLeft') pycmd('ls:prev')
    else if (e.key === 'ArrowRight') pycmd('ls:next')
    else if (e.key === 'Escape') pycmd('ls:close')
})
</script>
"""

active = None

_real_bottom = Reviewer._bottomHTML
_real_handler = Reviewer._linkHandler


def _bottom(self):
    return BOTTOM_BAR if active else _real_bottom(self)


def _handler(self, url):
    if active and url.startswith("ls:"):
        active.on_cmd(url[3:])
    else:
        _real_handler(self, url)


Reviewer._bottomHTML = _bottom
Reviewer._linkHandler = _handler


def _load_resume(deck_id):
    try:
        return json.loads(SAVE_PATH.read_text()).get(str(deck_id))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _save_resume(deck_id, card_id):
    try:
        data = json.loads(SAVE_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    data[str(deck_id)] = card_id
    SAVE_PATH.write_text(json.dumps(data))


def launch(deck):
    global active
    cards = list(mw.col.find_cards(f'"deck:{deck["name"]}"'))
    if not cards:
        from aqt.utils import showInfo
        showInfo("No cards in this deck.")
        return

    start_pos = 0
    saved_card = _load_resume(deck["id"])
    if saved_card and saved_card in cards:
        start_pos = cards.index(saved_card)

    active = Session(deck["id"], cards, start_pos)
    active.run()


def deactivate():
    global active
    if not active:
        return
    active.cleanup()
    active = None


class Session:
    def __init__(self, deck_id, cards, pos):
        self.deck_id = deck_id
        self.cards = cards
        self.pos = pos
        self.mode = "front"
        self.auto = False
        self.interval = 1.0
        self.wait_audio = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.go_next)

    def run(self):
        mw.moveToState("review")
        QTimer.singleShot(50, self.show)

    def cleanup(self):
        self.timer.stop()
        av_player.stop_and_clear_queue()
        _save_resume(self.deck_id, self.cards[self.pos])

    def show(self):
        if not active:
            return
        card = mw.col.get_card(self.cards[self.pos])
        rev = mw.reviewer
        rev.card = card
        rev._showQuestion()
        if self.mode == "back":
            rev._showAnswer()
        self.sync_bar()
        if self.auto and not self.wait_audio:
            self.timer.start(int(self.interval * 1000))

    def sync_bar(self):
        total = len(self.cards)
        prev_off = "true" if self.pos == 0 else "false"
        next_off = "true" if self.pos >= total - 1 else "false"
        auto_on = "true" if self.auto else "false"
        audio_on = "true" if self.wait_audio else "false"
        mw.reviewer.bottom.web.eval(f"""
            document.getElementById('progress').textContent = '{self.pos + 1} / {total}';
            document.getElementById('prev').disabled = {prev_off};
            document.getElementById('next').disabled = {next_off};
            document.getElementById('mode').value = '{self.mode}';
            document.getElementById('auto').checked = {auto_on};
            document.getElementById('speed').value = {self.interval};
            document.getElementById('audio').checked = {audio_on};
        """)

    def go_next(self):
        self.timer.stop()
        if self.pos < len(self.cards) - 1:
            self.pos += 1
            self.show()

    def go_prev(self):
        self.timer.stop()
        if self.pos > 0:
            self.pos -= 1
            self.show()

    def jump_to(self, num):
        self.timer.stop()
        self.pos = max(0, min(num - 1, len(self.cards) - 1))
        self.show()

    def set_auto(self, on):
        self.auto = on
        if on and not self.wait_audio:
            self.timer.start(int(self.interval * 1000))
        else:
            self.timer.stop()

    def set_interval(self, val):
        self.interval = max(0.1, float(val))
        if self.auto:
            self.timer.start(int(self.interval * 1000))

    def set_audio(self, on):
        self.wait_audio = on
        if self.auto:
            self.timer.stop() if on else self.timer.start(int(self.interval * 1000))

    def on_cmd(self, cmd):
        match cmd:
            case "next": self.go_next()
            case "prev": self.go_prev()
            case "close": mw.moveToState("overview")
            case "jump": self.prompt_jump()
            case _ if cmd.startswith("goto:"): self.jump_to(int(cmd[5:]))
            case _ if cmd.startswith("mode:"): self.mode = cmd[5:]; self.show()
            case _ if cmd.startswith("auto:"): self.set_auto(cmd[5:] == "true")
            case _ if cmd.startswith("speed:"): self.set_interval(cmd[6:])
            case _ if cmd.startswith("audio:"): self.set_audio(cmd[6:] == "true")

    def prompt_jump(self):
        total = len(self.cards)
        mw.reviewer.bottom.web.eval(f"""
            var n = prompt('Jump to card (1-{total}):', '{self.pos + 1}');
            if (n !== null && !isNaN(n)) pycmd('ls:goto:' + parseInt(n));
        """)
