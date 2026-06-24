# metro-code

Claude Code용 **인라인 주식 시세 알리미**. Claude Code 하단 status line에 관심
종목의 실시간 시세를 보여주고, skill을 통해 자연어로 종목을 추가/삭제할 수 있습니다.

```
📈 AAPL $294.30 ▼0.91%  │  TSLA $381.61 ▼5.79%  │  005930.KS ₩310,000 ▼12.31%
```

## 구성

| 경로 | 역할 |
|------|------|
| `.claude/settings.json` | status line 명령 등록 |
| `.claude/scripts/stock_statusline.py` | 시세 조회 + 인라인 출력 (60초 캐시) |
| `.claude/scripts/stock_manage.py` | 종목 추가/삭제/조회 CLI |
| `.claude/skills/stock-alerts/SKILL.md` | "종목 추가해줘" 등 자연어 트리거 |
| `.claude/stock-alerts/tickers.json` | 추적 종목 목록 |

시세는 Yahoo Finance 공개 API에서 가져오므로 **API 키가 필요 없습니다**.
미국·한국 주식과 암호화폐를 지원합니다.

## 사용법

### skill로 (권장)

Claude Code 대화창에서 자연어로 요청하면 됩니다.

- "삼성전자 종목 추가해줘"
- "테슬라 빼줘"
- "추적 중인 종목 보여줘"

### CLI로 직접

```bash
python3 .claude/scripts/stock_manage.py add AAPL 005930.KS
python3 .claude/scripts/stock_manage.py remove TSLA
python3 .claude/scripts/stock_manage.py list
python3 .claude/scripts/stock_manage.py clear
```

### 심볼 표기 (Yahoo Finance 형식)

| 시장 | 예시 |
|------|------|
| 미국 주식 | `AAPL`, `TSLA` |
| 코스피 | `005930.KS` (삼성전자) |
| 코스닥 | `035720.KQ` |
| 암호화폐 | `BTC-USD` |
| 도쿄 | `7203.T` |

## 요구 사항

- `python3` (표준 라이브러리만 사용 — 추가 설치 불필요)
- 시세 조회를 위한 인터넷 연결

> 변경 사항을 적용하려면 Claude Code를 재시작하거나 새 세션을 시작하세요
> (status line 설정과 skill은 세션 시작 시 로드됩니다).
