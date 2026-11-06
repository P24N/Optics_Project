import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.colors import LogNorm

# ==========================================
# 1. EXACT JONES CALCULUS MATRIX FUNCTIONS
# ==========================================
def rotation_matrix(theta_rad):
    c, s = np.cos(theta_rad), np.sin(theta_rad)
    return np.array([[c, s], [-s, c]], dtype=complex)

def linear_polarizer(angle_rad):
    R = rotation_matrix(angle_rad)
    R_inv = rotation_matrix(-angle_rad)
    lp_0 = np.array([[1, 0], [0, 0]], dtype=complex)
    return R_inv @ lp_0 @ R

def quarter_wave_plate(fast_axis_rad):
    R = rotation_matrix(fast_axis_rad)
    R_inv = rotation_matrix(-fast_axis_rad)
    qwp_0 = np.array([[np.exp(1j * np.pi / 4), 0],
                      [0, np.exp(-1j * np.pi / 4)]], dtype=complex)
    return R_inv @ qwp_0 @ R

def birefringent_medium(retardance_delta, fast_axis_rad=np.pi / 6):
    R = rotation_matrix(fast_axis_rad)
    R_inv = rotation_matrix(-fast_axis_rad)
    ret_0 = np.array([[np.exp(1j * retardance_delta / 2), 0],
                      [0, np.exp(-1j * retardance_delta / 2)]], dtype=complex)
    return R_inv @ ret_0 @ R

def compute_intensity(E_field):
    return float(np.real(np.vdot(E_field, E_field)))

# Incident RCP Wave & Analyzer Setup
E_RCP = (1.0 / np.sqrt(2.0)) * np.array([1.0, -1j], dtype=complex)
J_analyzer = linear_polarizer(np.pi / 4) @ quarter_wave_plate(0.0)
J_windshield = birefringent_medium(retardance_delta=0.25 * np.pi)

# ==========================================
# 2. STATIC CAMERA POV ROAD GRID
# ==========================================
obs_x, obs_y = 1.8, 1.2
source_x, source_h, source_I = -2.5, 0.65, 80000

az_deg = np.linspace(-22, 22, 220)
el_deg = np.linspace(-16, 8, 160)
AZ, EL = np.meshgrid(np.radians(az_deg), np.radians(el_deg))

Z_road = np.where(EL < -1e-3, -obs_y / np.tan(EL), np.nan)
X_road = np.where(EL < -1e-3, obs_x + Z_road * np.tan(AZ), np.nan)
valid = (Z_road >= 6.0) & (Z_road <= 100.0) & (np.abs(X_road) <= 9.0)

r_out = np.sqrt((obs_x - X_road)**2 + obs_y**2 + Z_road**2)

def compute_frame_fields(car_z, roll_rad):
    # Matrix transmission calculation for current vehicle roll angle
    R_t, R_t_inv = rotation_matrix(roll_rad), rotation_matrix(-roll_rad)
    J_tilted = R_t_inv @ J_analyzer @ R_t
    
    # Interior vs Exterior Jones intensity evaluation
    t_int_direct = compute_intensity(J_tilted @ J_windshield @ E_RCP) + 0.001
    t_ext_direct = compute_intensity(J_windshield @ J_tilted @ E_RCP) + 0.001
    
    # Road Illumination
    dx = np.where(valid, X_road - source_x, np.nan)
    dz = np.where(valid, Z_road - car_z, np.nan)
    r_sq = dx**2 + source_h**2 + dz**2
    r_in = np.sqrt(r_sq)
    
    beam = np.exp(-((np.arctan2(dx, -dz)) / 0.24)**2)
    diffuse = np.where(valid, (2 * source_I * beam / r_sq) * (source_h / r_in), 0.0)
    
    # Specular Wet Road Reflection
    cos_spec = np.clip(np.where(valid, (dx*(obs_x - X_road) + source_h*obs_y - dz*Z_road)/(r_in*r_out), 0.0), 0.0, 1.0)
    fresnel = 0.02 + 0.98 * (1.0 - (source_h / r_in))**5
    wet_patch = np.exp(-((Z_road - (car_z * 0.62)) / 14)**2)
    specular = np.where(valid, (2 * source_I * fresnel / (r_in + r_out)**2) * (cos_spec**30) * wet_patch, 0.0)
    
    # Direct Headlamp Bloom in Windshield
    az_bulb = np.arctan2(source_x - obs_x, car_z)
    el_bulb = np.arctan2(source_h - obs_y, car_z)
    raw_eye_lux = (2 * source_I) / (car_z**2 + (source_x - obs_x)**2)
    bloom = raw_eye_lux * np.exp(-((AZ - az_bulb)**2 + (EL - el_bulb)**2) / (np.radians(1.4))**2)
    
    f_raw = np.clip(diffuse + specular + bloom, 0.05, 150)
    f_int = np.clip(0.5*diffuse + 1.0*specular + t_int_direct*bloom, 0.05, 150)
    f_dual = np.clip(0.25*diffuse + 0.005*specular + t_ext_direct*bloom, 0.05, 150)
    
    return f_raw, f_int, f_dual, raw_eye_lux, raw_eye_lux * t_int_direct, raw_eye_lux * t_ext_direct

# ==========================================
# 3. FIGURE & ANIMATION SETUP
# ==========================================
num_frames = 60
z_trajectory = np.linspace(85.0, 15.0, num_frames)
roll_trajectory = np.radians(18.0 * np.sin(np.linspace(0, 3 * np.pi, num_frames)))

fig = plt.figure(figsize=(16, 8), layout='constrained')
gs = fig.add_gridspec(2, 3, height_ratios=[1.4, 1])

ax1 = fig.add_subplot(gs[0, 0])
ax2 = fig.add_subplot(gs[0, 1])
ax3 = fig.add_subplot(gs[0, 2])
ax_trace = fig.add_subplot(gs[1, :])

norm_scale = LogNorm(vmin=0.05, vmax=150)
f_raw0, f_int0, f_dual0, _, _, _ = compute_frame_fields(z_trajectory[0], roll_trajectory[0])

im1 = ax1.pcolormesh(az_deg, el_deg, f_raw0, cmap='inferno', norm=norm_scale, shading='auto')
im2 = ax2.pcolormesh(az_deg, el_deg, f_int0, cmap='inferno', norm=norm_scale, shading='auto')
im3 = ax3.pcolormesh(az_deg, el_deg, f_dual0, cmap='inferno', norm=norm_scale, shading='auto')

titles = [
    "1. Raw Unfiltered View\n(Blinding Beam & Wet Road)",
    "2. Interior CP + PVB Stress\n(Birefringence & LCP Glare Leak)",
    "3. Exterior Dual-Stage Analyzer\n(Direct & Brewster Extinguished)"
]

for ax, title in zip([ax1, ax2, ax3], titles):
    ax.axhline(0, color='cyan', linestyle=':', alpha=0.5)
    z_l = np.linspace(6, 100, 60)
    for lx in [-4.5, 0.0, 4.5]:
        ax.plot(np.degrees(np.arctan2(lx - obs_x, z_l)), np.degrees(np.arctan2(-obs_y, z_l)), 'w--', alpha=0.3)
    ax.set_xlim(-22, 22); ax.set_ylim(-16, 8)
    ax.set_title(title, fontsize=11, fontweight='bold')
    ax.set_xlabel("Horizontal Angle (°)"); ax.set_ylabel("Vertical Angle (°)")

cb = fig.colorbar(im3, ax=[ax1, ax2, ax3], orientation='vertical', fraction=0.015, pad=0.02)
cb.set_label("Perceived Illuminance (Lux)")

# Bottom Telemetry Trace Setup
line_raw, = ax_trace.plot([], [], color='crimson', lw=2.5, label='Raw High Beam Glare (lx)')
line_int, = ax_trace.plot([], [], color='darkorange', lw=2.5, linestyle='--', label='Interior CP Filter + PVB Stress (lx)')
line_dual, = ax_trace.plot([], [], color='forestgreen', lw=2.5, label='Exterior Dual-Stage Analyzer (lx)')

ax_trace.set_yscale('log')
ax_trace.set_xlim(85, 15)  # Countdown distance from 85m to 15m
ax_trace.set_ylim(1e-2, 1e3)
ax_trace.axhline(1.0, color='gray', linestyle=':', label='Safe Glare Threshold (1.0 lx)')
ax_trace.set_xlabel("Oncoming Vehicle Distance (meters)  |  Live Vehicle Roll Oscillation: ±18°", fontsize=11, fontweight='bold')
ax_trace.set_ylabel("Direct Eye Glare (Lux - Log)", fontsize=11)
ax_trace.grid(True, which='both', linestyle=':', alpha=0.6)
ax_trace.legend(loc='upper left', ncol=4)

dist_hist, raw_hist, int_hist, dual_hist = [], [], [], []

def update(frame):
    car_z = z_trajectory[frame]
    roll_r = roll_trajectory[frame]
    f_raw, f_int, f_dual, l_raw, l_int, l_dual = compute_frame_fields(car_z, roll_r)
    
    im1.set_array(f_raw.ravel())
    im2.set_array(f_int.ravel())
    im3.set_array(f_dual.ravel())
    
    dist_hist.append(car_z)
    raw_hist.append(l_raw)
    int_hist.append(l_int)
    dual_hist.append(l_dual)
    
    line_raw.set_data(dist_hist, raw_hist)
    line_int.set_data(dist_hist, int_hist)
    line_dual.set_data(dist_hist, dual_hist)
    
    fig.suptitle(f"Live Approach Simulation  |  Distance: {car_z:.1f} m  |  Vehicle Roll Angle: {np.degrees(roll_r):+.1f}°", 
                 fontsize=13, fontweight='bold')
    return im1, im2, im3, line_raw, line_int, line_dual

ani = FuncAnimation(fig, update, frames=num_frames, interval=80, blit=False)

# Uncomment the line below to export a high-res GIF for your PowerPoint slides:
ani.save("headlight_glare_simulation.gif", writer=PillowWriter(fps=12), dpi=120)

plt.show()