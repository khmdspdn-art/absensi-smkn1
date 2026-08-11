from datetime import datetime
import sqlite3
import pandas as pd
import streamlit as st
from geopy.distance import geodesic

# Konfigurasi Halaman
st.set_page_config(
    page_title="Absensi & Monitoring SMKN 1 Lemahsugih",
    page_icon="🏫",
    layout="wide",
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

# --- KONEKSI DATABASE SQLITE ---
@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect("absensi_smkn1.db", check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

conn = get_db_connection()

# --- SIDEBAR NAVIGASI MENU ---
st.sidebar.title("📌 Menu Navigasi")
menu = st.sidebar.radio("Pilih Halaman:", ["Absensi Siswa", "Monitoring Wakasek Kurikulum"])

# ==========================================
# HALAMAN 1: ABSENSI SISWA
# ==========================================
if menu == "Absensi Siswa":
    st.markdown("<h2 style='text-align: center; color: #2c3e50;'>🏫 APLIKASI ABSENSI SISWA</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #7f8c8d;'>SMKN 1 LEMAHSUGIH - GEOFENCING SYSTEM</p>", unsafe_allow_html=True)
    st.markdown("---")

    if "device_lock" not in st.session_state:
        st.session_state.device_lock = {}

    @st.cache_data(ttl=60)
    def load_siswa():
        return pd.read_sql("SELECT nisn, nama, kelas FROM siswa", conn)

    df_siswa = load_siswa()

    st.markdown("### 🔍 Cari Data Siswa")
    options = df_siswa.apply(lambda x: f"{x['nama']} (NISN: {x['nisn']} - {x['kelas']})", axis=1)

    selected_option = st.selectbox(
        "Ketik nama atau NISN Anda:",
        options=options,
        index=None,
        placeholder="Contoh: Akhmad..."
    )

    device_id = "user_device_browser_session"

    if selected_option:
        selected_nisn = selected_option.split('NISN: ')[1].split(' - ')[0]
        user_row = df_siswa[df_siswa['nisn'] == selected_nisn].iloc[0]
        nisn = user_row['nisn']
        nama = user_row['nama']
        kelas = user_row['kelas']

        if device_id in st.session_state.device_lock:
            if st.session_state.device_lock[device_id] != nisn:
                st.error("⚠️ Perangkat ini sudah terkunci untuk akun siswa lain! (Aturan 1 HP 1 Siswa Aktif)")
                st.stop()
        else:
            st.session_state.device_lock[device_id] = nisn

        st.success(f"Login Sesi: **{nama}** ({kelas})")
        st.markdown("---")
        
        st.markdown("### 📍 Verifikasi Lokasi & Waktu")
        use_gps_simulation = st.checkbox("Gunakan Simulasi Koordinat (Untuk Pengujian)", value=True)
        if use_gps_simulation:
            lat_siswa = st.number_input("Latitude Anda", value=LAT_SEKOLAH, format="%.6f")
            lon_siswa = st.number_input("Longitude Anda", value=LON_SEKOLAH, format="%.6f")
        else:
            lat_siswa, lon_siswa = LAT_SEKOLAH, LON_SEKOLAH

        jarak = geodesic((LAT_SEKOLAH, LON_SEKOLAH), (lat_siswa, lon_siswa)).meters
        st.write(f"📏 Jarak Anda dari sekolah: **{jarak:.2f} meter** (Maksimal: {RADIUS_MAX} meter)")

        waktu_sekarang = datetime.now().time()
        tanggal_hari_ini = datetime.now().strftime("%Y-%m-%d")
        st.write(f"⏰ Waktu Server: **{datetime.now().strftime('%H:%M:%S')}** | Tanggal: {tanggal_hari_ini}")

        cursor = conn.cursor()
        cursor.execute("SELECT jam_masuk, status_masuk, jam_pulang, status_pulang FROM absensi WHERE nisn = ? AND tanggal = ?", (nisn, tanggal_hari_ini))
        existing_data = cursor.fetchone()

        st.markdown("---")
        col_masuk, col_pulang = st.columns(2)

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

# ==========================================
# HALAMAN 2: MONITORING WAKASEK KURIKULUM
# ==========================================
elif menu == "Monitoring Wakasek Kurikulum":
    st.markdown("<h2 style='color: #2c3e50;'>📊 Dashboard Monitoring Kehadiran Siswa</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #7f8c8d;'>Khusus Administrator / Wakasek Kurikulum SMKN 1 Lemahsugih</p>", unsafe_allow_html=True)
    st.markdown("---")

    # Autentikasi Password Sederhana untuk Wakasek
    password_input = st.text_input("Masukkan Password Wakasek:", type="password")
    
    # Ganti "kurikulum2026" dengan password rahasia pilihan Anda
    if password_input == "kur2026": 
        st.success("🔓 Login Berhasil! Selamat datang, Wakasek Kurikulum.")
        st.markdown("---")

        # Ambil data rekap dari database
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
            st.info("ℹ️ Belum ada data absensi yang tercatat hari ini.")
        else:
            # Filter Sidebar Tambahan untuk Wakasek
            st.markdown("### 🔍 Filter Data Kehadiran")
            col_f1, col_f2 = st.columns(2)
            
            with col_f1:
                list_tanggal = df_rekap["tanggal"].unique().tolist()
                pilih_tanggal = st.selectbox("Filter Tanggal", ["Semua Tanggal"] + list_tanggal)
            with col_f2:
                list_kelas = df_rekap["kelas"].unique().tolist()
                pilih_kelas = st.selectbox("Filter Kelas", ["Semua Kelas"] + list_kelas)

            # Terapkan filter
            filtered_df = df_rekap.copy()
            if pilih_tanggal != "Semua Tanggal":
                filtered_df = filtered_df[filtered_df["tanggal"] == pilih_tanggal]
            if pilih_kelas != "Semua Kelas":
                filtered_df = filtered_df[filtered_df["kelas"] == pilih_kelas]

            # Metrik Ringkasan Utama
            st.markdown("---")
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
            st.markdown("### 📋 Tabel Rincian Data Kehadiran")
            st.dataframe(filtered_df, use_container_width=True)

            # Tombol Download Laporan Excel/CSV
            csv_data = filtered_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Rekap Kehadiran (CSV/Excel)",
                data=csv_data,
                file_name=f"rekap_absensi_smkn1_{datetime.now().strftime('%Y-%m-%d')}.csv",
                mime="text/csv",
            )
    elif password_input != "":
        st.error("❌ Password salah! Silakan hubungi pengembang aplikasi jika lupa.")
    else:
        st.info("🔒 Silakan masukkan password untuk membuka dashboard monitoring.")