"""메가바스켓 릴스 효과음·비트 합성기 (외부 음원 없이 numpy로 직접 생성)

사용: python3 sfx.py cues.json out.wav
cues.json = index.html의 window.__meta  {D, FPS, CUES:[{t,s,k?,p?,d?}], BED:{start,end,bpm}}
"""
import json
import sys
import wave

import numpy as np

SR = 48000
rng = np.random.default_rng(7)


def tt(dur):
    return np.arange(int(SR * dur)) / SR


def onepole_lp(x, fc):
    """시간에 따라 변하는 1차 저역통과 필터 (fc: 스칼라 또는 배열)."""
    fc = np.broadcast_to(np.asarray(fc, dtype=float), x.shape)
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    s = 0.0
    for i in range(len(x)):
        s = (1 - a[i]) * x[i] + a[i] * s
        y[i] = s
    return y


def kick(f0=150, f1=45, tau=.12, dur=.4, click=.3):
    t = tt(dur)
    f = f1 + (f0 - f1) * np.exp(-t / .03)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / tau)
    nclick = int(SR * .03)  # 클릭 성분은 저역통과로 다듬어 AAC 인코딩 시 과도 피크를 막음
    x[:nclick] += onepole_lp(rng.standard_normal(nclick), 3000) * np.exp(-t[:nclick] / .004) * click * 2.2
    return x


def hat(dur=.07):
    t = tt(dur)
    x = np.diff(rng.standard_normal(len(t) + 1)) * np.exp(-t / .014)
    return x * .35


def clap():
    t = tt(.28)
    n = rng.standard_normal(len(t))
    n = np.diff(np.concatenate([[0], n]))
    n = np.convolve(n, np.ones(5) / 5, 'same')
    e = np.zeros_like(t)
    for off in (0, .011, .022):
        m = t >= off
        e[m] += np.exp(-(t[m] - off) / (.009 if off < .02 else .07))
    return n * e * .9


def bass(freq, dur=.42):
    t = tt(dur)
    x = np.sin(2 * np.pi * freq * t) + .35 * np.sin(4 * np.pi * freq * t)
    env = np.minimum(1, t / .01) * np.exp(-t / .25)
    return np.tanh(x * 1.6) * env


def whoosh(pre=.24, post=.14, gain=1.0):
    t = tt(pre + post)
    x = rng.standard_normal(len(t))
    fc = np.where(t < pre, 250 + 6500 * (t / pre) ** 2, 300 + 6500 * np.exp(-(t - pre) / .05))
    y = onepole_lp(x, fc)
    env = np.where(t < pre, (t / pre) ** 2, np.exp(-(t - pre) / .06))
    return y * env * 2.6 * gain, pre


def riser(pre=.55):
    t = tt(pre)
    f = 260 * (1500 / 260) ** (t / pre)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * .25
    noise = onepole_lp(rng.standard_normal(len(t)), 400 + 7000 * (t / pre) ** 2) * 1.6
    return (tone + noise) * (t / pre) ** 2.2 * .7, pre


def pop(p=1.0):
    t = tt(.11)
    f = (420 + 900 * (1 - np.exp(-t / .02))) * p
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .035) * .8


def tick(p=1.0):
    t = tt(.03)
    return np.sin(2 * np.pi * 2300 * p * t) * np.exp(-t / .005) * .6


def ding(p=1.0):
    t = tt(.9)
    f0 = 1318.5 * p
    x = sum(a * np.sin(2 * np.pi * f0 * r * t) * np.exp(-t / d)
            for r, a, d in ((1, 1, .45), (2.0, .45, .28), (3.01, .22, .18), (4.2, .12, .1)))
    return x * .45


def cash():
    a = ding(1.5) * .7
    b = ding(2.0) * .6
    out = np.zeros(len(a) + int(.07 * SR))
    out[:len(a)] += a
    out[int(.07 * SR):int(.07 * SR) + len(b)] += b
    return out


def slam(k=1.0):
    boom = kick(f0=130, f1=36, tau=.28, dur=.8, click=.6) * 1.1
    t = tt(.8)
    crack = onepole_lp(rng.standard_normal(len(t)), 3500) * np.exp(-t / .03) * 1.4
    return (boom + crack) * (.55 + .45 * min(k, 1.3))


def stamp(k=1.0):
    t = tt(.35)
    knock = np.sin(2 * np.pi * 180 * t) * np.exp(-t / .05)
    thud = kick(f0=220, f1=60, tau=.07, dur=.35, click=.8)
    grit = onepole_lp(rng.standard_normal(len(t)), 2200) * np.exp(-t / .02) * 1.5
    return (knock + thud + grit) * (.45 + .4 * min(k, 1.3))


def thump(k=1.0):
    return kick(f0=110, f1=40, tau=.16, dur=.5, click=.2) * (.5 + .4 * k)


def type_clicks(d=.4):
    out = np.zeros(int(SR * (d + .05)))
    n = max(3, int(d / .045))
    for i in range(n):
        at = int((i / n * d + rng.uniform(-.006, .006)) * SR)
        c = tick(rng.uniform(.75, 1.3)) * rng.uniform(.5, .9)
        at = max(0, min(at, len(out) - len(c)))
        out[at:at + len(c)] += c
    return out


def limiter(buf, thr=.8, release=.09):
    """룩어헤드 피크 리미터: 1.5ms 앞의 피크를 보고 게인을 줄였다가 천천히 회복."""
    from numpy.lib.stride_tricks import sliding_window_view
    env = np.abs(buf).max(1)
    la = int(.0015 * SR)
    peak = sliding_window_view(np.concatenate([env, np.zeros(la)]), la + 1).max(1)[:len(env)]
    target = np.minimum(1.0, thr / np.maximum(peak, 1e-9))
    g = np.empty_like(target)
    rc = np.exp(-1 / (release * SR))
    s = 1.0
    for i, v in enumerate(target):
        s = v if v < s else v + (s - v) * rc
        g[i] = s
    g = np.minimum(g, np.convolve(g, np.ones(la) / la, 'same'))
    return buf * g[:, None]


def add(buf, sig, t, gain=1.0, pan=0.0):
    i = int(round(t * SR))
    if i < 0:
        sig = sig[-i:]
        i = 0
    j = min(len(buf), i + len(sig))
    if j <= i:
        return
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:j, 0] += sig[:j - i] * gain * l * 1.414
    buf[i:j, 1] += sig[:j - i] * gain * r * 1.414


def main(cues_path, out_path):
    meta = json.load(open(cues_path, encoding='utf-8'))
    D = meta['D']
    buf = np.zeros((int(SR * (D + .5)), 2))

    # --- 비트 베드 (120BPM, 드롭은 1.5초) ---
    bed = meta['BED']
    beat = 60 / bed['bpm']
    roots = [55.0, 55.0, 43.65, 49.0]
    t = bed['start']
    n = 0
    while t < bed['end'] - 1e-6:
        add(buf, kick(), t, .85)
        add(buf, bass(roots[(n // 2) % 4] if n % 2 == 0 else roots[(n // 2) % 4] * 2), t, .32)
        if n % 2 == 1:
            add(buf, clap(), t, .45, pan=.1)
        add(buf, hat(), t + beat / 2, .55, pan=-.25)
        if n % 4 == 3:
            add(buf, hat(), t + beat * .75, .35, pan=.25)
        t += beat
        n += 1

    # --- 효과음 ---
    for c in meta['CUES']:
        s, at = c['s'], c['t']
        p, k = c.get('p', 1.0), c.get('k', 1.0)
        if s == 'slam':
            add(buf, slam(k), at, .9)
        elif s == 'stamp':
            add(buf, stamp(k), at, .95)
        elif s == 'thump':
            add(buf, thump(k), at, .9)
        elif s == 'pop':
            add(buf, pop(p), at, .45)
        elif s == 'tick':
            add(buf, tick(p), at, .45)
        elif s == 'ding':
            add(buf, ding(p), at, .5)
        elif s == 'cash':
            add(buf, cash(), at, .5)
        elif s == 'type':
            add(buf, type_clicks(c.get('d', .4)), at, .5)
        elif s in ('whoosh', 'swish'):
            sig, pre = whoosh(.24, .14) if s == 'whoosh' else whoosh(.13, .1, .8)
            add(buf, sig, at - pre, .55, pan=-.3)
            add(buf, sig[::-1][::-1], at - pre + .004, .25, pan=.4)
        elif s == 'riser':
            sig, pre = riser()
            add(buf, sig, at - pre, .6)

    # --- 마무리: 소프트 리미터 + 페이드 ---
    buf = buf[:int(SR * D)]
    buf *= .8 / max(1e-9, np.percentile(np.abs(buf), 99.9))  # 게인 스테이징
    buf = limiter(buf, thr=.8)
    buf = np.tanh(buf * 1.05) / np.tanh(1.05)  # 안전용 소프트 클립 (거의 작동하지 않음)
    fade = int(SR * .35)
    buf[-fade:] *= np.linspace(1, 0, fade)[:, None]
    buf *= .78 / max(1e-9, np.abs(buf).max())  # 피크 약 -2.2dBFS (AAC 인코딩 여유)
    pcm = (buf * 32767).astype('<i2')
    with wave.open(out_path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print('audio:', out_path, f'{D:.1f}s')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
