#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEO Mini GUI — Gemini (Strict + Validation)
- Meta description / Slug / Focus keyphrase từ AI Gemini
- Strict mode + No fallback
- Tuỳ chọn bắt buộc khớp Brand/Category theo whitelist
- Tuỳ chọn kiểm chứng Google Trends (VN, timeframe, ngưỡng)

Cài đặt:
  pip install google-generativeai pytrends

Chạy:
  python seo_minigui_gemini_strict_validated.py
"""

import json, re, os, tkinter as tk
from tkinter import ttk, messagebox

# ===== Helpers =====
def strip_vi_diacritics(s: str) -> str:
    if not s: return ""
    s = s.lower()
    trans = str.maketrans({
        'à':'a','á':'a','ạ':'a','ả':'a','ã':'a','â':'a','ầ':'a','ấ':'a','ậ':'a','ẩ':'a','ẫ':'a','ă':'a','ằ':'a','ắ':'a','ặ':'a','ẳ':'a','ẵ':'a',
        'è':'e','é':'e','ẹ':'e','ẻ':'e','ẽ':'e','ê':'e','ề':'e','ế':'e','ệ':'e','ể':'e','ễ':'e',
        'ì':'i','í':'i','ị':'i','ỉ':'i','ĩ':'i',
        'ò':'o','ó':'o','ọ':'o','ỏ':'o','õ':'o','ô':'o','ồ':'o','ố':'o','ộ':'o','ổ':'o','ỗ':'o','ơ':'o','ờ':'o','ớ':'o','ợ':'o','ở':'o','ỡ':'o',
        'ù':'u','ú':'u','ụ':'u','ủ':'u','ũ':'u','ư':'u','ừ':'u','ứ':'u','ự':'u','ử':'u','ữ':'u',
        'ỳ':'y','ý':'y','ỵ':'y','ỷ':'y','ỹ':'y','đ':'d'
    })
    return s.translate(trans)

def smart_trim(text: str, max_len: int) -> str:
    t = (text or "").strip()
    if len(t) <= max_len: return t
    cut = t[:max_len]
    last_space = cut.rfind(" ")
    if last_space != -1: cut = cut[:last_space]
    return cut.rstrip(" .,-–—") + "…"

def slugify_vi(text: str) -> str:
    t = strip_vi_diacritics(text).strip()
    t = re.sub(r'[^a-z0-9\s-]', '', t)
    t = re.sub(r'\s+', '-', t)
    t = re.sub(r'-+', '-', t)
    return t.strip('-')

def sanitize_focus_keyphrase(text: str) -> str:
    words = re.findall(r'[A-Za-zÀ-ỹ0-9]+', (text or '').strip())
    if not words: return ""
    if len(words) > 5: words = words[:5]
    return " ".join(words).lower()

def looks_like_gibberish(name: str) -> bool:
    s = (name or "").strip()
    if not s: return True
    letters = re.findall(r'[A-Za-zÀ-ỹ]', s)
    if len(letters) >= 6:
        vowels = re.findall(r'[aeiouAEIOUàáạảãâầấậẩẫăằắặẳẵêèéẹẻẽềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹ]', s)
        if len(vowels) / max(len(letters),1) < 0.18:
            return True
    if re.search(r'(.)\1{3,}', s): return True
    if len(s) > 14 and ' ' not in s: return True
    return False

# ===== Gemini call =====
def call_gemini(api_key: str, product_name: str, model_name: str = "gemini-1.5-flash", strict: bool = True, no_fallback: bool = True) -> dict:
    if not api_key: raise RuntimeError("Thiếu API key.")
    try:
        import google.generativeai as genai
    except Exception as e:
        raise RuntimeError("Chưa cài 'google-generativeai'. Hãy chạy: pip install google-generativeai") from e

    if strict and looks_like_gibberish(product_name):
        return {"warning": "gibberish_detected", "meta_description": "", "slug": "", "focus_keyphrase": ""}

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    guard = """
Nếu tên sản phẩm có vẻ bịa đặt/không hợp lệ/không nhận diện được brand hoặc danh mục, TRẢ VỀ JSON:
{"warning":"unknown_or_made_up","meta_description":"","slug":"","focus_keyphrase":""}
và KHÔNG bịa thêm nội dung.
""" if strict else ""

    prompt = f"""
Bạn là chuyên gia SEO tiếng Việt. Với TÊN SẢN PHẨM: "{product_name}".
{guard}
Hãy trả về duy nhất một JSON Object với 3 trường:
- meta_description: tiếng Việt, 140–160 ký tự, nêu 2–3 lợi ích + CTA ngắn, không emoji.
- slug: URL không dấu (a-z0-9 và "-"), tối đa 8 từ.
- focus_keyphrase: 3–5 từ, tiếng Việt, sát ý định mua hàng.
Chỉ in JSON, không kèm giải thích.
"""
    resp = model.generate_content(prompt)
    text = getattr(resp, "text", "") or ""

    data = None
    try:
        data = json.loads(text)
    except Exception:
        m = re.search(r'\{\s*"(?:meta_description|slug|focus_keyphrase|warning)".*?\}', text, flags=re.S)
        if m:
            try: data = json.loads(m.group(0))
            except Exception: data = None

    if not isinstance(data, dict):
        if no_fallback:
            return {"warning": "llm_parse_error", "meta_description": "", "slug": "", "focus_keyphrase": ""}
        md = f"{product_name} chất lượng, bền bỉ, hiệu suất ổn định. Giá tốt, giao nhanh, đổi trả linh hoạt. Mua ngay!"
        return {"meta_description": smart_trim(md, 155), "slug": slugify_vi(product_name), "focus_keyphrase": sanitize_focus_keyphrase(product_name)}

    if data.get("warning"):
        return {"warning": data.get("warning"), "meta_description": "", "slug": "", "focus_keyphrase": ""}

    meta = smart_trim(data.get("meta_description",""), 155)
    slug = slugify_vi(data.get("slug","") or product_name)
    keyp = sanitize_focus_keyphrase(data.get("focus_keyphrase","") or product_name)
    return {"meta_description": meta, "slug": slug, "focus_keyphrase": keyp}

# ===== Trends validation =====
def trends_score_single(keyword: str, geo: str = "VN", timeframe: str = "today 3-m") -> dict:
    try:
        from pytrends.request import TrendReq
    except Exception as e:
        raise RuntimeError("Chưa cài 'pytrends'. Cài bằng: pip install pytrends") from e

    pytrends = TrendReq(hl='vi-VN', tz=420)
    pytrends.build_payload([keyword], timeframe=timeframe, geo=geo)
    df = pytrends.interest_over_time()
    if df.empty or keyword not in df.columns:
        return {"avg": 0.0, "last": 0}
    s = df[keyword].astype(int)
    return {"avg": float(s.mean()), "last": int(s.iloc[-1])}

# ===== GUI =====
class MiniGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SEO Mini GUI — Gemini (Strict + Validation)")
        self.geometry("900x600")
        self.resizable(True, True)

        # Core inputs
        self.api_var = tk.StringVar(value=os.environ.get("GEMINI_API_KEY",""))
        self.model_var = tk.StringVar(value=os.environ.get("GEMINI_MODEL","gemini-1.5-flash"))
        self.name_var = tk.StringVar()

        # Strict/fallback
        self.strict_var = tk.BooleanVar(value=True)
        self.nofallback_var = tk.BooleanVar(value=True)

        # Whitelists
        self.require_brand_var = tk.BooleanVar(value=False)
        self.brands_var = tk.StringVar(value="yonex, lining, victor, wilson, babolat, asics, adidas, nike")
        self.require_cat_var = tk.BooleanVar(value=False)
        self.cats_var = tk.StringVar(value="vot, giay, ao, quan, ao thun, bong, phu kien, day cam, bao tay")

        # Trends
        self.validate_trends_var = tk.BooleanVar(value=False)
        self.geo_var = tk.StringVar(value="VN")
        self.timeframe_var = tk.StringVar(value="today 3-m")
        self.min_avg_var = tk.DoubleVar(value=1.0)   # >0 theo yêu cầu
        self.min_last_var = tk.IntVar(value=1)

        # Outputs
        self.meta_var = tk.StringVar(); self.slug_var = tk.StringVar(); self.key_var = tk.StringVar()
        self.status = tk.StringVar(value="Ready.")

        self.build_ui()

    def build_ui(self):
        pad = {'padx': 6, 'pady': 4}

        # Inputs
        frm_in = ttk.LabelFrame(self, text="Nhập liệu")
        frm_in.pack(fill='x', padx=8, pady=6)
        ttk.Label(frm_in, text="API key (Gemini)").grid(row=0, column=0, sticky='w', **pad)
        ttk.Entry(frm_in, textvariable=self.api_var, width=52, show="•").grid(row=0, column=1, sticky='w', **pad)
        ttk.Label(frm_in, text="Model").grid(row=0, column=2, sticky='w', **pad)
        ttk.Entry(frm_in, textvariable=self.model_var, width=20).grid(row=0, column=3, sticky='w', **pad)
        ttk.Label(frm_in, text="Tên sản phẩm").grid(row=1, column=0, sticky='w', **pad)
        ttk.Entry(frm_in, textvariable=self.name_var, width=74).grid(row=1, column=1, columnspan=3, sticky='we', **pad)

        # Options: strict + fallback
        frm_opts = ttk.LabelFrame(self, text="Chế độ sinh & ràng buộc")
        frm_opts.pack(fill='x', padx=8, pady=4)
        ttk.Checkbutton(frm_opts, text="Strict mode (fail on nonsense / unknown)", variable=self.strict_var).grid(row=0, column=0, sticky='w', **pad)
        ttk.Checkbutton(frm_opts, text="No fallback (không tự sinh khi JSON lỗi)", variable=self.nofallback_var).grid(row=0, column=1, sticky='w', **pad)

        # Whitelist section
        frm_white = ttk.LabelFrame(self, text="Whitelist kiểm tra trong Tên sản phẩm (không phân biệt dấu)")
        frm_white.pack(fill='x', padx=8, pady=4)
        ttk.Checkbutton(frm_white, text="Require BRAND match", variable=self.require_brand_var).grid(row=0, column=0, sticky='w', **pad)
        ttk.Entry(frm_white, textvariable=self.brands_var, width=70).grid(row=0, column=1, columnspan=3, sticky='we', **pad)
        ttk.Checkbutton(frm_white, text="Require CATEGORY match", variable=self.require_cat_var).grid(row=1, column=0, sticky='w', **pad)
        ttk.Entry(frm_white, textvariable=self.cats_var, width=70).grid(row=1, column=1, columnspan=3, sticky='we', **pad)
        ttk.Label(frm_white, text="Ví dụ brand: yonex, lining, victor | Ví dụ category: vot, giay, ao, bong").grid(row=2, column=0, columnspan=4, sticky='w', **pad)

        # Trends section
        frm_tr = ttk.LabelFrame(self, text="Google Trends (tuỳ chọn) — chấm điểm Focus keyphrase")
        frm_tr.pack(fill='x', padx=8, pady=4)
        ttk.Checkbutton(frm_tr, text="Validate bằng Google Trends", variable=self.validate_trends_var).grid(row=0, column=0, sticky='w', **pad)
        ttk.Label(frm_tr, text="Geo").grid(row=0, column=1, sticky='e', **pad)
        ttk.Entry(frm_tr, textvariable=self.geo_var, width=6).grid(row=0, column=2, sticky='w', **pad)
        ttk.Label(frm_tr, text="Timeframe").grid(row=0, column=3, sticky='e', **pad)
        ttk.Entry(frm_tr, textvariable=self.timeframe_var, width=12).grid(row=0, column=4, sticky='w', **pad)
        ttk.Label(frm_tr, text="Min AVG").grid(row=0, column=5, sticky='e', **pad)
        ttk.Entry(frm_tr, textvariable=self.min_avg_var, width=6).grid(row=0, column=6, sticky='w', **pad)
        ttk.Label(frm_tr, text="Min LAST").grid(row=0, column=7, sticky='e', **pad)
        ttk.Entry(frm_tr, textvariable=self.min_last_var, width=6).grid(row=0, column=8, sticky='w', **pad)

        # Buttons
        frm_btn = ttk.Frame(self); frm_btn.pack(fill='x', padx=8, pady=6)
        ttk.Button(frm_btn, text="Generate", command=self.on_generate).pack(side='left', padx=4)
        ttk.Button(frm_btn, text="Copy All", command=self.copy_all).pack(side='left', padx=4)
        ttk.Button(frm_btn, text="Clear", command=self.clear_all).pack(side='left', padx=4)

        # Outputs
        frm_out = ttk.LabelFrame(self, text="Kết quả")
        frm_out.pack(fill='x', padx=8, pady=6)
        def row(label, var):
            r = ttk.Frame(frm_out); r.pack(fill='x', pady=2)
            ttk.Label(r, text=label, width=18).pack(side='left')
            e = ttk.Entry(r, textvariable=var); e.pack(side='left', fill='x', expand=True, padx=4)
            ttk.Button(r, text="Copy", command=lambda v=var: self.copy_text(v.get())).pack(side='left', padx=2)
        row("Meta description", self.meta_var)
        row("Slug", self.slug_var)
        row("Focus keyphrase", self.key_var)

        ttk.Label(self, textvariable=self.status).pack(fill='x', padx=8, pady=4)

    def _require_match(self, text: str, tokens_csv: str, label: str) -> bool:
        tokens = [t.strip() for t in re.split(r'[,\|/;]+', tokens_csv) if t.strip()]
        if not tokens:
            messagebox.showwarning("Thiếu danh sách", f"Bạn bật kiểm tra {label} nhưng chưa nhập danh sách."); return False
        norm_text = strip_vi_diacritics(text)
        for t in tokens:
            if strip_vi_diacritics(t) in norm_text:
                return True
        messagebox.showwarning("Không khớp", f"Tên sản phẩm chưa khớp bất kỳ {label} nào trong whitelist.")
        return False

    def on_generate(self):
        api = self.api_var.get().strip()
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Thiếu tên", "Nhập Tên sản phẩm"); return
        # Whitelist checks
        if self.require_brand_var.get() and not self._require_match(name, self.brands_var.get(), "BRAND"):
            self.status.set("Không đạt yêu cầu BRAND."); return
        if self.require_cat_var.get() and not self._require_match(name, self.cats_var.get(), "CATEGORY"):
            self.status.set("Không đạt yêu cầu CATEGORY."); return

        try:
            out = call_gemini(api, name, self.model_var.get().strip() or "gemini-1.5-flash",
                              strict=self.strict_var.get(), no_fallback=self.nofallback_var.get())
        except Exception as e:
            messagebox.showerror("AI Error", str(e)); return

        warn = out.get("warning")
        self.meta_var.set(out.get("meta_description",""))
        self.slug_var.set(out.get("slug",""))
        self.key_var.set(out.get("focus_keyphrase",""))

        if warn:
            if warn == "gibberish_detected":
                self.status.set("Phát hiện tên có vẻ bịa/không hợp lệ → dừng theo Strict mode.")
                messagebox.showwarning("Strict mode", "Tên sản phẩm có vẻ không hợp lệ (gibberish)."); return
            elif warn == "unknown_or_made_up":
                self.status.set("Gemini báo unknown/made-up → dừng theo Strict mode.")
                messagebox.showwarning("Strict mode", "AI báo tên sản phẩm không nhận diện được."); return
            elif warn == "llm_parse_error":
                self.status.set("Không parse được JSON và No fallback đang bật.")
                messagebox.showwarning("No fallback", "AI trả về sai định dạng JSON."); return

        # Trends validation (focus keyphrase)
        if self.validate_trends_var.get():
            kw = self.key_var.get().strip()
            if not kw:
                messagebox.showwarning("Trends", "Không có Focus keyphrase để kiểm chứng."); return
            try:
                sc = trends_score_single(kw, geo=self.geo_var.get().strip() or "VN", timeframe=self.timeframe_var.get().strip() or "today 3-m")
            except Exception as e:
                messagebox.showerror("Trends Error", str(e)); return

            passed = (sc.get("avg",0.0) >= float(self.min_avg_var.get() or 0.0)) and (sc.get("last",0) >= int(self.min_last_var.get() or 0))
            if not passed:
                self.meta_var.set(""); self.slug_var.set(""); self.key_var.set("")
                self.status.set(f"Trends FAIL: avg={sc.get('avg',0):.1f}, last={sc.get('last',0)} (yêu cầu ≥ {self.min_avg_var.get()}/{self.min_last_var.get()}).")
                messagebox.showwarning("Trends FAIL", f"Keyword không đạt ngưỡng Trends.\navg={sc.get('avg',0):.1f}, last={sc.get('last',0)}"); return
            else:
                self.status.set(f"Trends PASS: avg={sc.get('avg',0):.1f}, last={sc.get('last',0)}.")

        if not self.status.get().startswith("Trends"):
            self.status.set("Đã sinh kết quả.")

    def copy_text(self, text: str):
        self.clipboard_clear(); self.clipboard_append(text); self.update()
        try: messagebox.showinfo("Copied", "Đã copy vào clipboard!")
        except Exception: pass

    def copy_all(self):
        t = (f"Meta description: {self.meta_var.get()}\n"
             f"Slug: {self.slug_var.get()}\n"
             f"Focus keyphrase: {self.key_var.get()}")
        self.copy_text(t)

    def clear_all(self):
        for v in [self.name_var, self.meta_var, self.slug_var, self.key_var]:
            v.set("")
        self.status.set("Cleared.")

if __name__ == "__main__":
    app = MiniGUI()
    app.mainloop()
