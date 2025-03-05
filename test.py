import json
from elasticsearch import Elasticsearch

# Koneksi ke Elasticsearch
es = Elasticsearch("http://localhost:9200")

# Cek apakah Elasticsearch aktif
print(es.info())


# Muat data JSON ke dalam dictionary
kamus_typo = {
    "@": "di", "abis": "habis", "ad": "ada", "adlh": "adalah", "afaik": "as far as i know",
    "ahaha": "haha", "aj": "saja", "ak": "saya", "alay": "norak", "anjrit": "anjing",
    "btw": "ngomong", "cemen": "penakut", "cowwyy": "maaf", "cp": "siapa",
    "demen": "suka", "dodol": "bodoh", "doku": "uang", "dtg": "datang", "dpt": "dapat",
    "elu": "kamu", "enggak": "tidak", "fyi": "sebagai informasi", "gaada": "tidak ada uang",
    "gag": "tidak", "gaje": "tidak jelas"
}  # Masukkan semua kata dari JSON-mu

def koreksi_typo(text):
    kata_kata = text.split()  # Pisahkan teks menjadi kata-kata
    
    # Koreksi setiap kata berdasarkan kamus
    hasil = [kamus_typo[kata.lower()] if kata.lower() in kamus_typo else kata for kata in kata_kata]
    
    return " ".join(hasil)  # Gabungkan kembali menjadi kalimat

# Contoh Penggunaan
kalimat_typo = "btw elu gag datang karena abis duit ya?"
hasil_koreksi = koreksi_typo(kalimat_typo)
print(hasil_koreksi)  
# Output: "ngomong kamu tidak datang karena habis duit ya?"
