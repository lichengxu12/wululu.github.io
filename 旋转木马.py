# -*- coding: utf-8 -*-
"""
蓝白水晶 3D 旋转木马粒子动画（pygame 真发光 · 桌面悬浮版）
依赖：pygame-ce + numpy    运行：py 旋转木马粒子.py
发光：加法混合光斑（真光晕叠加），逐像素透明悬浮窗（UpdateLayeredWindow）-> 光晕直接叠在桌面壁纸上
形状：大尺寸旋转木马（锥形顶棚 + 波浪檐口 + 顶尖 + 中柱 + 六立柱 + 三匹木马 + 底座 + 八条灯串），绕垂直轴自转任何角度完整
动态：汇集后结构缓缓舒展 + 木马随旋转上下起伏 + 自转速度缓急变化 + 呼吸光晕
背景：双层视差星空 + 极光带 + 加密流星 + 上升光尘
退出：右键 / 双击 / Esc / q
"""
import os, sys, time, ctypes
from ctypes import wintypes
import numpy as np
import pygame

FPS = 60
CONV = 80                        # 汇集帧数
BLOOM_T = 2.5                    # 舒展动画时长（秒）
SPIN_T = 7.0                     # 自转基准周期（秒）
NOD_T = 9.0
F_PERSP = 55.0
N = 2934                         # 木马粒子数（顶棚 550 + 顶尖 80 + 檐口 240 + 灯串 264 + 中柱 160 + 立柱 360 + 底座 500 + 马 780）
DUST_N = 70                      # 上升光尘
SHOOT_N = 6                      # 流星

rng = np.random.default_rng(520)

# ---------- 3D 旋转木马采样 ----------
n_canopy, n_finial, n_eave, n_lights = 550, 80, 240, 264
n_cpole, n_poles, n_base, n_horse = 160, 360, 500, 780

# 顶棚：八棱帐篷锥面（微凹剖面 + 檐口波浪；按面积均匀采样避免顶点堆叠过曝）
th = rng.uniform(0, 2 * np.pi, n_canopy)
u = 1 - np.sqrt(1 - 2 * rng.uniform(0, 0.5, n_canopy))  # 0=檐口 1=顶点
r = 11.0 * (1 - u) ** 1.35 * (1 + 0.05 * np.cos(8 * th) * (1 - u))
canopy = np.column_stack([r * np.cos(th), 5.5 + 5.5 * u, r * np.sin(th)])
canopy += rng.normal(0, 0.12, canopy.shape)

# 顶尖：塔尖刺
uf = rng.uniform(0, 1, n_finial)
rf = 0.5 * (1 - uf) ** 0.8 * np.sqrt(rng.uniform(0.2, 1.0, n_finial))
tf = rng.uniform(0, 2 * np.pi, n_finial)
finial = np.column_stack([rf * np.cos(tf), 11.0 + 1.5 * uf, rf * np.sin(tf)])

# 檐口：波浪亮环（8 个扇贝，峰对齐棚棱）
te = rng.uniform(0, 2 * np.pi, n_eave)
re_ = 11.0 * rng.uniform(0.97, 1.04, n_eave)
eave = np.column_stack([re_ * np.cos(te), 5.5 + 0.6 * np.cos(8 * te) + rng.normal(0, 0.15, n_eave), re_ * np.sin(te)])

# 灯串：沿八条棚棱分布的灯珠
lights = []
for j in range(8):
    th_j = 2 * np.pi * j / 8
    s = rng.uniform(0.06, 0.98, n_lights // 8)
    rl = 11.0 * (1 - s) ** 1.35 * (1 + 0.05 * np.cos(8 * th_j) * (1 - s))
    lights.append(np.column_stack([rl * np.cos(th_j), 5.5 + 5.5 * s + 0.18, rl * np.sin(th_j)]))
lights = np.vstack(lights) + rng.normal(0, 0.06, (n_lights, 3))

# 中柱
yc = rng.uniform(-6.5, 11.0, n_cpole)
rc = 0.45 * np.sqrt(rng.uniform(0.1, 1.0, n_cpole))
tc = rng.uniform(0, 2 * np.pi, n_cpole)
cpole = np.column_stack([rc * np.cos(tc), yc, rc * np.sin(tc)])

# 六立柱
poles = []
for j in range(6):
    a = 2 * np.pi * j / 6
    m = n_poles // 6
    yp = rng.uniform(-6.5, 5.5, m)
    rp = 0.3 * np.sqrt(rng.uniform(0, 1, m))
    ap = rng.uniform(0, 2 * np.pi, m)
    poles.append(np.column_stack([7.0 * np.cos(a) + rp * np.cos(ap), yp, 7.0 * np.sin(a) + rp * np.sin(ap)]))
poles = np.vstack(poles)

# 底座：侧壁 + 顶面
n_bside, n_btop = 325, 175
tb = rng.uniform(0, 2 * np.pi, n_bside)
bside = np.column_stack([10.0 * np.cos(tb), rng.uniform(-7.5, -6.0, n_bside), 10.0 * np.sin(tb)])
rb = 10.0 * np.sqrt(rng.uniform(0, 1, n_btop))
tbt = rng.uniform(0, 2 * np.pi, n_btop)
btop = np.column_stack([rb * np.cos(tbt), np.full(n_btop, -6.0), rb * np.sin(tbt)])
base = np.vstack([bside, btop]) + rng.normal(0, 0.08, (n_base, 3))

# 木马：局部坐标 x=前进(切向) y=上 z=径向，再摆到立柱旁
def horse_cloud():
    pts = []
    m_body, m_legs, m_neck, m_head, m_mane, m_tail = 70, 84, 22, 30, 26, 28
    d = rng.normal(0, 1, (m_body, 3)); d /= np.linalg.norm(d, axis=1, keepdims=True)
    shell = 1 - 0.3 * rng.uniform(0, 1, m_body)[:, None]          # 身体：薄壳避免实心堆叠过曝
    pts.append(d * shell * np.array([1.5, 0.75, 0.5]))
    for lx, lz in [(0.85, 0.28), (0.85, -0.28), (-0.85, 0.28), (-0.85, -0.28)]:                  # 四肢
        m = m_legs // 4
        a = rng.uniform(0, 2 * np.pi, m); rr = 0.16 * np.sqrt(rng.uniform(0, 1, m))
        pts.append(np.column_stack([lx + rr * np.cos(a), rng.uniform(-2.1, -0.4, m), lz + rr * np.sin(a)]))
    s = rng.uniform(0, 1, m_neck)                                                                # 颈
    a = rng.uniform(0, 2 * np.pi, m_neck); rr = (0.30 - 0.10 * s) * np.sqrt(rng.uniform(0, 1, m_neck))
    pts.append(np.column_stack([1.10 + 0.75 * s + rr * np.cos(a), 0.35 + 1.00 * s, rr * np.sin(a)]))
    d = rng.normal(0, 1, (m_head, 3)); d /= np.linalg.norm(d, axis=1, keepdims=True)             # 头
    pts.append(d * rng.uniform(0, 1, m_head)[:, None] ** (1 / 3) * np.array([0.55, 0.28, 0.22]) + np.array([2.15, 1.50, 0.0]))
    s = rng.uniform(0, 1, m_mane)                                                                # 鬃毛
    a = rng.uniform(0, 2 * np.pi, m_mane); rr = 0.12 * np.sqrt(rng.uniform(0, 1, m_mane))
    pts.append(np.column_stack([1.00 + 0.80 * s - 0.22 * np.sin(np.pi * s) + rr * np.cos(a), 0.55 + 1.05 * s, rr * np.sin(a)]))
    s = rng.uniform(0, 1, m_tail)                                                                # 尾
    a = rng.uniform(0, 2 * np.pi, m_tail); rr = (0.16 - 0.06 * s) * np.sqrt(rng.uniform(0, 1, m_tail))
    pts.append(np.column_stack([-1.45 - 0.60 * s + rr * np.cos(a), 0.35 - 1.10 * s - 0.25 * np.sin(np.pi * s), rr * np.sin(a)]))
    return np.vstack(pts)

horses, horse_y = [], [1.8, -0.1, -2.0]
for j in range(3):
    a_j = 2 * np.pi * j / 3
    loc = horse_cloud() * 1.5
    tang = np.array([-np.sin(a_j), 0.0, np.cos(a_j)])
    rad_ = np.array([np.cos(a_j), 0.0, np.sin(a_j)])
    ctr = np.array([7.0 * np.cos(a_j), horse_y[j], 7.0 * np.sin(a_j)])
    horses.append(ctr + loc[:, 0:1] * tang + loc[:, 1:2] * np.array([0.0, 1.0, 0.0]) + loc[:, 2:3] * rad_)
horses = np.vstack(horses)

targets = np.vstack([canopy, finial, eave, lights, cpole, poles, base, horses])
targets += rng.normal(0, 0.10, targets.shape)
targets[:, 1] -= (targets[:, 1].max() + targets[:, 1].min()) / 2
center = targets[:, :2].mean(axis=0)

# 每粒子所属层（舒展动画用）：0 顶棚/顶尖 / 1 马 / 2 底座 / 3 檐口/灯串 / 4 中柱/立柱
layer_id = np.concatenate([np.zeros(n_canopy + n_finial, int), np.full(n_eave + n_lights, 3),
                           np.full(n_cpole + n_poles, 4), np.full(n_base, 2), np.full(n_horse, 1)])

# 木马起伏：每匹马一个相位，随自转上下滑动
bob_amp = np.zeros(N)
bob_ph = np.zeros(N)
h0 = n_canopy + n_finial + n_eave + n_lights + n_cpole + n_poles + n_base
bob_amp[h0:h0 + n_horse] = 0.8
for j in range(3):
    bob_ph[h0 + j * (n_horse // 3):h0 + (j + 1) * (n_horse // 3)] = 2 * np.pi * j / 3

# ---------- 汇聚路径 ----------
ang = rng.uniform(0, 2 * np.pi, N)
rad = rng.uniform(48, 70, N)
starts = np.column_stack([rad * np.cos(ang), rad * np.sin(ang), rng.uniform(-22, 22, N)])
ctrl = (targets + starts) / 2 + rng.normal(0, 16, (N, 3))
delays = rng.uniform(0, 0.35, N)

# ---------- 蓝白调色板（24 级冰色） ----------
ICE = np.array([[25, 118, 210], [66, 165, 245], [130, 212, 255], [200, 236, 255], [255, 255, 255]], float)
def ice_rgb(t):
    t = np.clip(t, 0, 1) * (len(ICE) - 1)
    i = np.clip(t.astype(int), 0, len(ICE) - 2)
    f = (t - i)[:, None]
    return ICE[i] * (1 - f) + ICE[i + 1] * f

PAL_N = 24
palette = ice_rgb(np.linspace(0, 1, PAL_N))
p_t = np.zeros(N)
_i = 0
def put(n, lo, hi):
    global _i
    p_t[_i:_i + n] = rng.uniform(lo, hi, n)
    _i += n
put(n_canopy, 0.20, 0.60); put(n_finial, 0.55, 0.95); put(n_eave, 0.70, 1.00); put(n_lights, 0.80, 1.00)
put(n_cpole, 0.10, 0.35); put(n_poles, 0.25, 0.60); put(n_base, 0.25, 0.60)
for _j in range(3):   # 马：躯干薄壳中亮成体积，四肢/颈/头/鬃/尾稍亮勾轮廓
    put(70, 0.30, 0.60); put(84, 0.40, 0.75); put(22, 0.35, 0.70)
    put(30, 0.40, 0.75); put(26, 0.45, 0.80); put(28, 0.40, 0.75)
p_idx = np.clip((p_t * (PAL_N - 1)).astype(int), 0, PAL_N - 1)

_hsz = np.concatenate([rng.uniform(0.5, 0.85, 70), rng.uniform(0.45, 0.8, 84), rng.uniform(0.45, 0.8, 22),
                       rng.uniform(0.5, 0.85, 30), rng.uniform(0.5, 0.85, 26), rng.uniform(0.45, 0.8, 28)])
p_size = np.concatenate([rng.uniform(0.65, 1.1, n_canopy), rng.uniform(0.8, 1.3, n_finial),
                         rng.uniform(0.85, 1.4, n_eave), rng.uniform(0.75, 1.3, n_lights),
                         rng.uniform(0.45, 0.8, n_cpole), rng.uniform(0.55, 0.9, n_poles),
                         rng.uniform(0.5, 0.85, n_base), np.tile(_hsz, 3)])
glint_phase = rng.uniform(0, 2 * np.pi, N)
glint_speed = rng.uniform(0.14, 0.36, N)

# ---------- 背景：双层视差星空 / 极光 / 流星 / 光尘 ----------
star_xy = [np.column_stack([rng.uniform(0, 1, 90), rng.uniform(0, 1, 90)]),
           np.column_stack([rng.uniform(0, 1, 70), rng.uniform(0, 1, 70)])]
star_spd = [0.004, 0.011]                       # 视差：远慢近快（每秒屏幕比例）
star_phase = [rng.uniform(0, 2 * np.pi, 90), rng.uniform(0, 2 * np.pi, 70)]
aurora_col = [(25, 118, 210), (66, 165, 245), (130, 212, 255)]
shoot = [[rng.uniform(-0.5, 0.3), rng.uniform(0.1, 0.45), np.cos(da), np.sin(da),
          rng.uniform(0.5, 0.8), rng.uniform(4, 8), rng.uniform(0, 8), 0.7]
         for da in rng.uniform(-0.9, -0.35, SHOOT_N)]
dust = np.column_stack([rng.uniform(0.30, 0.70, DUST_N), rng.uniform(0, 1, DUST_N)])
dust_v = rng.uniform(0.03, 0.08, DUST_N)
dust_ph = rng.uniform(0, 2 * np.pi, DUST_N)

# ---------- pygame 初始化 ----------
os.environ.setdefault("SDL_VIDEO_WINDOW_POS", "0,0")
pygame.init()
info = pygame.display.Info()
SW, SH = info.current_w, info.current_h
W, H = SW // 2, SH // 2                        # 内部半分辨率渲染，ULW 拉伸输出
screen = pygame.display.set_mode((SW, SH), pygame.NOFRAME)
pygame.mouse.set_visible(False)
clock = pygame.time.Clock()
scene = pygame.Surface((W, H), pygame.SRCALPHA)

# ---------- 光斑精灵（预渲染：24 色 x 4 尺寸档，光晕+核心合并为单精灵，每粒子一次 blit） ----------
TIERS = [0.6, 0.85, 1.15, 1.5]
def radial_sprite(radius, rgb, peak, power):
    yy, xx = np.mgrid[0:radius * 2, 0:radius * 2]
    d = np.clip(np.hypot(xx - radius + 0.5, yy - radius + 0.5) / radius, 0, 1)
    a = ((1 - d) ** power * peak).astype(np.uint8)
    arr = np.zeros((radius * 2, radius * 2, 4), np.uint8)
    rgbm = (np.asarray(rgb, float) * a[:, :, None] / 255.0).astype(np.uint8)  # 预乘 alpha：RGBA_ADD 才能正确叠光
    arr[:, :, :3] = rgbm
    arr[:, :, 3] = a
    return pygame.image.frombuffer(arr.tobytes(), (radius * 2, radius * 2), "RGBA")

def spark_sprite(radius, rgb, halo_peak, core_peak):
    # 宽光晕 + 亮核心合并成一张预乘精灵：密集堆叠时单粒子贡献更低、整体仍饱满
    R = radius * 2
    yy, xx = np.mgrid[0:R, 0:R]
    dd = np.hypot(xx - radius + 0.5, yy - radius + 0.5)
    a_h = (1 - np.clip(dd / radius, 0, 1)) ** 2.2 * halo_peak
    rgb_h = np.asarray(rgb, float) * 0.55 * a_h[:, :, None] / 255.0
    rc = max(2.0, radius / 3.0)
    a_c = (1 - np.clip(dd / rc, 0, 1)) ** 1.8 * core_peak
    rgb_c = (np.asarray(rgb, float) * 0.5 + 127.5) * a_c[:, :, None] / 255.0
    arr = np.zeros((R, R, 4), np.uint8)
    arr[:, :, :3] = np.clip(rgb_h + rgb_c, 0, 255).astype(np.uint8)
    arr[:, :, 3] = np.clip(a_h + a_c, 0, 255).astype(np.uint8)
    return pygame.image.frombuffer(arr.tobytes(), (R, R), "RGBA")

sparks = [[spark_sprite(int(9 * t), c, 30, 100) for t in TIERS] for c in palette.astype(int)]
cores = [[radial_sprite(max(2, int(3 * t)), (c * 0.5 + 255 * 0.5).astype(int), 80, 1.8) for t in TIERS]
         for c in palette.astype(int)]                                            # 流星/光尘用
white_halo = [radial_sprite(int(10 * t), (255, 255, 255), 50, 2.0) for t in TIERS]
breath_sp = [radial_sprite(int(36 * t), (200, 236, 255), 20, 2.4) for t in TIERS]  # 顶棚呼吸光晕
star_sp = [radial_sprite(r, (255, 255, 255), 210, 1.7) for r in (3, 4, 6)]         # 背景星星
aurora_sp = [radial_sprite(90, c, 22, 1.3) for c in aurora_col]
aurora_sp = [pygame.transform.scale(s, (760, 200)) for s in aurora_sp]   # 拉宽成极光带

# ---------- 逐像素透明悬浮窗（Win32 UpdateLayeredWindow） ----------
layered = False
if pygame.display.get_driver() not in ("dummy", "off"):
    try:
        user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
        hwnd = pygame.display.get_wm_info()["window"]
        GWL_EXSTYLE, WS_EX_LAYERED = -20, 0x80000
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE,
                              user32.GetWindowLongW(hwnd, GWL_EXSTYLE) | WS_EX_LAYERED)
        user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)

        class BMI(ctypes.Structure):
            _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                        ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                        ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                        ("biSizeImage", wintypes.DWORD), ("biXPels", wintypes.LONG),
                        ("biYPels", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                        ("biClrImp", wintypes.DWORD)]

        class BLENDF(ctypes.Structure):
            _fields_ = [("op", wintypes.BYTE), ("flags", wintypes.BYTE),
                        ("alpha", wintypes.BYTE), ("fmt", wintypes.BYTE)]

        class POINT(ctypes.Structure):
            _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

        class SIZE(ctypes.Structure):
            _fields_ = [("cx", wintypes.LONG), ("cy", wintypes.LONG)]

        hdc_scr = user32.GetDC(0)
        bmi = BMI()
        bmi.biSize = ctypes.sizeof(BMI)
        bmi.biWidth, bmi.biHeight, bmi.biPlanes, bmi.biBitCount = SW, -SH, 1, 32
        bits = ctypes.c_void_p()
        mem_dc = gdi32.CreateCompatibleDC(hdc_scr)
        dib = gdi32.CreateDIBSection(hdc_scr, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
        gdi32.SelectObject(mem_dc, dib)
        blend = BLENDF(0, 0, 255, 1)
        pt_dst, pt_src, sz = POINT(0, 0), POINT(0, 0), SIZE(SW, SH)
        bgra = np.empty((SH, SW, 4), np.uint8)
        layered = True
    except Exception:
        layered = False

def present():
    """把加法混合的 scene 提交到屏幕：透明模式走 ULW（逐像素 alpha），否则黑底不透明"""
    if layered:
        big = pygame.transform.scale(scene, (SW, SH))
        rgb = pygame.surfarray.pixels3d(big)
        alp = pygame.surfarray.pixels_alpha(big)
        bgra[:, :, 0] = rgb[:, :, 2].T          # surfarray 轴序 (x,y) -> DIB 扫描线 (y,x)
        bgra[:, :, 1] = rgb[:, :, 1].T
        bgra[:, :, 2] = rgb[:, :, 0].T
        bgra[:, :, 3] = alp.T
        del rgb, alp                     # scene 已是预乘结果（加法混合），符合 ULW 要求
        ctypes.memmove(bits, bgra.ctypes.data, SW * SH * 4)
        user32.UpdateLayeredWindow(hwnd, hdc_scr, ctypes.byref(pt_dst), ctypes.byref(sz),
                                   mem_dc, ctypes.byref(pt_src), 0, ctypes.byref(blend), 2)
    else:
        screen.fill((0, 0, 0))
        pygame.transform.scale(scene, (SW, SH), screen)
        pygame.display.flip()

# ---------- 主循环 ----------
az_state = 0.0
frame = 0
last_click = -9.0
running = True
t0 = time.perf_counter()

while running:
    dt = clock.tick(FPS) / 1000.0
    t = frame / FPS
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
        elif e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_q):
            running = False
        elif e.type == pygame.MOUSEBUTTONDOWN:
            if e.button == 3:
                running = False
            elif e.button == 1 and t - last_click < 0.35:
                running = False
            elif e.button == 1:
                last_click = t
    if not running:
        break

    scene.fill((0, 0, 0, 0))
    ADD = pygame.BLEND_RGBA_ADD

    # 双层视差星空（闪烁）
    for li in (0, 1):
        xs = (star_xy[li][:, 0] + t * star_spd[li]) % 1.0 * W
        ysv = star_xy[li][:, 1] * H
        tw = 0.5 + 0.5 * np.sin(star_phase[li] + frame * (0.05 if li == 0 else 0.09))
        for x, y, b in zip(xs, ysv, tw):
            tier = 0 if b < 0.45 else (1 if b < 0.8 else 2)
            s = star_sp[tier]
            scene.blit(s, (int(x) - s.get_width() // 2, int(y) - s.get_height() // 2), special_flags=ADD)

    # 极光带：缓慢漂移的宽光带
    for i, s in enumerate(aurora_sp):
        x = int((0.2 + 0.3 * i + 0.05 * np.sin(t * 0.13 + i * 2.1)) * W - s.get_width() // 2)
        y = int((0.12 + 0.10 * i) * H + 10 * np.sin(t * 0.21 + i))
        scene.blit(s, (x, y), special_flags=ADD)

    # 流星（加密）
    for x0, y0, dx, dy, spd, per, off, dur in shoot:
        u = ((t + off) % per) / dur
        if u < 1.0:
            hx = (x0 + dx * spd * u * dur) * W
            hy = (y0 + dy * spd * u * dur) * H
            fade = np.sin(np.pi * u)
            for k in range(8):
                px, py = hx - dx * k * 5, hy - dy * k * 5
                tier = 2 if k < 2 else (1 if k < 5 else 0)
                s = white_halo[tier] if k == 0 else cores[PAL_N - 1][tier]
                a = fade * (1 - k / 8)
                if a > 0.15:
                    scene.blit(s, (int(px) - s.get_width() // 2, int(py) - s.get_height() // 2),
                               special_flags=ADD)

    # ---- 木马粒子位置 ----
    if frame < CONV:
        settle = 0.0
        p = np.clip(frame / CONV, 0, 1)
        u = np.clip((p - delays) / (1 - delays + 1e-9), 0, 1)
        u = u * u * (3 - 2 * u)
        pos3 = ((1 - u) ** 2)[:, None] * starts + (2 * (1 - u) * u)[:, None] * ctrl + (u ** 2)[:, None] * targets
        bloom = np.zeros(5)
    else:
        settle = min((frame - CONV) / 90, 1)
        pos3 = targets
        bt = (frame - CONV) / FPS / BLOOM_T          # 舒展：顶棚先展开，马与底座随后
        bloom = np.clip((bt - np.array([0.0, 0.25, 0.5, 0.6, 1e9])), 0, 1)
        bloom = bloom * bloom * (3 - 2 * bloom)

    # 舒展动画：各层半径/高度从收拢到舒展（中柱/立柱不变）
    r_sc = np.where(layer_id < 4, 0.55 + 0.45 * bloom[layer_id], 1.0)
    v_sc = np.where(layer_id < 4, 0.80 + 0.20 * bloom[layer_id], 1.0)

    # 自转速度缓急变化 + 俯仰
    az_state += dt * 2 * np.pi / SPIN_T * (1 + 0.15 * np.sin(2 * np.pi * t / 9)) * settle
    ax_t = -(0.30 + 0.05 * np.sin(2 * np.pi * t / NOD_T)) * settle   # 俯仰：微俯视看清顶棚与底座椭圆

    X = (pos3[:, 0] - center[0]) * r_sc
    Y = (pos3[:, 1] - center[1] + 2.0) * v_sc - 2.0
    Y += bob_amp * np.sin(2.0 * az_state + bob_ph) * settle          # 木马随旋转上下起伏
    Z = pos3[:, 2] * r_sc * settle
    cz_, sz_ = np.cos(az_state), np.sin(az_state)
    X2 = X * cz_ + Z * sz_
    Z2 = -X * sz_ + Z * cz_
    cy_, sy_ = np.cos(ax_t), np.sin(ax_t)
    Y1 = Y * cy_ - Z2 * sy_
    Z1 = Y * sy_ + Z2 * cy_

    s = F_PERSP / (F_PERSP + Z1)
    k = min(W, H) / 42.0
    beat = 1 + 0.05 * (np.sin(t * 2 * np.pi / 1.1) + 0.45 * np.sin(4 * np.pi * t / 1.1))
    px = (X2 * s * beat * k + W / 2).astype(int)
    py = (H / 2 - Y1 * s * beat * k).astype(int)          # pygame y 轴向下，需翻转

    g = np.maximum(0, np.sin(glint_phase + frame * glint_speed)) ** 10
    wave = 0.5 + 0.5 * np.sin(2 * np.arctan2(Y1, X2) - frame * 0.05)   # 流光带
    near = np.clip((s - 1) * 1.4 + 0.15, 0, 1)
    bright = np.clip(0.16 + 0.32 * wave + 0.35 * near + 0.55 * g, 0, 1)   # 低基线：密集堆叠不过曝，星芒更跳
    tier = np.clip((bright * (0.6 + 0.5 * p_size) * 3.99).astype(int), 0, 3)

    for i in range(N):                                                  # 加法混合与顺序无关
        sp = sparks[p_idx[i]][tier[i]]
        hw = sp.get_width() // 2
        scene.blit(sp, (px[i] - hw, py[i] - hw), special_flags=ADD)
        if g[i] > 0.5:                                                  # 星芒闪：叠加白光晕
            ws = white_halo[tier[i]]
            ww = ws.get_width() // 2
            scene.blit(ws, (px[i] - ww, py[i] - ww), special_flags=ADD)

    # 呼吸光晕：顶棚处随节拍脉动的大光晕
    head_x = W // 2
    head_y = int(H / 2 - 6.0 * k * beat)
    bp = 0.5 + 0.5 * np.sin(t * 2 * np.pi / 1.1)
    ws = breath_sp[1 if bp < 0.5 else (2 if bp < 0.8 else 3)]
    scene.blit(ws, (head_x - ws.get_width() // 2, head_y - ws.get_height() // 2), special_flags=ADD)

    # 上升光尘：木马周围缓缓上浮的微光
    dy_ = (dust[:, 1] - t * dust_v) % 1.0
    dx_ = dust[:, 0] + 0.015 * np.sin(dust_ph + t * 0.7)
    fade = np.sin(np.pi * dy_)
    for x, y, f, ph in zip(dx_, dy_, fade, dust_ph):
        if f < 0.12:
            continue
        s2 = cores[18 + int(3 * (0.5 + 0.5 * np.sin(ph + t)))] [0 if f < 0.5 else 1]
        scene.blit(s2, (int(x * W) - 3, int((0.15 + 0.75 * y) * H) - 3), special_flags=ADD)

    present()
    frame += 1
    lim = os.environ.get("ROSE_FRAMES")          # 无头验证：跑满指定帧数存预览后退出
    if lim and frame >= int(lim):
        save = os.environ.get("ROSE_SAVE")
        if save:
            prev = pygame.Surface((SW, SH))
            prev.fill((6, 10, 18))
            prev.blit(pygame.transform.scale(scene, (SW, SH)), (0, 0))
            pygame.image.save(prev, save)
        running = False

pygame.quit()
sys.exit(0)
