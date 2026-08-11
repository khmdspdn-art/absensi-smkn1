from datetime import datetime
import sqlite3
import pandas as pd
import streamlit as st
from geopy.distance import geodesic

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Sistem Absensi & Geofencing SMKN 1 Lemahsugih",
    page_icon="🏫",
    layout="wide",
)

# --- KONFIGURASI PUSAT SEKOLAH ---
LAT_SEKOLAH = -6.877500  
LON_SEKOLAH = 108.285000
RADIUS_MAX = 50  # dalam meter

# --- CUSTOM CSS MODERN & PROFESIONAL ---
st.markdown(
    """
    <style>
    /* Global Styling & Background */
    .main {
        background-color: #f8fafc;
        font-family: 'Inter', sans-serif;
    }
    
    /* Header Styling */
    .header-container {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 2.5rem 2rem;
        border-radius: 16px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
    }
    .header-title {
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        letter-spacing: -0.5px;
    }
    .header-subtitle {
        font-size: 1.1rem;
        color: #94a3b8;
        font-weight: 400;
    }

    /* Card Box Styling */
    .custom-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        border: 1px solid #e2e8f0;
        margin-bottom: 1.5rem;
    }

    /* Button Styling */
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
        color: white;
        font-weight: 600;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        border: none;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.2);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #0369a1 0%, #075985 100%);
        box-shadow: 0 6px 15px rgba(2, 132, 199, 0.3);
        transform: translateY(-1px);
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0f172a;
        color: white;
    }
    section[data-testid="stSidebar"] .stRadio label {
        color: #e2e8f0 !important;
        font-weight: 500;
    }
    
    /* Metric Card Custom */
    div[data-testid="stMetric"] {
        background-color: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
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
    st.markdown("<h3 style='color: white; text-align: center; padding-top: 1rem;'>🏫 MENU NAVIGASI</h3>", unsafe_allow_html=True)
    st.markdown("---")
    menu = st.radio("Pilih Halaman:", ["Absensi Siswa", "Monitoring Wakasek Kurikulum"])
    st.markdown("---")
    st.markdown("<p style='text-align: center; color: #64748b; font-size: 0.85rem;'>© 2026 SMKN 1 Lemahsugih<br>Tim IT & Kurikulum</p>", unsafe_allow_html=True)

# ==========================================
# HALAMAN 1: ABSENSI SISWA
# ==========================================
if menu == "Absensi Siswa":
    st.markdown("""
        <div class='header-container'>
            <div class='header-title'>🏫 PORTAL ABSENSI SISWA</div>
            <div class='header-subtitle'>SMK Negeri 1 Lemahsugih • Sistem Geofencing Terpadu</div>
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
        st.markdown("#### 🔍 Identifikasi Siswa")
        options = df_siswa.apply(lambda x: f"{x['nama']} (NISN: {x['nisn']} - {x['kelas']})", axis=1)

        selected_option = st.selectbox(
            "Silakan ketik nama lengkap atau NISN Anda:",
            options=options,
            index=None,
            placeholder="Ketik nama Anda di sini..."
        )
        st.markdown("</div>", unsafe_allow_html=True)

    device_id = "user_device_browser_session"

    if selected_option:
        selected_nisn = selected_option.split('NISN: ')[1].split(' - ')[0]
        user_row = df_siswa[df_siswa['nisn'] == selected_nisn].iloc[0]
        nisn = user_row['nisn']
        nama = user_row['nama']
        kelas = user_row['kelas']

        if device_id in st.session_state.device_lock:
            if st.session_state.device_lock[device_id] != nisn:
                st.error("⚠️ Perangkat ini terkunci untuk akun siswa lain! (Kebijakan 1 HP 1 Akun Aktif)")
                st.stop()
        else:
            st.session_state.device_lock[device_id] = nisn

        # Kartu Info Identitas Aktif
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
            
            # Indikator Jarak Visual
            if jarak <= RADIUS_MAX:
                st.success(f"📏 Jarak Anda: **{jarak:.2f} meter** dari titik sekolah. *(Dalam radius valid max {RADIUS_MAX}m)*")
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

        # --- ABSEN MASUK ---
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

        # --- ABSEN PULANG ---
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
    st.markdown("""
        <div class='header-container'>
            <div class='header-title'>📊 DASHBOARD MONITORING KURIKULUM</div>
            <div class='header-subtitle'>Rekapitulasi Kehadiran Real-Time SMKN 1 Lemahsugih</div>
        </div>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
        st.markdown("#### 🔐 Otentikasi Administrator")
        password_input = st.text_input("Masukkan Password Akses Wakasek:", type="password", placeholder="Masukkan sandi...")
        st.markdown("</div>", unsafe_allow_html=True)
    
    if password_input == "kurikulum2026": 
        st.success("🔓 Akses Diberikan. Selamat bertugas, Wakasek Kurikulum.")
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

            # Metrik Ringkasan Eksekutif
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

            # Tombol Download Laporan Profesional
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