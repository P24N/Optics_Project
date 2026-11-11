# import streamlit as st
# import numpy as np
# import matplotlib.pyplot as plt
# from matplotlib.colors import LogNorm

# st.set_page_config(page_title="Automotive Anti-Glare Optical Simulator", layout="wide")
# st.title("Automotive Polarization & Anti-Glare Optical Testbench")

# # --- SIDEBAR CONTROLS ---
# st.sidebar.header("1. Optical Architecture")
# filter_mode = st.sidebar.radio(
#     "Select Receiver Filter:",
#     ["1. Raw Unfiltered (High Beam)",
#      "2. Linear Polarizer (45°/135°)",
#      "3. Interior CP (Windshield Stress)",
#      "4. Single-Stage Exterior CP",
#      "5. Dual-Stage Analyzer (CP + Vert LP)"]
# )

# st.sidebar.header("2. Dynamic Road & Vehicle State")
# car_dist = st.sidebar.slider("Oncoming Vehicle Distance (m)", 15.0, 90.0, 50.0, step=1.0)
# roll_deg = st.sidebar.slider("Vehicle Roll / Bank Angle (°)", -30.0, 30.0, 12.0, step=1.0)
# pvb_stress = st.sidebar.slider("Windshield PVB Retardance (×π rad)", 0.0, 0.50, 0.25, step=0.01)
# wetness_factor = st.sidebar.slider("Road Surface Wetness (Brewster Glare)", 0.0, 1.0, 0.85, step=0.05)

# # --- JONES CALCULUS & TRANSMISSION ENGINE ---
# roll_rad = np.radians(roll_deg)
# delta_rad = pvb_stress * np.pi

# if "1. Raw" in filter_mode:
#     t_direct, t_specular, t_diffuse = 1.0, 1.0, 1.0
# elif "2. Linear" in filter_mode:
#     t_direct = np.sin(roll_rad)**2 + 0.001
#     t_specular = 0.5 * (np.cos(np.pi/4 + roll_rad)**2)
#     t_diffuse = 0.50
# elif "3. Interior CP" in filter_mode:
#     # PVB stress converts RCP to elliptical, leaking sin^2(delta/2)
#     t_direct = np.sin(delta_rad / 2.0)**2 + 0.001
#     t_specular = np.cos(delta_rad / 2.0)**2
#     t_diffuse = 0.50
# elif "4. Single-Stage" in filter_mode:
#     t_direct = 0.001  # Extinguished before hitting windshield
#     t_specular = 1.0  # RCP flips to LCP on wet bounce and leaks
#     t_diffuse = 0.50
# else:  # 5. Dual-Stage Analyzer
#     t_direct = 0.001
#     t_specular = 0.005  # Vertical LP blocks horizontal Brewster reflection
#     t_diffuse = 0.25

# # --- SPATIAL & POV FIELD COMPUTATION ---
# obs_x, obs_y = 1.8, 1.2
# source_x, source_h, source_I = -2.5, 0.65, 80000

# az_deg = np.linspace(-22, 22, 300)
# el_deg = np.linspace(-16, 8, 220)
# AZ, EL = np.meshgrid(np.radians(az_deg), np.radians(el_deg))

# Z_road = np.where(EL < -1e-3, -obs_y / np.tan(EL), np.nan)
# X_road = np.where(EL < -1e-3, obs_x + Z_road * np.tan(AZ), np.nan)
# valid = (Z_road >= 6.0) & (Z_road <= 100.0) & (np.abs(X_road) <= 9.0)

# dx = np.where(valid, X_road - source_x, np.nan)
# dz = np.where(valid, Z_road - car_dist, np.nan)
# r_sq = dx**2 + source_h**2 + dz**2
# beam = np.exp(-((np.arctan2(dx, -dz)) / 0.24)**2)
# diffuse_lux = np.where(valid, (2 * source_I * beam / r_sq) * (source_h / np.sqrt(r_sq)), 0.0)

# # Specular wet road reflection
# r_in = np.sqrt(r_sq)
# r_out = np.sqrt((obs_x - X_road)**2 + obs_y**2 + Z_road**2)
# cos_spec = np.clip(np.where(valid, (dx*(obs_x - X_road) + source_h*obs_y - dz*Z_road)/(r_in*r_out), 0.0), 0.0, 1.0)
# fresnel = 0.02 + 0.98 * (1.0 - (source_h / r_in))**5
# wet_patch = wetness_factor * np.exp(-((Z_road - (car_dist * 0.65)) / 14)**2)
# spec_lux = np.where(valid, (2 * source_I * fresnel / (r_in + r_out)**2) * (cos_spec**30) * wet_patch, 0.0)

# # Direct bulb glare
# az_bulb = np.arctan2(source_x - obs_x, car_dist)
# el_bulb = np.arctan2(source_h - obs_y, car_dist)
# raw_eye_lux = (2 * source_I) / (car_dist**2 + (source_x - obs_x)**2)
# direct_bloom = raw_eye_lux * np.exp(-((AZ - az_bulb)**2 + (EL - el_bulb)**2) / (np.radians(1.3))**2)

# pov_scene = (t_diffuse * diffuse_lux) + (t_specular * spec_lux) + (t_direct * direct_bloom)
# eye_glare_now = raw_eye_lux * t_direct
# peak_road_glare = np.nanmax(t_specular * spec_lux)

# # --- METRICS ROW ---
# c1, c2, c3, c4 = st.columns(4)
# c1.metric("Direct Eye Glare", f"{eye_glare_now:.3f} lx", f"{-100*(1-t_direct):.1f}% vs Raw")
# c2.metric("Peak Wet-Road Glare", f"{peak_road_glare:.2f} lx")
# c3.metric("Optical Extinction", f"{-10*np.log10(max(t_direct, 1e-4)):.1f} dB")
# status = "SAFE (< 1.0 lx)" if (eye_glare_now < 1.0 and peak_road_glare < 5.0) else "GLARE HAZARD"
# c4.metric("Driver Vision Status", status)

# # --- PLOTS ---
# fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), gridspec_kw={'width_ratios': [2.2, 1]}, layout='constrained')

# im = ax1.pcolormesh(az_deg, el_deg, np.clip(pov_scene, 0.05, 150), cmap='inferno', norm=LogNorm(vmin=0.05, vmax=150), shading='auto')
# ax1.axhline(0, color='cyan', linestyle=':', alpha=0.5)
# for lx in [-4.5, 0.0, 4.5]:
#     z_l = np.linspace(6, 100, 80)
#     ax1.plot(np.degrees(np.arctan2(lx - obs_x, z_l)), np.degrees(np.arctan2(-obs_y, z_l)), 'w--', alpha=0.35)
# ax1.set_xlim(-22, 22); ax1.set_ylim(-16, 8)
# ax1.set_title(f"Live Driver Windshield POV ({filter_mode})", fontweight='bold')
# ax1.set_xlabel("Horizontal Field of View (°)"); ax1.set_ylabel("Vertical Field of View (°)")
# fig.colorbar(im, ax=ax1, label="Retinal Illuminance (Lux)")

# # Polarization State Ellipse after Windshield
# t_p = np.linspace(0, 2*np.pi, 200)
# Ex = np.cos(t_p)
# Ey = np.sin(t_p - (delta_rad if "3. Interior" in filter_mode else 0.0))
# ax2.plot(Ex, Ey, color='dodgerblue', lw=2.5, label='Wave State at Analyzer')
# ax2.set_xlim(-1.3, 1.3); ax2.set_ylim(-1.3, 1.3); ax2.set_aspect('equal')
# ax2.grid(True, linestyle=':')
# ax2.set_title("Incident Polarization Ellipse", fontweight='bold')
# ax2.set_xlabel("$E_x$ Amplitude"); ax2.set_ylabel("$E_y$ Amplitude")
# ax2.legend(loc='lower right')

# st.pyplot(fig)

# """
# Automotive polarization glare testbench (computed version).

# Conventions
# -----------
# * e^{-i w t} phasor convention. Handedness is defined relative to the propagation
#   direction k. Every field is a Jones vector in a right-handed triad (h, v, k):
#   v = vertical (perpendicular to k), h = v x k.
# * All cars carry identical hardware. The headlamp is: unpolarized LED -> linear
#   polarizer at 45 deg -> QWP (fast axis horizontal). The windshield analyzer is the
#   same film turned around, so light meets the QWP first, then a polarizer. In the
#   (h, v) frame of the arriving light this is J_A = J_P(45 deg) J_QWP, which rejects
#   RCP and passes LCP. A linear polarizer at 45 deg in the driver's own frame is at
#   135 deg in the (h, v) frame, which is why an oncoming 45 deg beam is crossed with it.
# * Reflection off the road uses complex Fresnel r_s and r_p (n = 1.33) in right-handed
#   (s, p, k) triads, so reflection reverses the handedness label at normal incidence
#   and preserves it above Brewster's angle.
# * Both quarter-wave plates are designed for 550 nm. At wavelength lam the retardance
#   is Gamma = (pi/2)(550/lam). Windshield retardance delta is specified at 550 nm and
#   scales as 1/lam.
# """
# import numpy as np
# import matplotlib.pyplot as plt
# from matplotlib.colors import LogNorm
# import streamlit as st

# # ----------------------------------------------------------------------------
# # Fixed scene parameters (same values as the report)
# # ----------------------------------------------------------------------------
# OBS_X, OBS_Y = 1.8, 1.2            # eye position (m): lateral, height
# LAMP_X, LAMP_H, LAMP_I = -2.5, 0.65, 80000.0   # lamp lateral (m), height (m), intensity (cd, assumed)
# N_WATER = 1.33
# LAM0 = 550.0                       # design wavelength of the QWPs (nm)
# LOBE_SIGMA = 0.12                  # angular width of the wet-road specular lobe (rad)
# AZ_DEG = np.linspace(-22, 22, 300)
# EL_DEG = np.linspace(-16, 8, 220)

# MODES = [
#     "1. Unfiltered (high beam)",
#     "2. Crossed linear polarizers",
#     "3. Interior circular analyzer",
#     "4. Exterior circular analyzer",
#     "5. Split-zone (circular above, vertical below)",
#     "6. Series stack (circular then vertical)",
# ]

# # ----------------------------------------------------------------------------
# # Jones matrices
# # ----------------------------------------------------------------------------
# I2 = np.eye(2, dtype=complex)


# def rot(a):
#     c, s = np.cos(a), np.sin(a)
#     return np.array([[c, -s], [s, c]], dtype=complex)


# def retarder(gamma, axis=0.0):
#     d = np.array([[np.exp(1j * gamma / 2), 0], [0, np.exp(-1j * gamma / 2)]], dtype=complex)
#     return rot(axis) @ d @ rot(-axis)


# def linear_pol(theta, eps):
#     """Linear polarizer at angle theta; eps is the power leaked on the blocked axis."""
#     d = np.array([[1, 0], [0, np.sqrt(eps)]], dtype=complex)
#     return rot(theta) @ d @ rot(-theta)


# def qwp(lam):
#     return retarder(np.pi / 2 * LAM0 / lam, 0.0)


# def windshield(delta_550, phi, lam):
#     return retarder(delta_550 * LAM0 / lam, phi)


# def build_chain(mode, lam, eps, delta, phi, roll, boundary_deg):
#     """Return (J_emit, J_rx_upper, J_rx_lower, uses_zones). Receiver chains act in the (h, v) frame."""
#     P45 = linear_pol(np.pi / 4, eps)
#     JA = P45 @ qwp(lam)
#     JV = linear_pol(np.pi / 2, eps)
#     Jlin = linear_pol(3 * np.pi / 4, eps)      # 45 deg in driver frame = 135 deg in (h, v)
#     JW = windshield(delta, phi, lam)
#     if mode == 1:
#         return I2, I2, I2, False
#     if mode == 2:
#         emit, up, lo = P45, JW @ Jlin, JW @ Jlin
#     elif mode == 3:
#         emit, up, lo = qwp(lam) @ P45, JA @ JW, JA @ JW
#     elif mode == 4:
#         emit, up, lo = qwp(lam) @ P45, JW @ JA, JW @ JA
#     elif mode == 5:
#         emit, up, lo = qwp(lam) @ P45, JW @ JA, JW @ JV
#     else:
#         emit, up, lo = qwp(lam) @ P45, JW @ JV @ JA, JW @ JV @ JA
#     R, Ri = rot(roll), rot(-roll)               # whole receiver rolls with the car
#     return emit, R @ up @ Ri, R @ lo @ Ri, (mode == 5)


# # ----------------------------------------------------------------------------
# # Fresnel reflection
# # ----------------------------------------------------------------------------
# def fresnel(cos_i, n=N_WATER):
#     sin_i = np.sqrt(np.clip(1 - cos_i**2, 0, 1))
#     cos_t = np.sqrt(np.clip(1 - (sin_i / n) ** 2, 0, 1))
#     rs = (cos_i - n * cos_t) / (cos_i + n * cos_t)
#     rp = (n * cos_i - cos_t) / (n * cos_i + cos_t)
#     return rs, rp


# def flip_fraction(rs, rp):
#     """Fraction of reflected power that changes handedness for circular input."""
#     return np.abs(rs - rp) ** 2 / (2 * (np.abs(rs) ** 2 + np.abs(rp) ** 2))


# # ----------------------------------------------------------------------------
# # Geometry (3D pinhole camera and road plane), cached per oncoming distance
# # ----------------------------------------------------------------------------
# def unit(a):
#     return a / np.linalg.norm(a, axis=-1, keepdims=True)


# @st.cache_data(show_spinner=False)
# def build_geometry(d):
#     AZ, EL = np.meshgrid(np.radians(AZ_DEG), np.radians(EL_DEG))
#     below = EL < -1e-3
#     with np.errstate(divide="ignore", invalid="ignore"):
#         Z = np.where(below, -OBS_Y / np.tan(EL), 50.0)
#     X = OBS_X + Z * np.tan(AZ)
#     valid = below & (Z >= 6.0) & (Z <= 100.0) & (np.abs(X) <= 9.0)
#     Z = np.where(valid, Z, 50.0)
#     X = np.where(valid, X, OBS_X)

#     dx, dz = X - LAMP_X, Z - d
#     r_in = np.sqrt(dx**2 + LAMP_H**2 + dz**2)
#     r_out = np.sqrt((OBS_X - X) ** 2 + OBS_Y**2 + Z**2)

#     yhat = np.array([0.0, 1.0, 0.0])
#     k_e = np.stack([dx, -LAMP_H * np.ones_like(dx), dz], -1) / r_in[..., None]      # lamp -> road
#     k_r = np.stack([OBS_X - X, OBS_Y * np.ones_like(X), -Z], -1) / r_out[..., None]  # road -> eye
#     v_e = unit(yhat - k_e[..., 1:2] * k_e)
#     h_e = np.cross(v_e, k_e)
#     v_r = unit(yhat - k_r[..., 1:2] * k_r)
#     h_r = np.cross(v_r, k_r)
#     s = unit(np.cross(k_e, yhat))
#     p_i = np.cross(k_e, s)
#     p_r = np.cross(k_r, s)

#     cos_i = LAMP_H / r_in
#     rs, rp = fresnel(cos_i)
#     mirror = np.stack([dx, LAMP_H * np.ones_like(dx), dz], -1) / r_in[..., None]
#     dev = np.arccos(np.clip(np.sum(mirror * k_r, -1), -1, 1))
#     lobe = np.exp(-((dev / LOBE_SIGMA) ** 2))

#     beam = np.exp(-((np.arctan2(dx, -dz)) / 0.24) ** 2)
#     diffuse = 2 * LAMP_I * beam / r_in**2 * (LAMP_H / r_in)
#     spec_base = 2 * LAMP_I / (r_in + r_out) ** 2
#     wet_patch = np.exp(-((Z - 0.65 * d) / 14.0) ** 2)

#     r_own = np.sqrt((X - OBS_X) ** 2 + LAMP_H**2 + Z**2)
#     w_own = np.exp(-((np.arctan2(X - OBS_X, Z)) / 0.20) ** 2) * (LAMP_H / r_own) / r_own**2

#     az_b = np.arctan2(LAMP_X - OBS_X, d)
#     el_b = np.arctan2(LAMP_H - OBS_Y, d)
#     E_eye = 2 * LAMP_I / (d**2 + (LAMP_X - OBS_X) ** 2)
#     bloom = np.exp(-((AZ - az_b) ** 2 + (EL - el_b) ** 2) / np.radians(1.3) ** 2)

#     return dict(AZ=AZ, EL=EL, valid=valid, X=X, Z=Z, k_e=k_e, h_e=h_e, v_e=v_e, h_r=h_r, v_r=v_r,
#                 s=s, p_i=p_i, p_r=p_r, rs=rs, rp=rp, theta_i=np.degrees(np.arccos(cos_i)),
#                 lobe=lobe, diffuse=diffuse, spec_base=spec_base, wet_patch=wet_patch,
#                 w_own=w_own, az_b=az_b, el_b=el_b, E_eye=E_eye, bloom=bloom)


# # ----------------------------------------------------------------------------
# # Transmission calculations
# # ----------------------------------------------------------------------------
# BASIS = (np.array([1, 0], dtype=complex), np.array([0, 1], dtype=complex))


# def emit_norm(Jemit):
#     """Normalise so the polarized beam carries the same power as the raw lamp."""
#     return 0.5 * np.trace(Jemit.conj().T @ Jemit).real


# def direct_T(Jrx, Jemit):
#     tot = 0.0
#     for e in BASIS:
#         out = Jrx @ (Jemit @ e)
#         tot += 0.5 * np.vdot(out, out).real
#     return tot / emit_norm(Jemit)


# def diffuse_T(Jrx):
#     """Depolarized light: transmitted fraction is half the trace of J^dagger J."""
#     return 0.5 * np.trace(Jrx.conj().T @ Jrx).real


# def reflect_gain(G, Jemit, Jup, Jlo, up_mask):
#     """Power fraction after emission, Fresnel reflection (s/p) and the receiver chain."""
#     tot = 0.0
#     for e in BASIS:
#         Eh, Ev = Jemit @ e
#         E3 = Eh * G["h_e"] + Ev * G["v_e"]
#         Es = np.sum(E3 * G["s"], -1)
#         Ep = np.sum(E3 * G["p_i"], -1)
#         E3r = (G["rs"] * Es)[..., None] * G["s"] + (G["rp"] * Ep)[..., None] * G["p_r"]
#         a = np.sum(E3r * G["h_r"], -1)
#         b = np.sum(E3r * G["v_r"], -1)
#         res = []
#         for J in (Jup, Jlo):
#             o1 = J[0, 0] * a + J[0, 1] * b
#             o2 = J[1, 0] * a + J[1, 1] * b
#             res.append(np.abs(o1) ** 2 + np.abs(o2) ** 2)
#         tot = tot + 0.5 * np.where(up_mask, res[0], res[1])
#     return tot / emit_norm(Jemit)


# def compute_scene(G, chain, boundary_deg, wetness):
#     Jemit, Jup, Jlo, _ = chain
#     up_mask = G["EL"] > np.radians(boundary_deg)
#     valid = G["valid"]
#     gain = reflect_gain(G, Jemit, Jup, Jlo, up_mask)
#     spec = np.where(valid, G["spec_base"] * G["lobe"] * wetness * G["wet_patch"] * gain, 0.0)
#     t_diff = np.where(up_mask, diffuse_T(Jup), diffuse_T(Jlo))
#     diff = np.where(valid, G["diffuse"], 0.0) * t_diff
#     Td = np.where(up_mask, direct_T(Jup, Jemit), direct_T(Jlo, Jemit))
#     bloom = G["E_eye"] * G["bloom"] * Td
#     lamp_up = G["el_b"] > np.radians(boundary_deg)
#     Td_lamp = direct_T(Jup if lamp_up else Jlo, Jemit)
#     w = np.where(valid, G["w_own"], 0.0)
#     useful = float(np.sum(w * t_diff) / np.sum(w))
#     return dict(scene=diff + spec + bloom, spec=spec, Td_lamp=Td_lamp, useful=useful)


# # ----------------------------------------------------------------------------
# # Polarization state shown in the ellipse panel
# # ----------------------------------------------------------------------------
# def state_at_analyzer(mode, lam, delta, phi):
#     if mode == 1:
#         return None
#     E = np.array([1, 1], dtype=complex) / np.sqrt(2)
#     if mode != 2:
#         E = qwp(lam) @ E
#     if mode == 3:
#         E = windshield(delta, phi, lam) @ E
#     return E


# def chirality(E):
#     s3 = -2 * np.imag(np.conj(E[0]) * E[1])
#     if s3 > 0.9:
#         return "RCP"
#     if s3 < -0.9:
#         return "LCP"
#     if abs(s3) < 0.05:
#         return "linear"
#     return f"elliptical (S3 = {s3:+.2f})"


# # ----------------------------------------------------------------------------
# # Self checks of the physics
# # ----------------------------------------------------------------------------
# def physics_checks(lam=550.0):
#     E_rcp = np.array([1, -1j]) / np.sqrt(2)
#     E_lcp = np.array([1, 1j]) / np.sqrt(2)
#     JA = linear_pol(np.pi / 4, 0.0) @ qwp(lam)
#     rs0, rp0 = fresnel(np.cos(np.radians(0.001)))
#     rs88, rp88 = fresnel(np.cos(np.radians(88)))
#     rs60, rp60 = fresnel(np.cos(np.radians(60)))
#     th_b = np.degrees(np.arctan(N_WATER))
#     _, rpb = fresnel(np.cos(np.radians(th_b)))
#     rows = [
#         ("J_A on RCP, power out", f"{np.vdot(JA @ E_rcp, JA @ E_rcp).real:.4f} (expect 0)"),
#         ("J_A on LCP, power out", f"{np.vdot(JA @ E_lcp, JA @ E_lcp).real:.4f} (expect 1)"),
#         ("Brewster angle", f"{th_b:.1f} deg, r_p there = {abs(rpb):.4f}"),
#         ("RCP to LCP at normal incidence", f"{flip_fraction(rs0, rp0) * 100:.1f}% (expect about 100%)"),
#         ("RCP to LCP at 60 deg", f"{flip_fraction(rs60, rp60) * 100:.1f}% (just above Brewster, partial flip)"),
#         ("RCP to LCP at 88 deg", f"{flip_fraction(rs88, rp88) * 100:.2f}% (near grazing, expect low)"),
#     ]
#     return rows


# # ----------------------------------------------------------------------------
# # Streamlit app
# # ----------------------------------------------------------------------------
# def main():
#     st.set_page_config(page_title="Automotive Polarization Glare Testbench", layout="wide")
#     st.title("Automotive Polarization Glare Testbench")
#     st.caption("Jones calculus, complex Fresnel reflection and a 3D pinhole road model. "
#                "Both quarter-wave plates are designed for 550 nm.")

#     sb = st.sidebar
#     sb.header("1. Optical architecture")
#     mode_name = sb.radio("Receiver configuration", MODES, index=3)
#     mode = MODES.index(mode_name) + 1

#     sb.header("2. Scene")
#     d = sb.slider("Oncoming vehicle distance (m)", 15.0, 90.0, 50.0, step=1.0)
#     roll_deg = sb.slider("Relative roll between cars (deg)", -30.0, 30.0, 0.0, step=1.0)
#     wetness = sb.slider("Road wetness (fraction of wet patch)", 0.0, 1.0, 0.85, step=0.05)

#     sb.header("3. Windshield")
#     delta_pi = sb.slider("Retardance delta at 550 nm (x pi rad)", 0.0, 0.50, 0.25, step=0.01)
#     phi_deg = sb.slider("Stress axis angle phi (deg)", 0.0, 90.0, 30.0, step=1.0)

#     sb.header("4. Element quality")
#     lam = sb.slider("Wavelength (nm), QWPs designed for 550 nm", 450.0, 650.0, 550.0, step=5.0)
#     log_er = sb.slider("Polarizer extinction ratio (log10)", 2.0, 5.0, 3.0, step=0.5)
#     boundary = sb.slider("Split-zone boundary elevation (deg)", -8.0, 0.0, -2.0, step=0.5,
#                          disabled=(mode != 5))

#     eps = 10.0 ** (-log_er)
#     chain = build_chain(mode, lam, eps, delta_pi * np.pi, np.radians(phi_deg),
#                         np.radians(roll_deg), boundary)
#     raw_chain = build_chain(1, lam, eps, 0.0, 0.0, 0.0, boundary)

#     G = build_geometry(d)
#     filt = compute_scene(G, chain, boundary, wetness)
#     raw = compute_scene(G, raw_chain, boundary, wetness)

#     # ---- metrics
#     raw_lux = G["E_eye"]
#     eye_lux = raw_lux * filt["Td_lamp"]
#     peak_wet = float(np.max(filt["spec"]))
#     ext_db = -10 * np.log10(max(filt["Td_lamp"], 1e-9))
#     c1, c2, c3, c4, c5 = st.columns(5)
#     c1.metric("Direct eye glare", f"{eye_lux:.3f} lx", f"{raw_lux:.1f} lx raw", delta_color="off")
#     c2.metric("Peak wet-road glare", f"{peak_wet:.2f} lx", f"{float(np.max(raw['spec'])):.2f} lx raw",
#               delta_color="off")
#     c3.metric("Direct extinction", f"{ext_db:.1f} dB")
#     c4.metric("Useful-light fraction", f"{filt['useful'] * 100:.0f}%")
#     safe = eye_lux < 1.0 and peak_wet < 5.0
#     c5.metric("Status", "Below 1 lx direct, 5 lx road" if safe else "Glare above limits")

#     # ---- 3 panel pinhole POV
#     fig, axs = plt.subplots(1, 3, figsize=(16, 4.8), layout="constrained")
#     norm = LogNorm(vmin=0.05, vmax=150)
#     raw_img = np.clip(raw["scene"], 0.05, 150)
#     flt_img = np.clip(filt["scene"], 0.05, 150)
#     im1 = axs[0].pcolormesh(AZ_DEG, EL_DEG, raw_img, cmap="inferno", norm=norm, shading="auto")
#     axs[1].pcolormesh(AZ_DEG, EL_DEG, flt_img, cmap="inferno", norm=norm, shading="auto")
#     att = 10 * np.log10(np.maximum(raw["scene"], 1e-6) / np.maximum(filt["scene"], 1e-6))
#     im3 = axs[2].pcolormesh(AZ_DEG, EL_DEG, np.clip(att, 0, 40), cmap="viridis", vmin=0, vmax=40,
#                             shading="auto")
#     titles = ["1. Unfiltered view", f"2. Filtered view\n{mode_name}", "3. Attenuation (raw / filtered)"]
#     z_l = np.linspace(6, 100, 80)
#     for ax, t in zip(axs, titles):
#         ax.axhline(0, color="cyan", ls=":", alpha=0.5)
#         for lx in (-4.5, 0.0, 4.5):
#             ax.plot(np.degrees(np.arctan2(lx - OBS_X, z_l)), np.degrees(np.arctan2(-OBS_Y, z_l)),
#                     "w--", alpha=0.35)
#         ax.plot(np.degrees(G["az_b"]), np.degrees(G["el_b"]), "w*", ms=9)
#         if mode == 5:
#             ax.axhline(boundary, color="lime", ls="-.", alpha=0.7)
#         ax.set_xlim(-22, 22)
#         ax.set_ylim(-16, 8)
#         ax.set_title(t, fontsize=10, fontweight="bold")
#         ax.set_xlabel("Horizontal angle (deg)")
#         ax.set_ylabel("Vertical angle (deg)")
#     fig.colorbar(im1, ax=axs[:2], label="Retinal illuminance (lx)", fraction=0.03, pad=0.01)
#     fig.colorbar(im3, ax=axs[2], label="Attenuation (dB)", fraction=0.05, pad=0.01)
#     st.pyplot(fig)

#     # ---- ellipse and Fresnel panels
#     colA, colB = st.columns(2)
#     with colA:
#         E = state_at_analyzer(mode, lam, delta_pi * np.pi, np.radians(phi_deg))
#         fig2, ax = plt.subplots(figsize=(5, 4.2), layout="constrained")
#         if E is None:
#             ax.text(0.5, 0.5, "Unpolarized lamp:\nno polarization ellipse", ha="center", va="center",
#                     transform=ax.transAxes)
#             ax.set_xticks([])
#             ax.set_yticks([])
#             ax.set_title("Polarization state at analyzer entrance")
#         else:
#             t = np.linspace(0, 2 * np.pi, 300)
#             ax.plot(np.real(E[0] * np.exp(-1j * t)), np.real(E[1] * np.exp(-1j * t)), lw=2.5,
#                     color="dodgerblue")
#             ax.set_xlim(-1.2, 1.2)
#             ax.set_ylim(-1.2, 1.2)
#             ax.set_aspect("equal")
#             ax.grid(True, ls=":")
#             ax.set_xlabel("$E_h$")
#             ax.set_ylabel("$E_v$")
#             ax.set_title(f"Polarization state at analyzer entrance: {chirality(E)}", fontsize=10)
#         st.pyplot(fig2)
#     with colB:
#         th = np.linspace(0, 89.9, 400)
#         rs, rp = fresnel(np.cos(np.radians(th)))
#         w = G["valid"] & (G["lobe"] * G["wet_patch"] > 0.1 * np.max(G["lobe"] * G["wet_patch"]))
#         lo, hi = float(np.min(G["theta_i"][w])), float(np.max(G["theta_i"][w]))
#         fig3, ax = plt.subplots(figsize=(5.5, 4.2), layout="constrained")
#         ax.plot(th, np.abs(rs) ** 2, label="$R_s$", color="crimson")
#         ax.plot(th, np.abs(rp) ** 2, label="$R_p$", color="navy")
#         ax.plot(th, flip_fraction(rs, rp), "--", label="RCP to LCP fraction", color="darkorange")
#         ax.axvline(np.degrees(np.arctan(N_WATER)), color="gray", ls=":", label="Brewster")
#         ax.axvspan(lo, hi, color="cyan", alpha=0.25, label=f"Glare incidence {lo:.0f} to {hi:.0f} deg")
#         ax.set_xlabel("Incidence angle from road normal (deg)")
#         ax.set_ylabel("Reflectance or fraction")
#         ax.set_title("Air to water reflection (n = 1.33)", fontsize=10)
#         ax.set_xlim(0, 90)
#         ax.set_ylim(0, 1.02)
#         ax.grid(True, ls=":")
#         ax.legend(fontsize=8, loc="upper left")
#         st.pyplot(fig3)

#     with st.expander("Physics self-check"):
#         for k, v in physics_checks(lam):
#             st.write(f"**{k}:** {v}")

#     st.caption("Assumed inputs: lamp intensity 80,000 cd, retardance range, wet patch position and width, "
#                "specular lobe width, own-beam weighting. The direct glare is for the combined source at the "
#                "chosen distance. Emitter film loss is assumed to be compensated by drive current, so all "
#                "configurations use the same lamp output. Elements are ideal apart from the extinction ratio "
#                "and the 550 nm wavelength dependence. In split-zone mode a lamp that enters the lower zone "
#                "(close range) is attenuated only about 50%.")


# if __name__ == "__main__":
#     main()

"""
Automotive polarization glare testbench (computed version).

Conventions
-----------
* e^{-i w t} phasor convention. Handedness is defined relative to the propagation
  direction k. Every field is a Jones vector in a right-handed triad (h, v, k):
  v = vertical (perpendicular to k), h = v x k.
* All cars carry identical hardware. The headlamp is: unpolarized LED -> linear
  polarizer at 45 deg -> QWP (fast axis horizontal). The windshield analyzer is the
  same film turned around, so light meets the QWP first, then a polarizer. In the
  (h, v) frame of the arriving light this is J_A = J_P(45 deg) J_QWP, which rejects
  RCP and passes LCP. A linear polarizer at 45 deg in the driver's own frame is at
  135 deg in the (h, v) frame, which is why an oncoming 45 deg beam is crossed with it.
* Reflection off the road uses complex Fresnel r_s and r_p (n = 1.33) in right-handed
  (s, p, k) triads, so reflection reverses the handedness label at normal incidence
  and preserves it above Brewster's angle.
* Both quarter-wave plates are designed for 550 nm. At wavelength lam the retardance
  is Gamma = (pi/2)(550/lam). Windshield retardance delta is specified at 550 nm and
  scales as 1/lam.
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import streamlit as st

# ----------------------------------------------------------------------------
# Fixed scene parameters (same values as the report)
# ----------------------------------------------------------------------------
OBS_X, OBS_Y = 1.8, 1.2            # eye position (m): lateral, height
LAMP_X, LAMP_H, LAMP_I = -2.5, 0.65, 80000.0   # lamp lateral (m), height (m), intensity (cd, assumed)
N_WATER = 1.33
LAM0 = 550.0                       # design wavelength of the QWPs (nm)
LOBE_SIGMA = 0.12                  # angular width of the wet-road specular lobe (rad)
AZ_DEG = np.linspace(-22, 22, 300)
EL_DEG = np.linspace(-16, 8, 220)

MODES = [
    "1. Unfiltered (high beam)",
    "2. Crossed linear polarizers",
    "3. Interior circular analyzer",
    "4. Exterior circular analyzer",
    "5. Split-zone (vertical lower zone, rejected)",
    "6. Series stack (circular then vertical)",
]

# ----------------------------------------------------------------------------
# Jones matrices
# ----------------------------------------------------------------------------
I2 = np.eye(2, dtype=complex)


def rot(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s], [s, c]], dtype=complex)


def retarder(gamma, axis=0.0):
    d = np.array([[np.exp(1j * gamma / 2), 0], [0, np.exp(-1j * gamma / 2)]], dtype=complex)
    return rot(axis) @ d @ rot(-axis)


def linear_pol(theta, eps):
    """Linear polarizer at angle theta; eps is the power leaked on the blocked axis."""
    d = np.array([[1, 0], [0, np.sqrt(eps)]], dtype=complex)
    return rot(theta) @ d @ rot(-theta)


def qwp(lam):
    return retarder(np.pi / 2 * LAM0 / lam, 0.0)


def windshield(delta_550, phi, lam):
    return retarder(delta_550 * LAM0 / lam, phi)


def build_chain(mode, lam, eps, delta, phi, roll, boundary_deg):
    """Return (J_emit, J_rx_upper, J_rx_lower, uses_zones). Receiver chains act in the (h, v) frame."""
    P45 = linear_pol(np.pi / 4, eps)
    JA = P45 @ qwp(lam)
    JV = linear_pol(np.pi / 2, eps)
    Jlin = linear_pol(3 * np.pi / 4, eps)      # 45 deg in driver frame = 135 deg in (h, v)
    JW = windshield(delta, phi, lam)
    if mode == 1:
        return I2, I2, I2, False
    if mode == 2:
        emit, up, lo = P45, JW @ Jlin, JW @ Jlin
    elif mode == 3:
        emit, up, lo = qwp(lam) @ P45, JA @ JW, JA @ JW
    elif mode == 4:
        emit, up, lo = qwp(lam) @ P45, JW @ JA, JW @ JA
    elif mode == 5:
        emit, up, lo = qwp(lam) @ P45, JW @ JA, JW @ JV
    else:
        emit, up, lo = qwp(lam) @ P45, JW @ JV @ JA, JW @ JV @ JA
    R, Ri = rot(roll), rot(-roll)               # whole receiver rolls with the car
    return emit, R @ up @ Ri, R @ lo @ Ri, (mode == 5)


# ----------------------------------------------------------------------------
# Fresnel reflection
# ----------------------------------------------------------------------------
def fresnel(cos_i, n=N_WATER):
    sin_i = np.sqrt(np.clip(1 - cos_i**2, 0, 1))
    cos_t = np.sqrt(np.clip(1 - (sin_i / n) ** 2, 0, 1))
    rs = (cos_i - n * cos_t) / (cos_i + n * cos_t)
    rp = (n * cos_i - cos_t) / (n * cos_i + cos_t)
    return rs, rp


def flip_fraction(rs, rp):
    """Fraction of reflected power that changes handedness for circular input."""
    return np.abs(rs - rp) ** 2 / (2 * (np.abs(rs) ** 2 + np.abs(rp) ** 2))


# ----------------------------------------------------------------------------
# Geometry (3D pinhole camera and road plane), cached per oncoming distance
# ----------------------------------------------------------------------------
def unit(a):
    return a / np.linalg.norm(a, axis=-1, keepdims=True)


@st.cache_data(show_spinner=False)
def build_geometry(d):
    AZ, EL = np.meshgrid(np.radians(AZ_DEG), np.radians(EL_DEG))
    below = EL < -1e-3
    with np.errstate(divide="ignore", invalid="ignore"):
        Z = np.where(below, -OBS_Y / np.tan(EL), 50.0)
    X = OBS_X + Z * np.tan(AZ)
    valid = below & (Z >= 6.0) & (Z <= 100.0) & (np.abs(X) <= 9.0)
    Z = np.where(valid, Z, 50.0)
    X = np.where(valid, X, OBS_X)

    dx, dz = X - LAMP_X, Z - d
    r_in = np.sqrt(dx**2 + LAMP_H**2 + dz**2)
    r_out = np.sqrt((OBS_X - X) ** 2 + OBS_Y**2 + Z**2)

    yhat = np.array([0.0, 1.0, 0.0])
    k_e = np.stack([dx, -LAMP_H * np.ones_like(dx), dz], -1) / r_in[..., None]      # lamp -> road
    k_r = np.stack([OBS_X - X, OBS_Y * np.ones_like(X), -Z], -1) / r_out[..., None]  # road -> eye
    v_e = unit(yhat - k_e[..., 1:2] * k_e)
    h_e = np.cross(v_e, k_e)
    v_r = unit(yhat - k_r[..., 1:2] * k_r)
    h_r = np.cross(v_r, k_r)
    s = unit(np.cross(k_e, yhat))
    p_i = np.cross(k_e, s)
    p_r = np.cross(k_r, s)

    cos_i = LAMP_H / r_in
    rs, rp = fresnel(cos_i)
    mirror = np.stack([dx, LAMP_H * np.ones_like(dx), dz], -1) / r_in[..., None]
    dev = np.arccos(np.clip(np.sum(mirror * k_r, -1), -1, 1))
    lobe = np.exp(-((dev / LOBE_SIGMA) ** 2))

    beam = np.exp(-((np.arctan2(dx, -dz)) / 0.24) ** 2)
    diffuse = 2 * LAMP_I * beam / r_in**2 * (LAMP_H / r_in)
    spec_base = 2 * LAMP_I / (r_in + r_out) ** 2
    wet_patch = np.exp(-((Z - 0.65 * d) / 14.0) ** 2)

    r_own = np.sqrt((X - OBS_X) ** 2 + LAMP_H**2 + Z**2)
    w_own = np.exp(-((np.arctan2(X - OBS_X, Z)) / 0.20) ** 2) * (LAMP_H / r_own) / r_own**2

    az_b = np.arctan2(LAMP_X - OBS_X, d)
    el_b = np.arctan2(LAMP_H - OBS_Y, d)
    E_eye = 2 * LAMP_I / (d**2 + (LAMP_X - OBS_X) ** 2)
    bloom = np.exp(-((AZ - az_b) ** 2 + (EL - el_b) ** 2) / np.radians(1.3) ** 2)

    return dict(AZ=AZ, EL=EL, valid=valid, X=X, Z=Z, k_e=k_e, h_e=h_e, v_e=v_e, h_r=h_r, v_r=v_r,
                s=s, p_i=p_i, p_r=p_r, rs=rs, rp=rp, theta_i=np.degrees(np.arccos(cos_i)),
                lobe=lobe, diffuse=diffuse, spec_base=spec_base, wet_patch=wet_patch,
                w_own=w_own, az_b=az_b, el_b=el_b, E_eye=E_eye, bloom=bloom)


# ----------------------------------------------------------------------------
# Transmission calculations
# ----------------------------------------------------------------------------
BASIS = (np.array([1, 0], dtype=complex), np.array([0, 1], dtype=complex))


def emit_norm(Jemit):
    """Normalise so the polarized beam carries the same power as the raw lamp."""
    return 0.5 * np.trace(Jemit.conj().T @ Jemit).real


def direct_T(Jrx, Jemit):
    tot = 0.0
    for e in BASIS:
        out = Jrx @ (Jemit @ e)
        tot += 0.5 * np.vdot(out, out).real
    return tot / emit_norm(Jemit)


def diffuse_T(Jrx):
    """Depolarized light: transmitted fraction is half the trace of J^dagger J."""
    return 0.5 * np.trace(Jrx.conj().T @ Jrx).real


def reflect_gain(G, Jemit, Jup, Jlo, up_mask):
    """Power fraction after emission, Fresnel reflection (s/p) and the receiver chain."""
    tot = 0.0
    for e in BASIS:
        Eh, Ev = Jemit @ e
        E3 = Eh * G["h_e"] + Ev * G["v_e"]
        Es = np.sum(E3 * G["s"], -1)
        Ep = np.sum(E3 * G["p_i"], -1)
        E3r = (G["rs"] * Es)[..., None] * G["s"] + (G["rp"] * Ep)[..., None] * G["p_r"]
        a = np.sum(E3r * G["h_r"], -1)
        b = np.sum(E3r * G["v_r"], -1)
        res = []
        for J in (Jup, Jlo):
            o1 = J[0, 0] * a + J[0, 1] * b
            o2 = J[1, 0] * a + J[1, 1] * b
            res.append(np.abs(o1) ** 2 + np.abs(o2) ** 2)
        tot = tot + 0.5 * np.where(up_mask, res[0], res[1])
    return tot / emit_norm(Jemit)


def compute_scene(G, chain, boundary_deg, wetness):
    Jemit, Jup, Jlo, _ = chain
    up_mask = G["EL"] > np.radians(boundary_deg)
    valid = G["valid"]
    gain = reflect_gain(G, Jemit, Jup, Jlo, up_mask)
    spec = np.where(valid, G["spec_base"] * G["lobe"] * wetness * G["wet_patch"] * gain, 0.0)
    t_diff = np.where(up_mask, diffuse_T(Jup), diffuse_T(Jlo))
    diff = np.where(valid, G["diffuse"], 0.0) * t_diff
    Td = np.where(up_mask, direct_T(Jup, Jemit), direct_T(Jlo, Jemit))
    bloom = G["E_eye"] * G["bloom"] * Td
    lamp_up = G["el_b"] > np.radians(boundary_deg)
    Td_lamp = direct_T(Jup if lamp_up else Jlo, Jemit)
    w = np.where(valid, G["w_own"], 0.0)
    useful = float(np.sum(w * t_diff) / np.sum(w))
    return dict(scene=diff + spec + bloom, spec=spec, Td_lamp=Td_lamp, useful=useful)


# ----------------------------------------------------------------------------
# Polarization state shown in the ellipse panel
# ----------------------------------------------------------------------------
def state_at_analyzer(mode, lam, delta, phi):
    if mode == 1:
        return None
    E = np.array([1, 1], dtype=complex) / np.sqrt(2)
    if mode != 2:
        E = qwp(lam) @ E
    if mode == 3:
        E = windshield(delta, phi, lam) @ E
    return E


def chirality(E):
    s3 = -2 * np.imag(np.conj(E[0]) * E[1])
    if s3 > 0.9:
        return "RCP"
    if s3 < -0.9:
        return "LCP"
    if abs(s3) < 0.05:
        return "linear"
    return f"elliptical (S3 = {s3:+.2f})"


# ----------------------------------------------------------------------------
# Self checks of the physics
# ----------------------------------------------------------------------------
def physics_checks(lam=550.0):
    E_rcp = np.array([1, -1j]) / np.sqrt(2)
    E_lcp = np.array([1, 1j]) / np.sqrt(2)
    JA = linear_pol(np.pi / 4, 0.0) @ qwp(lam)
    rs0, rp0 = fresnel(np.cos(np.radians(0.001)))
    rs88, rp88 = fresnel(np.cos(np.radians(88)))
    rs60, rp60 = fresnel(np.cos(np.radians(60)))
    th_b = np.degrees(np.arctan(N_WATER))
    _, rpb = fresnel(np.cos(np.radians(th_b)))
    rows = [
        ("J_A on RCP, power out", f"{np.vdot(JA @ E_rcp, JA @ E_rcp).real:.4f} (expect 0)"),
        ("J_A on LCP, power out", f"{np.vdot(JA @ E_lcp, JA @ E_lcp).real:.4f} (expect 1)"),
        ("Brewster angle", f"{th_b:.1f} deg, r_p there = {abs(rpb):.4f}"),
        ("RCP to LCP at normal incidence", f"{flip_fraction(rs0, rp0) * 100:.1f}% (expect about 100%)"),
        ("RCP to LCP at 60 deg", f"{flip_fraction(rs60, rp60) * 100:.1f}% (just above Brewster, partial flip)"),
        ("RCP to LCP at 88 deg", f"{flip_fraction(rs88, rp88) * 100:.2f}% (near grazing, expect low)"),
    ]
    return rows


# ----------------------------------------------------------------------------
# Streamlit app
# ----------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="Automotive Polarization Glare Testbench", layout="wide")
    st.title("Automotive Polarization Glare Testbench")
    st.caption("Jones calculus, complex Fresnel reflection and a 3D pinhole road model. "
               "Both quarter-wave plates are designed for 550 nm.")

    sb = st.sidebar
    sb.header("1. Optical architecture")
    mode_name = sb.radio("Receiver configuration", MODES, index=3)
    mode = MODES.index(mode_name) + 1

    sb.header("2. Scene")
    d = sb.slider("Oncoming vehicle distance (m)", 15.0, 90.0, 50.0, step=1.0)
    roll_deg = sb.slider("Relative roll between cars (deg)", -30.0, 30.0, 0.0, step=1.0)
    wetness = sb.slider("Road wetness (fraction of wet patch)", 0.0, 1.0, 0.85, step=0.05)

    sb.header("3. Windshield")
    delta_pi = sb.slider("Retardance delta at 550 nm (x pi rad)", 0.0, 0.50, 0.25, step=0.01)
    phi_deg = sb.slider("Stress axis angle phi (deg)", 0.0, 90.0, 30.0, step=1.0)

    sb.header("4. Element quality")
    lam = sb.slider("Wavelength (nm), QWPs designed for 550 nm", 450.0, 650.0, 550.0, step=5.0)
    log_er = sb.slider("Polarizer extinction ratio (log10)", 2.0, 5.0, 3.0, step=0.5)
    boundary = sb.slider("Split-zone boundary elevation (deg)", -8.0, 0.0, -2.0, step=0.5,
                         disabled=(mode != 5))

    eps = 10.0 ** (-log_er)
    chain = build_chain(mode, lam, eps, delta_pi * np.pi, np.radians(phi_deg),
                        np.radians(roll_deg), boundary)
    raw_chain = build_chain(1, lam, eps, 0.0, 0.0, 0.0, boundary)

    G = build_geometry(d)
    filt = compute_scene(G, chain, boundary, wetness)
    raw = compute_scene(G, raw_chain, boundary, wetness)

    # ---- metrics
    raw_lux = G["E_eye"]
    eye_lux = raw_lux * filt["Td_lamp"]
    peak_wet = float(np.max(filt["spec"]))
    ext_db = -10 * np.log10(max(filt["Td_lamp"], 1e-9))
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Direct eye glare", f"{eye_lux:.3f} lx", f"{raw_lux:.1f} lx raw", delta_color="off")
    c2.metric("Peak wet-road glare", f"{peak_wet:.2f} lx", f"{float(np.max(raw['spec'])):.2f} lx raw",
              delta_color="off")
    c3.metric("Direct extinction", f"{ext_db:.1f} dB")
    c4.metric("Useful-light fraction", f"{filt['useful'] * 100:.0f}%")
    safe = eye_lux < 1.0 and peak_wet < 5.0
    c5.metric("Status", "Below 1 lx direct, 5 lx road" if safe else "Glare above limits")

    # ---- 3 panel pinhole POV
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.8), layout="constrained")
    norm = LogNorm(vmin=0.05, vmax=150)
    raw_img = np.clip(raw["scene"], 0.05, 150)
    flt_img = np.clip(filt["scene"], 0.05, 150)
    im1 = axs[0].pcolormesh(AZ_DEG, EL_DEG, raw_img, cmap="inferno", norm=norm, shading="auto")
    axs[1].pcolormesh(AZ_DEG, EL_DEG, flt_img, cmap="inferno", norm=norm, shading="auto")
    att = 10 * np.log10(np.maximum(raw["scene"], 1e-6) / np.maximum(filt["scene"], 1e-6))
    im3 = axs[2].pcolormesh(AZ_DEG, EL_DEG, np.clip(att, 0, 40), cmap="viridis", vmin=0, vmax=40,
                            shading="auto")
    titles = ["1. Unfiltered view", f"2. Filtered view\n{mode_name}", "3. Attenuation (raw / filtered)"]
    z_l = np.linspace(6, 100, 80)
    for ax, t in zip(axs, titles):
        ax.axhline(0, color="cyan", ls=":", alpha=0.5)
        for lx in (-4.5, 0.0, 4.5):
            ax.plot(np.degrees(np.arctan2(lx - OBS_X, z_l)), np.degrees(np.arctan2(-OBS_Y, z_l)),
                    "w--", alpha=0.35)
        ax.plot(np.degrees(G["az_b"]), np.degrees(G["el_b"]), "w*", ms=9)
        if mode == 5:
            ax.axhline(boundary, color="lime", ls="-.", alpha=0.7)
        ax.set_xlim(-22, 22)
        ax.set_ylim(-16, 8)
        ax.set_title(t, fontsize=10, fontweight="bold")
        ax.set_xlabel("Horizontal angle (deg)")
        ax.set_ylabel("Vertical angle (deg)")
    fig.colorbar(im1, ax=axs[:2], label="Retinal illuminance (lx)", fraction=0.03, pad=0.01)
    fig.colorbar(im3, ax=axs[2], label="Attenuation (dB)", fraction=0.05, pad=0.01)
    st.pyplot(fig)

    # ---- ellipse and Fresnel panels
    colA, colB = st.columns(2)
    with colA:
        E = state_at_analyzer(mode, lam, delta_pi * np.pi, np.radians(phi_deg))
        fig2, ax = plt.subplots(figsize=(5, 4.2), layout="constrained")
        if E is None:
            ax.text(0.5, 0.5, "Unpolarized lamp:\nno polarization ellipse", ha="center", va="center",
                    transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_title("Polarization state at analyzer entrance")
        else:
            t = np.linspace(0, 2 * np.pi, 300)
            ax.plot(np.real(E[0] * np.exp(-1j * t)), np.real(E[1] * np.exp(-1j * t)), lw=2.5,
                    color="dodgerblue")
            ax.set_xlim(-1.2, 1.2)
            ax.set_ylim(-1.2, 1.2)
            ax.set_aspect("equal")
            ax.grid(True, ls=":")
            ax.set_xlabel("$E_h$")
            ax.set_ylabel("$E_v$")
            ax.set_title(f"Polarization state at analyzer entrance: {chirality(E)}", fontsize=10)
        st.pyplot(fig2)
    with colB:
        th = np.linspace(0, 89.9, 400)
        rs, rp = fresnel(np.cos(np.radians(th)))
        w = G["valid"] & (G["lobe"] * G["wet_patch"] > 0.1 * np.max(G["lobe"] * G["wet_patch"]))
        lo, hi = float(np.min(G["theta_i"][w])), float(np.max(G["theta_i"][w]))
        fig3, ax = plt.subplots(figsize=(5.5, 4.2), layout="constrained")
        ax.plot(th, np.abs(rs) ** 2, label="$R_s$", color="crimson")
        ax.plot(th, np.abs(rp) ** 2, label="$R_p$", color="navy")
        ax.plot(th, flip_fraction(rs, rp), "--", label="RCP to LCP fraction", color="darkorange")
        ax.axvline(np.degrees(np.arctan(N_WATER)), color="gray", ls=":", label="Brewster")
        ax.axvspan(lo, hi, color="cyan", alpha=0.25, label=f"Glare incidence {lo:.0f} to {hi:.0f} deg")
        ax.set_xlabel("Incidence angle from road normal (deg)")
        ax.set_ylabel("Reflectance or fraction")
        ax.set_title("Air to water reflection (n = 1.33)", fontsize=10)
        ax.set_xlim(0, 90)
        ax.set_ylim(0, 1.02)
        ax.grid(True, ls=":")
        ax.legend(fontsize=8, loc="upper left")
        st.pyplot(fig3)

    with st.expander("Physics self-check"):
        for k, v in physics_checks(lam):
            st.write(f"**{k}:** {v}")

    st.caption("Assumed inputs: lamp intensity 80,000 cd, retardance range, wet patch position and width, "
               "specular lobe width, own-beam weighting. The direct glare is for the combined source at the "
               "chosen distance. Emitter film loss is assumed to be compensated by drive current, so all "
               "configurations use the same lamp output. Elements are ideal apart from the extinction ratio "
               "and the 550 nm wavelength dependence. Split-zone mode is kept as a negative result: reflected glare from compliant lamps stays circular, "
               "so the vertical lower zone passes about 50% of it, and a lamp entering the lower zone at close range "
               "is attenuated only about 50%.")


if __name__ == "__main__":
    main()