#!/bin/bash

echo "🚀 한국 법률 챗봇 MVP 시작하기"
echo "================================"

# 백엔드 시작
echo "1. 백엔드 서버 시작..."
cd backend
if [ ! -d "venv" ]; then
    echo "   가상환경 생성 중..."
    python3 -m venv venv
fi

echo "   가상환경 활성화..."
source venv/bin/activate  # Windows: venv\Scripts\activate

echo "   패키지 설치 중..."
pip install -r requirements.txt

echo "   백엔드 서버 실행 (포트 8000)..."
uvicorn app:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

cd ..

# 프론트엔드 시작
echo ""
echo "2. 프론트엔드 시작..."
cd frontend
echo "   패키지 설치 중..."
npm install

echo "   프론트엔드 서버 실행 (포트 3000)..."
npm start &
FRONTEND_PID=$!

cd ..

echo ""
echo "========================================"
echo "✅ 서버가 시작되었습니다!"
echo ""
echo "백엔드: http://localhost:8000"
echo "프론트엔드: http://localhost:3000"
echo ""
echo "종료하려면 Ctrl+C를 누르세요"
echo "========================================"

# 종료 시그널 대기
trap "echo '서버 종료 중...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

# 실행 유지
wait
