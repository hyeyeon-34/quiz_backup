from flask import Flask, jsonify
import openai
from pymongo import MongoClient
from datetime import datetime
from flask_cors import CORS
import random
import os
from dotenv import load_dotenv
load_dotenv()
# OpenAI API 키 설정
openai_api_key = os.getenv("OPENAI_API_KEY")  # 여기에 OpenAI API 키를 입력하세요.

# MongoDB 설정
mongo_client = MongoClient('mongodb://recycle:recycleuser@222.112.27.120:27017/?authSource=admin')
db = mongo_client['recycle']
quiz_collection = db['quiz']

# Flask 앱 설정
app = Flask(__name__)
CORS(app)

# 오늘 날짜
today_date = datetime.now().strftime("%Y-%m-%d")

# 주제 목록
topics = [
    "환경 보호", "분리수거", "기후변화", "신재생에너지", "야생동물 보호", "오염",
    "지속 가능한 삶", "자연 자원", "파리 기후 협약", "탄소세", "환경 보호법",
    "국제 환경 협약", "지속 가능한 개발 목표 (SDGs)", "환경 규제", "탄소 발자국 줄이기",
    "친환경 제품", "친환경 건축", "대중교통 이용", "도시 열섬 현상", "해양 쓰레기 문제",
    "에너지 절약", "탄소 중립", "지구 온난화", "대기 오염", "업사이클링", "제로 웨이스트",
    "음식물 쓰레기 관리", "물 부족 문제"
]

# 퀴즈 생성 함수
def generate_quiz():
    # MongoDB에서 기존 퀴즈 가져오기
    existing_quizzes = quiz_collection.find_one({"date": today_date})

    # 주제 랜덤 선택
    selected_topic = random.choice(topics)
    existing_questions = []

    if existing_quizzes and "quizzes" in existing_quizzes:
        existing_questions = [quiz['question'] for quiz in existing_quizzes["quizzes"]]


    # 기존 퀴즈를 프롬프트에 포함
    existing_questions_text = "\n".join(f"- {q}" for q in existing_questions)
    prompt = f"""
    다음은 이미 생성된 환경 관련 OX 퀴즈 목록입니다:
    {existing_questions_text}

    위의 퀴즈와 중복되지 않는 {selected_topic}에 관한 OX 퀴즈 1개를 생성해 주세요.
    예시 형식: '질문: 태양광은 신재생에너지에 속한다. / 정답: [O 또는 X]'
    """

    # OpenAI API 호출
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100
    )

    quiz_text = response['choices'][0]['message']['content'].strip()
    try:
        question, answer = quiz_text.split('/ 정답: ')
        question = question.strip()
        answer = answer.strip().upper()
        return question, answer
    except ValueError:
        return None, None

# 매일 10문제 생성 및 MongoDB에 저장 API
@app.route('/generate_quiz', methods=['GET', 'POST'])
def create_daily_quizzes():
    print(today_date)

    # 오늘 날짜의 퀴즈가 이미 생성되었는지 확인
    if quiz_collection.find_one({"date": today_date}):
        return jsonify({"message": "오늘의 퀴즈는 이미 생성되었습니다."})

    # 새로운 퀴즈 생성
    quizzes = []
    for i in range(1, 11):  # 10개의 퀴즈 생성
        question, answer = generate_quiz()
        if question and answer:
            quiz = {"id": i, "question": question, "answer": answer}
            quizzes.append(quiz)

    # MongoDB에 저장 (한 문서에 날짜와 퀴즈 리스트로 저장)
    if quizzes:
        quiz_collection.insert_one({
            "date": today_date,
            "quizzes": quizzes
        })
        return jsonify({"message": "오늘의 퀴즈 10문제가 생성되었습니다."})
    else:
        return jsonify({"message": "퀴즈 생성에 실패했습니다. 다시 시도해 주세요."})

# 크론탭에서 실행하기 위한 함수
def generate_quizzes_cron():
    print(today_date)

    # 오늘 날짜의 퀴즈가 이미 생성되었는지 확인
    if quiz_collection.find_one({"date": today_date}):
        print("오늘의 퀴즈는 이미 생성되었습니다.")
        return

    # 새로운 퀴즈 생성
    quizzes = []
    for i in range(1, 11):
        question, answer = generate_quiz()
        if question and answer:
            quiz = {"id": i, "question": question, "answer": answer}
            quizzes.append(quiz)

    # MongoDB에 저장 (한 문서에 날짜와 퀴즈 리스트로 저장)
    if quizzes:
        quiz_collection.insert_one({
            "date": today_date,
            "quizzes": quizzes
        })
        print("오늘의 퀴즈 10문제가 생성되었습니다.")
    else:
        print("퀴즈 생성에 실패했습니다. 다시 시도해 주세요.")


# Flask 앱 실행
if __name__ == "__main__":
    import sys

    # 크론탭에서 호출할 때 create_daily_quizzes 실행
    if len(sys.argv) > 1 and sys.argv[1] == "create_daily_quizzes":
        generate_quizzes_cron()
    else:
        app.run(debug=True)

