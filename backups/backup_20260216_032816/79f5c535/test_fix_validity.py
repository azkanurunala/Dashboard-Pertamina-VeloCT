
def process_user(data):
    user_name = data.get('user_name')
    email = data.get('email')
    return {'user_name': user_name, 'email': email}
