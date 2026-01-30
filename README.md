# Korean Legal Chatbot MVP

Legal support chatbot for foreigners and foreign companies in Korea (MVP Version).  
**Focused on English laws (영문법령)** via [National Law Information](https://www.law.go.kr) (국가법령정보 공유서비스).

## 🚀 Quick Start

### Method 1: Using Auto-Run Script
```bash
# Grant execution permission
chmod +x run.sh

# Run
./run.sh
```

### Method 2: Manual Execution
```bash
# 1. Start Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy .env.example to .env and configure API keys
cp .env.example .env

uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# 2. Start Frontend (in a new terminal)
cd frontend
npm install
npm start
```

## 📖 English Laws (영문법령) — National Law Information

This chatbot is **centered on English laws** using the National Law Information service.

- **Base URL**: https://www.law.go.kr  
- **Usage**: Enter a **Korean path (한글 주소)** after the base URL.  
- **English laws**: `/영문법령/법령명`  
  - Example: https://www.law.go.kr/영문법령/출입국관리법  
  - More precise: `/영문법령/법령명/(공포번호,공포일자)`  

Categories on the service: 법령, 행정규칙, 자치법규, 조약, 별표서식, 판례, 결정례, 해석례, 심판례. This MVP uses **영문법령** (English translations of Korean laws).

### API Endpoints for English Laws

| Method | Path | Description |
|--------|------|-------------|
| GET | `/english-laws` | List English laws by topic (visa, company, tax, contract, labor) |
| GET | `/english-laws?topic=visa` | English laws for a single topic |
| GET | `/english-laws/url?law_name=출입국관리법` | Build official URL for an English law |

## 🔑 API Configuration (Optional)

For additional law search (법령체계도 등), register at https://open.law.go.kr and set `LAW_GO_KR_OC` in `.env`.  
**English law links work without an API key** — they use the public URL structure above.

### Environment Variables
```bash
# backend/.env
LAW_GO_KR_OC=your_email_id_here   # optional
LAW_GO_KR_BASE=https://www.law.go.kr
```

## 📁 Project Structure

```
legal-chatbot-mvp/
├── backend/
│   ├── app.py              # FastAPI Backend
│   ├── requirements.txt    # Python Dependencies
│   ├── .env.example        # Environment Variables Template
│   └── .env                # Your API Keys (git-ignored)
├── frontend/
│   ├── package.json        # Node.js Dependencies
│   ├── public/
│   └── src/
│       ├── App.js          # React Main Component
│       ├── App.css         # Styles
│       ├── index.js        # Entry Point
│       └── index.css       # Base Styles
├── .gitignore              # Git Ignore Rules
├── render.yaml             # Render Blueprint (backend + frontend)
├── run.sh                  # Run Script
└── README.md
```

## 🔧 Tech Stack

### Backend
- **FastAPI**: Python Web Framework
- **Pydantic**: Data Validation
- **Uvicorn**: ASGI Server
- **urllib**: HTTP (no extra deps)
- **python-dotenv**: Environment Variables

### Frontend
- **React 18**: UI Library
- **Axios**: HTTP Client
- **CSS3**: Styling

## 📌 Key Features

1. **Multi-Country Support**: USA, UAE, UK, General
2. **Legal Topics**: Visa, Company Establishment, Tax, Contracts, Labor Law
3. **Confidence Display**: Response accuracy indicator
4. **Expert Connection**: Expert recommendations for high-risk questions
5. **Quick Questions**: Frequently asked questions buttons
6. **English laws (영문법령)**: Links to official English translations at https://www.law.go.kr (한글 주소: /영문법령/법령명)

## 🌐 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | API Info |
| POST | `/chat` | Chatbot Conversation |
| GET | `/health` | Health Check |
| GET | `/countries` | Supported Countries List |
| POST | `/laws/search` | Search Korean Laws |
| GET | `/laws/{law_id}` | Get Law Details |

### Law Search Request Example
```json
{
  "keyword": "출입국관리법",
  "search_type": "law",
  "page": 1,
  "count": 10
}
```
- `search_type`: law (법령), prec (판례), detc (행정심판), expc (법령해석)

## 📌 Git 설정 (Render 배포 전)

Render는 **GitHub** 또는 **GitLab** 저장소를 연결해야 배포할 수 있습니다. 먼저 Git 저장소를 만들고 원격에 올려 두세요.

**Frontend/Backend 중 어디서 해야 하나요?**  
→ **프로젝트 루트**에서만 하면 됩니다. (`legal-chatbot-mvp` 폴더, 즉 `frontend`와 `backend`가 함께 있는 폴더.)  
한 저장소에 프론트엔드·백엔드가 모두 포함되고, Render가 그 저장소를 연결한 뒤 `render.yaml`에 따라 백엔드 서비스와 프론트엔드 서비스를 **각각** 만듭니다. Frontend 폴더나 Backend 폴더 안에서 따로 Git을 켤 필요는 없습니다.

```bash
# 프로젝트 루트(legal-chatbot-mvp)에서 실행
cd legal-chatbot-mvp

# 1. Git 초기화 (이미 되어 있으면 생략)
git init

# 2. 파일 추가 및 첫 커밋
git add .
git commit -m "Initial commit: legal chatbot MVP"

# 3. GitHub/GitLab에서 새 저장소 생성 후 원격 추가
git remote add origin https://github.com/YOUR_USERNAME/legal-chatbot-mvp.git

# 4. 기본 브랜치를 main으로 하고 푸시
git branch -M main
git push -u origin main
```

- GitHub: [github.com/new](https://github.com/new) 에서 저장소 생성 후 위 `origin` URL을 본인 저장소 주소로 바꿉니다.
- GitLab: [gitlab.com](https://gitlab.com) 에서 새 프로젝트 생성 후 `git remote add origin <프로젝트 URL>` 로 연결합니다.

원격 저장소에 코드가 올라간 뒤 **Render**에서 해당 저장소를 연결하면 됩니다.

## 🚀 Deploy with Render (Frontend + Backend)

프론트엔드와 백엔드를 **Render**에서 한 번에 배포할 수 있습니다. 저장소 루트의 `render.yaml`(Blueprint)으로 백엔드 API와 프론트엔드 정적 사이트를 정의해 두었습니다.

### 1. Blueprint로 한 번에 배포

1. [render.com](https://render.com) 로그인 후 **New** → **Blueprint**.
2. 이 저장소를 연결하고 **Apply**.
3. 생성되는 서비스:
   - **legal-chatbot-api**: 백엔드 (FastAPI, `backend/`) — **Runtime: Python 3** (Web Service)
   - **legal-chatbot-frontend**: 프론트엔드 (React 정적 사이트, `frontend/`) — **Runtime: Static** (Static Site, 빌드 시 Node 사용)
4. 환경 변수 입력:
   - **legal-chatbot-api**: `LAW_GO_KR_OC` (선택, 국가법령정보 API 사용 시 [open.law.go.kr](https://open.law.go.kr)에서 발급).
   - **legal-chatbot-frontend**: `REACT_APP_API_URL` — 백엔드 배포 후 나온 URL 입력 (예: `https://legal-chatbot-api.onrender.com`). 끝에 `/` 없이 입력.
5. 백엔드가 먼저 배포되면 해당 URL을 복사해, 프론트엔드 서비스 **Environment**에 `REACT_APP_API_URL`로 넣고 **Save Changes** 후 재배포합니다.

### 2. 수동으로 서비스 추가 (Blueprint 없이)

**백엔드**

1. **New** → **Web Service** → 저장소 연결.
2. **Root Directory**: `backend`
3. **Build Command**: `pip install -r requirements.txt`
4. **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
5. **Environment**: `LAW_GO_KR_OC` (선택) 추가.
6. **Create Web Service** 후 URL 복사.

**프론트엔드**

1. **New** → **Static Site** → 같은 저장소 연결.
2. **Root Directory**: `frontend`
3. **Build Command**: `npm install && npm run build`
4. **Publish Directory**: `build`
5. **Environment**: `REACT_APP_API_URL` = 위에서 복사한 백엔드 URL (끝에 `/` 없이).
6. **Create Static Site**.

### 요약

| 서비스 | Root Directory | Runtime (Language) | 결과 URL 예시 |
|--------|----------------|-------------------|----------------|
| 백엔드 (Web Service) | `backend` | **Python 3** | `https://legal-chatbot-api.onrender.com` |
| 프론트엔드 (Static Site) | `frontend` | **Static** (빌드만 Node) | `https://legal-chatbot-frontend.onrender.com` |

**Blueprint 배포 시 Language(Runtime) 선택:**  
- **백엔드(legal-chatbot-api)**: **Python 3** — Web Service이고 `render.yaml`에 `runtime: python`으로 되어 있음. Docker 아님.  
- **프론트엔드(legal-chatbot-frontend)**: **Static** — Static Site이고 `runtime: static`. 빌드 시에만 Node(npm)가 사용되고, 서비스 자체는 정적 파일 호스팅.

- 프론트엔드의 **Environment**에 `REACT_APP_API_URL`을 백엔드 URL로 설정해야 챗봇이 API를 호출합니다.
- 백엔드는 CORS로 모든 오리진을 허용하므로, Render 프론트엔드 도메인에서 바로 호출 가능합니다.

**Render 프론트엔드에서 "Could not reach the API"가 나올 때**

1. **백엔드 URL 확인**: Render 대시보드에서 **legal-chatbot-api** 서비스 → 상단 URL 복사 (예: `https://legal-chatbot-api.onrender.com`, 끝에 `/` 없이).
2. **프론트엔드 환경 변수 설정**: **legal-chatbot-frontend** 서비스 → **Environment** → **Add Environment Variable**  
   - Key: `REACT_APP_API_URL`  
   - Value: 위에서 복사한 백엔드 URL
3. **재배포**: 환경 변수는 **빌드 시** 적용되므로, 저장 후 **Manual Deploy** → **Deploy latest commit** 으로 프론트엔드를 다시 빌드·배포해야 합니다.

## ⚠️ Disclaimer

This chatbot is for **informational purposes only**. It does not replace legal advice. 
Please consult with a qualified attorney before making any important decisions.

## 📞 Contact

- Email: virtual.esq@gmail.com
- Version: 1.0.0
