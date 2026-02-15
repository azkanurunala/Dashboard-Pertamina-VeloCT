
def save_data():
    cursor.execute("INSERT INTO users (user_name, email) VALUES (?, ?)", (name, email))
