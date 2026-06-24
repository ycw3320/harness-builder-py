# 패키징·배포 명세 (골격 — PM4에서 본문)

> 프레임워크 확정 후 본문 작성.

## 목차(예정)
- Flet 채택 시: `flet build windows`(MSIX) — 번들 100MB+ 수용
- Qt 채택 시: PyInstaller(onedir) / Briefcase
- 코드서명: 개인 OV 인증서(고정비용) · 미서명+SmartScreen 경고 감수 선택지
- 산출: 설치본 + 버전 태그 + 변경로그
- (향후) macOS Developer ID 공증

## 원칙
1인 유지보수 — 확정 프레임워크의 단일 빌드 도구로 통일.
