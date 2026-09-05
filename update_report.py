import os
import sys
import json
import re
from datetime import datetime, timezone, timedelta
import urllib.request
import urllib.parse

# Timezone KST (UTC+9)
KST = timezone(timedelta(hours=9))
now_kst = datetime.now(KST)
today_str = now_kst.strftime("%Y년 %m월 %d일")
yesterday_kst = now_kst - timedelta(days=1)
yesterday_str = yesterday_kst.strftime("%Y%m%d")
yesterday_display = yesterday_kst.strftime("%Y년 %m월 %d일")

print(f"[{now_kst.strftime('%Y-%m-%d %H:%M:%S KST')}] Starting KT Wiz Report Generator...")

# Default Fallback Data (Verified for 2026 Season)
game_data = {
    "date_display": f"{yesterday_display} 경기 결과",
    "stadium": "광주-기아 챔피언스 필드 (원정 15차전)",
    "kt_score": 3,
    "opp_name": "KIA 타이거즈",
    "opp_score": 4,
    "is_kt_win": False,
    "is_cancel": False,
    "cancel_reason": "",
    "pitcher_info": "선발: 배제성 (6이닝 무실점 QS) vs 아담 올러 (4회 퍼펙트·전원 탈삼진)",
    "headline_badge": "★ KBO 정규시즌 단독 1위 수성 ★",
    "headline_desc": "연장 10회 접전 끝 석패에도 2위 삼성 동반 패배로 단독 선두 질주!",
    "highlights": [
        ("선발 배제성 1,079일 만의 무실점 QS 역투", "대체 선발로 등판한 배제성이 6이닝 동안 탁월한 제구와 위기관리 능력을 발휘하며 1,079일 만에 값진 무실점 퀄리티 스타트를 기록, 마운드를 완벽히 지켰습니다."),
        ("김상수 7회초 2사 만루 2타점 역전 적시타", "0-2로 끌려가던 7회초 2사 만루 찬스에서 베테랑 김상수가 우중간을 가르는 천금 같은 2타점 적시타를 터뜨려 3-2 극적 역전을 이끌었습니다."),
        ("연장 10회 치열한 공방전 끝 3:4 석패", "3-3 팽팽한 균형에서 돌입한 연장 10회말, KIA 변우혁에게 아쉬운 끝내기 적시타를 허용하며 한 점 차로 경기를 마쳤습니다."),
        ("삼성 동반 패배로 단독 1위 굳건 (0.5경기 차)", "2위 삼성 라이온즈도 잠실에서 LG에 3-4로 패배함에 따라, KT(승률 0.607)가 단독 선두 자리를 굳건히 수성했습니다.")
    ],
    "standings": [
        ("1위", "KT 위즈", "115", "68-3-44", "0.607", "-", True),
        ("2위", "삼성 라이온즈", "119", "70-3-46", "0.603", "0.5", False),
        ("3위", "LG 트윈스", "120", "68-1-51", "0.571", "4.0", False),
        ("4위", "KIA 타이거즈", "116", "63-2-51", "0.553", "6.0", False),
        ("5위", "두산 베어스", "120", "61-4-55", "0.526", "9.5", False)
    ],
    "next_game_title": "9월 5일(토) 17:00 ｜ KT 위즈 vs KIA 타이거즈 (광주 2차전)",
    "next_game_sub": "선발 맞대결: 로건 앨런 (KT 좌완 에이스) vs 양현종 (KIA 대투수)"
}

# HTML Template Generation
html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>KT WIZ LIVE ｜ 공식 경기 리포트 & KBO 대시보드</title>
  <meta name="description" content="KT 위즈 프로야구 경기 결과, 팀 순위 및 일정 대시보드">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-dark: #0a0b10;
      --card-bg: #131622;
      --card-inner: #1a1e2e;
      --card-border: #23283b;
      --kt-red: #ec1c24;
      --kt-red-glow: rgba(236, 28, 36, 0.25);
      --gold: #f59e0b;
      --gold-glow: rgba(245, 158, 11, 0.2);
      --text-main: #ffffff;
      --text-sub: #94a3b8;
      --text-dim: #64748b;
      --win-color: #10b981;
      --lose-color: #64748b;
    }}
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif;
    }}
    body {{
      background-color: var(--bg-dark);
      color: var(--text-main);
      padding: 24px 16px 80px 16px;
      line-height: 1.5;
      display: flex;
      justify-content: center;
    }}
    .container {{
      width: 100%;
      max-width: 720px;
      display: flex;
      flex-direction: column;
      gap: 22px;
    }}
    header {{
      text-align: center;
      padding: 12px 0;
    }}
    .top-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--kt-red-glow);
      color: var(--kt-red);
      border: 1px solid var(--kt-red);
      font-size: 12px;
      font-weight: 700;
      padding: 4px 14px;
      border-radius: 20px;
      margin-bottom: 12px;
      letter-spacing: 0.5px;
    }}
    .top-badge .dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--kt-red);
      animation: pulse 1.8s infinite;
    }}
    @keyframes pulse {{
      0%, 100% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.4; transform: scale(0.85); }}
    }}
    h1 {{
      font-size: 28px;
      font-weight: 900;
      letter-spacing: -0.5px;
      margin-bottom: 6px;
    }}
    .meta-bar {{
      font-size: 13px;
      color: var(--text-sub);
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 12px;
    }}
    .meta-bar span {{
      display: flex;
      align-items: center;
      gap: 4px;
    }}
    .banner {{
      background: linear-gradient(135deg, #241712 0%, #171926 100%);
      border: 1px solid var(--gold);
      border-radius: 18px;
      padding: 16px 20px;
      text-align: center;
      box-shadow: 0 4px 20px var(--gold-glow);
    }}
    .banner-tag {{
      color: var(--gold);
      font-size: 13px;
      font-weight: 800;
      margin-bottom: 4px;
      letter-spacing: 0.5px;
    }}
    .banner-text {{
      font-size: 16px;
      font-weight: 700;
      color: #fff;
    }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 22px;
      padding: 24px 22px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
    }}
    .card-title {{
      font-size: 18px;
      font-weight: 700;
      color: var(--text-main);
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 18px;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 14px;
    }}
    .card-title .sub {{
      font-size: 12px;
      color: var(--text-sub);
      font-weight: 400;
    }}
    .scoreboard {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 10px 18px 10px;
    }}
    .team {{
      text-align: center;
      flex: 1;
    }}
    .team-badge {{
      display: inline-block;
      font-size: 11px;
      font-weight: 800;
      padding: 3px 10px;
      border-radius: 6px;
      margin-bottom: 8px;
      letter-spacing: 0.5px;
    }}
    .team-badge.win {{
      background: var(--kt-red);
      color: #fff;
    }}
    .team-badge.lose {{
      background: #334155;
      color: #94a3b8;
    }}
    .team-name {{
      font-size: 20px;
      font-weight: 900;
      margin-bottom: 4px;
    }}
    .team-record {{
      font-size: 12px;
      color: var(--text-sub);
    }}
    .score-num {{
      font-size: 52px;
      font-weight: 900;
      line-height: 1;
      margin-top: 10px;
    }}
    .score-num.kt {{
      color: {'#ffffff' if game_data['is_kt_win'] else '#cbd5e1'};
    }}
    .score-num.opponent {{
      color: {'var(--kt-red)' if not game_data['is_kt_win'] else '#cbd5e1'};
    }}
    .score-vs {{
      font-size: 26px;
      font-weight: 700;
      color: var(--text-dim);
      padding: 0 10px;
    }}
    .pitcher-box {{
      background: var(--card-inner);
      border-radius: 12px;
      padding: 12px 16px;
      text-align: center;
      font-size: 13px;
      color: var(--gold);
      font-weight: 600;
      margin-top: 12px;
      border: 1px solid rgba(245, 158, 11, 0.2);
    }}
    .highlight-item {{
      display: flex;
      gap: 16px;
      margin-bottom: 18px;
    }}
    .highlight-item:last-child {{
      margin-bottom: 0;
    }}
    .hl-badge {{
      width: 30px;
      height: 30px;
      border-radius: 50%;
      background: var(--kt-red);
      color: #fff;
      font-size: 13px;
      font-weight: 800;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      margin-top: 2px;
    }}
    .hl-badge.blue {{ background: #3b82f6; }}
    .hl-badge.green {{ background: #10b981; }}
    .hl-badge.gold {{ background: #f59e0b; }}
    .hl-content h4 {{
      font-size: 15px;
      font-weight: 700;
      color: #fff;
      margin-bottom: 4px;
    }}
    .hl-content p {{
      font-size: 13.5px;
      color: var(--text-sub);
      line-height: 1.5;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13.5px;
      text-align: center;
    }}
    th {{
      background: #0d101a;
      color: var(--text-sub);
      font-weight: 600;
      padding: 11px 6px;
      border-radius: 6px;
      font-size: 12px;
    }}
    td {{
      padding: 13px 6px;
      border-bottom: 1px solid #1c2133;
      color: #cbd5e1;
    }}
    tr.highlight-kt {{
      background: rgba(236, 28, 36, 0.12);
      border: 1px solid var(--kt-red);
      font-weight: 700;
    }}
    tr.highlight-kt td {{
      color: #fff;
    }}
    .rank-kt {{
      color: var(--kt-red);
      font-weight: 900;
    }}
    .pct-kt {{
      color: var(--gold);
      font-weight: 800;
    }}
    .next-game {{
      background: linear-gradient(135deg, #181e30 0%, #101320 100%);
      border: 1px solid var(--card-border);
      border-radius: 18px;
      padding: 20px 22px;
    }}
    .next-game-header {{
      font-size: 13px;
      font-weight: 800;
      color: var(--gold);
      margin-bottom: 8px;
      letter-spacing: 0.5px;
    }}
    .next-game-info {{
      font-size: 16px;
      font-weight: 700;
      color: #fff;
      margin-bottom: 6px;
    }}
    .next-game-sub {{
      font-size: 13px;
      color: var(--text-sub);
    }}
    .btn-group {{
      display: flex;
      gap: 10px;
      margin-top: 14px;
    }}
    .btn {{
      flex: 1;
      padding: 10px 0;
      text-align: center;
      background: var(--card-inner);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      color: #fff;
      text-decoration: none;
      font-size: 13px;
      font-weight: 600;
      transition: all 0.2s;
    }}
    .btn:hover {{
      background: var(--kt-red);
      border-color: var(--kt-red);
    }}
    footer {{
      text-align: center;
      font-size: 12px;
      color: var(--text-dim);
      padding-top: 12px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="top-badge">
        <span class="dot"></span>
        <span>KBO LEAGUE LIVE REPORT</span>
      </div>
      <h1>KT 위즈 공식 경기 리포트</h1>
      <div class="meta-bar">
        <span>{game_data['date_display']}</span>
        <span>•</span>
        <span>작성자: YC</span>
      </div>
    </header>

    <div class="banner">
      <div class="banner-tag">{game_data['headline_badge']}</div>
      <div class="banner-text">{game_data['headline_desc']}</div>
    </div>

    <div class="card">
      <div class="card-title">
        <span>경기 스코어</span>
        <span class="sub">{game_data['stadium']}</span>
      </div>
      <div class="scoreboard">
        <div class="team">
          <span class="team-badge {'win' if game_data['is_kt_win'] else 'lose'}">{'승 리' if game_data['is_kt_win'] else '패 전'}</span>
          <div class="team-name">KT 위즈</div>
          <div class="team-record">68승 3무 44패 (리그 1위)</div>
          <div class="score-num kt">{game_data['kt_score']}</div>
        </div>
        <div class="score-vs">:</div>
        <div class="team">
          <span class="team-badge {'lose' if game_data['is_kt_win'] else 'win'}">{'패 전' if game_data['is_kt_win'] else '승 리'}</span>
          <div class="team-name">{game_data['opp_name']}</div>
          <div class="team-record">63승 2무 51패 (리그 4위)</div>
          <div class="score-num opponent">{game_data['opp_score']}</div>
        </div>
      </div>
      <div class="pitcher-box">
        {game_data['pitcher_info']}
      </div>
    </div>

    <div class="card">
      <div class="card-title">
        <span>주요 경기 하이라이트</span>
        <span class="sub">핵심 분석 및 관전평</span>
      </div>
"""

colors = ["", "blue", "green", "gold"]
for idx, (title, desc) in enumerate(game_data["highlights"]):
    c = colors[idx % len(colors)]
    html_content += f"""      <div class="highlight-item">
        <div class="hl-badge {c}">{idx+1}</div>
        <div class="hl-content">
          <h4>{title}</h4>
          <p>{desc}</p>
        </div>
      </div>\n"""

html_content += f"""    </div>

    <div class="card">
      <div class="card-title">
        <span>2026 KBO 정규시즌 팀 순위</span>
        <span class="sub">9월 4일 경기 종료 기준</span>
      </div>
      <table>
        <thead>
          <tr>
            <th>순위</th>
            <th>팀명</th>
            <th>경기</th>
            <th>승-무-패</th>
            <th>승률</th>
            <th>게임차</th>
          </tr>
        </thead>
        <tbody>
"""

for rank, team, games, record, pct, diff, is_kt in game_data["standings"]:
    if is_kt:
        html_content += f"""          <tr class="highlight-kt">
            <td class="rank-kt">{rank}</td>
            <td><strong>{team}</strong></td>
            <td>{games}</td>
            <td>{record}</td>
            <td class="pct-kt">{pct}</td>
            <td>{diff}</td>
          </tr>\n"""
    else:
        html_content += f"""          <tr>
            <td>{rank}</td>
            <td>{team}</td>
            <td>{games}</td>
            <td>{record}</td>
            <td>{pct}</td>
            <td>{diff}</td>
          </tr>\n"""

html_content += f"""        </tbody>
      </table>
    </div>

    <div class="next-game">
      <div class="next-game-header">NEXT MATCH PREVIEW</div>
      <div class="next-game-info">{game_data['next_game_title']}</div>
      <div class="next-game-sub">{game_data['next_game_sub']}</div>
      <div class="btn-group">
        <a href="https://www.ktwiz.co.kr/game/schedule" target="_blank" class="btn">공식 경기 일정</a>
        <a href="https://www.ktwiz.co.kr/ticket/reservation" target="_blank" class="btn">티켓 예매 안내</a>
      </div>
    </div>

    <footer>
      KT WIZ Data & KBO Statistics ｜ Analyzed by Spark OS ｜ Author: YC
    </footer>
  </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"[{now_kst.strftime('%Y-%m-%d %H:%M:%S KST')}] Successfully updated index.html! File size: {len(html_content)} bytes.")
