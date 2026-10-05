"""
GTZ ID Studio - Card Renderer
Renders portrait ID card at 300 DPI using Pillow.
Card size: 54mm W x 84.5mm H = 638 x 998 px at 300 DPI
"""
import os
import io
from typing import Dict, Optional, List
from PIL import Image, ImageDraw, ImageFont

MM_TO_PX = 300 / 25.4   # 11.811 px/mm
CARD_W_MM = 54.0
CARD_H_MM = 84.5
CARD_W_PX = int(CARD_W_MM * MM_TO_PX)   # 638
CARD_H_PX = int(CARD_H_MM * MM_TO_PX)   # 998
DPI = 300

ELEM_TEXT    = "text"
ELEM_PHOTO   = "photo"
ELEM_QR      = "qr"
ELEM_RECT    = "rect"
ELEM_ELLIPSE = "ellipse"
ELEM_IMAGE   = "image"


def mm2px(mm): return int(mm * MM_TO_PX)


class CardRenderer:
    def __init__(self, qr_folder: str = ""):
        self.qr_folder = qr_folder

    def set_qr_folder(self, folder: str):
        self.qr_folder = folder

    def find_qr_for_staff(self, staff: Dict) -> Optional[str]:
        if not self.qr_folder or not os.path.isdir(self.qr_folder):
            return None

        qr_filename = (staff.get("qr_filename") or "").strip()
        staff_id    = (staff.get("staff_id") or "").strip()
        name        = (staff.get("name") or "").strip()

        # Build candidate strings (normalised)
        candidates = set()
        for s in [qr_filename, staff_id]:
            if s:
                candidates.add(s)
                candidates.add(s.lower())
                candidates.add(s.replace(" ", "_"))
                candidates.add(s.replace("_", " "))
                candidates.add(s.replace("-", "_"))

        # Also try firstname_lastname and lastname_firstname
        parts = name.split()
        if len(parts) >= 2:
            candidates.add("{}_{}".format(parts[0], parts[-1]).lower())
            candidates.add("{}_{}".format(parts[-1], parts[0]).lower())
            candidates.add("{} {}".format(parts[0], parts[-1]).lower())

        exts = [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"]

        for fname in os.listdir(self.qr_folder):
            name_no_ext, fext = os.path.splitext(fname)
            if fext.lower() not in exts:
                continue
            nne_lower = name_no_ext.lower().strip()
            nne_norm  = nne_lower.replace(" ", "_")
            for cand in candidates:
                if cand.lower().replace(" ", "_") == nne_norm:
                    return os.path.join(self.qr_folder, fname)

        return None

    def render_card(
        self,
        staff: Dict,
        template_path: Optional[str],
        config: Dict,
        width: int = CARD_W_PX,
        height: int = CARD_H_PX,
    ) -> Image.Image:
        card = Image.new("RGB", (width, height), (255, 255, 255))

        elements = config.get("elements", [])

        if elements:
            # ── New visual-editor config ──────────────────────────
            # Background color
            bg_color = config.get("bg_color", "#FFFFFF")
            try:
                card.paste(Image.new("RGB", (width, height), self._hex2rgb(bg_color)))
            except Exception:
                pass

            # Background image
            bg_img = config.get("bg_image", "")
            if bg_img and os.path.exists(bg_img):
                try:
                    bg = Image.open(bg_img).convert("RGB")
                    bg = bg.resize((width, height), Image.LANCZOS)
                    card.paste(bg)
                except Exception:
                    pass

            qr_path = self.find_qr_for_staff(staff)

            for el in elements:
                if not el.get("visible", True):
                    continue
                x  = mm2px(el.get("x", 0))
                y  = mm2px(el.get("y", 0))
                w  = mm2px(el.get("w", 10))
                h  = mm2px(el.get("h", 10))
                et = el.get("type", ELEM_TEXT)

                if et == ELEM_RECT:
                    self._render_rect(card, x, y, w, h, el)
                elif et == ELEM_ELLIPSE:
                    self._render_ellipse(card, x, y, w, h, el)
                elif et == "line":
                    x2 = mm2px(el.get("x2", el.get("x",0)+el.get("w",10)))
                    y2 = mm2px(el.get("y2", el.get("y",0)))
                    draw = __import__("PIL.ImageDraw", fromlist=["ImageDraw"]).Draw(card)
                    sw = max(1, mm2px(el.get("stroke_width",0.5)))
                    color = self._hex2rgb(el.get("stroke_color","#000000"))
                    draw.line([(x,y),(int(x2),int(y2))], fill=color, width=int(sw))
                elif et == ELEM_IMAGE:
                    self._render_image_el(card, x, y, w, h, el.get("image_path",""))
                elif et == ELEM_PHOTO:
                    self._render_photo(card, x, y, w, h, staff.get("photo_path",""))
                elif et == ELEM_QR:
                    self._render_qr(card, x, y, w, h, qr_path)
                elif et == ELEM_TEXT:
                    key   = el.get("key", "")
                    typed = el.get("text", "").strip()
                    # If bound to a data field, staff data takes priority over typed text
                    if key:
                        value = staff.get(key, "") or ""
                        # Auto-derive first_name/last_name from name if columns empty
                        if key == "first_name" and not value:
                            full = (staff.get("name") or "").strip()
                            value = full.split(" ", 1)[0] if full else ""
                        elif key == "last_name" and not value:
                            full = (staff.get("name") or "").strip()
                            parts = full.split(" ", 1)
                            value = parts[1] if len(parts) > 1 else ""
                    else:
                        # No binding — use typed text
                        value = typed
                    if value:
                        self._render_text(card, x, y, w, h, str(value), el)
        else:
            # ── Legacy fallback ───────────────────────────────────
            if template_path and os.path.exists(template_path):
                try:
                    bg = Image.open(template_path).convert("RGB")
                    card.paste(bg.resize((width, height), Image.LANCZOS))
                except Exception:
                    pass

            qr_path = self.find_qr_for_staff(staff)
            self._render_photo(card, mm2px(2),  mm2px(2),  mm2px(50), mm2px(46), staff.get("photo_path",""))
            self._render_text(card, mm2px(2), mm2px(50), mm2px(50), mm2px(8),
                              staff.get("name",""), {"font_size":9,"bold":True,"text_color":"#1A1A1A"})
            self._render_text(card, mm2px(2), mm2px(60), mm2px(50), mm2px(7),
                              staff.get("staff_id",""), {"font_size":7,"bold":False,"text_color":"#505050"})
            qr_x = mm2px((CARD_W_MM-15.5)/2)
            self._render_qr(card, qr_x, mm2px(CARD_H_MM-18), mm2px(15.5), mm2px(15.5), qr_path)

        return card

    # ── element renderers ─────────────────────────────────────────────
    def _render_rect(self, card, x, y, w, h, el):
        draw = ImageDraw.Draw(card)
        if el.get("fill_enabled", True):
            draw.rectangle([x, y, x+w, y+h], fill=self._hex2rgb(el.get("fill_color","#FFFFFF")))
        sw = el.get("stroke_width", 0)
        if sw > 0:
            draw.rectangle([x, y, x+w, y+h],
                           outline=self._hex2rgb(el.get("stroke_color","#000000")),
                           width=max(1, mm2px(sw)))

    def _render_ellipse(self, card, x, y, w, h, el):
        from PIL import ImageDraw as ID
        tmp = Image.new("RGBA", card.size, (0,0,0,0))
        draw = ID.Draw(tmp)
        if el.get("fill_enabled", True):
            draw.ellipse([x, y, x+w, y+h], fill=self._hex2rgba(el.get("fill_color","#FFFFFF")))
        sw = el.get("stroke_width", 0)
        if sw > 0:
            draw.ellipse([x, y, x+w, y+h],
                         outline=self._hex2rgba(el.get("stroke_color","#000000")),
                         width=max(1, mm2px(sw)))
        card.paste(Image.alpha_composite(card.convert("RGBA"), tmp).convert("RGB"))

    def _render_image_el(self, card, x, y, w, h, path):
        if path and os.path.exists(path):
            try:
                img = Image.open(path).convert("RGB").resize((w,h), Image.LANCZOS)
                card.paste(img, (x,y))
            except Exception:
                pass

    def _render_photo(self, card, x, y, w, h, photo_path):
        if photo_path and os.path.exists(photo_path):
            try:
                photo = Image.open(photo_path)
                # Flatten transparency onto white — removes black background from PNGs
                if photo.mode in ("RGBA", "LA", "P"):
                    bg = Image.new("RGB", photo.size, (255, 255, 255))
                    if photo.mode == "P":
                        photo = photo.convert("RGBA")
                    if photo.mode in ("RGBA", "LA"):
                        bg.paste(photo, mask=photo.split()[-1])
                    else:
                        bg.paste(photo)
                    photo = bg
                else:
                    photo = photo.convert("RGB")
                # Crop to fill ratio
                pw, ph = photo.size
                target_ratio = w / h
                src_ratio    = pw / ph
                if src_ratio > target_ratio:
                    new_w = int(ph * target_ratio)
                    left  = (pw - new_w) // 2
                    photo = photo.crop((left, 0, left+new_w, ph))
                else:
                    new_h = int(pw / target_ratio)
                    top   = (ph - new_h) // 2
                    photo = photo.crop((0, top, pw, top+new_h))
                photo = photo.resize((w, h), Image.LANCZOS)
                card.paste(photo, (x, y))
                return
            except Exception as e:
                print("Photo error:", e)
        draw = ImageDraw.Draw(card)
        draw.rectangle([x, y, x+w, y+h], fill=(220,220,220))
        draw.text((x+w//2, y+h//2), "No Photo", fill=(160,160,160), anchor="mm")

    def _render_qr(self, card, x, y, w, h, qr_path):
        if qr_path and os.path.exists(qr_path):
            try:
                qr = Image.open(qr_path).convert("RGBA")
                bg = Image.new("RGB", (w,h), (255,255,255))
                qr = qr.resize((w,h), Image.LANCZOS)
                if qr.mode == "RGBA":
                    bg.paste(qr, mask=qr.split()[3])
                else:
                    bg.paste(qr)
                card.paste(bg, (x,y))
                return
            except Exception as e:
                print("QR error:", e)
        draw = ImageDraw.Draw(card)
        draw.rectangle([x, y, x+w, y+h], outline=(180,180,180), width=2)
        draw.text((x+w//2, y+h//2), "QR", fill=(180,180,180), anchor="mm")

    def _render_text(self, card, x, y, w, h, text, el):
        draw = ImageDraw.Draw(card)
        font_size = el.get("font_size", 8)
        bold      = el.get("bold", False)
        color     = self._hex2rgb(el.get("text_color", "#1A1A1A"))
        font_name = el.get("font_name", "Arial")
        font      = self._get_font(font_size, bold, font_name)
        # Handle multi-line text (\n line breaks)
        lines = str(text).split("\n")
        line_h = int(font_size * DPI / 72 * 1.3)
        cy = y + h // 6
        for line in lines:
            if line.strip():
                draw.text((x, cy), line, fill=color, font=font)
            cy += line_h

    def _get_font(self, size_pt: int, bold: bool = False, font_name: str = "Arial") -> ImageFont.FreeTypeFont:
        size_px = max(8, int(size_pt * DPI / 72))
        win = "C:/Windows/Fonts/"

        # Try by font name
        name_clean = font_name.replace(" ", "")
        candidates = []
        if bold:
            candidates += [
                win + name_clean + "bd.ttf",
                win + name_clean + "Bold.ttf",
                win + name_clean + "-Bold.ttf",
                win + name_clean.lower() + "bd.ttf",
                win + "Montserrat-Bold.ttf",
                win + "arialbd.ttf",
            ]
        else:
            candidates += [
                win + name_clean + ".ttf",
                win + name_clean + "-Regular.ttf",
                win + name_clean.lower() + ".ttf",
                win + "Montserrat-Regular.ttf",
                win + "arial.ttf",
            ]
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans{}.ttf".format("-Bold" if bold else ""),
        ]

        for path in candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size_px)
                except Exception:
                    pass
        return ImageFont.load_default()

    def _hex2rgb(self, h):
        h = h.lstrip("#")
        try: return tuple(int(h[i:i+2],16) for i in (0,2,4))
        except: return (20,20,20)

    def _hex2rgba(self, h):
        r,g,b = self._hex2rgb(h)
        return (r,g,b,255)

    def render_to_bytes(self, staff, template_path, config,
                        width=CARD_W_PX, height=CARD_H_PX, fmt="PNG") -> bytes:
        img = self.render_card(staff, template_path, config, width, height)
        buf = io.BytesIO()
        img.save(buf, format=fmt, dpi=(DPI,DPI))
        buf.seek(0)
        return buf.read()

    def save_card(self, staff, template_path, config, output_path,
                  width=CARD_W_PX, height=CARD_H_PX):
        img = self.render_card(staff, template_path, config, width, height)
        img.save(output_path, dpi=(DPI,DPI))
        return output_path

    def save_card_as_pdf(self, staff, template_path, config, output_path,
                         width=CARD_W_PX, height=CARD_H_PX):
        """Save rendered card as a PDF at actual CR80 size (54x84.5mm)."""
        img = self.render_card(staff, template_path, config, width, height)
        # Convert to RGB for PDF (no alpha channel in PDF)
        if img.mode != "RGB":
            img = img.convert("RGB")
        # Save as PDF — Pillow embeds at the correct DPI so physical size is preserved
        img.save(output_path, format="PDF", resolution=DPI)
        return output_path

    def save_all_cards_as_pdf(self, staff_list, template_path, config, output_path,
                               width=CARD_W_PX, height=CARD_H_PX):
        """Save all staff cards as a multi-page PDF — one card per page."""
        images = []
        for staff in staff_list:
            img = self.render_card(staff, template_path, config, width, height)
            if img.mode != "RGB":
                img = img.convert("RGB")
            images.append(img)
        if not images:
            return
        images[0].save(
            output_path, format="PDF", resolution=DPI,
            save_all=True, append_images=images[1:]
        )
        return output_path
