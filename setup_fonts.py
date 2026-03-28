#!/usr/bin/env python3
"""
Pretendard 폰트 설치 스크립트
────────────────────────────────────────────────────
Pretendard: 한국 트렌드 디자인 표준 폰트
라이선스:   SIL Open Font License (무료 상용 가능)
출처:        https://github.com/orioncactus/pretendard

Usage: python setup_fonts.py
"""

import io
import zipfile
import urllib.request
from pathlib import Path

FONTS_DIR = Path("fonts")
FONTS_DIR.mkdir(exist_ok=True)

_PRETENDARD_ZIP_URL = (
    "https://github.com/orioncactus/pretendard/releases/"
    "download/v1.3.9/Pretendard-1.3.9.zip"
)

NEEDED = [
    "Pretendard-Bold.otf",
    "Pretendard-SemiBold.otf",
    "Pretendard-Medium.otf",
    "Pretendard-Regular.otf",
]


def is_installed() -> bool:
    return all((FONTS_DIR / f).exists() for f in NEEDED)


def download():
    if is_installed():
        print("✅ Pretendard 이미 설치됨 (fonts/ 폴더)")
        return

    print(f"⬇️  Pretendard v1.3.9 다운로드 중...")
    print(f"   URL: {_PRETENDARD_ZIP_URL}")

    try:
        req = urllib.request.Request(
            _PRETENDARD_ZIP_URL,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = resp.read()
    except Exception as e:
        print(f"❌ 다운로드 실패: {e}")
        print("   수동 설치: https://github.com/orioncactus/pretendard/releases")
        return

    installed = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for entry in z.namelist():
            for needed in NEEDED:
                if entry.endswith(needed):
                    out = FONTS_DIR / needed
                    out.write_bytes(z.read(entry))
                    installed.append(needed)
                    print(f"   ✅ {needed}")
                    break

    if installed:
        print(f"\n✅ Pretendard 설치 완료 → fonts/ ({len(installed)}개)")
    else:
        print("⚠️  ZIP에서 OTF 파일을 찾지 못했습니다.")


if __name__ == "__main__":
    download()
