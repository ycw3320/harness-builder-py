"""Qt 셸 오프스크린 렌더 → PNG (무디스플레이 스크린샷, 루브릭 시각 채점용)."""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from harness_app.qt_shell.app import RowWidget, make_app

app, win = make_app()
win.resize(1160, 700)
win.show()
app.processEvents()

# S3 시연: 첫 행 펼친 상태 강제(애니메이션 최종값)
if win._rows:
    win._rows[0].set_open(True)
    win._rows[0].setMaximumHeight(RowWidget.EXPANDED)
for _ in range(6):
    app.processEvents()

out = sys.argv[1] if len(sys.argv) > 1 else "_shot_qt.png"
win.grab().save(out)
print("saved", out, os.path.getsize(out), "bytes")
