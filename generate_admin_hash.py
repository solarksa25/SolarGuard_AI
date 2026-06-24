import bcrypt

password = "admin123"
# Hash a password for the first time
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

print(f"Email: admin@gmail.com")
print(f"Password: {password}")
print(f"Hashed Password to insert into Database:")
print(hashed.decode('utf-8'))
