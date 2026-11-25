# Lightspeed

Anki addon — quick card browsing without grading.

## Structure

```
lightspeed/
  __init__.py      entry point, hooks into overview + state changes
  reviewer.py      session class, bottom bar HTML, resume save/load
  manifest.json    addon metadata for Anki
  resume.json      auto-generated at runtime, gitignored
```

## Commands

```bash
# symlink into Anki for development
ln -s $(pwd)/lightspeed ~/.local/share/Anki2/addons21/lightspeed
```

No build step. No dependencies outside Anki.

## Code style

- Python 3.10+ (match/case is fine)
- No comments, no docstrings — code should read on its own
- Keep files small. Two files is enough for this addon
- Use `aqt.qt` imports, not direct PyQt6
- Flat over nested. Module-level functions over class methods where it makes sense

## Anki addon conventions

- `manifest.json` is required, `config.json` is optional
- Addon entry point is `__init__.py`
- Use `gui_hooks` for integration, avoid monkey-patching when a hook exists
- `mw.col` is the collection, `mw.reviewer` is the active reviewer
- `find_cards()` returns a protobuf container — wrap with `list()`
- `webview_did_receive_js_message` for handling custom JS→Python bridge calls
- `state_will_change` to clean up when user navigates away

## Testing

Manual only. Restart Anki after changes (`Tools > Add-ons > View Files` to verify path).
