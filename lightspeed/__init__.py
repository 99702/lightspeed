from aqt import mw, gui_hooks
from . import reviewer


def add_button(link_handler, links):
    links.append(["Ctrl+Shift+L", "lightspeed", "Lightspeed"])
    return link_handler


def on_message(handled, message, context):
    if message != "lightspeed":
        return handled
    deck = mw.col.decks.current()
    reviewer.launch(deck)
    return True, None


def on_state_change(new_state, old_state):
    if new_state != "review":
        reviewer.deactivate()


gui_hooks.overview_will_render_bottom.append(add_button)
gui_hooks.webview_did_receive_js_message.append(on_message)
gui_hooks.state_will_change.append(on_state_change)
