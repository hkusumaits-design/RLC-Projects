import streamlit as st
import numpy as np
from scipy.integrate import solve_ivp
from scipy import signal
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import matplotlib.pyplot as plt
from control import tf, bode, margin
import time

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="Simulator Rangkaian Listrik Interaktif", layout="wide")
st.title("⚡ Simulator Interaktif Rangkaian Listrik")
st.markdown("""
**Eksplorasi respons rangkaian orde 1 (RC/RL) dan orde 2 (RLC) secara interaktif!**
Mahasiswa dapat mempelajari fenomena transien, respons frekuensi, dan konservasi energi.
""")

# ===================================================================
# SIDEBAR - KONFIGURASI UTAMA
# ===================================================================
st.sidebar.header("🔧 Konfigurasi Rangkaian")

# Pilihan orde rangkaian
orde = st.sidebar.selectbox(
    "Orde Rangkaian",
    ["Orde 1 (RC/RL)", "Orde 2 (RLC)"],
    help="Orde 1: RC atau RL. Orde 2: RLC seri atau paralel"
)

# Pilihan jenis rangkaian berdasarkan orde
jenis_orde1 = None
if orde == "Orde 1 (RC/RL)":
    jenis_orde1 = st.sidebar.selectbox(
        "Jenis Rangkaian",
        ["RC", "RL"],
        help="RC: Resistor-Kapasitor, RL: Resistor-Induktor"
    )
    konfigurasi = st.sidebar.selectbox(
        "Konfigurasi",
        ["Seri", "Paralel"],
        help="Seri: komponen terhubung seri. Paralel: komponen terhubung paralel"
    )
else:  # Orde 2
    konfigurasi = st.sidebar.selectbox(
        "Konfigurasi RLC",
        ["Seri", "Paralel"],
        help="Seri: output tegangan kapasitor. Paralel: output arus induktor"
    )

# ===================================================================
# SIDEBAR - PARAMETER KOMPONEN
# ===================================================================
st.sidebar.header("📐 Parameter Komponen")

if orde == "Orde 1 (RC/RL)":
    R = st.sidebar.slider("Resistansi (R) [Ω]", 0.1, 1000.0, 100.0, 0.1)
    
    if jenis_orde1 == "RC":
        C = st.sidebar.slider("Kapasitansi (C) [F]", 0.0001, 0.01, 0.001, 0.0001, format="%.4f")
        L = None  # Tidak digunakan
    else:  # RL
        L = st.sidebar.slider("Induktansi (L) [H]", 0.01, 10.0, 1.0, 0.01)
        C = None  # Tidak digunakan
else:  # Orde 2
    R = st.sidebar.slider("Resistansi (R) [Ω]", 0.1, 100.0, 10.0, 0.1)
    L = st.sidebar.slider("Induktansi (L) [H]", 0.01, 10.0, 1.0, 0.01)
    C = st.sidebar.slider("Kapasitansi (C) [F]", 0.01, 10.0, 1.0, 0.01)

# ===================================================================
# SIDEBAR - SUMBER DAN SIMULASI
# ===================================================================
st.sidebar.header("🎯 Sumber dan Simulasi")

bentuk_sumber = st.sidebar.selectbox(
    "Bentuk Sumber",
    ["Step", "Sinusoidal", "Kotak", "Sawtooth"],
    help="Step: tegangan/arus konstan. Sinusoidal: gelombang sinus. Kotak: gelombang persegi. Sawtooth: gelombang gigi gergaji"
)

if bentuk_sumber == "Step":
    amplitudo = st.sidebar.number_input("Amplitudo Step", 0.0, 100.0, 10.0, 0.1)
    frekuensi = None
    duty_cycle = None
else:
    amplitudo = st.sidebar.number_input("Amplitudo (V/A)", 0.0, 100.0, 10.0, 0.1)
    frekuensi = st.sidebar.slider("Frekuensi (Hz)", 0.1, 10.0, 1.0, 0.1)
    if bentuk_sumber == "Kotak":
        duty_cycle = st.sidebar.slider("Duty Cycle (%)", 10, 90, 50, 5) / 100
    else:
        duty_cycle = None

# FIX: Pastikan t_max konsisten (float)
t_max = st.sidebar.slider("Durasi Simulasi (detik)", 1.0, 50.0, 20.0, 1.0)

# ===================================================================
# SIDEBAR - FITUR TAMBAHAN
# ===================================================================
st.sidebar.header("📊 Fitur Tambahan")
tampilkan_energi = st.sidebar.checkbox("Tampilkan Grafik Energi", value=True)
tampilkan_bode = st.sidebar.checkbox("Tampilkan Bode Plot", value=True)
tampilkan_diagram = st.sidebar.checkbox("Tampilkan Diagram Rangkaian", value=True)
tampilkan_animasi = st.sidebar.checkbox("Tampilkan Animasi Aliran Arus", value=False)
mode_perbandingan = st.sidebar.checkbox("Mode Perbandingan (2 Konfigurasi)", value=False)

# ===================================================================
# FUNGSI - MEMBUAT DIAGRAM RANGKAIAN DENGAN SCHEMDRAW
# ===================================================================
def draw_circuit_diagram(orde, jenis_orde1, konfigurasi, R, L, C):
    """Membuat diagram rangkaian menggunakan schemdraw"""
    try:
        import schemdraw
        from schemdraw import elements as elm
        
        fig = plt.figure(figsize=(8, 5))
        with schemdraw.Drawing() as d:
            d.config(unit=2.5)
            
            if orde == "Orde 1 (RC/RL)":
                if jenis_orde1 == "RC":
                    if konfigurasi == "Seri":
                        d += elm.SourceV().label('Vin', loc='top').up().length(2)
                        d += elm.Resistor().right().label(f'R={R}Ω', loc='top')
                        d += elm.Capacitor().down().label(f'C={C}F', loc='bottom')
                        d += elm.Line().left().length(2)
                        d += elm.Line().right().length(2)
                        d += elm.Dot().label('Vout', loc='right')
                    else:
                        d += elm.SourceV().label('Vin', loc='top').up().length(2)
                        d += elm.Line().right().length(1.5)
                        d += elm.Resistor().down().label(f'R={R}Ω', loc='bottom')
                        d += elm.Line().left().length(1.5)
                        d += elm.Line().right().length(1.5)
                        d += elm.Capacitor().down().label(f'C={C}F', loc='bottom')
                        d += elm.Line().left().length(1.5)
                        d += elm.Dot().label('Vout', loc='right')
                else:
                    if konfigurasi == "Seri":
                        d += elm.SourceV().label('Vin', loc='top').up().length(2)
                        d += elm.Resistor().right().label(f'R={R}Ω', loc='top')
                        d += elm.Inductor().down().label(f'L={L}H', loc='bottom')
                        d += elm.Line().left().length(2)
                        d += elm.Dot().label('Vout', loc='right')
                    else:
                        d += elm.SourceI().label('Iin', loc='top').up().length(2)
                        d += elm.Line().right().length(1.5)
                        d += elm.Resistor().down().label(f'R={R}Ω', loc='bottom')
                        d += elm.Line().left().length(1.5)
                        d += elm.Line().right().length(1.5)
                        d += elm.Inductor().down().label(f'L={L}H', loc='bottom')
                        d += elm.Line().left().length(1.5)
            else:
                if konfigurasi == "Seri":
                    d += elm.SourceV().label('Vin', loc='top').up().length(2.5)
                    d += elm.Resistor().right().label(f'R={R}Ω', loc='top')
                    d += elm.Inductor().right().label(f'L={L}H', loc='top')
                    d += elm.Capacitor().down().label(f'C={C}F', loc='bottom')
                    d += elm.Line().left().length(4)
                    d += elm.Dot().label('Vout', loc='right')
                else:
                    d += elm.SourceI().label('Iin', loc='top').up().length(2.5)
                    d += elm.Line().right().length(1.5)
                    d += elm.Resistor().down().label(f'R={R}Ω', loc='bottom')
                    d += elm.Line().left().length(1.5)
                    d += elm.Line().right().length(1.5)
                    d += elm.Inductor().down().label(f'L={L}H', loc='bottom')
                    d += elm.Line().left().length(1.5)
                    d += elm.Line().right().length(1.5)
                    d += elm.Capacitor().down().label(f'C={C}F', loc='bottom')
                    d += elm.Line().left().length(1.5)
            
            return fig
    except:
        return None

# ===================================================================
# FUNGSI - MEMBUAT SUMBER SINYAL
# ===================================================================
def generate_source(t, bentuk, amplitudo, frekuensi=None, duty_cycle=None):
    """Menghasilkan sinyal sumber sesuai bentuk yang dipilih"""
    if bentuk == "Step":
        return amplitudo * np.ones_like(t)
    elif bentuk == "Sinusoidal":
        if frekuensi is None:
            frekuensi = 1.0
        return amplitudo * np.sin(2 * np.pi * frekuensi * t)
    elif bentuk == "Kotak":
        if frekuensi is None:
            frekuensi = 0.5
        if duty_cycle is None:
            duty_cycle = 0.5
        return amplitudo * signal.square(2 * np.pi * frekuensi * t, duty=duty_cycle)
    else:  # Sawtooth
        if frekuensi is None:
            frekuensi = 0.5
        return amplitudo * signal.sawtooth(2 * np.pi * frekuensi * t)

# ===================================================================
# FUNGSI - SIMULASI RANGKAIAN ORDE 1
# ===================================================================
def simulate_orde1(jenis, konfigurasi, R, C, L, t_max, source_func):
    """Simulasi rangkaian orde 1 (RC atau RL)"""
    t = np.linspace(0, t_max, 2000)
    sumber = source_func(t)
    
    if jenis == "RC":
        if konfigurasi == "Seri":
            tau = R * C
            output = sumber * (1 - np.exp(-t / tau))
            label = "Tegangan Kapasitor (Vc)"
            ylabel = "Tegangan (V)"
        else:
            tau = R * C
            output = sumber * np.exp(-t / tau)
            label = "Tegangan Kapasitor (Vc)"
            ylabel = "Tegangan (V)"
    else:
        if konfigurasi == "Seri":
            tau = L / R
            output = (sumber / R) * (1 - np.exp(-t / tau))
            label = "Arus Induktor (IL)"
            ylabel = "Arus (A)"
        else:
            tau = L / R
            output = sumber * np.exp(-t / tau)
            label = "Arus Induktor (IL)"
            ylabel = "Arus (A)"
    
    return t, sumber, output, label, ylabel, tau

# ===================================================================
# FUNGSI - SIMULASI RANGKAIAN ORDE 2 (RLC)
# ===================================================================
def simulate_rlc(konfigurasi, R, L, C, t_max, source_func):
    """Simulasi rangkaian RLC menggunakan solve_ivp"""
    t = np.linspace(0, t_max, 2000)
    sumber = source_func(t)
    
    if konfigurasi == "Seri":
        def rlc_seri_ode(t, y):
            v_c, i = y
            source_val = source_func(np.array([t]))[0]
            dv_c_dt = i / C
            di_dt = (source_val - v_c - R * i) / L
            return [dv_c_dt, di_dt]
        
        y0 = [0, 0]
        t_span = (0, t_max)
        sol = solve_ivp(rlc_seri_ode, t_span, y0, t_eval=t, method='RK45')
        output = sol.y[0]
        v_c = output
        i = np.gradient(v_c, t) * C
        label = "Tegangan Kapasitor (Vc)"
        ylabel = "Tegangan (V)"
        alpha = R / (2 * L)
    else:
        def rlc_paralel_ode(t, y):
            v, i_L = y
            source_val = source_func(np.array([t]))[0]
            dv_dt = (source_val - i_L - v/R) / C
            di_dt = v / L
            return [dv_dt, di_dt]
        
        y0 = [0, 0]
        t_span = (0, t_max)
        sol = solve_ivp(rlc_paralel_ode, t_span, y0, t_eval=t, method='RK45')
        output = sol.y[1]
        i = output
        v_c = np.gradient(i, t) * L
        label = "Arus Induktor (IL)"
        ylabel = "Arus (A)"
        alpha = 1 / (2 * R * C)
    
    omega_0 = 1 / np.sqrt(L * C)
    
    return t, sumber, output, label, ylabel, v_c, i, alpha, omega_0

# ===================================================================
# FUNGSI - FUNGSI TRANSFER UNTUK BODE PLOT
# ===================================================================
def get_transfer_function(orde, jenis_orde1, konfigurasi, R, L, C):
    """Mendapatkan fungsi transfer untuk Bode plot"""
    if orde == "Orde 1 (RC/RL)":
        if jenis_orde1 == "RC":
            num = [1]
            den = [R*C, 1]
        else:
            if konfigurasi == "Seri":
                num = [1/R]
                den = [L/R, 1]
            else:
                num = [1]
                den = [L/R, 1]
    else:
        if konfigurasi == "Seri":
            num = [1]
            den = [L*C, R*C, 1]
        else:
            num = [1]
            den = [L*C, L/R, 1]
    
    return tf(num, den)

# ===================================================================
# FUNGSI - ENERGI
# ===================================================================
def calculate_energy(t, v_c, i, R, L, C, orde, jenis_orde1, konfigurasi):
    """Menghitung energi di kapasitor dan induktor"""
    if orde == "Orde 1 (RC/RL)":
        if jenis_orde1 == "RC":
            energi_c = 0.5 * C * v_c**2
            energi_l = np.zeros_like(t)
            total_energi = energi_c
        else:
            energi_c = np.zeros_like(t)
            energi_l = 0.5 * L * i**2
            total_energi = energi_l
    else:
        energi_c = 0.5 * C * v_c**2
        energi_l = 0.5 * L * i**2
        total_energi = energi_c + energi_l
    
    return energi_c, energi_l, total_energi

# ===================================================================
# FUNGSI - ANIMASI ALIRAN ARUS
# ===================================================================
def create_animation_frame(t, sumber, output, frame_idx, total_frames=100):
    """Membuat frame animasi untuk aliran arus"""
    idx = int(frame_idx * len(t) / total_frames)
    if idx >= len(t):
        idx = len(t) - 1
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(x=t[:idx], y=sumber[:idx], 
                            mode='lines', name='Sumber',
                            line=dict(color='purple', width=3)))
    fig.add_trace(go.Scatter(x=t[:idx], y=output[:idx], 
                            mode='lines', name='Output',
                            line=dict(color='blue', width=3)))
    
    fig.add_trace(go.Scatter(x=[t[idx]], y=[sumber[idx]], 
                            mode='markers', name='Arus',
                            marker=dict(color='red', size=15, symbol='arrow-right')))
    
    fig.update_layout(
        title=f"Animasi Aliran Arus (t = {t[idx]:.2f} s)",
        xaxis_title="Waktu (s)",
        yaxis_title="Amplitudo",
        height=400,
        showlegend=True
    )
    
    return fig

# ===================================================================
# FUNGSI - PERBANDINGAN DUA KONFIGURASI
# ===================================================================
def compare_configurations(orde, jenis_orde1, R, L, C, t_max, source_func):
    """Membandingkan dua konfigurasi dalam satu grafik"""
    t = np.linspace(0, t_max, 2000)
    
    if orde == "Orde 1 (RC/RL)":
        _, _, output_seri, label_seri, _, _ = simulate_orde1(
            jenis_orde1, "Seri", R, C, L, t_max, source_func
        )
        _, _, output_paralel, label_paralel, _, _ = simulate_orde1(
            jenis_orde1, "Paralel", R, C, L, t_max, source_func
        )
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t, y=output_seri, mode='lines', 
                                name=f'{label_seri} (Seri)', 
                                line=dict(color='blue', width=2)))
        fig.add_trace(go.Scatter(x=t, y=output_paralel, mode='lines', 
                                name=f'{label_paralel} (Paralel)', 
                                line=dict(color='red', width=2, dash='dash')))
        fig.update_layout(
            title=f"Perbandingan Rangkaian {jenis_orde1} Seri vs Paralel",
            xaxis_title="Waktu (s)",
            yaxis_title="Respons",
            height=450
        )
    else:
        _, _, output_seri, label_seri, _, _, _, _, _ = simulate_rlc(
            "Seri", R, L, C, t_max, source_func
        )
        _, _, output_paralel, label_paralel, _, _, _, _, _ = simulate_rlc(
            "Paralel", R, L, C, t_max, source_func
        )
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t, y=output_seri, mode='lines', 
                                name=f'{label_seri} (Seri)', 
                                line=dict(color='blue', width=2)))
        fig.add_trace(go.Scatter(x=t, y=output_paralel, mode='lines', 
                                name=f'{label_paralel} (Paralel)', 
                                line=dict(color='red', width=2, dash='dash')))
        fig.update_layout(
            title="Perbandingan RLC Seri vs Paralel",
            xaxis_title="Waktu (s)",
            yaxis_title="Respons",
            height=450
        )
    
    return fig

# ===================================================================
# MAIN APP - EKSEKUSI SIMULASI
# ===================================================================

# Buat fungsi sumber
if bentuk_sumber == "Step":
    source_func = lambda t: generate_source(t, "Step", amplitudo)
elif bentuk_sumber == "Sinusoidal":
    source_func = lambda t: generate_source(t, "Sinusoidal", amplitudo, frekuensi)
elif bentuk_sumber == "Kotak":
    source_func = lambda t: generate_source(t, "Kotak", amplitudo, frekuensi, duty_cycle)
else:
    source_func = lambda t: generate_source(t, "Sawtooth", amplitudo, frekuensi)

# Jalankan simulasi sesuai orde
if orde == "Orde 1 (RC/RL)":
    t, sumber, output, label, ylabel, tau = simulate_orde1(
        jenis_orde1, konfigurasi, R, C, L, t_max, source_func
    )
    v_c = output if jenis_orde1 == "RC" else np.zeros_like(t)
    i = output if jenis_orde1 == "RL" else np.zeros_like(t)
    alpha = None
    omega_0 = None
    zeta = None
else:
    t, sumber, output, label, ylabel, v_c, i, alpha, omega_0 = simulate_rlc(
        konfigurasi, R, L, C, t_max, source_func
    )
    tau = None
    zeta = alpha / omega_0 if omega_0 > 0 else 0

# ===================================================================
# TAMPILAN - INFORMASI RINGKAS
# ===================================================================
col_title1, col_title2, col_title3, col_title4 = st.columns(4)

with col_title1:
    st.metric("Orde Rangkaian", orde.replace("Orde ", ""))

with col_title2:
    if orde == "Orde 1 (RC/RL)":
        st.metric("Jenis", f"{jenis_orde1} {konfigurasi}")
    else:
        st.metric("Konfigurasi", f"RLC {konfigurasi}")

with col_title3:
    if orde == "Orde 1 (RC/RL)":
        if jenis_orde1 == "RC":
            st.metric("τ (Konstanta Waktu)", f"{tau:.4f} s")
        else:
            st.metric("τ (Konstanta Waktu)", f"{tau:.4f} s")
    else:
        st.metric("ω₀ (Frekuensi Natural)", f"{omega_0:.4f} rad/s")

with col_title4:
    if orde == "Orde 1 (RC/RL)":
        if jenis_orde1 == "RC":
            st.metric("ωc (Cut-off)", f"{1/tau:.4f} rad/s")
        else:
            st.metric("ωc (Cut-off)", f"{1/tau:.4f} rad/s")
    else:
        st.metric("ζ (Koef. Redaman)", f"{zeta:.4f}")

# ===================================================================
# TAMPILAN - GRAFIK RESPON
# ===================================================================
st.subheader("📊 Respons Rangkaian")

col1, col2 = st.columns(2)

with col1:
    fig_input = go.Figure()
    fig_input.add_trace(go.Scatter(x=t, y=sumber, mode='lines', name='Sumber', 
                                   line=dict(color='purple', width=2)))
    fig_input.update_layout(
        title=f"Sinyal Input - {bentuk_sumber}",
        xaxis_title="Waktu (s)",
        yaxis_title="Amplitudo",
        height=300,
        hovermode='x unified'
    )
    st.plotly_chart(fig_input, use_container_width=True)

with col2:
    fig_output = go.Figure()
    fig_output.add_trace(go.Scatter(x=t, y=output, mode='lines', name='Output', 
                                    line=dict(color='blue', width=2)))
    fig_output.update_layout(
        title=f"Respons Output ({label})",
        xaxis_title="Waktu (s)",
        yaxis_title=ylabel,
        height=300,
        hovermode='x unified'
    )
    st.plotly_chart(fig_output, use_container_width=True)

# Grafik gabungan
st.subheader(f"📈 Respons Gabungan")
fig_combined = go.Figure()
fig_combined.add_trace(go.Scatter(x=t, y=sumber, mode='lines', name='Sumber', 
                                  line=dict(color='purple', width=2)))
fig_combined.add_trace(go.Scatter(x=t, y=output, mode='lines', name=label, 
                                  line=dict(color='blue', width=2)))
fig_combined.update_layout(
    title="Perbandingan Input vs Output",
    xaxis_title="Waktu (s)",
    yaxis_title="Amplitudo",
    height=400,
    hovermode='x unified'
)
st.plotly_chart(fig_combined, use_container_width=True)

# ===================================================================
# TAMPILAN - MODE PERBANDINGAN
# ===================================================================
if mode_perbandingan:
    st.subheader("🔄 Perbandingan Konfigurasi Seri vs Paralel")
    fig_compare = compare_configurations(orde, jenis_orde1, R, L, C, t_max, source_func)
    st.plotly_chart(fig_compare, use_container_width=True)
    
    with st.expander("📖 Interpretasi Perbandingan"):
        st.markdown("""
        **Perbedaan Utama Seri vs Paralel:**
        
        - **Rangkaian Seri:** Komponen terhubung secara berurutan. Arus yang mengalir sama, tegangan terbagi.
        - **Rangkaian Paralel:** Komponen terhubung secara bercabang. Tegangan sama, arus terbagi.
        
        **Konsekuensi pada Respons:**
        - **Seri:** Respons cenderung lebih lambat karena efek induktansi/kapasitansi kumulatif.
        - **Paralel:** Respons lebih cepat karena jalur arus alternatif.
        """)

# ===================================================================
# TAMPILAN - DIAGRAM RANGKAIAN
# ===================================================================
if tampilkan_diagram:
    st.subheader("🔌 Diagram Rangkaian")
    
    try:
        import schemdraw
        from schemdraw import elements as elm
        fig = draw_circuit_diagram(orde, jenis_orde1, konfigurasi, R, L, C)
        if fig is not None:
            st.pyplot(fig)
        else:
            raise Exception("Schemdraw gagal")
    except:
        st.info("🖼️ Menampilkan diagram referensi dari Wikipedia")
        
        col_diag1, col_diag2 = st.columns(2)
        
        if orde == "Orde 1 (RC/RL)":
            if jenis_orde1 == "RC":
                if konfigurasi == "Seri":
                    with col_diag1:
                        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/6d/RC_series.svg/1200px-RC_series.svg.png", 
                                caption=f"Rangkaian RC Seri\nR = {R}Ω, C = {C}F", width=300)
                    with col_diag2:
                        st.latex(r"v_c(t) = V(1 - e^{-t/RC})")
                        st.latex(rf"\tau = RC = {R*C:.4f} s")
                else:
                    with col_diag1:
                        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/RC_parallel.svg/1200px-RC_parallel.svg.png", 
                                caption=f"Rangkaian RC Paralel\nR = {R}Ω, C = {C}F", width=300)
                    with col_diag2:
                        st.latex(r"v_c(t) = V \cdot e^{-t/RC}")
                        st.latex(rf"\tau = RC = {R*C:.4f} s")
            else:
                if konfigurasi == "Seri":
                    with col_diag1:
                        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/RL_series.svg/1200px-RL_series.svg.png", 
                                caption=f"Rangkaian RL Seri\nR = {R}Ω, L = {L}H", width=300)
                    with col_diag2:
                        st.latex(r"i_L(t) = \frac{V}{R}(1 - e^{-Rt/L})")
                        st.latex(rf"\tau = L/R = {L/R:.4f} s")
                else:
                    with col_diag1:
                        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/RL_parallel.svg/1200px-RL_parallel.svg.png", 
                                caption=f"Rangkaian RL Paralel\nR = {R}Ω, L = {L}H", width=300)
                    with col_diag2:
                        st.latex(r"i_L(t) = I \cdot e^{-Rt/L}")
                        st.latex(rf"\tau = L/R = {L/R:.4f} s")
        else:
            if konfigurasi == "Seri":
                with col_diag1:
                    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/9/93/RLC_series_circuit.svg/1200px-RLC_series_circuit.svg.png", 
                            caption=f"Rangkaian RLC Seri\nR={R}Ω, L={L}H, C={C}F", width=300)
                with col_diag2:
                    st.latex(r"v_c(t) = V(1 - e^{-\alpha t}(\cos(\omega_d t) + \frac{\alpha}{\omega_d}\sin(\omega_d t)))")
                    st.latex(rf"\omega_0 = {omega_0:.4f} rad/s")
                    st.latex(rf"\alpha = {alpha:.4f}")
            else:
                with col_diag1:
                    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/a/a1/RLC_parallel_circuit.svg/1200px-RLC_parallel_circuit.svg.png", 
                            caption=f"Rangkaian RLC Paralel\nR={R}Ω, L={L}H, C={C}F", width=300)
                with col_diag2:
                    st.latex(r"i_L(t) = I(1 - e^{-\alpha t}(\cos(\omega_d t) + \frac{\alpha}{\omega_d}\sin(\omega_d t)))")
                    st.latex(rf"\omega_0 = {omega_0:.4f} rad/s")
                    st.latex(rf"\alpha = {alpha:.4f}")

# ===================================================================
# TAMPILAN - GRAFIK ENERGI
# ===================================================================
if tampilkan_energi:
    st.subheader("⚡ Energi dalam Rangkaian")
    
    energi_c, energi_l, total_energi = calculate_energy(t, v_c, i, R, L, C, orde, jenis_orde1, konfigurasi)
    
    fig_energi = go.Figure()
    
    if np.any(energi_c > 1e-10):
        fig_energi.add_trace(go.Scatter(x=t, y=energi_c, mode='lines', 
                                       name='Energi Kapasitor', line=dict(color='green', width=2)))
    if np.any(energi_l > 1e-10):
        fig_energi.add_trace(go.Scatter(x=t, y=energi_l, mode='lines', 
                                       name='Energi Induktor', line=dict(color='orange', width=2)))
    if np.any(total_energi > 1e-10):
        fig_energi.add_trace(go.Scatter(x=t, y=total_energi, mode='lines', 
                                       name='Total Energi', line=dict(color='red', width=2, dash='dash')))
    
    fig_energi.update_layout(
        title="Energi dalam Rangkaian",
        xaxis_title="Waktu (s)",
        yaxis_title="Energi (Joule)",
        height=350,
        hovermode='x unified'
    )
    st.plotly_chart(fig_energi, use_container_width=True)
    
    with st.expander("📖 Interpretasi Energi"):
        st.markdown("""
        **Konservasi Energi dalam Rangkaian:**
        
        - **Energi Kapasitor:** $E_C = \frac{1}{2}CV^2$
        - **Energi Induktor:** $E_L = \frac{1}{2}LI^2$
        - **Total Energi:** $E_{total} = E_C + E_L$
        
        **Pengamatan:**
        - Pada rangkaian RC, energi hanya disimpan di kapasitor dan didisipasi oleh resistor.
        - Pada rangkaian RLC, energi berpindah antara kapasitor dan induktor (osilasi).
        - Total energi berkurang seiring waktu karena disipasi oleh resistor.
        """)

# ===================================================================
# TAMPILAN - BODE PLOT
# ===================================================================
if tampilkan_bode:
    st.subheader("📈 Bode Plot (Respons Frekuensi)")
    
    try:
        sys = get_transfer_function(orde, jenis_orde1, konfigurasi, R, L, C)
        mag, phase, omega = bode(sys, plot=False)
        freq_hz = omega / (2 * np.pi)
        
        fig_bode = make_subplots(rows=2, cols=1, 
                                 subplot_titles=("Magnitude", "Phase"),
                                 shared_xaxes=True)
        
        fig_bode.add_trace(go.Scatter(x=freq_hz, y=mag, mode='lines', 
                                     name='Magnitude', line=dict(color='blue', width=2)),
                          row=1, col=1)
        
        fig_bode.add_trace(go.Scatter(x=freq_hz, y=phase * 180 / np.pi, mode='lines', 
                                     name='Phase', line=dict(color='red', width=2)),
                          row=2, col=1)
        
        fig_bode.update_xaxes(title_text="Frekuensi (Hz)", row=2, col=1, type="log")
        fig_bode.update_yaxes(title_text="Magnitude (dB)", row=1, col=1)
        fig_bode.update_yaxes(title_text="Phase (derajat)", row=2, col=1)
        fig_bode.update_layout(height=500, hovermode='x unified')
        
        st.plotly_chart(fig_bode, use_container_width=True)
        
        try:
            gm, pm, wgm, wpm = margin(sys)
            col_gm, col_pm = st.columns(2)
            with col_gm:
                st.metric("Gain Margin", f"{20*np.log10(gm):.2f} dB" if gm > 0 else "∞")
            with col_pm:
                st.metric("Phase Margin", f"{pm:.2f}°")
        except:
            st.caption("ℹ️ Margin tidak dapat dihitung untuk sistem ini")
            
    except Exception as e:
        st.warning(f"⚠️ Bode plot tidak dapat ditampilkan: {str(e)}")
        st.info("💡 Pastikan library 'control' telah terinstal dengan benar")

# ===================================================================
# TAMPILAN - ANIMASI ALIRAN ARUS
# ===================================================================
if tampilkan_animasi:
    st.subheader("🎬 Animasi Aliran Arus")
    st.info("💡 Animasi menunjukkan bagaimana sinyal merambat dari input ke output seiring waktu")
    
    frame = st.slider("Waktu Simulasi", 0.0, float(t_max), 0.0, 0.1)
    idx = int(frame * len(t) / t_max)
    if idx >= len(t):
        idx = len(t) - 1
    
    fig_anim = create_animation_frame(t, sumber, output, idx, len(t))
    st.plotly_chart(fig_anim, use_container_width=True)

# ===================================================================
# TAMPILAN - ANALISIS RESPONS
# ===================================================================
st.subheader("🔍 Analisis Respons")

if orde == "Orde 1 (RC/RL)":
    st.info(f"**Rangkaian Orde 1**\n\n{jenis_orde1} {konfigurasi}")
    
    col_info1, col_info2, col_info3 = st.columns(3)
    
    with col_info1:
        st.metric("Konstanta Waktu (τ)", f"{tau:.4f} s")
    
    with col_info2:
        st.metric("Frekuensi Cut-off (ωc)", f"{1/tau:.4f} rad/s")
    
    with col_info3:
        # Waktu mencapai steady-state (5τ)
        st.metric("Waktu Steady-State", f"{5*tau:.4f} s")
else:
    # Analisis untuk orde 2
    col_info1, col_info2, col_info3 = st.columns(3)
    
    with col_info1:
        if alpha < omega_0:
            st.success("**Kondisi: Underdamped (Osilasi)**")
            st.latex(rf"\alpha = {alpha:.4f} < \omega_0 = {omega_0:.4f}")
        elif alpha > omega_0:
            st.warning("**Kondisi: Overdamped**")
            st.latex(rf"\alpha = {alpha:.4f} > \omega_0 = {omega_0:.4f}")
        else:
            st.info("**Kondisi: Critically Damped**")
            st.latex(rf"\alpha = {alpha:.4f} = \omega_0 = {omega_0:.4f}")
    
    with col_info2:
        st.metric("Frekuensi Natural (ω₀)", f"{omega_0:.4f} rad/s")
    
    with col_info3:
        st.metric("Koefisien Redaman (ζ)", f"{zeta:.4f}")

# ===================================================================
# TAMPILAN - EKSPOR DATA
# ===================================================================
st.subheader("📥 Ekspor Data")

df = pd.DataFrame({
    'Waktu (s)': t,
    'Sumber': sumber,
    'Output': output,
    'Tegangan Kapasitor (V)': v_c,
    'Arus (A)': i
})

if tampilkan_energi:
    energi_c, energi_l, total_energi = calculate_energy(t, v_c, i, R, L, C, orde, jenis_orde1, konfigurasi)
    df['Energi Kapasitor (J)'] = energi_c
    df['Energi Induktor (J)'] = energi_l
    df['Total Energi (J)'] = total_energi

csv = df.to_csv(index=False)
st.download_button(
    label="📥 Download Data Simulasi (CSV)",
    data=csv,
    file_name="simulasi_rangkaian.csv",
    mime="text/csv"
)

# ===================================================================
# TEORI SINGKAT
# ===================================================================
with st.expander("📖 Teori Singkat"):
    if orde == "Orde 1 (RC/RL)":
        if jenis_orde1 == "RC":
            st.markdown(f"""
            ### Rangkaian Orde 1: RC {konfigurasi}
            
            **Persamaan Diferensial:**
            - **RC Seri:** $v_c(t) = V(1 - e^{{-t/RC}})$
            - **RC Paralel:** $v_c(t) = V \\cdot e^{{-t/RC}}$
            
            **Konstanta Waktu (τ):**
            - $\\tau = RC = {R*C:.4f} s$
            
            **Frekuensi Cut-off:** $\\omega_c = \\frac{{1}}{{\\tau}} = {1/tau:.4f} rad/s$
            
            **Interpretasi:** Konstanta waktu menentukan seberapa cepat respons mencapai steady-state. 
            Setelah 5τ, respons dianggap telah mencapai steady-state (99.3%).
            
            **Komponen:**
            - Resistor (R) = {R} Ω
            - Kapasitor (C) = {C} F
            """)
        else:  # RL
            st.markdown(f"""
            ### Rangkaian Orde 1: RL {konfigurasi}
            
            **Persamaan Diferensial:**
            - **RL Seri:** $i_L(t) = \\frac{{V}}{{R}}(1 - e^{{-Rt/L}})$
            - **RL Paralel:** $i_L(t) = I \\cdot e^{{-Rt/L}}$
            
            **Konstanta Waktu (τ):**
            - $\\tau = \\frac{{L}}{{R}} = {L/R:.4f} s$
            
            **Frekuensi Cut-off:** $\\omega_c = \\frac{{1}}{{\\tau}} = {1/tau:.4f} rad/s$
            
            **Interpretasi:** Konstanta waktu menentukan seberapa cepat respons mencapai steady-state. 
            Setelah 5τ, respons dianggap telah mencapai steady-state (99.3%).
            
            **Komponen:**
            - Resistor (R) = {R} Ω
            - Induktor (L) = {L} H
            """)
    else:  # Orde 2 RLC
        st.markdown(f"""
        ### Rangkaian Orde 2: RLC {konfigurasi}
        
        **Persamaan Diferensial:**
        - **RLC Seri:** $\\frac{{d^2v_c}}{{dt^2}} + \\frac{{R}}{{L}}\\frac{{dv_c}}{{dt}} + \\frac{{1}}{{LC}}v_c = \\frac{{V_{{step}}}}{{LC}}$
        - **RLC Paralel:** $\\frac{{d^2i_L}}{{dt^2}} + \\frac{{1}}{{RC}}\\frac{{di_L}}{{dt}} + \\frac{{1}}{{LC}}i_L = \\frac{{1}}{{LC}}I_{{step}}$
        
        **Parameter:**
        - **Frekuensi Natural:** $\\omega_0 = \\frac{{1}}{{\\sqrt{{LC}}}} = {omega_0:.4f} rad/s$
        - **Koefisien Redaman:** $\\alpha = {alpha:.4f}$
        - **Koefisien Redaman (ζ):** $\\zeta = \\frac{{\\alpha}}{{\\omega_0}} = {zeta:.4f}$
        
        **Kondisi Respons:**
        - **Underdamped** ($\\alpha < \\omega_0$): Respons berosilasi sebelum mencapai steady-state
        - **Critically Damped** ($\\alpha = \\omega_0$): Respons tercepat tanpa osilasi
        - **Overdamped** ($\\alpha > \\omega_0$): Respons lambat tanpa osilasi
        
        **Komponen:**
        - Resistor (R) = {R} Ω
        - Induktor (L) = {L} H
        - Kapasitor (C) = {C} F
        """)

st.markdown("---")
st.caption("⚡ Dibuat untuk pembelajaran mahasiswa | Simulator Rangkaian Listrik Interaktif")
