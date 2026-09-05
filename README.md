# KT Wiz Live Report & KBO Dashboard (kasoft27)

KT 위즈 프로야구 공식 경기 리포트 및 KBO 순위 웹 대시보드입니다.

## 🌐 나의 전용 웹사이트 주소
👉 **[https://kasoft27.github.io/kt-wiz-report/](https://kasoft27.github.io/kt-wiz-report/)**

---

## ⚙️ 100% 완전 무인 자동화 동작 원리
1. **매일 새벽 3:00 (KST):** GitHub Actions 서버가 자동으로 실행됩니다.
2. **최신 경기 수집 및 갱신:** `update_report.py`가 KBO/KT 위즈의 경기 결과, 스코어, 순위표를 수집하여 `index.html`을 최신 상태로 새로 생성합니다.
3. **자동 커밋 & 배포:** 최신 내용이 자동으로 저장소에 커밋되고 GitHub Pages로 즉시 배포됩니다.
4. **결과:** 사용자가 아무런 작업을 하지 않아도 매일 아침 웹사이트가 최신 정보로 유지됩니다!

---

## 🚀 최초 1회 세팅 방법 (단 2단계)
1. GitHub 저장소(`kt-wiz-report`)에 이 압축 파일 안의 파일들을 업로드합니다:
   - `index.html`
   - `update_report.py`
   - `.github/workflows/deploy.yml`
2. 저장소의 **Settings** ➡ **Pages** 메뉴에서:
   - **Source**를 **`GitHub Actions`**로 선택하고 저장합니다.
3. (선택 사항) 저장소의 **Settings** ➡ 좌측 **Actions** ➡ **General** 메뉴 맨 아래의 **Workflow permissions**가 `Read and write permissions`로 체크되어 있는지 확인합니다. (Actions가 파일 커밋을 할 수 있게 허용)
