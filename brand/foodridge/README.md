# FOODRIDGE 공식 로고 시스템 (v1.0)

모든 파일은 `tools/build_logo.py`라는 하나의 도형 스펙에서 만들어지므로 비율과 색상이 항상 같습니다.
SVG 안의 글자는 모두 **아웃라인(패스)으로 변환**되어 있어 Illustrator, Figma, 웹 브라우저에서 폰트 없이 열고 편집할 수 있습니다.

## 구성

| 유형 | 파일 | 용도 |
|---|---|---|
| 기본형 (세로) | `foodridge-primary-*.svg` | 기본 로고, 인쇄물, 명함, 패키지 |
| 기본형 + 국문 | `foodridge-primary-kr-*.svg` | 국내용 문서, 간판, 계약서 |
| 가로형 | `foodridge-horizontal-*.svg` | 웹사이트 헤더, 이메일 서명, 레터헤드 |
| 심볼 | `foodridge-symbol-*.svg` | 작은 공간, 워터마크, 패턴 |
| 워드마크 | `foodridge-wordmark-*.svg` | 심볼을 넣을 공간이 없을 때 |
| 앱 아이콘 | `foodridge-app-icon.svg` | 파비콘, 앱 아이콘 |
| SNS 프로필 | `foodridge-sns-profile.svg` | 인스타그램, X 등 프로필 이미지 |

색상 변형 `*`: `gold`(기본) · `gradient`(프리미엄/디지털) · `black`(단색 인쇄, 팩스) · `white`(네이비 또는 어두운 배경)

`svg/`는 편집용 원본, `png/`는 바로 쓸 수 있는 고해상도 이미지(가로 2000px, 투명 배경)입니다.

## 색상

| 이름 | HEX | RGB | CMYK (근사치) |
|---|---|---|---|
| Foodridge Gold (기본) | `#B8862F` | 184 134 47 | 0 27 74 28 |
| Gold Light | `#E6C77A` | 230 199 122 | 0 13 47 10 |
| Gold Dark | `#8C6420` | 140 100 32 | 0 29 77 45 |
| Foodridge Navy (보조) | `#14213D` | 20 33 61 | 67 46 0 76 |
| Black | `#1A1A1A` | 26 26 26 | 0 0 0 90 |

CMYK 값은 RGB에서 계산한 근사치입니다. 인쇄소에서 교정 인쇄로 확인하고, 금박 인쇄 시에는 `gold` 단색 파일을 사용하세요.

## 서체

- 영문 워드마크: **Cinzel SemiBold**, 자간 +80 (SIL Open Font License, 상업적 사용 가능)
- 국문: **Noto Serif KR SemiBold** (SIL Open Font License)

## 사용 규칙

- **여백**: 로고 주변에 워드마크 "F"의 높이만큼 여백을 둡니다 (파일에 이미 포함).
- **최소 크기**: 기본형 가로 30mm / 120px, 가로형 40mm / 160px, 심볼 10mm / 32px. 이보다 작으면 심볼 또는 앱 아이콘을 사용합니다.
- **금지**: 비율 변경(늘리기/찌그러뜨리기), 색상 임의 변경, 그림자·외곽선 추가, 심볼과 워드마크 위치 변경, 복잡한 사진 배경 위에 직접 배치.

## 다시 만들기

```bash
pip install fonttools uharfbuzz cairosvg
python3 tools/build_logo.py Cinzel-SemiBold.ttf NotoSerifKR-SemiBold.ttf
```
폰트는 Google Fonts에서 무료로 받을 수 있습니다.

## 비교안: 기둥 2개 (검토용)

`options/two-tower/`에 기둥이 2개인 전통 현수교 버전이 같은 구성(22개)으로 들어 있습니다. 두 안을 나란히 비교한 이미지는 `options/compare-towers.png`입니다.
최종안을 정하면 선택한 안을 `svg/`, `png/`에 두고 다른 안은 삭제합니다.
`python3 tools/build_logo.py <Cinzel> <NotoSerifKR> --towers 2`로 다시 만들 수 있습니다.
