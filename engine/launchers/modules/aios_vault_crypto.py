
def encrypt(text): return f"enc:{text}"
def decrypt(text): return text.replace("enc:", "")
