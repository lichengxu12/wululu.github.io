# -*- coding: utf-8 -*-
"""
连环关心弹窗表白（爱心成形版）
单文件、纯 Python 标准库(tkinter)，无任何外部依赖
运行：python 连环关心弹窗.py

流程：
  1. 先沿爱心轮廓逐颗弹出关心弹窗，围成大爱心
  2. 爱心围成后停留片刻，整颗爱心自动淡出消失
  3. 随后满屏疯狂弹出大量关心弹窗（常驻不消失，越多越好）
  4. 最后屏幕中央压轴弹出【一键收到 ❤】窗口，点击后终止整个程序
  5. 其他退出方式：Esc；单个弹窗点【收到 ❤】可手动关掉
"""
import tkinter as tk
import random
import math

# ============ 可自由修改的内容区 ============
HEART_POINTS = 40             # 第一阶段：爱心轮廓弹窗数量
HEART_INTERVAL = 130          # 第一阶段：弹出间隔（毫秒）
HEART_STAY = 1600             # 爱心围成后停留时长（毫秒），随后淡出
RND_COUNT = 100               # 第二阶段：满屏随机弹窗数量（越多越好）
RND_INTERVAL = 45             # 第二阶段：弹出间隔（毫秒）
CARING = [
    "今天也要记得吃早饭，别空腹喝咖啡 ☕",
    "天气预报说会降温，外套记得穿，别只要风度",
    "忙起来也别忘了喝水，一天八杯，我远程监督你",
    "今晚十一点半前必须睡觉，熬夜的我可是会知道的",
    "屏幕看久了就望望窗外，眼睛比手机重要",
    "如果今天有点累，允许自己难过五分钟，第五分钟开始要笑",
    "午饭别糊弄，好好吃饭的人才有力气被喜欢",
    "出门记得带钥匙和伞，还有——带上想念",
    "今晚散步二十分钟吧，我隔着屏幕陪你走",
    "早晚凉，多带一件薄外套，别嫌麻烦",
    "今天紫外线强，防晒霜涂够，别晒黑了我心疼",
    "中午眯十五分钟，下午才有精神，别硬撑",
    "今日份的想念已送达，请查收，不接受退货 💌",
    "你今天也很棒哦，别忘了给自己一点掌声 👏",
    "晚上别饿着，实在想吃就吃点热的，我陪你",
    "天气预报：你所在区域今天全天有我的喜欢 ☀",
    "水杯举一举，跟我一起干杯 🥤",
    "背挺直！别窝在椅子里，小腰受不了",
    "到点就撤，工作是做不完的，但快乐是自己给的",
    "走路别看手机，车多人杂，安全第一",
    "头发该洗就洗，香香的好心情是自己给的 🫧",
    "喜欢的剧记得看，别攒着，快乐要即时",
    "现在，跟我一起：吸气——呼气——有没有轻松一点",
    "受委屈了可以说给我听，我嘴笨但永远站你这边",
    "再忙也要好好吃饭，你健康我就安心",
    "今天的风很温柔，像想到你时的我",
    "记得涂护手霜，手冰冰凉凉我会心疼",
    "这条没有别的意思，就是想跟你说一声：晚安 🌙",
]
# ==========================================

FONT = "Microsoft YaHei UI"
POP_W, POP_H = 290, 106       # 弹窗尺寸（已调小）


def heart_outline(n, sw, sh):
    """心形参数方程取 n 个屏幕坐标（弹窗左上角），从顶部凹陷顺时针绕行"""
    cx, cy = sw / 2, sh / 2 - 20
    scale = min((sw - POP_W - 60) / 34.0, (sh - POP_H - 140) / 26.0)
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        hx = 16 * math.sin(t) ** 3
        hy = -(13 * math.cos(t) - 5 * math.cos(2 * t)
               - 2 * math.cos(3 * t) - math.cos(4 * t))
        x = max(0, min(cx + hx * scale - POP_W / 2, sw - POP_W))
        y = max(0, min(cy + hy * scale - POP_H / 2, sh - POP_H - 40))
        pts.append((int(x), int(y)))
    # 爱心图形 y∈[-7,17]，视觉中心比几何中心略低
    center = (cx, cy + 5 * scale)
    return pts, center, scale


class ConfessionApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.sw = self.root.winfo_screenwidth()
        self.sh = self.root.winfo_screenheight()
        # hcenter 是爱心视觉中心 (x, y) 元组
        self.pts, self.hcenter, self.hscale = heart_outline(HEART_POINTS, self.sw, self.sh)
        self.dodged = set()
        self.heart_windows = []   # 记录爱心轮廓弹窗，用于统一淡出
        self.idx = 0
        self.phase1()

    # ---------- 消息弹窗通用（全部常驻，不自动消失） ----------
    def make_popup(self, title, msg, x, y):
        w = tk.Toplevel(self.root)
        w.title(title)
        w.resizable(False, False)
        w.geometry(f"{POP_W}x{POP_H}+{int(x)}+{int(y)}")
        w.configure(bg="#f4f7fb", highlightbackground="#c9d6e8", highlightthickness=1)

        tk.Label(w, text=f"💌 {title}", font=(FONT, 9, "bold"),
                 bg="#f4f7fb", fg="#2c5aa0").pack(anchor="w", padx=12, pady=(6, 2))
        tk.Label(w, text=msg, font=(FONT, 9), bg="#f4f7fb", fg="#333",
                 wraplength=POP_W - 28, justify="left").pack(anchor="w", padx=12)

        tk.Button(w, text="收到 ❤", font=(FONT, 8, "bold"),
                  bg="#e8f0fb", fg="#2c5aa0", activebackground="#d5e4f7",
                  relief="flat", padx=12, pady=0, cursor="hand2",
                  command=w.destroy).pack(side="bottom", pady=(0, 5))
        w.attributes("-topmost", True)

        # 常驻弹窗：点 X 关不掉，躲到随机位置
        w.protocol("WM_DELETE_WINDOW", lambda: self.dodge(w, title))
        return w

    def dodge(self, w, title):
        self.dodged.add(w)
        w.title("关不掉的关心 :)" if len(self.dodged) == 1 else title)
        x = random.randint(0, max(0, self.sw - POP_W - 40))
        y = random.randint(0, max(0, self.sh - POP_H - 80))
        w.geometry(f"+{x}+{y}")
        w.configure(bg="#fdf3f7")
        w.after(300, lambda: w.configure(bg="#f4f7fb"))

    # ---------- 第一阶段：先围出爱心 ----------
    def phase1(self):
        if self.idx < len(self.pts):
            i = self.idx
            x, y = self.pts[i]
            msg = CARING[i % len(CARING)]
            w = self.make_popup(f"关心 · 第 {i + 1} 封", msg, x, y)
            self.heart_windows.append(w)
            self.idx += 1
            self.root.after(HEART_INTERVAL, self.phase1)
        else:
            # 爱心停留片刻后整体淡出消失
            self.root.after(HEART_STAY, self.fade_heart)

    # ---------- 爱心整体淡出 ----------
    def fade_heart(self):
        for w in self.heart_windows:
            self._fade(w)
        # 淡出动画约 0.5 秒，结束后进入满屏弹窗阶段
        self.root.after(700, self.phase2)

    def _fade(self, w, step=0):
        try:
            if not w.winfo_exists():
                return
            a = 1.0 - step * 0.2
            if a <= 0.05:
                w.destroy()
            else:
                w.attributes("-alpha", a)
                w.after(60, lambda: self._fade(w, step + 1))
        except tk.TclError:
            pass

    # ---------- 第二阶段：满屏随机弹窗 ----------
    def phase2(self):
        if self.idx - len(self.pts) < RND_COUNT:
            i = self.idx - len(self.pts)
            x = random.uniform(0, self.sw - POP_W)
            y = random.uniform(0, self.sh - POP_H - 40)
            msg = CARING[i % len(CARING)]
            self.make_popup(f"小提醒 · {i + 1}", msg, x, y)
            self.idx += 1
            self.root.after(RND_INTERVAL, self.phase2)
        else:
            self.root.after(400, self.finish)

    # ---------- 第三阶段：收尾 ----------
    def finish(self):
        self.root.bind_all("<Escape>", lambda e: self.quit_all())
        self.make_receive()

    # ---------- 压轴：一键收到，点击终止运行 ----------
    def make_receive(self):
        pw, ph = 420, 180
        x = (self.sw - pw) // 2
        y = int(self.hcenter[1] + 115)  # 爱心中央偏下，压住爱心中心区域
        y = max(0, min(y, self.sh - ph - 20))
        w = tk.Toplevel(self.root)
        w.title("压轴 · 一键收到")
        w.resizable(False, False)
        w.geometry(f"{pw}x{ph}+{x}+{y}")
        w.configure(bg="#fff6f9", highlightbackground="#ff6b9d", highlightthickness=2)

        tk.Label(w, text="💝 全部关心已送达", font=(FONT, 13, "bold"),
                 bg="#fff6f9", fg="#d6336c").pack(pady=(18, 6))
        tk.Label(w, text="爱心已围成，满屏唠叨也送达完毕\n点击下方按钮，一键收下并结束本次表白",
                 font=(FONT, 10), bg="#fff6f9", fg="#666", justify="center").pack()

        tk.Button(w, text="一键收到 ❤", font=(FONT, 12, "bold"),
                  bg="#d6336c", fg="white", activebackground="#b02a58",
                  relief="flat", padx=34, pady=8, cursor="hand2",
                  command=self.quit_all).pack(pady=(10, 0))

        # 点 X 关不掉，和关心弹窗同一套逻辑
        w.protocol("WM_DELETE_WINDOW", lambda: self.dodge_receive(w))
        w.attributes("-topmost", True)

    def dodge_receive(self, w):
        x = random.randint(0, max(0, self.sw - 420))
        y = random.randint(0, max(0, self.sh - 180))
        w.title("这份关心也躲不掉哦 ~")
        w.geometry(f"+{x}+{y}")

    def quit_all(self):
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    ConfessionApp().run()
