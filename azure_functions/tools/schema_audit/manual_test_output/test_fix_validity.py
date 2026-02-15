
def process_user(data):
    username = data.get('username')
    email = data.get('email')
    return {'username': username, 'email': email}
