import mysql.connector

def get_db():
    return mysql.connector.connect(
        host="mysql.railway.internal",
        port=3306,
        user="root",
        password="dzVNsdxaLHxLfZRQHbKBKifHaujuebIF",
        database="railway"
    )