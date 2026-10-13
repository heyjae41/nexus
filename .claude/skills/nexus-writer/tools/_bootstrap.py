"""작가 도구 공통 부트스트랩 — 백엔드 패키지(app.*)를 import 경로에 올린다.

각 도구는 `from _bootstrap import PROJECT_ROOT` 한 줄로 쓴다 (스크립트 실행 시 도구 폴더가
sys.path[0] 이라 형제 모듈 import 가 된다)."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
