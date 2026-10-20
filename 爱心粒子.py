# -*- coding: utf-8 -*-
"""
蓝白水晶 3D 旋转爱心粒子动画 v8（桌面悬浮版）
依赖：matplotlib + numpy    运行：python 爱心粒子.py
效果：无边框透明全屏层，明亮的蓝白水晶粒子浮在桌面上（可看到壁纸/图标）
      无暗色粒子：全部粒子保持高亮度，近处泛白 + 空间流光带 + 星芒 + 流星 + 强光晕
退出：鼠标右键单击，或双击任意处（Esc 也可，取决于窗口焦点）
"""
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.animation import FuncAnimation
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

MAGIC = "#010203"                # 透明魔法色：该颜色的像素会被 Windows 抠掉

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun"]
plt.rcParams["axes.unicode_minus"] = False

FPS = 60
CONV = 160
BEAT_T = 1.1
SPIN_T = 4.0                     # 3D 自转一圈周期（秒）
NOD_T = 9.0
TRAIL = 4                        # 拖尾层数
F_PERSP = 55.0
N = 900                          # 粒子数
N_EDGE = int(N * 0.45)
STAR_N = 160
SPARK_N = 90                     # 星芒闪烁粒子数
SHOOT_N = 4                      # 流星数量

rng = np.random.default_rng(520)

# ---------- 2D 心形采样点 ----------
def heart_xy(tt):
    return np.column_stack([16 * np.sin(tt) ** 3,
                            13 * np.cos(tt) - 5 * np.cos(2 * tt)
                            - 2 * np.cos(3 * tt) - np.cos(4 * tt)])

te = np.linspace(0, 2 * np.pi, N_EDGE, endpoint=False)
edge_raw = heart_xy(te)
edge_noisy = edge_raw + rng.normal(0, 0.16, edge_raw.shape)
tf = rng.uniform(0, 2 * np.pi, N - N_EDGE)
rf = np.sqrt(rng.uniform(0.05, 0.90, N - N_EDGE))
fill = heart_xy(tf) * rf[:, None]
targets = np.vstack([edge_noisy, fill])
targets_tidy = np.vstack([edge_raw, fill])
depth2d = np.concatenate([np.ones(N_EDGE), rf])
center = targets_tidy.mean(axis=0)

# ---------- 3D 厚度：透镜状水晶心 ----------
rr = np.hypot(*(targets_tidy - center).T) / 17.5
bulge = np.sqrt(np.clip(1 - rr ** 2, 0, 1))
Z3 = rng.choice([-1.0, 1.0], N) * 8.0 * bulge * rng.uniform(0.3, 1.0, N)

# ---------- 汇聚路径 ----------
ang = rng.uniform(0, 2 * np.pi, N)
rad = rng.uniform(48, 70, N)
starts = np.column_stack([rad * np.cos(ang), rad * np.sin(ang)])
ctrl = (targets + starts) / 2 + rng.normal(0, 16, (N, 2))
delays = rng.uniform(0, 0.35, N)

# ---------- 明亮蓝白配色（去掉深蓝/近黑段，最暗也是亮蓝） ----------
crystal = mcolors.LinearSegmentedColormap.from_list(
    "ice", ["#1976d2", "#42a5f5", "#82d4ff", "#c8ecff", "#ffffff"])
pcolors = crystal(0.25 + 0.70 * (1 - depth2d))
pcolors[:N_EDGE] = crystal(1.0)           # 轮廓纯白
psizes = np.concatenate([rng.uniform(11, 24, N_EDGE),
                         rng.uniform(4, 14, N - N_EDGE)])
glint_phase = rng.uniform(0, 2 * np.pi, N)
glint_speed = rng.uniform(0.14, 0.36, N)  # 闪光更频繁

# ---------- 星芒闪烁粒子 ----------
spark_idx = rng.choice(N, SPARK_N, replace=False)
spark_phase = rng.uniform(0, 2 * np.pi, SPARK_N)
spark_speed = rng.uniform(0.18, 0.34, SPARK_N)

# ---------- 背景星星 ----------
star_xy = np.column_stack([rng.uniform(-40, 40, STAR_N), rng.uniform(-32, 32, STAR_N)])
star_s = rng.uniform(1, 10, STAR_N)
star_phase = rng.uniform(0, 2 * np.pi, STAR_N)
star_speed = rng.uniform(0.04, 0.14, STAR_N)
star_base = rng.uniform(0.3, 0.9, STAR_N)

# ---------- 流星 ----------
shoot = []
for _ in range(SHOOT_N):
    x0 = rng.uniform(-38, 8)
    y0 = rng.uniform(12, 30)
    da = rng.uniform(-0.9, -0.35)          # 向右下方划过
    shoot.append([x0, y0, np.cos(da), np.sin(da),
                  rng.uniform(55, 85),      # 速度（单位/秒）
                  rng.uniform(5, 9),        # 出现周期（秒）
                  rng.uniform(0, 9), 0.7])  # 相位偏移、单次持续

# ---------- 画布（背景必须为 MAGIC 色，桌面才能透出来） ----------
fig, ax = plt.subplots(figsize=(16, 9), dpi=90)
fig.patch.set_facecolor(MAGIC)
ax.set_facecolor(MAGIC)
ax.set_xlim(-40, 40)
ax.set_ylim(-32, 32)
ax.axis("off")

star_rgba = np.column_stack([np.full(STAR_N, 0.80), np.full(STAR_N, 0.92),
                             np.ones(STAR_N), np.clip(star_base, 0, 1)])
stars = ax.scatter(star_xy[:, 0], star_xy[:, 1], s=star_s, c=star_rgba, zorder=1)
shoot_lines = [ax.plot([], [], lw=1.6, color="#bfe8ff", alpha=0,
                       zorder=1.5, solid_capstyle="round")[0] for _ in shoot]
glow = ax.scatter(starts[:, 0], starts[:, 1], s=psizes * 6, c=pcolors,
                  alpha=0.11, zorder=2)    # 更强的光晕

hist = np.repeat(starts[None], TRAIL, 0)
layer = np.repeat(np.arange(TRAIL), N)
trail_cols = np.tile(pcolors, (TRAIL, 1))
trail_cols[:, 3] = 0.38 * ((layer + 1) / TRAIL) ** 1.5   # 拖尾更亮
trail_sizes = np.tile(psizes, TRAIL) * (0.15 + 0.45 * (layer + 1) / TRAIL)
p0 = hist.reshape(-1, 2)
trail = ax.scatter(p0[:, 0], p0[:, 1], s=trail_sizes, c=trail_cols, zorder=2.5)

heart = ax.scatter(starts[:, 0], starts[:, 1], s=psizes, c=pcolors, zorder=4)
sparks = ax.scatter([], [], marker="*", s=0, c="#ffffff", zorder=5)


def update(frame):
    sc = stars.get_facecolor().copy()
    sc[:, 3] = np.clip(star_base + 0.4 * np.sin(star_phase + frame * star_speed), 0.05, 1)
    stars.set_facecolor(sc)

    # 流星：周期性划过天空
    tsec = frame / FPS
    for line, (x0, y0, dx, dy, spd, per, off, dur) in zip(shoot_lines, shoot):
        u = ((tsec + off) % per) / dur
        if u < 1.0:
            d = spd * u * dur
            hx, hy = x0 + dx * d, y0 + dy * d
            line.set_data([hx - dx * 7, hx], [hy - dy * 7, hy])
            line.set_alpha(np.sin(np.pi * u) * 0.85)
        else:
            line.set_alpha(0)

    g = np.maximum(0, np.sin(glint_phase + frame * glint_speed)) ** 10
    ph = frame / FPS * 2 * np.pi / BEAT_T
    scale = 1 + 0.05 * (np.sin(ph) + 0.45 * np.sin(2 * ph))

    if frame < CONV:
        settle = 0.0
        p = np.clip(frame / CONV, 0, 1)
        u = np.clip((p - delays) / (1 - delays + 1e-9), 0, 1)
        u = u * u * (3 - 2 * u)
        pos_xy = ((1 - u) ** 2)[:, None] * starts \
            + (2 * (1 - u) * u)[:, None] * ctrl \
            + (u ** 2)[:, None] * targets
    else:
        settle = min((frame - CONV) / 90, 1)
        pos_xy = targets + (targets_tidy - targets) * settle

    X = pos_xy[:, 0] - center[0]
    Y = pos_xy[:, 1] - center[1]
    Z = Z3 * settle
    az = settle * (frame - CONV) / FPS * 2 * np.pi / SPIN_T
    ax_t = (0.15 + 0.10 * np.sin(2 * np.pi * (frame - CONV) / FPS / NOD_T)) * settle

    cy_, sy_ = np.cos(ax_t), np.sin(ax_t)
    Y1 = Y * cy_ - Z * sy_
    Z1 = Y * sy_ + Z * cy_
    cz_, sz_ = np.cos(az), np.sin(az)
    X2 = X * cz_ + Z1 * sz_
    Z2 = -X * sz_ + Z1 * cz_

    s = F_PERSP / (F_PERSP + Z2)
    pos = np.column_stack([X2 * s, Y1 * s]) * scale + center

    hist[:-1] = hist[1:]
    hist[-1] = pos
    trail.set_offsets(hist.reshape(-1, 2))

    idx = np.argsort(-Z2)
    heart.set_offsets(pos[idx])
    glow.set_offsets(pos)

    # 空间流光带：光带固定，旋转的水晶心不断穿过它
    wave = 0.5 + 0.5 * np.sin(2 * np.arctan2(Y1, X2) - frame * 0.05)
    near = np.clip((s - 1) * 1.4 + 0.15, 0, 1)          # 近处泛白
    # 亮度下限 0.2：任何粒子都不会变暗发黑
    w = np.clip(0.20 + 0.30 * wave + 0.45 * near + 0.55 * g, 0.2, 0.97)

    # 透明度下限 0.45：消灭暗色粒子
    a = np.clip(0.45 + 0.4 * g + 0.5 * (s - 1), 0.45, 1)
    hc = pcolors.copy()
    hc[:, :3] = hc[:, :3] * (1 - w[:, None]) + w[:, None]   # 向纯白混色
    hc[:, 3] = a
    heart.set_facecolor(hc[idx])
    heart.set_sizes((psizes * (0.85 + 0.9 * g) * s ** 2 * scale ** 2)[idx])
    glow.set_sizes(psizes * 6 * scale ** 2)

    # 星芒：白色四角星芒，更大更亮
    sp = np.maximum(0, np.sin(spark_phase + frame * spark_speed)) ** 12
    sparks.set_offsets(pos[idx][spark_idx])
    sparks.set_sizes(sp * 130)
    sparks.set_alpha(np.clip(sp * 1.8, 0, 1))
    return (stars, heart, glow, trail, sparks, *shoot_lines)


def main():
    anim = FuncAnimation(fig, update, frames=None, interval=1000 / FPS,
                         blit=True, cache_frame_data=False)

    win = fig.canvas.manager.window
    win.overrideredirect(True)                    # 去掉标题栏和边框
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    win.geometry(f"{sw}x{sh}+0+0")                # 手动铺满屏幕（与 overrideredirect 兼容）
    win.attributes("-transparentcolor", MAGIC)    # MAGIC 色像素透明 -> 透出桌面
    win.config(cursor="none")                     # 隐藏鼠标，屏保感

    def quit_(event=None):
        plt.close(fig)

    win.bind("<Button-3>", quit_)                 # 右键退出
    win.bind("<Double-Button-1>", quit_)          # 双击退出

    def on_key(event):
        if event.key in ("escape", "q"):
            plt.close(fig)

    fig.canvas.mpl_connect("key_press_event", on_key)
    plt.show()


if __name__ == "__main__":
    main()
