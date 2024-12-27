const express = require('express');
const router = express.Router();
const bodyParser = require('body-parser');
const MongoClient = require('mongodb').MongoClient;
const sqlite3 = require('sqlite3').verbose();
const util = require('util');

// MongoDB 연결 설정
const mongoUri = 'mongodb://recycle:recycleuser@222.112.27.120:27017/?authSource=admin';

const mongoDbName = 'recycle';
let mongoClient;

// SQLite 설정
const sqliteDb = new sqlite3.Database('./quizProgress.db');

// SQLite 쿼리를 Promise로 사용 가능하도록 설정
sqliteDb.run = util.promisify(sqliteDb.run);
sqliteDb.all = util.promisify(sqliteDb.all);
sqliteDb.get = util.promisify(sqliteDb.get);

// MongoDB 연결
async function connectMongo() {
  try {
    mongoClient = new MongoClient(mongoUri, { useUnifiedTopology: true });
    await mongoClient.connect();
    console.log('MongoDB 연결 성공');
  } catch (error) {
    console.error('MongoDB 연결 실패:', error.message);
    process.exit(1);
  }
}

// SQLite 테이블 생성
async function setupSQLite() {
  const createTableQuery = `
    CREATE TABLE IF NOT EXISTS quiz_progress (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id TEXT NOT NULL,
      quiz_id INTEGER NOT NULL,
      is_correct INTEGER NOT NULL,
      date TEXT NOT NULL
    );
  `;
  await sqliteDb.run(createTableQuery);
  console.log('SQLite 테이블 생성 성공');
}

// 사용자 퀴즈 진행 상황 가져오기
async function getUserProgress(userId, date) {
  const query = `SELECT quiz_id FROM quiz_progress WHERE user_id = ? AND date = ?`;
  console.log("진행상황 가져오기");
  const progress = await sqliteDb.all(query, [userId, date]);
  return progress;
}

// 사용자 퀴즈 진행 상황 저장
async function saveUserProgress(userId, quizId, isCorrect, date) {
  console.log(`saveUserProgress 호출됨: userId=${userId}, quizId=${quizId}, isCorrect=${isCorrect}, date=${date}`);
  const insertQuery = `
    INSERT INTO quiz_progress (user_id, quiz_id, is_correct, date)
    VALUES (?, ?, ?, ?)
  `;
  try {
    await sqliteDb.run('BEGIN TRANSACTION');
    await sqliteDb.run(insertQuery, [userId, quizId, isCorrect, date]);
    await sqliteDb.run('COMMIT');
    console.log(`SQLite 저장 성공: userId=${userId}, quizId=${quizId}, isCorrect=${isCorrect}, date=${date}`);
  } catch (error) {
    console.error('SQLite 저장 실패:', error.message || error);
    await sqliteDb.run('ROLLBACK'); // 예외 발생 시 롤백
  }
}

// 오늘의 퀴즈 가져오기 API
router.get('/daily_quiz', async (req, res) => {
  try {
    const today = new Date().toISOString().split('T')[0]; // 오늘 날짜
    const db = mongoClient.db(mongoDbName);

    // MongoDB에서 해당 날짜의 모든 퀴즈 가져오기
    const quizDoc = await db.collection('quiz').findOne({ date: today });

    if (!quizDoc) {
      return res.status(404).json({ message: '오늘의 퀴즈가 없습니다.' });
    }

    // 모든 퀴즈 데이터를 반환
    res.json({ quizzes: quizDoc.quizzes });
  } catch (error) {
    console.error('getDailyQuiz 오류:', error);
    res.status(500).json({ message: '서버 오류', error: error.message });
  }
});

// 리뷰 퀴즈 API
router.get('/review_quiz/:userId', async (req, res) => {
  try {
    const userId = req.params.userId;
    console.log(`리뷰 API 요청 - userId: ${userId}`);
    const today = new Date().toISOString().split('T')[0];

    // MongoDB에서 오늘의 퀴즈 가져오기
    const db = mongoClient.db(mongoDbName);
    const quizDoc = await db.collection('quiz').findOne({ date: today });

    if (!quizDoc) {
      return res.status(404).json({ message: '오늘의 퀴즈가 없습니다.' });
    }

    // SQLite에서 진행 상황 가져오기
    const progress = await getUserProgress(userId, today);

    if (progress.length === 0) {
      return res.json({ message: '진행한 퀴즈가 없습니다.', reviewData: [] });
    }

    const reviewData = progress.map((p) => {
      const quiz = quizDoc.quizzes.find((q) => q.id === p.quiz_id) || {};
      console.log(`퀴즈 매칭 확인 - quiz_id: ${p.quiz_id}, 매칭된 퀴즈:`, quiz);

      return {
        question: quiz.question || '알 수 없음',
        correctAnswer: quiz.answer || '알 수 없음',
        isCorrect: p.is_correct === 1 ? '맞춤' : '틀림',
        date: p.date,
      };
    });

    console.log("최종 리뷰 데이터:", reviewData);

    res.json({ reviewData });
  } catch (error) {
    console.error('getReviewQuiz 오류:', error);
    res.status(500).json({ message: '서버 오류', error: error.message });
  }
});

// 사용자 퀴즈 제출 API
router.post('/submit_quiz', async (req, res) => {
  try {
    const { userId, quizId, isCorrect } = req.body;
    const today = new Date().toISOString().split('T')[0];

    await saveUserProgress(userId, quizId, isCorrect, today);

    res.json({ message: '퀴즈 진행 상황이 저장되었습니다.' });
  } catch (error) {
    console.error('submitQuizAnswer 오류:', error);
    res.status(500).json({ message: '서버 오류', error: error.message });
  }
});

// 초기화 함수
async function initialize() {
  await connectMongo();
  await setupSQLite();
}

initialize();

module.exports = {
  router,
  initialize,
};
