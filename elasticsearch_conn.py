from elasticsearch import Elasticsearch

# Koneksi ke Elasticsearch
es = Elasticsearch("http://localhost:9200")

# Cek apakah Elasticsearch aktif
if es.ping():
    print("✅ Elasticsearch Connected!")
else:
    print("❌ Elasticsearch Connection Failed!")

# Fungsi untuk menyimpan data ke Elasticsearch
def insert_to_elasticsearch(index_name, data):
    res = es.index(index=index_name, body=data)
    return res

# Fungsi untuk mengambil data berdasarkan ID
def get_from_elasticsearch(index_name, doc_id):
    try:
        res = es.get(index=index_name, id=doc_id)
        return res['_source']
    except Exception as e:
        return {'error': str(e)}

# Fungsi untuk menghapus data berdasarkan ID
def delete_from_elasticsearch(index_name, doc_id):
    try:
        res = es.delete(index=index_name, id=doc_id)
        return res
    except Exception as e:
        return {'error': str(e)}

# Fungsi untuk mencari data berdasarkan query
def search_in_elasticsearch(index_name, query):
    try:
        res = es.search(index=index_name, body=query)
        return res['hits']['hits']
    except Exception as e:
        return {'error': str(e)}

def add_name_to_document(index_name, doc_id, new_name):
    """
    Menambahkan value baru ke field 'nama' dalam dokumen yang sudah ada.
    
    :param index_name: Nama index Elasticsearch
    :param doc_id: ID dokumen yang ingin diupdate
    :param new_name: Value baru yang ingin ditambahkan ke field 'nama'
    """
    script = {
        "script": {
            "source": "if (!ctx._source.nama.contains(params.new_name)) { ctx._source.nama.add(params.new_name) }",
            "lang": "painless",
            "params": {"new_name": new_name}
        }
    }
    
    res = es.update(index=index_name, id=doc_id, body=script)
    return res

def get_data_by_id(doc_id):
    try:
        # Query untuk mencari berdasarkan ID di semua index
        query = {
            "query": {
                "term": {
                    "_id": doc_id  # Cari berdasarkan _id
                }
            }
        }

        # Cari di semua indeks
        response = es.search(body=query)

        # Jika ada hasil, ambil dokumen pertama
        if response["hits"]["hits"]:
            return response["hits"]["hits"][0]["_source"]  # Data dokumen
        else:
            return {"error": "Document not found"}

    except Exception as e:
        return {"error": str(e)}

