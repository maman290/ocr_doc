from flask import Flask, request, jsonify
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
from datetime import datetime
from nameparser import HumanName
import spacy
import json
from spellchecker import SpellChecker

app = Flask(__name__)

@app.route('/test', methods=['GET'])
def test_api():
    return jsonify({'message': 'API is accessible!'})

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Inisialisasi model bahasa Inggris
nlp = spacy.load("en_core_web_sm")

spell = SpellChecker(language=None)  # Tidak pakai bahasa default (English)
spell.word_frequency.load_text_file("data.txt")  # Pakai kamus ID

def cleanse_data(data):
    # 1. Hapus elemen kosong
    data = [item for item in data if item.strip()]

    # 2. Hapus prefix ": " dari elemen yang mengandungnya
    data = [item.lstrip(": ").strip() for item in data]

    return data



def koreksi_typo(text):

    text =  " ".join(text)

    kata_kata = text.split()
    
    hasil = [spell.correction(kata) if spell.correction(kata) else kata for kata in kata_kata]

    print(hasil)

    return hasil


def extract_between(data, start_keyword, end_keyword):
   
    try:
        start_index = data.index(start_keyword) + 1
    except ValueError:
        start_index = 0  # Mulai dari awal jika start_keyword tidak ditemukan

    try:
        end_index = data.index(end_keyword)
    except ValueError:
        end_index = len(data)  # Sampai akhir jika end_keyword tidak ditemukan

    return data[start_index:end_index]


def get_email(data):
    # Cek apakah "As Is" dan "Scope" ada dalam data
    if "As Is" in data and "Scope" in data:
        start_index = data.index("As Is") + 1
        end_index = data.index("Scope")
        return data[start_index:end_index]
    else:
        return []  # Return list kosong jika tidak ditemukan

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

def convert_list_to_dict(data):
    result = {}
    key = None

    for item in data:
        if item.endswith(":"):  # Jika item adalah kunci (key)
            key = item.rstrip(":").strip()
            result[key] = ""  # Inisialisasi dengan string kosong
        elif key:  # Jika item adalah nilai (value)
            if result[key]:  # Jika sudah ada isinya, tambahkan ke list
                if isinstance(result[key], list):
                    result[key].append(item.strip())
                else:
                    result[key] = [result[key], item.strip()]
            else:
                result[key] = item.strip()

    print(result)

    return result

def extract_text_from_pdf(pdf_file):

    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    extracted_text = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()

        # print(text.splitlines())
        

        if text.strip():
            text = text.rstrip()  # Jika ada teks, langsung ditambahkan ke array
            extracted_text.extend(text.splitlines()) 
            print('pdf biasa') # Memisahkan berdasarkan baris
        else:  # Jika tidak ada teks, gunakan OCR
            pix = page.get_pixmap()
            img = Image.open(io.BytesIO(pix.tobytes()))
            text = pytesseract.image_to_string(img)
            extracted_text.extend(text.splitlines())  # Memisahkan berdasarkan baris
            print('pdf pytesseract')
            print(extracted_text)


    clean_data = [item.rstrip() for item in extracted_text]

    # Membersihkan data
    # clean_data = [item for item in clean_data if is_meaningful(item)]
    
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
    file_name = pdf_file.filename
    text = extract_text_from_pdf(pdf_file)


    if file_name == 'template blue print test.pdf':

        text = cleanse_data(text)

        print(text)

        # data = convert_list_to_dict(text)
        document_name = find_document_name_blueprint(text, 'Document name').lstrip(": ").strip()
        plant = find_document_name_blueprint(text, 'PC / Plant').lstrip(": ").strip()
        cost_center = find_document_name_blueprint(text, 'Cost Center').lstrip(": ").strip()
        document_subject = find_document_name_blueprint(text, 'Document Subject').lstrip(": ").strip()
        date = find_document_name_blueprint(text, 'Date').lstrip(": ").strip()

        releaser = extract_between(text, "Sign", "Body Email Text")

        email = extract_between(text, "Body Email Text", "Nonexistent")
        email =  " ".join(email)
        data = {
                'document_name': document_name,
                'plant': plant,
                'cost_center': cost_center,
                'date': date,
                'document_subject': document_subject,
                'releaser': releaser,
                'email': email,
                'status': 'Success'
            }

        return data

    else:

        
        nama_bpo = filter_names_by_position(text, 'Business Process Owner')
        nama_it_dev = filter_names_by_position(text, 'Developer')
        nama_it_pm = filter_names_by_position(text, 'IT Project Manager')
        nama_stering_comite = filter_names_by_position(text, 'Steering Committee')
        document_name = find_document_name_blueprint(text, 'Solution Blue Print')
        author = filter_names_by_position(text, '1.0')

        email = extract_between(text, "As Is", "Scope")

        # email = get_email(text)
        email =  " ".join(email)
        
        all_names = nama_bpo + nama_it_pm + nama_it_dev + nama_stering_comite

        # print(author)

        if author :
            data = {
                'author':author,
                'document_name': document_name,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'releaser': all_names,
                'email' : email,
                'status': 'Success'
            }
        else:

            text = koreksi_typo(text)

            text =  " ".join(text)

            data = {
                'text' : text,
                'status': 'File tidak sesuai template.'
            }

        
        return jsonify(data)


    
    
    

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
