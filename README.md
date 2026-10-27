# 대련 2박 3일 (2026.11.20 – 11.22)

여행 일정표 페이지예요. GitHub Pages로 열려요: https://gus-wn.github.io/travel_dalian/

- `index.html` — 페이지 화면
- `data.json` — 일정 내용 (페이지에서 '저장'을 누르면 여기에 기록돼요)
- `photos/` — 페이지에서 올린 사진

## 페이지에서 수정하는 방법

1. 페이지 맨 위 **편집하기** 누르기
2. GitHub에서 저장 키 만들기: Settings → Developer settings → Personal access tokens → **Fine-grained tokens** → Generate new token
   - Repository access: **Only select repositories** → `gus-wn/travel_dalian`
   - Repository permissions → **Contents: Read and write**
3. 만든 키(`github_pat_…`)를 붙여넣기. 키는 그 기기 브라우저에만 저장돼요.
4. 일정을 고친 뒤 화면 아래 **저장**. 다른 기기에는 1~2분 뒤에 반영돼요.

저장 키가 없는 사람은 보기만 할 수 있어요.

## 지도

맨 위 지도는 고덕지도 바탕지도 위에 [Leaflet](https://leafletjs.com) (BSD-2, `lib/leaflet/`)으로 핀을 찍어요.
일정 카드에 **+ 고덕지도**로 고덕 앱의 공유 링크(surl.amap.com/…)를 넣으면, GitHub Actions(`scripts/resolve_amap.py`)가 링크에서 좌표를 찾아 30초~1분 안에 핀을 찍어요.
