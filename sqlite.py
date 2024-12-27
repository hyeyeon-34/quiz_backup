import sqlite3

# 데이터베이스 연결 (파일이 없으면 새로 생성됨)
conn = sqlite3.connect('test.db')
cursor = conn.cursor()

# 테이블 생성
def create_table():
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        age INTEGER NOT NULL
    )
    ''')
    conn.commit()

# 데이터 삽입
def insert_data(name, age):
    cursor.execute('''
    INSERT INTO users (name, age) VALUES (?, ?)
    ''', (name, age))
    conn.commit()

# 데이터 조회
def fetch_data():
    cursor.execute('SELECT * FROM users')
    rows = cursor.fetchall()
    for row in rows:
        print(row)

# # 데이터 삭제
# def delete_data(user_id):
#     cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
#     conn.commit()

# 메인 함수
def main():
    create_table()           # 테이블 생성
    insert_data("Alice", 25) # 데이터 삽입
    insert_data("Bob", 30)   # 데이터 삽입
    insert_data("Charlie", 35) # 데이터 삽입

    print("\n--- 모든 데이터 조회 ---")
    fetch_data()             # 데이터 조회

    print("\n--- ID가 2인 데이터 삭제 ---")
    # delete_data(2)           # ID가 2인 데이터 삭제

    print("\n--- 데이터 삭제 후 조회 ---")
    # fetch_data()             # 삭제 후 데이터 조회

    # 연결 종료
    # conn.close()

# 코드 실행
if __name__ == "__main__":
    main()
