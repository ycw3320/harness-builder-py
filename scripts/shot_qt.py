"""Qt 셸 오프스크린 렌더 → PNG. 인자: [out_png] [theme(light|dark)]."""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from harness_app.qt_shell.app import make_app

app, win = make_app()
theme = sys.argv[2] if len(sys.argv) > 2 else "light"
win.set_theme(theme)
win.resize(1180, 720)
win.show()
app.processEvents()

# S3 시연: 첫 행 펼친 상태 강제(오프스크린 settle — min/max 고정으로 편집부 공간 확보)
if win._rows:
    r0 = win._rows[0]
    r0.set_open(True)
    r0.setMinimumHeight(r0._expanded)
    r0.setMaximumHeight(r0._expanded)
for _ in range(10):
    app.processEvents()
win.repaint()
app.processEvents()

out = sys.argv[1] if len(sys.argv) > 1 else "_shot_qt.png"
win.grab().save(out)
print("saved", out, theme, os.path.getsize(out), "bytes")
