import psycopg2
import time

print("Waiting for postgres...")
time.sleep(5)  # ADD THIS - give postgres time to fully start

for i in range(10):
    try:
        conn = psycopg2.connect(
            host='127.0.0.1',
            port=5432,
            dbname='rapidremedy',
            user='admin',
            password='admin123',
            sslmode='disable',
            connect_timeout=10
        )
        print("Connected!")
        break
    except Exception as e:
        print(f"Attempt {i+1}/10 failed: {e}")
        time.sleep(3)
else:
    raise Exception("Could not connect after 10 attempts")