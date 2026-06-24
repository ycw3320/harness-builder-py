# UI 명세 (골격 — PM3에서 본문)

> 프레임워크 확정(PM2) 후 본문 작성. 현재는 목차·원칙만.

## 목차(예정)
- 3-pane 레이아웃(좌 nav / 중 center / 우 right) — `B2 shell`
- 좌 nav: 6계층 + 결정방식 색점 + enabled/total 카운트 + 에러배지 + verification 잠금
- 중 center: 컴팩트 36px collapsible 행 + 6 kind 폼 + 컨텍스트 문서/섹션 뷰
- 우 right: 라이브 시뮬레이터 + lint(보안) 패널 + export(폴더쓰기) + 파일 미리보기
- 안내형 누적 흐름(§0.6): 영역 인트로 · "다음 추천 영역" · 완성도 미터 · 안내 모드
- 기본/고급(advanced) 점진 노출

## 원칙
- 위젯은 로직 없음 — state/fs 호출만(controllers B7).
- 북극성: 초심자가 한눈에 "여기서 뭘 설정하고, 다음에 뭘 할지" 알게.
