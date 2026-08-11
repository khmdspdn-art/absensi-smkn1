from datetime import datetime
import base64
import sqlite3
import pandas as pd
import streamlit as st
from geopy.distance import geodesic

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Sistem Absensi & Geofencing SMKN 1 Lemahsugih",
    page_icon="🎓",
    layout="wide",
)

# --- KONFIGURASI PUSAT SEKOLAH ---
LAT_SEKOLAH = -6.877500  
LON_SEKOLAH = 108.285000
RADIUS_MAX = 50  # dalam meter

# --- FUNGSI LOAD GAMBAR LOGO KE BASE64 ---
def get_img_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception:
        return None

# Ubah "logo.png" sesuai dengan nama file gambar logo Anda di folder proyek
img_base64 = get_img_as_base64("logo.png")

# --- CUSTOM CSS DENGAN EFEK GRADASI & STYLE GAMBAR LOGO ---
st.markdown(
    """
    <style>
    .main {
        background: linear-gradient(135deg, #f8fafc 0%, #edf2f7 100%);
        font-family: 'Inter', sans-serif;
    }
    
    .header-container {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 50%, #1d4ed8 100%);
        padding: 2.5rem 2rem;
        border-radius: 18px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .school-logo {
        width: 100px;
        height: 100px;
        object-fit: contain;
        margin-bottom: 1rem;
        filter: drop-shadow(0 4px 8px rgba(0,0,0,0.2));
    }

    .header-title {
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 0.4rem;
        letter-spacing: -0.5px;
    }
    
    .header-subtitle {
        font-size: 1.1rem;
        color: #e2e8f0;
        font-weight: 400;
        letter-spacing: 0.5px;
    }

    .custom-card {
        background: rgba(255, 255, 255, 0.95);
        padding: 1.8rem;
        border-radius: 14px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
        border: 1px solid #e2e8f0;
        margin-bottom: 1.5rem;
        backdrop-filter: blur(10px);
    }

    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: white;
        font-weight: 600;
        border-radius: 10px;
        padding: 0.75rem 1rem;
        border: none;
        box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #1d4ed8 100%, #1e40af 100%);
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4);
        transform: translateY(-2px);
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        color: white;
    }
    section[data-testid="stSidebar"] .stRadio label {
        color: #f1f5f9 !important;
        font-weight: 500;
    }
    
    div[data-testid="stMetric"] {
        background: white;
        padding: 1.2rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02);
        border: 1px solid #e2e8f0;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- KONEKSI DATABASE SQLITE ---
@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect("absensi_smkn1.db", check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

conn = get_db_connection()

# --- SIDEBAR NAVIGASI ---
with st.sidebar:
    st.markdown("<h3 style='color: white; text-align: center; padding-top: 1rem;'>🎓 NAVIGASI UTAMA</h3>", unsafe_allow_html=True)
    st.markdown("---")
    menu = st.radio("Pilih Halaman:", ["Absensi Siswa", "Monitoring Wakasek Kurikulum"])
    st.markdown("---")
    st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 0.85rem;'>SMKN 1 Lemahsugih<br>Digital Geofencing System © 2026</p>", unsafe_allow_html=True)

# HTML Tag untuk Logo Sekolah di Header
logo_html = f"<img src='data:image/png;base64,{img_base64}' class='school-logo'>" if img_base64 else "<div style='font-size: 3rem;'>🎓</div>"

# ==========================================
# HALAMAN 1: ABSENSI SISWA
# ==========================================
if menu == "Absensi Siswa":
    st.markdown(f"""
        <div class='header-container'>
            {logo_html}
            <div class='header-title'>SMKN 1 LEMAHSUGIH</div>
            <div class='header-subtitle'>Portal Resmi Absensi & Geofencing Siswa Berbasis Digital</div>
        </div>
    """, unsafe_allow_html=True)

    if "device_lock" not in st.session_state:
        st.session_state.device_lock = {}

    @st.cache_data(ttl=60)
    def load_siswa():
        return pd.read_sql("SELECT nisn, nama, kelas FROM siswa", conn)

    df_siswa = load_siswa()

    with st.container():
        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
        st.markdown("#### 🔍 Cari Identitas Siswa")
        st.caption("Ketik Nama atau NISN pada kolom di bawah untuk mencari:")
        
        # Menggunakan text_input agar bisa diketik bebas oleh pengguna
        keyword = st.text_input("Masukkan Nama atau NISN:", placeholder="Contoh: Ahmad atau 005...").strip()
        
        selected_nisn = None
        if keyword:
            # Filter data berdasarkan nama atau NISN yang diketik
            df_filtered = df_siswa[
                df_siswa['nama'].str.contains(keyword, case=False, na=False) | 
                df_siswa['nisn'].astype(str).str.contains(keyword, case=False, na=False)
            ]
            
            if len(df_filtered) == 1:
                # Jika hasil pencarian hanya 1, otomatis dipilih
                user_row = df_filtered.iloc[0]
                selected_nisn = str(user_row['nisn'])
                st.success( ditemukan: **{user_row['nama']}** (Kelas: {user_row['kelas']})")
            elif len(df_filtered) > 1:
                # Jika ada beberapa nama yang mirip, tampilkan pilihan spesifik
                st.info(f"Ditemukan {len(df_filtered)} siswa dengan kata kunci tersebut. Silakan pilih di bawah:")
                options_map = {f"{row['nama']} — NISN: {row['nisn']} — Kelas: {row['kelas']}": str(row['nisn']) for _, row in df_filtered.iterrows()}
                pilihan_nama = st.selectbox("Pilih Nama Siswa:", options=list(options_map.keys()), index=None)
                if pilihan_nama:
                    selected_nisn = options_map[pilihan_nama]
            else:
                st.warning("⚠️ Siswa dengan nama atau NISN tersebut tidak ditemukan.")
        st.markdown("</div>", unsafe_allow_html=True)

    device_id = "user_device_browser_session"

    if selected_nisn:
        user_row = df_siswa[df_siswa['nisn'].astype(str) == selected_nisn].iloc[0]
        nisn = str(user_row['nisn'])
        nama = user_row['nama']
        kelas = user_row['kelas']

        if device_id in st.session_state.device_lock:
            if st.session_state.device_lock[device_id] != nisn:
                st.error("⚠️ Perangkat ini terkunci untuk akun siswa lain! (Kebijakan 1 HP 1 Akun Aktif)")
                st.stop()
        else:
            st.session_state.device_lock[device_id] = nisn

        st.info(f"👤 **Siswa Aktif:** {nama} &nbsp;|&nbsp; **Kelas:** {kelas} &nbsp;|&nbsp; **NISN:** {nisn}")
        
        with st.container():
            st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
            st.markdown("#### 📍 Verifikasi Lokasi & Waktu Server")
            
            use_gps_simulation = st.checkbox("Gunakan Simulasi Koordinat (Mode Pengujian)", value=True)
            if use_gps_simulation:
                col_lat, col_lon = st.columns(2)
                with col_lat:
                    lat_siswa = st.number_input("Latitude", value=LAT_SEKOLAH, format="%.6f")
                with col_lon:
                    lon_siswa = st.number_input("Longitude", value=LON_SEKOLAH, format="%.6f")
            else:
                lat_siswa, lon_siswa = LAT_SEKOLAH, LON_SEKOLAH

            jarak = geodesic((LAT_SEKOLAH, LON_SEKOLAH), (lat_siswa, lon_siswa)).meters
            
            if jarak <= RADIUS_MAX:
                st.success(f"📏 Jarak Anda: **{jarak:.2f} meter** dari titik sekolah. *(Valid, dalam radius max {RADIUS_MAX}m)*")
            else:
                st.error(f"📏 Jarak Anda: **{jarak:.2f} meter** dari titik sekolah. *(Di luar radius valid max {RADIUS_MAX}m)*")

            waktu_sekarang = datetime.now().time()
            tanggal_hari_ini = datetime.now().strftime("%Y-%m-%d")
            st.caption(f"⏰ Waktu Server: **{datetime.now().strftime('%H:%M:%S')} WIB** | Tanggal: {tanggal_hari_ini}")
            st.markdown("</div>", unsafe_allow_html=True)

        cursor = conn.cursor()
        cursor.execute("SELECT jam_masuk, status_masuk, jam_pulang, status_pulang FROM absensi WHERE nisn = ? AND tanggal = ?", (nisn, tanggal_hari_ini))
        existing_data = cursor.fetchone()

        col_masuk, col_pulang = st.columns(2)

        with col_masuk:
            st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
            st.markdown("#### 📥 Absen Masuk")
            st.caption("Pukul 06.30 - 07.30 WIB")
            
            if existing_data and existing_data[0]:
                st.success(f"✅ Sudah Absen Masuk\n\n**Jam:** {existing_data[0]}\n**Status:** {existing_data[1]}")
            else:
                if st.button("Kirim Absen Masuk", key=f"btn_masuk_{nisn}"):
                    if jarak > RADIUS_MAX:
                        st.error(f"❌ Gagal! Anda berada di luar radius sekolah ({jarak:.2f}m).")
                    else:
                        jam_awal = datetime.strptime("06:30:00", "%H:%M:%S").time()
                        jam_akhir = datetime.strptime("07:30:00", "%H:%M:%S").time()
                        
                        if waktu_sekarang < jam_awal:
                            st.warning("⏳ Belum waktunya melakukan absen masuk.")
                        elif waktu_sekarang <= jam_akhir:
                            status_m = "TEPAT WAKTU"
                            jam_str = datetime.now().strftime("%H:%M:%S")
                            cursor.execute("""
                                INSERT INTO absensi (nisn, tanggal, jam_masuk, status_masuk) 
                                VALUES (?, ?, ?, ?)
                                ON CONFLICT(nisn, tanggal) DO UPDATE SET jam_masuk=?, status_masuk=?
                            """, (nisn, tanggal_hari_ini, jam_str, status_m, jam_str, status_m))
                            conn.commit()
                            st.success("✅ Berhasil: TEPAT WAKTU!")
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
                            st.warning("⚠️ Tercatat Terlambat (lewat 07.30 WIB).")
                            st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with col_pulang:
            st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
            st.markdown("#### 📤 Absen Pulang")
            st.caption("Pukul 14.30 - 15.15 WIB")
            
            if existing_data and existing_data[2]:
                st.success(f"✅ Sudah Absen Pulang\n\n**Jam:** {existing_data[2]}\n**Status:** {existing_data[3]}")
            else:
                if st.button("Kirim Absen Pulang", key=f"btn_pulang_{nisn}"):
                    if jarak > RADIUS_MAX:
                        st.error(f"❌ Gagal! Anda berada di luar radius sekolah ({jarak:.2f}m).")
                    else:
                        jam_p_awal = datetime.strptime("14:30:00", "%H:%M:%S").time()
                        jam_p_akhir = datetime.strptime("15:15:00", "%H:%M:%S").time()
                        
                        if waktu_sekarang < jam_p_awal:
                            st.warning("⏳ Belum waktunya jam pulang sekolah.")
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
                            st.error("🚨 Melewati batas pukul 15.15 WIB! Tercatat: **MINGGAT**.")
                            st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# HALAMAN 2: MONITORING WAKASEK KURIKULUM
# ==========================================
elif menu == "Monitoring Wakasek Kurikulum":
    st.markdown(f"""
        <div class='header-container'>
            {logo_html}
            <div class='header-title'>DASHBOARD WAKASEK KURIKULUM</div>
            <div class='header-subtitle'>Monitoring Kehadiran Siswa Real-Time • SMKN 1 Lemahsugih</div>
        </div>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
        st.markdown("#### 🔐 Otentikasi Administrator")
        password_input = st.text_input("Masukkan Password Akses Wakasek:", type="password", placeholder="Masukkan kata sandi...")
        st.markdown("</div>", unsafe_allow_html=True)
    
    if password_input == "kurikulum2026": 
        st.success("🔓 Akses Berhasil. Selamat bertugas, Wakasek Kurikulum.")
        st.markdown("---")

        query_rekap = """
            SELECT 
                s.nisn, 
                s.nama, 
                s.kelas, 
                a.tanggal, 
                a.jam_masuk, 
                a.status_masuk, 
                a.jam_pulang, 
                a.status_pulang
            FROM absensi a
            JOIN siswa s ON a.nisn = s.nisn
            ORDER BY a.tanggal DESC, a.jam_masuk DESC
        """
        df_rekap = pd.read_sql(query_rekap, conn)

        if df_rekap.empty:
            st.info("ℹ️ Belum ada data absensi yang tercatat di dalam database.")
        else:
            with st.container():
                st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
                st.markdown("#### 🔍 Filter Data Kehadiran")
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    list_tanggal = df_rekap["tanggal"].unique().tolist()
                    pilih_tanggal = st.selectbox("Filter Berdasarkan Tanggal", ["Semua Tanggal"] + list_tanggal)
                with col_f2:
                    list_kelas = df_rekap["kelas"].unique().tolist()
                    pilih_kelas = st.selectbox("Filter Berdasarkan Kelas", ["Semua Kelas"] + list_kelas)
                st.markdown("</div>", unsafe_allow_html=True)

            filtered_df = df_rekap.copy()
            if pilih_tanggal != "Semua Tanggal":
                filtered_df = filtered_df[filtered_df["tanggal"] == pilih_tanggal]
            if pilih_kelas != "Semua Kelas":
                filtered_df = filtered_df[filtered_df["kelas"] == pilih_kelas]

            m1, m2, m3, m4 = st.columns(4)
            total_absen = len(filtered_df)
            tepat_waktu = len(filtered_df[filtered_df["status_masuk"] == "TEPAT WAKTU"])
            terlambat = len(filtered_df[filtered_df["status_masuk"] == "TERLAMBAT"])
            minggat = len(filtered_df[filtered_df["status_pulang"] == "MINGGAT"])

            m1.metric("Total Absen Tercatat", total_absen)
            m2.metric("Tepat Waktu", tepat_waktu)
            m3.metric("Terlambat", terlambat)
            m4.metric("Minggat", minggat)

            st.markdown("---")
            st.markdown("#### 📋 Rincian Tabel Kehadiran")
            st.dataframe(filtered_df, use_container_width=True)

            csv_data = filtered_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Laporan Rekap (Format CSV / Excel)",
                data=csv_data,
                file_name=f"Laporan_Absensi_SMKN1_{datetime.now().strftime('%Y-%m-%d')}.csv",
                mime="text/csv",
            )
    elif password_input != "":
        st.error("❌ Kata sandi yang Anda masukkan salah.")
    else:
        st.info("🔒 Masukkan kata sandi pada kolom di atas untuk menampilkan isi dashboard.")