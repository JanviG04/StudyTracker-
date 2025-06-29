from db_config import get_connection
from datetime import date

def register_user(username, password):
    con = get_connection()
    cur = con.cursor()
    try:
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        con.commit()
        return True
    except:
        return False
    finally:
        cur.close()
        con.close()

def login_user(username, password):
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT id FROM users WHERE username=%s AND password=%s", (username, password))
    user = cur.fetchone()
    cur.close()
    con.close()
    return user[0] if user else None

def log_study_session(user_id, subject, hours, mood):
    con = get_connection()
    cur = con.cursor()
    cur.execute("INSERT INTO study_sessions (user_id, subject, hours, mood, session_date) VALUES (%s, %s, %s, %s, %s)",
                (user_id, subject, hours, mood, date.today()))
    con.commit()
    cur.close()
    con.close()