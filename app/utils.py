import bcrypt

def verify_password(plain_password, hashed_password):
    password_byte_enc = plain_password.encode('utf-8')
    hashed_password=hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_byte_enc , hashed_password)

def get_password_hash(password):
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password=pwd_bytes, salt=salt)
    hashed_password = hashed_password.decode('utf-8')
    return hashed_password