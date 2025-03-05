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
from elasticsearch_conn import insert_to_elasticsearch, get_from_elasticsearch, get_data_by_id
import sys


app = Flask(__name__)
# data = {
#     'nama': ['document name']
# }
# print(get_from_elasticsearch('template.pdf', '11aBX5UB-5F5DibPhRkk'))
# es_insert = insert_to_elasticsearch('master_nama_dokumen', data)

print('===============================')
@app.route('/test', methods=['GET'])
def test_api():
    return jsonify({'message': 'API is accessible!'})

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Inisialisasi model bahasa Inggris
nlp = spacy.load("en_core_web_sm")

spell = SpellChecker(language=None)  # Tidak pakai bahasa default (English)
spell.word_frequency.load_text_file("data.txt")  # Pakai kamus ID

with open("kamus.json", "r", encoding="utf-8") as file:
    kamus_typo = json.load(file)

def cleanse_data(data):
    # 1. Hapus elemen kosong
    data = [item for item in data if item.strip()]

    # 2. Hapus prefix ": " dari elemen yang mengandungnya
    data = [item.lstrip(": ").strip() for item in data]

    return data

def koreksi_typo(text):
    text =  " ".join(text)

    kata_kata = text.split()  # Pisahkan teks menjadi kata-kata
    
    # Koreksi setiap kata berdasarkan kamus
    hasil = [kamus_typo[kata.lower()] if kata.lower() in kamus_typo else kata for kata in kata_kata]
    
    return hasil



def koreksi_typotxt(text):

    text =  " ".join(text)

    kata_kata = text.split()
    
    hasil = [spell.correction(kata) if spell.correction(kata) else kata for kata in kata_kata]

    print(hasil)

    return hasil


def extract_between_old(data, start_keyword, end_keyword):
   
    try:
        start_index = data.index(start_keyword) + 1
    except ValueError:
        start_index = 0  # Mulai dari awal jika start_keyword tidak ditemukan

    try:
        end_index = data.index(end_keyword)
    except ValueError:
        end_index = len(data)  # Sampai akhir jika end_keyword tidak ditemukan

    return data[start_index:end_index]

def extract_between(data, start_keywords, end_keywords):
    start_index = 0  # Default mulai dari awal
    end_index = 0  # Default sampai akhir

    print(end_index)

    # Cari index start_keyword pertama yang ditemukan dalam data
    for keyword in start_keywords:
        if keyword in data:
            temp_index = data.index(keyword) + 1
            start_index = min(start_index, temp_index) if start_index > 0 else temp_index

    # Cari index end_keyword pertama yang ditemukan dalam data
    for keyword in end_keywords:
        if keyword in data:
            temp_index = data.index(keyword)
            end_index = min(end_index, temp_index)

    return data[start_index:end_index] if start_index < end_index else []



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
            # print(extracted_text)


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

def find_document_name_blueprintold(data, pattern):
    for i in range(len(data) - 1):
        if data[i].strip() == pattern and data[i + 1].strip():
            return data[i + 1].strip()  # Ambil elemen setelahnya

def find_document_name_blueprint(data, patterns):

    # print(patterns)
    for i in range(len(data) - 1):
        if data[i].strip() in patterns and data[i + 1].strip():
            return data[i + 1].strip()  # Ambil elemen setelahnya jika ditemukan
    return None  # Jika tidak ada yang cocok, return None

def get_label_before_value(data, target_value):
    for i in range(1, len(data)):  # Mulai dari index 1 agar bisa cek index sebelumnya
        if data[i] == target_value:
            return data[i - 1]  # Ambil elemen sebelum target_value
    return None  # Return None jika tidak ditemukan

def add_multiple_items_by_names(data, keys, val_label):
    """
    Menambahkan item ke dalam "items" berdasarkan name yang ada dalam keys.
    """
    for name, new_item in zip(keys, val_label):  # Loop berdasarkan pasangan keys dan values
        for label in data["label"]:
            if label["name"] == name:  # Mencari berdasarkan 'name'
                if new_item not in label["items"]:  # Hindari duplikasi
                    label["items"].append(new_item)
                break  # Keluar dari loop setelah menemukan 'name' yang cocok
    return data


@app.route('/extract', methods=['POST'])
def extract_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    pdf_file = request.files['file']
    file_name = pdf_file.filename
    text = extract_text_from_pdf(pdf_file)


    if file_name == 'template blue print test.pdf' or file_name == 'template blue print testv2.pdf' or file_name == '55768_Document BAST_.pdf':

        text = cleanse_data(text)

        # print(text)

        with open('master.json') as file:
            data = json.load(file)

        author_label = next((label["items"] for label in data["label"] if label["name"] == "label_author"), [])
        doc_label = next((label["items"] for label in data["label"] if label["name"] == "label_dokumen_name"), [])
        plant_label = next((label["items"] for label in data["label"] if label["name"] == "label_plant"), [])
        cs_label = next((label["items"] for label in data["label"] if label["name"] == "label_cost_center"), [])
        doc_subject_label = next((label["items"] for label in data["label"] if label["name"] == "label_dokumen_subject"), [])
        date_label = next((label["items"] for label in data["label"] if label["name"] == "label_date"), [])

        label_email = next((item for item in data['label'] if item['name'] == 'label_email'), None)

        label_sign = next((item for item in data['label'] if item['name'] == 'label_sign'), None)

        print(label_sign)

        # print(text)

        


        author = find_document_name_blueprint(text, author_label)
        document_name = find_document_name_blueprint(text, doc_label)
        plant = find_document_name_blueprint(text, plant_label)
        cost_center = find_document_name_blueprint(text, cs_label)
        document_subject = find_document_name_blueprint(text, doc_subject_label)
        date = find_document_name_blueprint(text, date_label)


        releaser = extract_between(text, label_sign['items_start'], label_sign['items_end'])

        # print(releaser)
        # sys.exit()

        email = extract_between(text, label_email['items_start'], label_email['items_end'])
        email =  " ".join(email)

        index_name = 'template.pdf'
        data_insert = {
            "pdf_details": text,
            'author':[author],
            'document_name': document_name,
            'plant': plant,
            'cost_center': cost_center,
            'date': date,
            'document_subject': document_subject,
            'releaser': releaser,
            'email': email,
            'status': 'Success'
        }

        es_insert = insert_to_elasticsearch(index_name, data_insert)

        index_name = es_insert['_index']
        doc_id = es_insert['_id']

        # print(es_insert)

        data = {
                'doc_id':doc_id,
                'index_name': index_name,
                'author':[author],
                'document_name': document_name,
                'plant': plant,
                'cost_center': cost_center,
                'date': date,
                'document_subject': document_subject,
                'releaser': releaser,
                'email': email,
                'status': 'Success'
            }

        data = {key: ("" if value is None else value) for key, value in data.items()}

        return jsonify(data)
        # return{"a":"b"}

    else:

        
        nama_bpo = filter_names_by_position(text, 'Business Process Owner')
        nama_it_dev = filter_names_by_position(text, 'Developer')
        nama_it_pm = filter_names_by_position(text, 'IT Project Manager')
        nama_stering_comite = filter_names_by_position(text, ['Steering Committee'])
        document_name = find_document_name_blueprint(text, ['Solution Blue Print'])
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


@app.route('/edit_data', methods=['POST'])
def get_document():
    # Menerima data JSON dari request
    request_data = request.json

    print(request_data)

    with open('master.json') as file:
        data_master = json.load(file)

    # Ambil doc_id dari request, jika tidak ada, beri error
    doc_id = request_data.get("doc_id")
    if not doc_id:
        return jsonify({"error": "doc_id is required"}), 400

    # Ambil filter tambahan (jika ada)
    edit_data = request_data.get("edit_data", {})

    values = list(edit_data.values())  # Mengambil semua value dalam bentuk list
    keys = list(edit_data.keys())

    # print(keys)

    data = get_data_by_id(doc_id)


    # Ambil data dari request
    edit_data = request_data.get("edit_data", {})
    keys = list(edit_data.keys())  # Ambil semua keys
    values = list(edit_data.values())  # Ambil semua values

    # Ambil label sebelum value di pdf_details
    val_label = [get_label_before_value(data['pdf_details'], item) for item in values]

    # Update data JSON dengan tambahan values
    updated_data = add_multiple_items_by_names(data_master, keys, val_label)

    # Simpan hasil perubahan kembali ke master.json
    with open('master.json', 'w', encoding='utf-8') as file:
        json.dump(updated_data, file, indent=2, ensure_ascii=False)


    return jsonify(data)    
    
    

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
