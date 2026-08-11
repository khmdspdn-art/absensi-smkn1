from datetime import datetime
import sqlite3
import pandas as pd
import streamlit as st
from geopy.distance import geodesic

# Konfigurasi Halaman
st.set_page_config(
    page_title="Absensi Geofencing SMKN 1 Lemahsugih",
    page_icon="🏫",
    layout="centered",
)

# --- KONFIGURASI PUSAT SEKOLAH ---
LAT_SEKOLAH = -6.877500  # Koordinat SMKN 1 Lemahsugih
LON_SEKOLAH = 108.285000
RADIUS_MAX = 50  # dalam meter

# CSS Styling agar menarik
st.markdown(
    """
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 10px;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- KONEKSI DATABASE SQLITE (WAL Mode untuk performa tinggi anti-delay) ---
@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect("absensi_smkn1.db", check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

conn = get_db_connection()

# Header Aplikasi
st.markdown(
    "<h2 style='text-align: center; color: #2c3e50;'>🏫 APLIKASI ABSENSI SISWA</h2>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align: center; color: #7f8c8d;'>SMKN 1 LEMAHSUGIH - GEOFENCING SYSTEM</p>",
    unsafe_allow_html=True,
)
st.markdown("---")

# Inisialisasi Session State untuk Device Binding (1 HP 1 Siswa)
if "device_lock" not in st.session_state:
    st.session_state.device_lock = {}

# --- LOAD DATA SISWA DARI DATABASE UNTUK PENCARIAN CEPAT ---
@st.cache_data(ttl=60)
def load_siswa():
    query = "SELECT nisn, nama, kelas FROM siswa"
    return pd.read_sql(query, conn)

df_siswa = load_siswa()

# --- FITUR PENCARIAN NAMA SISWA ---
st.markdown("### 🔍 Cari Data Siswa")
options = df_siswa.apply(lambda x: f"{x['nama']} (NISN: {x['nisn']} - {x['kelas']})", axis=1)

selected_option = st.selectbox(
    "Ketik nama atau NISN Anda:",
    options=options,
    index=None,
    placeholder="Contoh: Akhmad..."
)

device_id = "user_device_browser_session"  # Simulasi kunci perangkat

if selected_option:
    # Ekstrak NISN dari string yang dipilih
    selected_nisn = selected_option.split('NISN: ')[1].split(' - ')[0]
    
    # Ambil info siswa
    user_row = df_siswa[df_siswa['nisn'] == selected_nisn].iloc[0]
    nisn = user_row['nisn']
    nama = user_row['nama']
    kelas = user_row['kelas']

    # Validasi Konsep 1 HP 1 Siswa
    if device_id in st.session_state.device_lock:
        if st.session_state.device_lock[device_id] != nisn:
            st.error("⚠️ Perangkat ini sudah terkunci untuk akun siswa lain! (Aturan 1 HP 1 Siswa Aktif)")
            st.stop()
    else:
        st.session_state.device_lock[device_id] = nisn

    st.success(f"Login Sesi: **{nama}** ({kelas})")
    st.markdown("---")
    
    # --- VERIFIKASI LOKASI & WAKTU ---
    st.markdown("### 📍 Verifikasi Lokasi & Waktu")
    
    use_gps_simulation = st.checkbox("Gunakan Simulasi Koordinat (Untuk Pengujian)", value=True)
    if use_gps_simulation:
        lat_siswa = st.number_input("Latitude Anda", value=LAT_SEKOLAH, format="%.6f")
        lon_siswa = st.number_input("Longitude Anda", value=LON_SEKOLAH, format="%.6f")
    else:
        lat_siswa, lon_siswa = LAT_SEKOLAH, LON_SEKOLAH

    # Hitung Jarak
    jarak = geodesic((LAT_SEKOLAH, LON_SEKOLAH), (lat_siswa, lon_siswa)).meters
    st.write(f"📏 Jarak Anda dari sekolah: **{jarak:.2f} meter** (Maksimal: {RADIUS_MAX} meter)")

    waktu_sekarang = datetime.now().time()
    tanggal_hari_ini = datetime.now().strftime("%Y-%m-%d")
    st.write(f"⏰ Waktu Server: **{datetime.now().strftime('%H:%M:%S')}** | Tanggal: {tanggal_hari_ini}")

    # Cek status absen hari ini di database
    cursor = conn.cursor()
    cursor.execute("SELECT jam_masuk, status_masuk, jam_pulang, status_pulang FROM absensi WHERE nisn = ? AND tanggal = ?", (nisn, tanggal_hari_ini))
    existing_data = cursor.fetchone()

    st.markdown("---")
    col_masuk, col_pulang = st.columns(2)

    # --- PROSES ABSEN MASUK ---
    with col_masuk:
        st.markdown("#### Absen Masuk")
        st.caption("06.30 - 07.30 (Lewat = Terlambat)")
        
        if existing_data and existing_data[0]:
            st.info(f"✅ Sudah Absen Masuk\nJam: {existing_data[0]}\nStatus: **{existing_data[1]}**")
        else:
            if st.button("Kirim Absen Masuk", key=f"btn_masuk_{nisn}"):
                if jarak > RADIUS_MAX:
                    st.error(f"❌ Gagal! Anda di luar radius sekolah ({jarak:.2f}m > 50m).")
                else:
                    jam_awal = datetime.strptime("06:30:00", "%H:%M:%S").time()
                    jam_akhir = datetime.strptime("07:30:00", "%H:%M:%S").time()
                    
                    if waktu_sekarang < jam_awal:
                        st.warning("⏳ Belum waktunya absen masuk.")
                    elif waktu_sekarang <= jam_akhir:
                        status_m = "TEPAT WAKTU"
                        jam_str = datetime.now().strftime("%H:%M:%S")
                        
                        cursor.execute("""
                            INSERT INTO absensi (nisn, tanggal, jam_masuk, status_masuk) 
                            VALUES (?, ?, ?, ?)
                            ON CONFLICT(nisn, tanggal) DO UPDATE SET jam_masuk=?, status_masuk=?
                        """, (nisn, tanggal_hari_ini, jam_str, status_m, jam_str, status_m))
                        conn.commit()
                        st.success("✅ Berhasil Absen Masuk: TEPAT WAKTU!")
                        st.rerun()
                    else:
                        status_m = "TERLAMBAT"
                        jam_str = datetime.now().strftime("%H:%M:%S")
                        
                        cursor.execute("""
                            INSERT INTO absensi (nisn, tanggal, jam_masuk, status_masuk) 
                            VALUES (?, ?, ?, ?)
                            ON CONFLICT(nisn, tanggal) DO UPDATE SET jam_masuk=?, status_masuk=?
                        """, (nisn, tanggal_hari_ini, jam_str, status_m, jam_str, status_m))
                        conn.commit()
                        st.warning("⚠️ Anda Terlambat! Tercatat lewat pukul 07.30.")
                        st.rerun()

    # --- PROSES ABSEN PULANG ---
    with col_pulang:
        st.markdown("#### Absen Pulang")
        st.caption("14.30 - 15.15 (Lewat = Minggat)")
        
        if existing_data and existing_data[2]:
            st.info(f"✅ Sudah Absen Pulang\nJam: {existing_data[2]}\nStatus: **{existing_data[3]}**")
        else:
            if st.button("Kirim Absen Pulang", key=f"btn_pulang_{nisn}"):
                if jarak > RADIUS_MAX:
                    st.error(f"❌ Gagal! Anda di luar radius sekolah ({jarak:.2f}m > 50m).")
                else:
                    jam_p_awal = datetime.strptime("14:30:00", "%H:%M:%S").time()
                    jam_p_akhir = datetime.strptime("15:15:00", "%H:%M:%S").time()
                    
                    if waktu_sekarang < jam_p_awal:
                        st.warning("⏳ Belum waktunya jam pulang.")
                    elif waktu_sekarang <= jam_p_akhir:
                        status_p = "PULANG"
                        jam_str = datetime.now().strftime("%H:%M:%S")
                        
                        cursor.execute("""
                            UPDATE absensi SET jam_pulang=?, status_pulang=? WHERE nisn=? AND tanggal=?
                        """, (jam_str, status_p, nisn, tanggal_hari_ini))
                        conn.commit()
                        st.success("✅ Berhasil Absen Pulang!")
                        st.rerun()
                    else:
                        status_p = "MINGGAT"
                        jam_str = datetime.now().strftime("%H:%M:%S")
                        
                        cursor.execute("""
                            UPDATE absensi SET jam_pulang=?, status_pulang=? WHERE nisn=? AND tanggal=?
                        """, (jam_str, status_p, nisn, tanggal_hari_ini))
                        conn.commit()
                        st.error("🚨 Melewati batas jam 15.15! Tercatat: **MINGGAT**.")
                        st.rerun()