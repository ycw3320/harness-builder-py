# 패키징 (PM4) — Windows 단일 실행본

> Qt 셸(`harness_app.qt_shell`)을 PyInstaller 로 `.exe` 단일 실행본으로 빌드한다([[ADR-0007]] PySide6 확정).

## 빌드
```bash
pip install -e ".[llm]" pyinstaller   # 앱 + 인앱 LLM(anthropic·keyring) + 빌드 도구
python packaging/build_exe.py         # → dist/HarnessBuilder.exe
```

- 진입점: `packaging/app_entry.py` → `harness_app.qt_shell.app.main()`.
- `--onefile --windowed`: 콘솔 없는 단일 exe. PySide6 Qt 플러그인은 PyInstaller 훅이 자동 번들.
- **인앱 LLM 의존성은 지연 import** 라 정적 분석에 안 잡힘 → `--collect-all anthropic keyring` 으로 명시 수집. keyring Windows 백엔드(자격증명관리자)도 함께 포함.
- 산출물(`build/`·`dist/`·`*.spec`)은 `.gitignore` 대상(저장소 미포함).

## 실행·배포
- `dist/HarnessBuilder.exe` 더블클릭 실행(설치 불요). 첫 실행은 onefile 임시 추출로 수초 소요.
- 한글 폰트는 **번들 Pretendard 우선**(`--add-data` 로 `harness_app/qt_shell/fonts/` 동봉, OFL.txt 포함) — 번들 누락 시 시스템 malgun 폴백. 소형 크기 가로획 드롭아웃('안전벨ㅌ' 현상) 방지를 위해 `PreferNoHinting` 적용.
- 테마·LLM 모델 선택은 `QSettings`("harness-builder"), API 키는 OS 자격증명관리자에 저장(exe 에 미포함).

## 검증
- 빌드 후 exe 실행 → 창 표시 확인. 오프라인 기본(키 없으면 복사→붙여넣기), 'LLM 설정'에서 키 입력 시 'AI로 채우기' 활성.
- **적용 폰트가 Pretendard 인지 확인**(제목 렌더가 시스템 Malgun 과 다름; 폴백이면 --add-data 경로 점검).
- 폴더 생성(write_tree)·기존 폴더 가져오기(import) 동작 확인.

## 대안(참고)
- `--onedir`(기본): `dist/HarnessBuilder/` 폴더 배포 — 시작 빠름, 파일 다수.
- 서명/인스톨러(PM4+): signtool 코드서명 · Inno Setup/NSIS 인스톨러는 추후. (미서명은 SmartScreen 경고 감수.)
