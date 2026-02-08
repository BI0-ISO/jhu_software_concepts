import psycopg

connection = psycopg.connect(
    dbname="studentcourses",
    user="mckeysa1",
    host="localhost",
    port=5432
)

with connection.cursor() as cur:
    cur.execute("SELECT * FROM students;")
    rows = cur.fetchall()
    print(rows)

connection.close()
