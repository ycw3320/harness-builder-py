"""PyInstaller 진입점 — 버클(하네스 빌더) Qt GUI 단일 실행본."""

if __name__ == "__main__":
    try:
        from harness_app.qt_shell.app import main

        main()
    except Exception:
        # windowed 모드는 stderr 가 없어 예외가 대화상자 한 장으로만 남음 —
        # 진단 가능하도록 트레이스백을 홈 디렉터리 로그 파일에 기록 후 재던짐.
        import traceback
        from pathlib import Path

        Path.home().joinpath("HarnessBuilder-crash.log").write_text(
            traceback.format_exc(), encoding="utf-8"
        )
        raise
