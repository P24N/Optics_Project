import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

st.set_page_config(page_title="Automotive Anti-Glare Optical Simulator", layout="wide")
st.title("Automotive Polarization & Anti-Glare Optical Testbench")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("1. Optical Architecture")
filter_mode = st.sidebar.radio(
    "Select Receiver Filter:",
    ["1. Raw Unfiltered (High Beam)",
     "2. Linear Polarizer (45°/135°)",
     "3. Interior CP (Windshield Stress)",
     "4. Single-Stage Exterior CP",
     "5. Dual-Stage Analyzer (CP + Vert LP)"]
)

st.sidebar.header("2. Dynamic Road & Vehicle State")
car_dist = st.sidebar.slider("Oncoming Vehicle Distance (m)", 15.0, 90.0, 50.0, step=1.0)
roll_deg = st.sidebar.slider("Vehicle Roll / Bank Angle (°)", -30.0, 30.0, 12.0, step=1.0)
pvb_stress = st.sidebar.slider("Windshield PVB Retardance (×π rad)", 0.0, 0.50, 0.25, step=0.01)
wetness_factor = st.sidebar.slider("Road Surface Wetness (Brewster Glare)", 0.0, 1.0, 0.85, step=0.05)

# --- JONES CALCULUS & TRANSMISSION ENGINE ---
roll_rad = np.radians(roll_deg)
delta_rad = pvb_stress * np.pi

if "1. Raw" in filter_mode:
    t_direct, t_specular, t_diffuse = 1.0, 1.0, 1.0
elif "2. Linear" in filter_mode:
    t_direct = np.sin(roll_rad)**2 + 0.001
    t_specular = 0.5 * (np.cos(np.pi/4 + roll_rad)**2)
    t_diffuse = 0.50
elif "3. Interior CP" in filter_mode:
    # PVB stress converts RCP to elliptical, leaking sin^2(delta/2)
    t_direct = np.sin(delta_rad / 2.0)**2 + 0.001
    t_specular = np.cos(delta_rad / 2.0)**2
    t_diffuse = 0.50
elif "4. Single-Stage" in filter_mode:
    t_direct = 0.001  # Extinguished before hitting windshield
    t_specular = 1.0  # RCP flips to LCP on wet bounce and leaks
    t_diffuse = 0.50
else:  # 5. Dual-Stage Analyzer
    t_direct = 0.001
    t_specular = 0.005  # Vertical LP blocks horizontal Brewster reflection
    t_diffuse = 0.25

# --- SPATIAL & POV FIELD COMPUTATION ---
obs_x, obs_y = 1.8, 1.2
source_x, source_h, source_I = -2.5, 0.65, 80000

az_deg = np.linspace(-22, 22, 300)
el_deg = np.linspace(-16, 8, 220)
AZ, EL = np.meshgrid(np.radians(az_deg), np.radians(el_deg))

Z_road = np.where(EL < -1e-3, -obs_y / np.tan(EL), np.nan)
X_road = np.where(EL < -1e-3, obs_x + Z_road * np.tan(AZ), np.nan)
valid = (Z_road >= 6.0) & (Z_road <= 100.0) & (np.abs(X_road) <= 9.0)

dx = np.where(valid, X_road - source_x, np.nan)
dz = np.where(valid, Z_road - car_dist, np.nan)
r_sq = dx**2 + source_h**2 + dz**2
beam = np.exp(-((np.arctan2(dx, -dz)) / 0.24)**2)
diffuse_lux = np.where(valid, (2 * source_I * beam / r_sq) * (source_h / np.sqrt(r_sq)), 0.0)

# Specular wet road reflection
r_in = np.sqrt(r_sq)
r_out = np.sqrt((obs_x - X_road)**2 + obs_y**2 + Z_road**2)
cos_spec = np.clip(np.where(valid, (dx*(obs_x - X_road) + source_h*obs_y - dz*Z_road)/(r_in*r_out), 0.0), 0.0, 1.0)
fresnel = 0.02 + 0.98 * (1.0 - (source_h / r_in))**5
wet_patch = wetness_factor * np.exp(-((Z_road - (car_dist * 0.65)) / 14)**2)
spec_lux = np.where(valid, (2 * source_I * fresnel / (r_in + r_out)**2) * (cos_spec**30) * wet_patch, 0.0)

# Direct bulb glare
az_bulb = np.arctan2(source_x - obs_x, car_dist)
el_bulb = np.arctan2(source_h - obs_y, car_dist)
raw_eye_lux = (2 * source_I) / (car_dist**2 + (source_x - obs_x)**2)
direct_bloom = raw_eye_lux * np.exp(-((AZ - az_bulb)**2 + (EL - el_bulb)**2) / (np.radians(1.3))**2)

pov_scene = (t_diffuse * diffuse_lux) + (t_specular * spec_lux) + (t_direct * direct_bloom)
eye_glare_now = raw_eye_lux * t_direct
peak_road_glare = np.nanmax(t_specular * spec_lux)

# --- METRICS ROW ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Direct Eye Glare", f"{eye_glare_now:.3f} lx", f"{-100*(1-t_direct):.1f}% vs Raw")
c2.metric("Peak Wet-Road Glare", f"{peak_road_glare:.2f} lx")
c3.metric("Optical Extinction", f"{-10*np.log10(max(t_direct, 1e-4)):.1f} dB")
status = "SAFE (< 1.0 lx)" if (eye_glare_now < 1.0 and peak_road_glare < 5.0) else "GLARE HAZARD"
c4.metric("Driver Vision Status", status)

# --- PLOTS ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), gridspec_kw={'width_ratios': [2.2, 1]}, layout='constrained')

im = ax1.pcolormesh(az_deg, el_deg, np.clip(pov_scene, 0.05, 150), cmap='inferno', norm=LogNorm(vmin=0.05, vmax=150), shading='auto')
ax1.axhline(0, color='cyan', linestyle=':', alpha=0.5)
for lx in [-4.5, 0.0, 4.5]:
    z_l = np.linspace(6, 100, 80)
    ax1.plot(np.degrees(np.arctan2(lx - obs_x, z_l)), np.degrees(np.arctan2(-obs_y, z_l)), 'w--', alpha=0.35)
ax1.set_xlim(-22, 22); ax1.set_ylim(-16, 8)
ax1.set_title(f"Live Driver Windshield POV ({filter_mode})", fontweight='bold')
ax1.set_xlabel("Horizontal Field of View (°)"); ax1.set_ylabel("Vertical Field of View (°)")
fig.colorbar(im, ax=ax1, label="Retinal Illuminance (Lux)")

# Polarization State Ellipse after Windshield
t_p = np.linspace(0, 2*np.pi, 200)
Ex = np.cos(t_p)
Ey = np.sin(t_p - (delta_rad if "3. Interior" in filter_mode else 0.0))
ax2.plot(Ex, Ey, color='dodgerblue', lw=2.5, label='Wave State at Analyzer')
ax2.set_xlim(-1.3, 1.3); ax2.set_ylim(-1.3, 1.3); ax2.set_aspect('equal')
ax2.grid(True, linestyle=':')
ax2.set_title("Incident Polarization Ellipse", fontweight='bold')
ax2.set_xlabel("$E_x$ Amplitude"); ax2.set_ylabel("$E_y$ Amplitude")
ax2.legend(loc='lower right')

st.pyplot(fig)