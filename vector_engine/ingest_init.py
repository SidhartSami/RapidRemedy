import pandas as pd
from sentence_transformers import SentenceTransformer
import numpy as np
import psycopg2
from pgvector.psycopg2 import register_vector

# Load data
df = pd.read_csv('data/working_dataset.csv')
texts = df['abstract_text'].tolist()
print(f"Total rows: {len(texts)}")

# Generate embeddings - this will take 10-20 mins, go do something else
model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(texts, show_progress_bar=True, batch_size=64)

# Save to disk - IMPORTANT, never regenerate
np.save('embeddings/embeddings.npy', embeddings)
df.to_csv('embeddings/metadata.csv', index=False)
print(f"Embeddings saved. Shape: {embeddings.shape}")
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    dbname='rapidremedy',
    user='admin',
    password='admin123'
)

# Enable extension FIRST before registering
cur = conn.cursor()
cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
conn.commit()

register_vector(conn)  # NOW register after extension exists
cur.close()

# Connect to pgvector
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    dbname='rapidremedy',
    user='admin',
    password='admin123'
)
cur = conn.cursor()

# Enable extension FIRST before registering
cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
conn.commit()

register_vector(conn)

# Create table
cur.execute("""
    CREATE TABLE IF NOT EXISTS medical_abstracts (
        id SERIAL PRIMARY KEY,
        abstract_id VARCHAR(50),
        line_id VARCHAR(100),
        abstract_text TEXT,
        target VARCHAR(50),
        embedding vector(384)
    );
""")
conn.commit()

# Insert in batches
print("Inserting into pgvector...")
batch_size = 500
for i in range(0, len(df), batch_size):
    batch_df = df.iloc[i:i+batch_size]
    batch_emb = embeddings[i:i+batch_size]
    for j, (_, row) in enumerate(batch_df.iterrows()):
        cur.execute("""
            INSERT INTO medical_abstracts 
            (abstract_id, line_id, abstract_text, target, embedding)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            str(row['abstract_id']),
            str(row['line_id']),
            row['abstract_text'],
            row['target'],
            batch_emb[j].tolist()
        ))
    conn.commit()
    print(f"Inserted {min(i+batch_size, len(df))}/{len(df)}")

cur.close()
conn.close()
print("Done. All data in pgvector.")