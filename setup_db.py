import sqlite3

def create_database():
    conn = sqlite3.connect("absensi_smkn1.db")
    cursor = conn.cursor()

    # 1. Tabel Master Data Siswa
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS siswa (
            nisn TEXT PRIMARY KEY,
            nama TEXT NOT NULL,
            kelas TEXT NOT NULL
        )
    """)

    # 2. Tabel Transaksi Absensi Harian (UNIQUE mencegah dobel absen di hari yg sama)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS absensi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nisn TEXT,
            tanggal TEXT,
            jam_masuk TEXT,
            status_masuk TEXT,
            jam_pulang TEXT,
            status_pulang TEXT,
            UNIQUE(nisn, tanggal)
        )
    """)

    # --- SIMULASI MEMASUKKAN DATA SISWA ---
    # (Untuk uji coba, kita masukkan beberapa data. Aslinya bisa di-import ribuan siswa dari Excel/CSV)
    dummy_siswa = [
        ("1201", "Akhmad Saepudin", "XII TKJ"),
        ("1202", "Budi Santoso", "XI PPLG"),
        ("1203", "Siti Aminah", "X Akuntansi"),
        ("1204", "Rian Hidayat", "XI MPLB"),
    ]
    
    cursor.executemany("INSERT OR IGNORE INTO siswa (nisn, nama, kelas) VALUES (?, ?, ?)", dummy_siswa)

    conn.commit()
    conn.close()
    print("Database 'absensi_smkn1.db' berhasil dibuat!")

if __name__ == "__main__":
    create_database()