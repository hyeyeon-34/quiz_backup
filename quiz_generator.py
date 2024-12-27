from flask import Flask, jsonify, request
import openai
import sqlite3
from datetime import datetime
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer, util
from dotenv import load_dotenv
import os
load_dotenv()
# OpenAI API 키 설정
openai_api_key = os.getenv("OPENAI_API_KEY")  # 여기에 OpenAI API 키를 입력하세요.

# MongoDB 설정
mongo_client = MongoClient('mongodb://222.112.27.120:27017')
db = mongo_client['recycle']
quiz_collection = db['quiz']

# 유사도 분석 모델 초기화
model = SentenceTransformer('all-MiniLM-L6-v2')

# Flask 앱 설정
app = Flask(__name__)

# SQLite 데이터베이스 초기화
def init_sqlite():
    conn = sqlite3.connect('user_progress.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_progress (
        user_id TEXT,
        date TEXT,
        last_question INTEGER,
        PRIMARY KEY (user_id, date)
    )
    ''')
    conn.commit()
    return conn

sqlite_conn = init_sqlite()
sqlite_cursor = sqlite_conn.cursor()

# 오늘 날짜
today_date = datetime.now().strftime("%Y-%m-%d")

# 퀴즈 생성 함수 (유사도 검사 포함)
def generate_quiz():
    existing_questions = [quiz['question'] for quiz in quiz_collection.find()]
    threshold = 0.8

    while True:
        prompt = "환경, 분리수거, 기후변화, 신재생에너지, 야생동물 보호, 오염, 지속가능한 삶 및 자연 자원에 관한 OX 퀴즈를 하나 생성해 주세요. 예시 형식: '질문: 플라스틱은 500년 이상 분해되지 않는다. / 정답: [O 또는 X]'"
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
        except ValueError:
            continue

        # 유사도 검사
        if existing_questions:
            new_question_embedding = model.encode(question, convert_to_tensor=True)
            existing_embeddings = model.encode(existing_questions, convert_to_tensor=True)
            similarities = util.cos_sim(new_question_embedding, existing_embeddings)

            if max(similarities[0]).item() < threshold:
                return question, answer
        else:
            return question, answer

# 매일 10문제 생성 API
@app.route('/generate_quiz', methods=['POST'])
def create_daily_quizzes():
    if quiz_collection.count_documents({"date": today_date}) == 0:
        for _ in range(10):
            question, answer = generate_quiz()
            quiz_collection.insert_one({"date": today_date, "question": question, "answer": answer})
        return jsonify({"message": "오늘의 퀴즈 10문제가 생성되었습니다."})
    return jsonify({"message": "오늘의 퀴즈는 이미 생성되었습니다."})

# 사용자 퀴즈 제공 API
@app.route('/get_quiz', methods=['POST'])
def get_daily_quizzes():
    user_id = request.json.get('user_id')

    # 오늘 퀴즈 가져오기
    quizzes = list(quiz_collection.find({"date": today_date}))
    if not quizzes:
        return jsonify({"message": "오늘의 퀴즈가 아직 생성되지 않았습니다."})

    # 사용자 진행 상태 확인
    sqlite_cursor.execute("SELECT last_question FROM user_progress WHERE user_id = ? AND date = ?", (user_id, today_date))
    row = sqlite_cursor.fetchone()
    last_question = row[0] if row else 0

    if last_question >= 10:
        return jsonify({"message": "오늘의 퀴즈를 모두 완료하였습니다."})

    # 다음 문제 제공
    next_quiz = quizzes[last_question]
    return jsonify({
        "question_number": last_question + 1,
        "question": next_quiz['question'],
        "answer": next_quiz['answer']
    })

# 사용자 진행 상태 업데이트 API
@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    user_id = request.json.get('user_id')
    user_answer = request.json.get('answer').strip().upper()

    # 오늘 퀴즈 가져오기
    quizzes = list(quiz_collection.find({"date": today_date}))
    sqlite_cursor.execute("SELECT last_question FROM user_progress WHERE user_id = ? AND date = ?", (user_id, today_date))
    row = sqlite_cursor.fetchone()
    last_question = row[0] if row else 0

    correct_answer = quizzes[last_question]['answer']

    # 정답 확인
    if user_answer == correct_answer:
        message = "정답입니다! 🎉"
    else:
        message = f"틀렸습니다! 정답은 {correct_answer}입니다. ❌"

    # 진행 상태 업데이트
    new_last_question = last_question + 1
    sqlite_cursor.execute(
        "INSERT OR REPLACE INTO user_progress (user_id, date, last_question) VALUES (?, ?, ?)",
        (user_id, today_date, new_last_question)
    )
    sqlite_conn.commit()

    return jsonify({"message": message})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
