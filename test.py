from spellchecker import SpellChecker

# Load spell checker dengan kamus bahasa Indonesia
spell = SpellChecker(language=None)  # Tidak pakai bahasa default (English)
spell.word_frequency.load_text_file("data.txt")  # Pakai kamus ID

# Contoh teks
teks_salah = "Selamat Datanag ke Dokumen Ini Ini adlaah conttoh dokumen yang memilikki berbgai kesalhan ketik. Adakah anda menyadari kesaahan yang ada Terimkasih sudah membacca"
kata_kata = teks_salah.split()

# Koreksi setiap kata
hasil = [spell.correction(kata) if spell.correction(kata) else kata for kata in kata_kata]

print("Sebelum:", teks_salah)
print("Sesudah:", " ".join(hasil))
