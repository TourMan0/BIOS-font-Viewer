import tkinter as tk
from tkinter import filedialog, messagebox, ttk, colorchooser
from PIL import Image, ImageDraw, ImageTk
import re

# Предустановленные цвета (название → RGB)
COLOR_PRESETS = {
    "Белый": (255, 255, 255),
    "Чёрный": (0, 0, 0),
    "Красный": (255, 0, 0),
    "Зелёный": (0, 255, 0),
    "Синий": (0, 0, 255),
    "Жёлтый": (255, 255, 0),
    "Оранжевый": (255, 165, 0),
    "Розовый": (255, 105, 180),
    "Серый": (128, 128, 128),
    "Голубой": (0, 255, 255),
    "Фиолетовый": (128, 0, 128),
    "Светло-серый": (200, 200, 200),
    "Тёмно-синий": (0, 0, 128)
}

def rgb888_to_rgb565(r, g, b):
    r5 = (r * 31) // 255
    g6 = (g * 63) // 255
    b5 = (b * 31) // 255
    return (r5 << 11) | (g6 << 5) | b5

def rgb565_to_rgb888(c):
    r5 = (c >> 11) & 0x1F
    g6 = (c >> 5) & 0x3F
    b5 = c & 0x1F
    r = (r5 * 255) // 31
    g = (g6 * 255) // 63
    b = (b5 * 255) // 31
    return (r, g, b)

def clamp_color_to_rgb565(r, g, b):
    c565 = rgb888_to_rgb565(r, g, b)
    return rgb565_to_rgb888(c565)

def parse_hex_input(hex_data):
    clean = hex_data.replace(',', ' ').replace('\n', ' ').replace('\r', ' ')
    clean = clean.replace('0x', '').replace('0X', '')
    parts = clean.strip().split()
    valid = [p for p in parts if all(c in '0123456789ABCDEFabcdef' for c in p) and len(p) <= 2]
    return ' '.join(valid)

def draw_font(hex_data, scale, out_width, out_height, glyph_w, glyph_h, padding=2):
    try:
        bytes_data = bytes(int(b, 16) for b in hex_data.split())
        glyphs_count = len(bytes_data) // glyph_h

        full_glyph_w = glyph_w + padding
        full_glyph_h = glyph_h + padding

        chars_per_row = max(1, out_width // (full_glyph_w * scale))
        max_rows = max(1, out_height // (full_glyph_h * scale))
        max_chars = chars_per_row * max_rows
        glyphs_count = min(glyphs_count, max_chars)

        img_width = chars_per_row * full_glyph_w
        img_height = max_rows * full_glyph_h

        img = Image.new("RGB", (img_width, img_height), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)

        for idx in range(glyphs_count):
            char_data = bytes_data[idx * glyph_h:(idx + 1) * glyph_h]
            x0 = (idx % chars_per_row) * full_glyph_w
            y0 = (idx // chars_per_row) * full_glyph_h
            for y, byte in enumerate(char_data):
                for x in range(glyph_w):
                    if (byte >> (7 - x)) & 1:
                        draw.point((x0 + x, y0 + y), fill=text_color)

        final_img = img.resize((img_width * scale, img_height * scale), Image.NEAREST)
        return final_img
    except Exception as e:
        messagebox.showerror("Ошибка при отрисовке", str(e))
        return None

def render():
    global current_image, showing_text
    raw_text = text_input.get("1.0", "end").strip()
    hex_data = parse_hex_input(raw_text)
    try:
        scale = int(scale_entry.get())
        out_w = int(width_entry.get())
        out_h = int(height_entry.get())
        format_str = font_format_cb.get()
        glyph_w, glyph_h = map(int, format_str.split('x'))
        img = draw_font(hex_data, scale, out_w, out_h, glyph_w, glyph_h)
        if img:
            current_image = img
            showing_text = False
            update_canvas(img)
    except Exception as e:
        messagebox.showerror("Ошибка", "Проверьте параметры отображения\n" + str(e))

def update_canvas(img):
    img_tk = ImageTk.PhotoImage(img)
    canvas.delete("all")
    canvas.config(scrollregion=(0, 0, img.width, img.height))
    canvas.image = img_tk
    canvas.create_image(0, 0, anchor="nw", image=img_tk)

def parse_text_and_indices(text_line):
    pattern = r'([^\[\]\s]+)(?:\[(\d+)\])?'
    result = []
    for match in re.finditer(pattern, text_line):
        word = match.group(1)
        idx = int(match.group(2)) if match.group(2) else None
        result.append((word, idx))
    return result

def render_text_with_colors():
    global current_image, glyphs_data, showing_text

    raw_text = text_entry.get("1.0", "end").rstrip('\n')
    if not raw_text or not glyphs_data:
        messagebox.showwarning("Ошибка", "Нет текста или данных для отрисовки")
        return

    try:
        scale = int(scale_entry.get())
        format_str = font_format_cb.get()
        glyph_w, glyph_h = map(int, format_str.split('x'))
    except Exception:
        messagebox.showerror("Ошибка", "Неверные параметры")
        return

    bytes_per_glyph = glyph_h
    total_glyphs = len(glyphs_data) // bytes_per_glyph

    lines = raw_text.split('\n')
    max_line_len = max(len(line) for line in lines)
    img_width = (glyph_w + 1) * max_line_len
    img_height = glyph_h * len(lines) + (len(lines) - 1)

    img = Image.new("RGB", (img_width, img_height), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    occurrence_counter = {}

    y_offset = 0
    for line in lines:
        parts = parse_text_and_indices(line)
        x_offset = 0

        for word, idx_in_text in parts:
            if idx_in_text is None:
                occurrence_counter[word] = occurrence_counter.get(word, 0) + 1
                idx = occurrence_counter[word]
            else:
                idx = idx_in_text

            key = f"{word}[{idx}]" if idx_in_text is not None else word
            color = colors_for_texts.get(key, text_color)

            for ch in word:
                if ch == ' ':
                    x_offset += glyph_w + 1
                    continue
                code = ord(ch)
                if code >= total_glyphs:
                    x_offset += glyph_w + 1
                    continue
                offset = code * bytes_per_glyph
                glyph = glyphs_data[offset:offset + bytes_per_glyph]
                for y, byte in enumerate(glyph):
                    for x in range(glyph_w):
                        if (byte >> (7 - x)) & 1:
                            draw.point((x_offset + x, y_offset + y), fill=color)
                x_offset += glyph_w + 1

            x_offset += glyph_w + 1

        y_offset += glyph_h + 1

    final_img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    current_image = final_img
    showing_text = True
    update_canvas(final_img)

def update_color_from_menu(event=None):
    global text_color
    selected = color_combobox.get()
    if selected in COLOR_PRESETS:
        r, g, b = COLOR_PRESETS[selected]
        r, g, b = clamp_color_to_rgb565(r, g, b)
        text_color = (r, g, b)
    else:
        pass

def choose_color():
    global text_color
    color_code = colorchooser.askcolor(title="Выберите цвет")
    if color_code[0] is None:
        return
    r, g, b = map(int, color_code[0])
    r, g, b = clamp_color_to_rgb565(r, g, b)
    text_color = (r, g, b)

    found = None
    for name, rgb in COLOR_PRESETS.items():
        if rgb == text_color:
            found = name
            break
    if found:
        color_combobox.set(found)
    else:
        color_combobox.set('')

    color_btn.config(bg=_rgb_to_hex(text_color))

def _rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb

def open_file(filetype):
    global glyphs_data
    if filetype == "txt":
        path = filedialog.askopenfilename(filetypes=[("Text", "*.txt")])
        if not path: return
        with open(path, "r", encoding="utf-8") as f:
            hex_text = f.read().strip()
        text_input.delete("1.0", "end")
        text_input.insert("1.0", hex_text)
    else:
        path = filedialog.askopenfilename(filetypes=[("Binary Files", "*.bin *.rom *.bios")])
        if not path: return
        with open(path, "rb") as f:
            glyphs_data = f.read()
        hex_text = ', '.join(f'0x{b:02X}' for b in glyphs_data)
        text_input.delete("1.0", "end")
        text_input.insert("1.0", hex_text)

def show_glyph_table():
    render()

def set_color_for_text():
    def apply_color():
        key = key_entry.get().strip()
        if not key:
            messagebox.showerror("Ошибка", "Введите текст или текст с индексом (например, HELLO или HELLO[2])")
            return
        color_code = colorchooser.askcolor(title="Выберите цвет для " + key)
        if color_code[0] is None:
            return
        r, g, b = map(int, color_code[0])
        r, g, b = clamp_color_to_rgb565(r, g, b)
        colors_for_texts[key] = (r, g, b)
        color_win.destroy()
        messagebox.showinfo("Готово", f"Цвет для '{key}' установлен")

    color_win = tk.Toplevel(root)
    color_win.title("Установить цвет для текста/вхождения")

    tk.Label(color_win, text="Введите текст или с индексом (например HELLO или HELLO[2]):").pack(padx=10, pady=5)
    key_entry = tk.Entry(color_win, width=30)
    key_entry.pack(padx=10, pady=5)
    key_entry.focus()

    tk.Button(color_win, text="Выбрать цвет", command=apply_color).pack(pady=10)

def save_image():
    global current_image
    if current_image is None:
        messagebox.showwarning("Внимание", "Нет изображения для сохранения")
        return
    filetypes = [("PNG файл", "*.png"), ("BMP файл", "*.bmp")]
    path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=filetypes)
    if not path:
        return
    try:
        current_image.save(path)
        messagebox.showinfo("Успех", f"Изображение сохранено в {path}")
    except Exception as e:
        messagebox.showerror("Ошибка сохранения", str(e))

# --- GUI ---

root = tk.Tk()
root.title("BIOS Font Viewer")

current_image = None
glyphs_data = b''
text_color = (255, 255, 255)
showing_text = False
colors_for_texts = {}

tk.Label(root, text="HEX код (через пробел или 0xXX,):").pack()
text_input = tk.Text(root, height=6, wrap="word")
text_input.pack(fill="x")

frame1 = tk.Frame(root)
frame1.pack(pady=5)

tk.Label(frame1, text="Масштаб:").pack(side="left")
scale_entry = tk.Entry(frame1, width=5)
scale_entry.insert(0, "4")
scale_entry.pack(side="left", padx=5)

tk.Label(frame1, text="Ширина:").pack(side="left")
width_entry = tk.Entry(frame1, width=6)
width_entry.insert(0, "512")
width_entry.pack(side="left", padx=5)

tk.Label(frame1, text="Высота:").pack(side="left")
height_entry = tk.Entry(frame1, width=6)
height_entry.insert(0, "256")
height_entry.pack(side="left", padx=5)

frame2 = tk.Frame(root)
frame2.pack(pady=5)

tk.Label(frame2, text="Формат шрифта:").pack(side="left")
font_format_cb = ttk.Combobox(frame2, values=["8x8", "8x12", "8x14", "8x16", "8x18", "8x20"], width=5)
font_format_cb.set("8x16")
font_format_cb.pack(side="left", padx=5)

tk.Button(frame2, text="Показать", command=render).pack(side="left", padx=5)
tk.Button(frame2, text="Открыть .txt", command=lambda: open_file("txt")).pack(side="left", padx=5)
tk.Button(frame2, text="Открыть .bin/.rom", command=lambda: open_file("bin")).pack(side="left", padx=5)

frame3 = tk.Frame(root)
frame3.pack(pady=5)

tk.Label(frame3, text="Цвет текста:").pack(side="left")
color_combobox = ttk.Combobox(frame3, values=list(COLOR_PRESETS.keys()), width=15)
color_combobox.set("Белый")
color_combobox.pack(side="left", padx=5)
color_combobox.bind("<<ComboboxSelected>>", update_color_from_menu)

color_btn = tk.Button(frame3, text="Выбрать цвет...", command=choose_color, bg=_rgb_to_hex(text_color))
color_btn.pack(side="left", padx=5)

tk.Label(frame3, text="Текст для отрисовки:").pack(side="left", padx=5)
text_entry = tk.Text(frame3, width=30, height=4)
text_entry.pack(side="left", padx=5)

tk.Button(frame3, text="Показать текст", command=render_text_with_colors).pack(side="left", padx=5)
tk.Button(frame3, text="Назад", command=show_glyph_table).pack(side="left", padx=5)
tk.Button(frame3, text="Установить цвет для текста/вхождения", command=set_color_for_text).pack(side="left", padx=5)

# Кнопка сохранения изображения
tk.Button(frame3, text="Сохранить изображение", command=save_image).pack(side="left", padx=5)

canvas_frame = tk.Frame(root)
canvas_frame.pack(fill="both", expand=True)

x_scroll = tk.Scrollbar(canvas_frame, orient="horizontal")
y_scroll = tk.Scrollbar(canvas_frame, orient="vertical")
canvas = tk.Canvas(canvas_frame, bg="black",
                   xscrollcommand=x_scroll.set,
                   yscrollcommand=y_scroll.set)

x_scroll.config(command=canvas.xview)
y_scroll.config(command=canvas.yview)

x_scroll.pack(side="bottom", fill="x")
y_scroll.pack(side="right", fill="y")
canvas.pack(side="left", fill="both", expand=True)

root.mainloop()
