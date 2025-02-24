from flask import Flask, request, jsonify
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
from datetime import datetime
from nameparser import HumanName
import spacy

app = Flask(__name__)

@app.route('/test', methods=['GET'])
def test_api():
    return jsonify({'message': 'API is accessible!'})

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Inisialisasi model bahasa Inggris
nlp = spacy.load("en_core_web_sm")

def is_meaningful(text):
    # Hapus spasi di awal/akhir
    text = text.strip()

    # Abaikan string kosong atau satu karakter (kecuali angka)
    if len(text) <= 2 and not text.isdigit():
        return False

    # Proses dengan SpaCy
    doc = nlp(text)

    # Validasi menggunakan POS tagging atau entity
    # Contoh: Hanya ambil kata yang bukan simbol dan bukan stopword
    return any(token.is_alpha or token.like_num for token in doc)



def extract_text_from_pdf(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    extracted_text = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()

        # print(text.splitlines())
        

        if text.strip():
            text = text.rstrip()  # Jika ada teks, langsung ditambahkan ke array
            extracted_text.extend(text.splitlines())  # Memisahkan berdasarkan baris
        else:  # Jika tidak ada teks, gunakan OCR
            pix = page.get_pixmap()
            img = Image.open(io.BytesIO(pix.tobytes()))
            text = pytesseract.image_to_string(img)
            extracted_text.extend(text.splitlines())  # Memisahkan berdasarkan baris


    clean_data = [item.rstrip() for item in extracted_text]

    # Membersihkan data
    clean_data = [item for item in clean_data if is_meaningful(item)]
    
    return clean_data


def filter_names_by_position(data, position):
    filtered_names = []
    for i in range(len(data) - 1):  # Iterasi seluruh elemen array, kecuali yang terakhir
        if data[i+1] == position:  # Cek apakah jabatan pada elemen setelahnya sesuai dengan yang dicari
            filtered_names.append(data[i])  # Tambahkan nama ke dalam hasil
    return filtered_names

def find_document_name_blueprint(data, pattern):
    for i in range(len(data) - 1):
        if data[i].strip() == pattern and data[i + 1].strip():
            return data[i + 1].strip()  # Ambil elemen setelahnya

@app.route('/extract', methods=['POST'])
def extract_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    pdf_file = request.files['file']
    text = extract_text_from_pdf(pdf_file)

    # print(text)
    
    nama_bpo = filter_names_by_position(text, 'Business Process Owner')
    nama_it_dev = filter_names_by_position(text, 'Developer')
    nama_it_pm = filter_names_by_position(text, 'IT Project Manager')
    nama_stering_comite = filter_names_by_position(text, 'Steering Committee')
    document_name = find_document_name_blueprint(text, 'Solution Blue Print')
    author = filter_names_by_position(text, '1.0')
    
    all_names = nama_bpo + nama_it_pm + nama_it_dev + nama_stering_comite

    # print(author)

    if author :
        data = {
            'author':author,
            'document_name': document_name,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'releaser': all_names,
            'status': 'Success'
        }
    else:
        data = {
            'text' : text,
            'status': 'File tidak sesuai template.'
        }

    
    
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
