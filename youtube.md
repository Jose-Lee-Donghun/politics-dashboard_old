# YouTube 댓글 기능 장애 보고서

## 요약

댓글 기능이 작동하지 않은 근본 원인은 두 가지입니다.

1. **yt-dlp의 JS 런타임 의존성**: YouTube 댓글 추출에 Node.js/Deno가 필요한데 HF Spaces에 없었음
2. **무음 예외 처리**: `except Exception: return []` 구조가 실제 에러를 숨겨서 원인 파악이 늦어짐

---

## 시도 순서별 실패 원인

### 1단계 — yt-dlp subprocess (최초 코드)

```python
YTDLP = os.path.join(os.path.dirname(sys.executable), "yt-dlp")
result = subprocess.run([YTDLP, "--dump-json", ...])
```

**실패 원인**: HF Spaces에서 subprocess로 yt-dlp 바이너리를 실행하면 YouTube가 클라우드 IP를 차단하고, 120초 타임아웃 동안 앱이 "채널 스캔 중..." 상태로 멈춤.

---

### 2단계 — RSS media:statistics로 조회수 교체

```python
stats = media_group.find("media:statistics", NS)
```

**실패 원인**: YouTube RSS XML 구조상 `media:statistics`는 `media:group > media:community > media:statistics` 경로에 있는데, `media:community`를 빠뜨리고 찾아서 항상 `None` 반환.

**수정**: `community = media_group.find("media:community", NS)` 경로 추가로 해결.

---

### 3단계 — yt-dlp Python 라이브러리로 댓글 시도

```python
import yt_dlp
ydl_opts = {"getcomments": True, ...}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=False)
    comments = info.get("comments")  # → []
```

**실패 원인**: yt-dlp 최신 버전은 YouTube 댓글 추출에 JavaScript 런타임(Node.js 또는 Deno)이 필수. HF Spaces 기본 환경에 없어서 댓글 수 0 반환.

로컬 테스트 결과:
```
WARNING: No supported JavaScript runtime could be found.
Only deno is enabled by default...
댓글 수: 0
```

---

### 4단계 — packages.txt에 nodejs 추가

```
# packages.txt
nodejs
```

**결과 미확인**: 빌드는 성공했으나 실제 댓글 로딩 여부 검증 전에 다음 단계로 넘어감.

---

### 5단계 — youtube-comment-downloader 교체 (현재)

```python
from youtube_comment_downloader import YoutubeCommentDownloader, SORT_BY_POPULAR
dl = YoutubeCommentDownloader()
for c in dl.get_comments_from_url(url, sort_by=SORT_BY_POPULAR):
    ...
```

**장점**: JS 런타임 불필요, 순수 Python requests 기반.  
**로컬 테스트**: 정상 동작 확인 (댓글 5개 수신).  
**현재 상태**: HF Spaces에서 실제 에러 확인 중 (에러 트레이스 추가 배포 완료).

---

## 핵심 교훈

| 문제 | 원인 | 해결책 |
|------|------|--------|
| 앱이 멈춤 | subprocess yt-dlp 타임아웃 | RSS 직접 파싱으로 교체 |
| 조회수 None | XML 경로 오류 (community 누락) | 올바른 경로로 수정 |
| 댓글 0개 | yt-dlp JS 런타임 없음 | youtube-comment-downloader로 교체 |
| 디버깅 지연 | 모든 에러를 `except Exception`으로 묵살 | 에러 메시지 사이드바에 노출 |

---

## 현재 아키텍처

```
조회수: YouTube RSS (media:community > media:statistics)
댓글:   youtube-comment-downloader (순수 Python)
배포:   GitHub → HF Spaces (자동 sync via GitHub Actions)
```

