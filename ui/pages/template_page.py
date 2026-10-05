"""
GTZ ID Studio - Template Designer
Full card designer: select, draw, rotate, group/ungroup, line, draw tool,
front/back templates, data binding, save & sync.
Portrait CR80: 54mm W x 84.5mm H @ 300 DPI
"""
import os, json, math, shutil
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QMessageBox,
    QFrame, QSplitter, QFormLayout, QSpinBox, QGroupBox,
    QScrollArea, QComboBox, QInputDialog, QColorDialog,
    QSizePolicy, QCheckBox, QDoubleSpinBox, QAbstractItemView,
    QTabWidget, QLineEdit, QTextEdit, QSlider, QDialog, QDialogButtonBox,
    QProgressDialog
)
from PyQt5.QtCore import Qt, QRectF, QPointF, QRect, pyqtSignal, QTimer
from PyQt5.QtGui import (
    QPixmap, QColor, QPainter, QPen, QFont, QFontDatabase,
    QImage, QBrush, QCursor, QTransform
)

# ── Card dimensions ──────────────────────────────────────────────────
CARD_W_MM  = 54.0
CARD_H_MM  = 84.5
DPI        = 300
MM_TO_PX   = DPI / 25.4
CARD_W_PX  = int(CARD_W_MM * MM_TO_PX)
CARD_H_PX  = int(CARD_H_MM * MM_TO_PX)
RULER_SIZE = 24
HANDLE     = 9

# Element types
ELEM_TEXT    = "text"
ELEM_PHOTO   = "photo"
ELEM_QR      = "qr"
ELEM_RECT    = "rect"
ELEM_ELLIPSE = "ellipse"
ELEM_IMAGE   = "image"
ELEM_LINE    = "line"

# Data binding keys → labels
DATA_FIELDS = {
    "name":        "Full Name",
    "first_name":  "First Name",
    "last_name":   "Last Name",
    "staff_id":    "Staff ID",
    "department":  "Department",
    "designation": "Designation",
    "email":       "Email",
    "phone":       "Phone",
}

POPULAR_FONTS = [
    "Montserrat",
    "Arial","Arial Black","Calibri","Cambria","Comic Sans MS",
    "Courier New","Georgia","Impact","Segoe UI","Tahoma",
    "Times New Roman","Trebuchet MS","Verdana","Century Gothic",
    "Franklin Gothic Medium",
]

def mm2px(mm): return mm * MM_TO_PX
def px2mm(px): return px / MM_TO_PX


# ── CanvasElement ────────────────────────────────────────────────────
class CanvasElement:
    _id_counter = 0

    def __init__(self, etype, x_mm, y_mm, w_mm, h_mm, **kw):
        CanvasElement._id_counter += 1
        self.id      = CanvasElement._id_counter
        self.type    = etype
        self.x       = x_mm
        self.y       = y_mm
        self.w       = w_mm
        self.h       = h_mm
        self.visible = True
        self.rotation= kw.get("rotation", 0.0)   # degrees
        self.locked  = kw.get("locked", False)
        self.group_id= kw.get("group_id", None)   # for group/ungroup

        # Text
        self.text       = kw.get("text", "")
        self.key        = kw.get("key", "")        # data binding field
        self.label      = kw.get("label", "")
        self.font_name  = kw.get("font_name", "Arial")
        self.font_size  = kw.get("font_size", 8)
        self.bold       = kw.get("bold", False)
        self.italic     = kw.get("italic", False)
        self.text_color = kw.get("text_color", "#1A1A1A")
        self.align      = kw.get("align", int(Qt.AlignLeft))

        # Shape / image
        self.fill_color   = kw.get("fill_color", "#FFFFFF")
        self.stroke_color = kw.get("stroke_color", "#000000")
        self.stroke_width = kw.get("stroke_width", 0.5)
        self.fill_enabled = kw.get("fill_enabled", True)
        self.image_path   = kw.get("image_path", "")
        self._pixmap_cache = None

        # Line (second point, relative to x,y in mm)
        self.x2 = kw.get("x2", x_mm + w_mm)
        self.y2 = kw.get("y2", y_mm)

    def to_dict(self):
        return {
            "id":self.id,"type":self.type,
            "x":self.x,"y":self.y,"w":self.w,"h":self.h,
            "visible":self.visible,"rotation":self.rotation,
            "locked":self.locked,"group_id":self.group_id,
            "text":self.text,"key":self.key,"label":self.label,
            "font_name":self.font_name,"font_size":self.font_size,
            "bold":self.bold,"italic":self.italic,
            "text_color":self.text_color,"align":int(self.align),
            "fill_color":self.fill_color,"stroke_color":self.stroke_color,
            "stroke_width":self.stroke_width,"fill_enabled":self.fill_enabled,
            "image_path":self.image_path,
            "x2":self.x2,"y2":self.y2,
        }

    @staticmethod
    def from_dict(d):
        el = CanvasElement(
            d["type"],d["x"],d["y"],d["w"],d["h"],
            text=d.get("text",""),key=d.get("key",""),label=d.get("label",""),
            font_name=d.get("font_name","Arial"),font_size=d.get("font_size",8),
            bold=d.get("bold",False),italic=d.get("italic",False),
            text_color=d.get("text_color","#1A1A1A"),
            align=d.get("align",int(Qt.AlignLeft)),
            fill_color=d.get("fill_color","#FFFFFF"),
            stroke_color=d.get("stroke_color","#000000"),
            stroke_width=d.get("stroke_width",0.5),
            fill_enabled=d.get("fill_enabled",True),
            image_path=d.get("image_path",""),
            rotation=d.get("rotation",0.0),
            locked=d.get("locked",False),
            group_id=d.get("group_id",None),
            x2=d.get("x2",0),y2=d.get("y2",0),
        )
        el.id = d.get("id", el.id)
        el.visible = d.get("visible", True)
        return el


# ── CardCanvas ───────────────────────────────────────────────────────
class CardCanvas(QWidget):
    selection_changed = pyqtSignal(object)
    canvas_changed    = pyqtSignal()

    TOOL_SELECT  = "select"
    TOOL_RECT    = "rect"
    TOOL_ELLIPSE = "ellipse"
    TOOL_TEXT    = "text"
    TOOL_LINE    = "line"
    TOOL_DRAW    = "draw"
    TOOL_ROTATE  = "rotate"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 500)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        self.elements   = []
        self.selected   = []      # list — supports multi-select
        self.bg_pixmap  = None
        self.bg_color   = "#F5F5F5"
        self.staff      = {}
        self.show_grid  = True
        self.tool       = self.TOOL_SELECT
        self.zoom       = 1.0
        self._group_counter = 0

        # Drag/resize/draw state
        self._drag       = False
        self._resize     = False
        self._resize_handle = None
        self._drag_off   = QPointF()
        self._drag_start_positions = {}   # id -> (x,y) for multi-drag
        self._draw_start = None
        self._draw_cur   = None
        self._draw_path  = []             # for freehand draw
        self._rotate_start_angle = 0.0
        self._rotate_center = QPointF()

    # ── coordinate helpers ───────────────────────────────────────────
    def _scale(self):
        aw = self.width()  - RULER_SIZE
        ah = self.height() - RULER_SIZE
        sx = aw / CARD_W_MM
        sy = ah / CARD_H_MM
        s  = min(sx, sy) * self.zoom
        ox = RULER_SIZE + (aw - CARD_W_MM * s) / 2
        oy = RULER_SIZE + (ah - CARD_H_MM * s) / 2
        return s, ox, oy

    def _to_screen(self, xmm, ymm, s, ox, oy):
        return QPointF(ox + xmm*s, oy + ymm*s)

    def _to_mm(self, sx, sy, s, ox, oy):
        return ((sx-ox)/s, (sy-oy)/s)

    def _elem_rect_screen(self, el, s, ox, oy):
        return QRectF(ox+el.x*s, oy+el.y*s, el.w*s, el.h*s)

    def _handle_rects(self, r):
        hw = HANDLE/2
        cx, cy = r.center().x(), r.center().y()
        return {
            "tl":QRectF(r.left()-hw,  r.top()-hw,   HANDLE,HANDLE),
            "tm":QRectF(cx-hw,        r.top()-hw,   HANDLE,HANDLE),
            "tr":QRectF(r.right()-hw, r.top()-hw,   HANDLE,HANDLE),
            "ml":QRectF(r.left()-hw,  cy-hw,        HANDLE,HANDLE),
            "mr":QRectF(r.right()-hw, cy-hw,        HANDLE,HANDLE),
            "bl":QRectF(r.left()-hw,  r.bottom()-hw,HANDLE,HANDLE),
            "bm":QRectF(cx-hw,        r.bottom()-hw,HANDLE,HANDLE),
            "br":QRectF(r.right()-hw, r.bottom()-hw,HANDLE,HANDLE),
            "rot":QRectF(cx-hw,       r.top()-hw-18,HANDLE,HANDLE),  # rotate handle
        }

    def _primary(self):
        return self.selected[0] if self.selected else None

    # ── public API ───────────────────────────────────────────────────
    def set_background(self, pixmap_or_none):
        self.bg_pixmap = pixmap_or_none
        self.update()

    def set_bg_color(self, color_hex):
        self.bg_color = color_hex
        self.bg_pixmap = None
        self.update()

    def set_tool(self, tool):
        self.tool = tool
        cursors = {
            self.TOOL_SELECT:  Qt.ArrowCursor,
            self.TOOL_RECT:    Qt.CrossCursor,
            self.TOOL_ELLIPSE: Qt.CrossCursor,
            self.TOOL_TEXT:    Qt.IBeamCursor,
            self.TOOL_LINE:    Qt.CrossCursor,
            self.TOOL_DRAW:    Qt.CrossCursor,
            self.TOOL_ROTATE:  Qt.SizeAllCursor,
        }
        self.setCursor(cursors.get(tool, Qt.ArrowCursor))

    def set_staff(self, staff):
        self.staff = staff or {}
        self.update()

    def add_element(self, el):
        self.elements.append(el)
        self.selected = [el]
        self.selection_changed.emit(el)
        self.canvas_changed.emit()
        self.update()

    def delete_selected(self):
        if not self.selected:
            return
        for el in list(self.selected):
            if el in self.elements:
                self.elements.remove(el)
        self.selected = []
        self.selection_changed.emit(None)
        self.canvas_changed.emit()
        self.update()

    def move_up(self):
        el = self._primary()
        if el and el in self.elements:
            i = self.elements.index(el)
            if i < len(self.elements)-1:
                self.elements[i], self.elements[i+1] = self.elements[i+1], self.elements[i]
                self.canvas_changed.emit(); self.update()

    def move_down(self):
        el = self._primary()
        if el and el in self.elements:
            i = self.elements.index(el)
            if i > 0:
                self.elements[i], self.elements[i-1] = self.elements[i-1], self.elements[i]
                self.canvas_changed.emit(); self.update()

    def select_all(self):
        self.selected = list(self.elements)
        self.selection_changed.emit(self._primary())
        self.update()

    def group_selected(self):
        targets = self.selected if len(self.selected) >= 2 else self.elements
        if len(targets) < 2:
            return
        self._group_counter += 1
        gid = "group_{}".format(self._group_counter)
        for el in targets:
            el.group_id = gid
        self.canvas_changed.emit(); self.update()

    def ungroup_selected(self):
        el = self._primary()
        if not el or not el.group_id:
            return
        gid = el.group_id
        for e in self.elements:
            if e.group_id == gid:
                e.group_id = None
        self.canvas_changed.emit(); self.update()

    def rotate_selected(self, delta_deg):
        for el in self.selected:
            el.rotation = (el.rotation + delta_deg) % 360
        self.canvas_changed.emit(); self.update()

    def get_config(self):
        return {
            "elements": [e.to_dict() for e in self.elements],
            "bg_color": self.bg_color,
            "bg_image": getattr(self, "_bg_image_path", ""),
        }

    def load_config(self, config):
        self.elements = [CanvasElement.from_dict(d) for d in config.get("elements", [])]
        self.bg_color = config.get("bg_color", "#F5F5F5")
        self._bg_image_path = config.get("bg_image", "")
        if self._bg_image_path and os.path.exists(self._bg_image_path):
            self.bg_pixmap = QPixmap(self._bg_image_path)
        else:
            self.bg_pixmap = None
        self.selected = []
        self.update()

    # ── painting ─────────────────────────────────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        s, ox, oy = self._scale()

        p.fillRect(self.rect(), QColor("#4A4A4A"))

        card_rect = QRectF(ox, oy, CARD_W_MM*s, CARD_H_MM*s)

        if self.bg_pixmap and not self.bg_pixmap.isNull():
            p.drawPixmap(card_rect.toRect(), self.bg_pixmap)
        else:
            p.fillRect(card_rect, QColor(self.bg_color))

        if self.show_grid:
            self._draw_grid(p, s, ox, oy)

        p.setPen(QPen(QColor("#555"), 1))
        p.drawRect(card_rect)

        p.setClipRect(card_rect)
        for el in self.elements:
            if el.visible:
                self._draw_element(p, el, s, ox, oy)
        p.setClipping(False)

        # Draw-in-progress
        if self._draw_cur and self._draw_start:
            p.setPen(QPen(QColor("#2E5BFF"), 1.5, Qt.DashLine))
            if self.tool == self.TOOL_LINE:
                p.drawLine(self._draw_start, self._draw_cur)
            else:
                r = QRectF(self._draw_start, self._draw_cur).normalized()
                p.drawRect(r)

        if self._draw_path and self.tool == self.TOOL_DRAW:
            p.setPen(QPen(QColor("#EF4444"), 2))
            pts = self._draw_path
            for i in range(1, len(pts)):
                p.drawLine(pts[i-1], pts[i])

        # Selection outlines
        for el in self.selected:
            if el in self.elements:
                self._draw_selection(p, el, s, ox, oy)

        self._draw_rulers(p, s, ox, oy)
        p.end()

    def _draw_selection(self, p, el, s, ox, oy):
        r = self._elem_rect_screen(el, s, ox, oy)
        if el.rotation:
            p.save()
            cx, cy = r.center().x(), r.center().y()
            p.translate(cx, cy)
            p.rotate(el.rotation)
            p.translate(-cx, -cy)

        p.setPen(QPen(QColor("#2E5BFF"), 1.5, Qt.DashLine))
        p.setBrush(Qt.NoBrush)
        p.drawRect(r)

        # Resize handles
        p.setBrush(QBrush(QColor("#2E5BFF")))
        p.setPen(Qt.NoPen)
        handles = self._handle_rects(r)
        for hk, hr in handles.items():
            if hk == "rot":
                p.setBrush(QBrush(QColor("#10B981")))
            else:
                p.setBrush(QBrush(QColor("#2E5BFF")))
            p.drawRect(hr)

        if el.rotation:
            p.restore()

    def _draw_grid(self, p, s, ox, oy):
        p.setPen(QPen(QColor(200,200,200,80), 0.5))
        mm = 0.0
        while mm <= CARD_W_MM:
            sx = ox + mm*s
            p.drawLine(QPointF(sx,oy), QPointF(sx,oy+CARD_H_MM*s))
            mm += 5.0
        mm = 0.0
        while mm <= CARD_H_MM:
            sy = oy + mm*s
            p.drawLine(QPointF(ox,sy), QPointF(ox+CARD_W_MM*s,sy))
            mm += 5.0

    def _draw_rulers(self, p, s, ox, oy):
        p.fillRect(QRect(0,0,self.width(),RULER_SIZE), QColor("#2C2C2C"))
        p.fillRect(QRect(0,0,RULER_SIZE,self.height()), QColor("#2C2C2C"))
        p.fillRect(QRect(0,0,RULER_SIZE,RULER_SIZE), QColor("#1A1A1A"))
        p.setPen(QPen(QColor("#CCCCCC"), 0.5))
        p.setFont(QFont("Arial", 6))
        mm = 0.0
        while mm <= CARD_W_MM+0.1:
            sx = ox+mm*s
            if 0 <= sx <= self.width():
                p.drawLine(QPointF(sx,RULER_SIZE-6),QPointF(sx,RULER_SIZE))
                if mm % 10 == 0:
                    p.drawText(QRectF(sx-10,2,20,12),Qt.AlignCenter,"{}".format(int(mm)))
            mm += 5.0
        mm = 0.0
        while mm <= CARD_H_MM+0.1:
            sy = oy+mm*s
            if 0 <= sy <= self.height():
                p.drawLine(QPointF(RULER_SIZE-6,sy),QPointF(RULER_SIZE,sy))
                if mm % 10 == 0:
                    p.save()
                    p.translate(RULER_SIZE/2,sy)
                    p.rotate(-90)
                    p.drawText(QRectF(-10,-6,20,12),Qt.AlignCenter,"{}".format(int(mm)))
                    p.restore()
            mm += 5.0

    def _draw_element(self, p, el, s, ox, oy):
        r = self._elem_rect_screen(el, s, ox, oy)

        if el.rotation:
            p.save()
            cx, cy = r.center().x(), r.center().y()
            p.translate(cx, cy)
            p.rotate(el.rotation)
            p.translate(-cx, -cy)

        if el.type == ELEM_RECT:
            if el.fill_enabled:
                p.fillRect(r, QColor(el.fill_color))
            if el.stroke_width > 0:
                sw = max(1, el.stroke_width * s * 0.1)
                p.setPen(QPen(QColor(el.stroke_color), sw))
                p.setBrush(Qt.NoBrush)
                p.drawRect(r)

        elif el.type == ELEM_ELLIPSE:
            p.setBrush(QBrush(QColor(el.fill_color)) if el.fill_enabled else Qt.NoBrush)
            sw = max(1, el.stroke_width*s*0.1) if el.stroke_width > 0 else 0
            p.setPen(QPen(QColor(el.stroke_color), sw) if sw else Qt.NoPen)
            p.drawEllipse(r)
            p.setBrush(Qt.NoBrush)

        elif el.type == ELEM_LINE:
            sw = max(1, el.stroke_width*s*0.1)
            p.setPen(QPen(QColor(el.stroke_color), sw))
            p1 = self._to_screen(el.x, el.y, s, ox, oy)
            p2 = self._to_screen(el.x2, el.y2, s, ox, oy)
            p.drawLine(p1, p2)

        elif el.type == ELEM_IMAGE:
            if not el._pixmap_cache and el.image_path and os.path.exists(el.image_path):
                el._pixmap_cache = QPixmap(el.image_path)
            if el._pixmap_cache and not el._pixmap_cache.isNull():
                p.drawPixmap(r.toRect(), el._pixmap_cache)
            else:
                p.fillRect(r, QColor("#DDDDDD"))
                p.setPen(QColor("#999")); p.drawText(r, Qt.AlignCenter, "Image")

        elif el.type == ELEM_PHOTO:
            photo = self.staff.get("photo_path","")
            if photo and os.path.exists(photo):
                pix = QPixmap(photo)
                if not pix.isNull():
                    # Convert to ARGB32 to handle transparency — no black bg
                    img = pix.toImage().convertToFormat(QImage.Format_ARGB32_Premultiplied)
                    pix2 = QPixmap.fromImage(img)
                    p.save()
                    p.setClipRect(r)
                    # Scale keeping aspect ratio, centre in box
                    scaled = pix2.scaled(int(r.width()), int(r.height()),
                                         Qt.KeepAspectRatioByExpanding,
                                         Qt.SmoothTransformation)
                    ox2 = r.x() + (r.width()  - scaled.width())  / 2
                    oy2 = r.y() + (r.height() - scaled.height()) / 2
                    p.drawPixmap(int(ox2), int(oy2), scaled)
                    p.restore()
                    if el.rotation: p.restore()
                    return
            p.fillRect(r, QColor("#E8E8E8"))
            p.setPen(QColor("#999")); p.drawText(r, Qt.AlignCenter, "📷  Photo")

        elif el.type == ELEM_QR:
            p.fillRect(r, QColor("#FFFFFF"))
            p.setPen(QPen(QColor("#AAAAAA"), 1)); p.drawRect(r)
            p.setPen(QColor("#AAAAAA"))
            p.setFont(QFont("Arial", max(6, int(7*s*0.04))))
            p.drawText(r, Qt.AlignCenter, "[ QR Code ]")

        elif el.type == ELEM_TEXT:
            font = QFont(el.font_name, max(6, int(el.font_size * s * 0.35)))
            font.setBold(el.bold); font.setItalic(el.italic)
            p.setFont(font); p.setPen(QColor(el.text_color))
            # Priority: typed text first, then staff data binding, then label placeholder
            if el.text and el.text.strip():
                display = el.text
            elif el.key and self.staff.get(el.key, ""):
                display = str(self.staff.get(el.key, ""))
            else:
                display = "[{}]".format(el.label or el.key or "Text")
            p.drawText(r, Qt.AlignVCenter | Qt.TextWordWrap | int(el.align), display)

        if el.rotation:
            p.restore()

    # ── mouse events ─────────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        s, ox, oy = self._scale()
        pos = QPointF(event.pos())
        multi = event.modifiers() & Qt.ControlModifier

        if self.tool == self.TOOL_SELECT:
            el = self._primary()
            # Check rotate handle first
            if el and el in self.elements:
                r = self._elem_rect_screen(el, s, ox, oy)
                rot_h = self._handle_rects(r)["rot"]
                if rot_h.contains(pos):
                    self._resize = True
                    self._resize_handle = "rot"
                    cx = r.center()
                    self._rotate_center = cx
                    self._rotate_start_angle = el.rotation
                    self._drag_off = pos
                    return
                # Resize handles
                for hname, hr in self._handle_rects(r).items():
                    if hname == "rot": continue
                    if hr.contains(pos):
                        self._resize = True
                        self._resize_handle = hname
                        self._drag_off = pos
                        return

            # Click element
            hit = None
            for e in reversed(self.elements):
                if not e.visible: continue
                r = self._elem_rect_screen(e, s, ox, oy)
                if r.contains(pos):
                    hit = e; break

            if hit:
                if multi:
                    if hit in self.selected:
                        self.selected.remove(hit)
                    else:
                        self.selected.append(hit)
                else:
                    self.selected = [hit]
                self._drag = True
                r = self._elem_rect_screen(hit, s, ox, oy)
                self._drag_off = pos - r.topLeft()
                # Record start positions for multi-drag
                self._drag_start_positions = {e.id: (e.x, e.y) for e in self.selected}
                self._drag_start_pos = pos
                self.selection_changed.emit(hit)
            else:
                if not multi:
                    self.selected = []
                    self.selection_changed.emit(None)
            self.update()

        elif self.tool == self.TOOL_ROTATE:
            el = self._primary()
            if el:
                r = self._elem_rect_screen(el, s, ox, oy)
                self._rotate_center = r.center()
                self._drag = True
                self._drag_off = pos

        elif self.tool == self.TOOL_DRAW:
            self._draw_path = [pos]
            self._draw_start = pos

        else:
            # Drawing shapes/line/text
            self._draw_start = pos
            self._draw_cur   = pos

    def mouseMoveEvent(self, event):
        s, ox, oy = self._scale()
        pos = QPointF(event.pos())

        if self._drag and self.selected and self.tool in (self.TOOL_SELECT, self.TOOL_ROTATE):
            if self.tool == self.TOOL_ROTATE:
                el = self._primary()
                if el:
                    dx = pos.x() - self._rotate_center.x()
                    dy = pos.y() - self._rotate_center.y()
                    angle = math.degrees(math.atan2(dy, dx))
                    el.rotation = round(angle, 1)
                    self.canvas_changed.emit(); self.update()
            else:
                # Move all selected elements together
                if len(self.selected) == 1:
                    el = self.selected[0]
                    new_tl = pos - self._drag_off
                    xmm, ymm = self._to_mm(new_tl.x(), new_tl.y(), s, ox, oy)
                    dx = round(xmm, 2) - el.x
                    dy = round(ymm, 2) - el.y
                    # If element is in a group, move all group members together
                    if el.group_id:
                        for e in self.elements:
                            if e.group_id == el.group_id:
                                e.x = max(0, round(e.x + dx, 2))
                                e.y = max(0, round(e.y + dy, 2))
                    else:
                        el.x = max(0, round(xmm, 2))
                        el.y = max(0, round(ymm, 2))
                else:
                    dx_px = pos.x() - self._drag_start_pos.x()
                    dy_px = pos.y() - self._drag_start_pos.y()
                    dx_mm = dx_px / s
                    dy_mm = dy_px / s
                    for el in self.selected:
                        sx0, sy0 = self._drag_start_positions.get(el.id, (el.x, el.y))
                        el.x = max(0, round(sx0 + dx_mm, 2))
                        el.y = max(0, round(sy0 + dy_mm, 2))
                self.canvas_changed.emit(); self.update()

        elif self._resize and self._primary():
            el = self._primary()
            h = self._resize_handle
            if h == "rot":
                dx = pos.x() - self._rotate_center.x()
                dy = pos.y() - self._rotate_center.y()
                el.rotation = round(math.degrees(math.atan2(dy, dx)), 1)
            else:
                dx = (pos.x() - self._drag_off.x()) / s
                dy = (pos.y() - self._drag_off.y()) / s
                if "r" in h: el.w = max(2, round(el.w+dx, 2))
                if "b" in h: el.h = max(2, round(el.h+dy, 2))
                if "l" in h: el.x = round(el.x+dx,2); el.w = max(2,round(el.w-dx,2))
                if "t" in h: el.y = round(el.y+dy,2); el.h = max(2,round(el.h-dy,2))
                self._drag_off = pos
            self.canvas_changed.emit(); self.update()

        elif self.tool == self.TOOL_DRAW and self._draw_path:
            self._draw_path.append(pos)
            self.update()

        elif self._draw_start and self.tool not in (self.TOOL_SELECT, self.TOOL_ROTATE, self.TOOL_DRAW):
            self._draw_cur = pos
            self.update()

    def mouseReleaseEvent(self, event):
        s, ox, oy = self._scale()
        pos = QPointF(event.pos())

        if self.tool == self.TOOL_DRAW and self._draw_path and len(self._draw_path) > 3:
            # Convert freehand path to a polyline stored as image element placeholder
            # For now create a rect bounding the path
            xs = [p.x() for p in self._draw_path]
            ys = [p.y() for p in self._draw_path]
            xmm, ymm = self._to_mm(min(xs), min(ys), s, ox, oy)
            wmm = (max(xs)-min(xs)) / s
            hmm = (max(ys)-min(ys)) / s
            el = CanvasElement(ELEM_RECT, xmm, ymm, max(2,wmm), max(2,hmm),
                               fill_color="#EF4444", stroke_color="#EF4444",
                               stroke_width=0.3, fill_enabled=False, label="Drawing")
            self.add_element(el)
            self._draw_path = []

        elif self._draw_start and self._draw_cur:
            r = QRectF(self._draw_start, self._draw_cur).normalized()
            if r.width() > 4 or self.tool == self.TOOL_LINE:
                xmm, ymm = self._to_mm(r.left(), r.top(), s, ox, oy)
                wmm = r.width() / s
                hmm = r.height() / s
                x2mm, y2mm = self._to_mm(self._draw_cur.x(), self._draw_cur.y(), s, ox, oy)

                if self.tool == self.TOOL_RECT:
                    el = CanvasElement(ELEM_RECT, xmm, ymm, wmm, hmm,
                                       fill_color="#2E5BFF", stroke_color="#1A47E8",
                                       stroke_width=0.3, fill_enabled=True, label="Rectangle")
                elif self.tool == self.TOOL_ELLIPSE:
                    el = CanvasElement(ELEM_ELLIPSE, xmm, ymm, wmm, hmm,
                                       fill_color="#10B981", stroke_color="#059669",
                                       stroke_width=0.3, fill_enabled=True, label="Ellipse")
                elif self.tool == self.TOOL_TEXT:
                    el = CanvasElement(ELEM_TEXT, xmm, ymm, wmm, max(hmm,6),
                                       text="Text", label="Text Box",
                                       font_name="Arial", font_size=10, text_color="#1A1A1A")
                elif self.tool == self.TOOL_LINE:
                    x1mm, y1mm = self._to_mm(self._draw_start.x(), self._draw_start.y(), s, ox, oy)
                    el = CanvasElement(ELEM_LINE, x1mm, y1mm, wmm, 0,
                                       stroke_color="#1A1A1A", stroke_width=0.5,
                                       fill_enabled=False, label="Line",
                                       x2=x2mm, y2=y2mm)
                else:
                    el = None

                if el:
                    self.add_element(el)
                    self.set_tool(self.TOOL_SELECT)

        self._drag = False
        self._resize = False
        self._draw_start = None
        self._draw_cur   = None
        self._draw_path  = []

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self.delete_selected()
        elif event.key() == Qt.Key_A and event.modifiers() & Qt.ControlModifier:
            self.select_all()
        elif event.key() == Qt.Key_G and event.modifiers() & Qt.ControlModifier:
            self.group_selected()
        elif event.key() == Qt.Key_U and event.modifiers() & Qt.ControlModifier:
            self.ungroup_selected()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        self.zoom = max(0.4, min(3.0, self.zoom + delta*0.001))
        self.update()


# ── PropertiesPanel ──────────────────────────────────────────────────
class PropertiesPanel(QWidget):
    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._el = None
        self._building = False
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10,10,10,10)
        layout.setSpacing(8)

        self.title_lbl = QLabel("No element selected")
        self.title_lbl.setStyleSheet(
            "font-size:10pt; font-weight:bold; color:#1A1F36; "
            "background:#F0F4FF; border-radius:6px; padding:8px;"
        )
        self.title_lbl.setWordWrap(True)
        layout.addWidget(self.title_lbl)

        # Position & size
        pos_grp = QGroupBox("Position & Size (mm)")
        pf = QFormLayout(pos_grp); pf.setSpacing(5)
        pf.setLabelAlignment(Qt.AlignRight)
        pf.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        def _dspin(lo=0,hi=300):
            w = QDoubleSpinBox(); w.setRange(lo,hi); w.setDecimals(1); w.setSuffix(" mm")
            w.setStyleSheet("QDoubleSpinBox { background:#FFF; color:#1A1F36; border:1px solid #D1D5DB; border-radius:4px; padding:3px 6px; }")
            return w
        self.px=_dspin(); self.py=_dspin(); self.pw=_dspin(1); self.ph=_dspin(1)
        self.pr=_dspin(-360,360); self.pr.setSuffix(" °")
        for w in [self.px,self.py,self.pw,self.ph,self.pr]:
            w.valueChanged.connect(self._on_pos_changed)
        pf.addRow("X:", self.px); pf.addRow("Y:", self.py)
        pf.addRow("W:", self.pw); pf.addRow("H:", self.ph)
        pf.addRow("Rotate:", self.pr)
        layout.addWidget(pos_grp)

        # Data binding
        bind_grp = QGroupBox("Data Binding")
        bf = QFormLayout(bind_grp); bf.setSpacing(5)
        self.bind_combo = QComboBox()
        self.bind_combo.setStyleSheet("QComboBox { background:#FFF; color:#1A1F36; border:1px solid #D1D5DB; border-radius:4px; padding:3px 6px; } QComboBox QAbstractItemView { background:#FFF; color:#1A1F36; selection-background-color:#EEF2FF;}")
        self.bind_combo.addItem("— None —", "")
        for k, v in DATA_FIELDS.items():
            self.bind_combo.addItem(v, k)
        self.bind_combo.currentIndexChanged.connect(self._on_bind_changed)
        bf.addRow("Bind to:", self.bind_combo)
        self.bind_grp = bind_grp
        layout.addWidget(bind_grp)

        # Text
        text_grp = QGroupBox("Text")
        tf = QFormLayout(text_grp); tf.setSpacing(5)
        tf.setLabelAlignment(Qt.AlignRight)
        tf.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.t_content = QTextEdit()
        self.t_content.setFixedHeight(60)
        self.t_content.setStyleSheet("QTextEdit { background:#FFF; color:#1A1F36; border:1px solid #D1D5DB; border-radius:4px; padding:4px; font-size:9pt; }")
        self.t_content.setPlaceholderText("Type text here...\nUse Enter for new line")
        self.t_content.textChanged.connect(self._on_text_changed)
        self.t_font = QComboBox()
        self.t_font.setStyleSheet("QComboBox { background:#FFF; color:#1A1F36; border:1px solid #D1D5DB; border-radius:4px; padding:3px 6px; } QComboBox QAbstractItemView { background:#FFF; color:#1A1F36; selection-background-color:#EEF2FF;}")
        db = QFontDatabase()
        self.t_font.addItems(sorted(set(POPULAR_FONTS + list(db.families()))))
        self.t_font.currentTextChanged.connect(self._on_text_changed)
        self.t_size = QSpinBox(); self.t_size.setRange(4,120)
        self.t_size.setStyleSheet("QSpinBox { background:#FFF; color:#1A1F36; border:1px solid #D1D5DB; border-radius:4px; padding:3px 6px; }")
        self.t_size.valueChanged.connect(self._on_text_changed)
        self.t_bold   = QCheckBox("Bold"); self.t_bold.stateChanged.connect(self._on_text_changed)
        self.t_italic = QCheckBox("Italic"); self.t_italic.stateChanged.connect(self._on_text_changed)
        self.t_color_btn = QPushButton("■  Text Color")
        self.t_color_btn.clicked.connect(self._pick_text_color)
        self._tcolor = "#1A1A1A"; self._upd_tc()
        style_row = QHBoxLayout(); style_row.addWidget(self.t_bold); style_row.addWidget(self.t_italic)
        tf.addRow("Content:", self.t_content)
        tf.addRow("Font:", self.t_font)
        tf.addRow("Size pt:", self.t_size)
        tf.addRow("Style:", style_row)
        tf.addRow("Color:", self.t_color_btn)
        self.text_grp = text_grp
        layout.addWidget(text_grp)

        # Shape
        shape_grp = QGroupBox("Fill & Stroke")
        sf = QFormLayout(shape_grp); sf.setSpacing(5)
        sf.setLabelAlignment(Qt.AlignRight)
        sf.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.s_fill_on = QCheckBox("Fill enabled"); self.s_fill_on.stateChanged.connect(self._on_shape_changed)
        self.s_fill_btn = QPushButton("■  Fill Color"); self.s_fill_btn.clicked.connect(self._pick_fill)
        self.s_stroke_btn = QPushButton("■  Stroke Color"); self.s_stroke_btn.clicked.connect(self._pick_stroke)
        self._fill="#2E5BFF"; self._stroke="#000000"; self._upd_fill(); self._upd_stroke()
        self.s_stroke_w = QDoubleSpinBox(); self.s_stroke_w.setRange(0,5); self.s_stroke_w.setDecimals(1); self.s_stroke_w.setSuffix(" mm")
        self.s_stroke_w.setStyleSheet("QDoubleSpinBox { background:#FFF; color:#1A1F36; border:1px solid #D1D5DB; border-radius:4px; padding:3px 6px; }")
        self.s_stroke_w.valueChanged.connect(self._on_shape_changed)
        sf.addRow("", self.s_fill_on)
        sf.addRow("Fill:", self.s_fill_btn)
        sf.addRow("Stroke:", self.s_stroke_btn)
        sf.addRow("Width:", self.s_stroke_w)
        self.shape_grp = shape_grp
        layout.addWidget(shape_grp)

        # Layer
        layer_grp = QGroupBox("Layer")
        ll = QHBoxLayout(layer_grp)
        self._up_btn = QPushButton("▲ Up"); self._up_btn.setObjectName("SecondaryBtn"); self._up_btn.setFixedHeight(28)
        self._dn_btn = QPushButton("▼ Down"); self._dn_btn.setObjectName("SecondaryBtn"); self._dn_btn.setFixedHeight(28)
        ll.addWidget(self._up_btn); ll.addWidget(self._dn_btn)
        layout.addWidget(layer_grp)

        layout.addStretch()

        self.text_grp.setVisible(False)
        self.shape_grp.setVisible(False)
        self.bind_grp.setVisible(False)

    def _upd_tc(self):
        self.t_color_btn.setStyleSheet(
            "QPushButton {{ background:{}; color:{}; border:1px solid #D1D5DB; border-radius:4px; padding:4px; }}".format(
                self._tcolor, "#FFF" if QColor(self._tcolor).lightness()<128 else "#000"
            ))
    def _upd_fill(self):
        self.s_fill_btn.setStyleSheet(
            "QPushButton {{ background:{}; color:{}; border:1px solid #D1D5DB; border-radius:4px; padding:4px; }}".format(
                self._fill, "#FFF" if QColor(self._fill).lightness()<128 else "#000"
            ))
    def _upd_stroke(self):
        self.s_stroke_btn.setStyleSheet(
            "QPushButton {{ background:{}; color:{}; border:1px solid #D1D5DB; border-radius:4px; padding:4px; }}".format(
                self._stroke, "#FFF" if QColor(self._stroke).lightness()<128 else "#000"
            ))

    def load(self, el):
        self._building = True
        self._el = el
        if el is None:
            self.title_lbl.setText("No element selected")
            self.text_grp.setVisible(False)
            self.shape_grp.setVisible(False)
            self.bind_grp.setVisible(False)
            self._building = False
            return

        self.title_lbl.setText("{}  [{}]".format(el.label or el.type, el.type.upper()))
        self.px.setValue(el.x); self.py.setValue(el.y)
        self.pw.setValue(el.w); self.ph.setValue(el.h)
        self.pr.setValue(el.rotation)

        is_text  = el.type == ELEM_TEXT
        is_shape = el.type in (ELEM_RECT, ELEM_ELLIPSE, ELEM_LINE)
        is_bindable = el.type in (ELEM_TEXT, ELEM_PHOTO, ELEM_QR)

        self.text_grp.setVisible(is_text)
        self.shape_grp.setVisible(is_shape)
        self.bind_grp.setVisible(is_bindable)

        if is_bindable:
            idx = self.bind_combo.findData(el.key or "")
            self.bind_combo.setCurrentIndex(max(0, idx))

        if is_text:
            for w in [self.t_content, self.t_font, self.t_size, self.t_bold, self.t_italic]:
                w.blockSignals(True)
            bound = bool(el.key)
            self.t_content.setReadOnly(bound)
            if bound:
                self.t_content.setPlainText("")
                self.t_content.setPlaceholderText("Bound to «{}» — set Bind to «None» to type custom text".format(
                    DATA_FIELDS.get(el.key, el.key)))
                self.t_content.setStyleSheet(
                    "QTextEdit { background:#F3F4F6; color:#9CA3AF; border:1px solid #D1D5DB; border-radius:4px; padding:4px; font-size:9pt; font-style:italic; }")
            else:
                self.t_content.setPlainText(el.text or "")
                self.t_content.setPlaceholderText("Type text here...\nUse Enter for new line")
                self.t_content.setStyleSheet(
                    "QTextEdit { background:#FFF; color:#1A1F36; border:1px solid #D1D5DB; border-radius:4px; padding:4px; font-size:9pt; }")
            idx = self.t_font.findText(el.font_name)
            if idx >= 0: self.t_font.setCurrentIndex(idx)
            self.t_size.setValue(el.font_size)
            self.t_bold.setChecked(el.bold)
            self.t_italic.setChecked(el.italic)
            self._tcolor = el.text_color; self._upd_tc()
            for w in [self.t_content, self.t_font, self.t_size, self.t_bold, self.t_italic]:
                w.blockSignals(False)

        if is_shape:
            self.s_fill_on.setChecked(el.fill_enabled)
            self._fill = el.fill_color; self._upd_fill()
            self._stroke = el.stroke_color; self._upd_stroke()
            self.s_stroke_w.setValue(el.stroke_width)

        self._building = False

    def _on_pos_changed(self):
        if self._building or not self._el: return
        self._el.x = self.px.value(); self._el.y = self.py.value()
        self._el.w = self.pw.value(); self._el.h = self.ph.value()
        self._el.rotation = self.pr.value()
        self.changed.emit()

    def _on_bind_changed(self):
        if self._building or not self._el: return
        self._el.key = self.bind_combo.currentData() or ""
        # Refresh content box state based on new binding
        bound = bool(self._el.key)
        self.t_content.blockSignals(True)
        self.t_content.setReadOnly(bound)
        if bound:
            self.t_content.setPlainText("")
            self.t_content.setPlaceholderText("Bound to «{}» — set Bind to «None» to type custom text".format(
                DATA_FIELDS.get(self._el.key, self._el.key)))
            self.t_content.setStyleSheet(
                "QTextEdit { background:#F3F4F6; color:#9CA3AF; border:1px solid #D1D5DB; border-radius:4px; padding:4px; font-size:9pt; font-style:italic; }")
        else:
            self.t_content.setPlainText(self._el.text or "")
            self.t_content.setPlaceholderText("Type text here...\nUse Enter for new line")
            self.t_content.setStyleSheet(
                "QTextEdit { background:#FFF; color:#1A1F36; border:1px solid #D1D5DB; border-radius:4px; padding:4px; font-size:9pt; }")
        self.t_content.blockSignals(False)
        self.changed.emit()

    def _on_text_changed(self):
        if self._building or not self._el: return
        self._el.text       = self.t_content.toPlainText()
        self._el.font_name  = self.t_font.currentText()
        self._el.font_size  = self.t_size.value()
        self._el.bold       = self.t_bold.isChecked()
        self._el.italic     = self.t_italic.isChecked()
        self._el.text_color = self._tcolor
        self.changed.emit()

    def _on_shape_changed(self):
        if self._building or not self._el: return
        self._el.fill_enabled  = self.s_fill_on.isChecked()
        self._el.fill_color    = self._fill
        self._el.stroke_color  = self._stroke
        self._el.stroke_width  = self.s_stroke_w.value()
        self.changed.emit()

    def _pick_text_color(self):
        c = QColorDialog.getColor(QColor(self._tcolor), self)
        if c.isValid():
            self._tcolor = c.name(); self._upd_tc(); self._on_text_changed()

    def _pick_fill(self):
        c = QColorDialog.getColor(QColor(self._fill), self)
        if c.isValid():
            self._fill = c.name(); self._upd_fill(); self._on_shape_changed()

    def _pick_stroke(self):
        c = QColorDialog.getColor(QColor(self._stroke), self)
        if c.isValid():
            self._stroke = c.name(); self._upd_stroke(); self._on_shape_changed()


# ── TemplatePage ─────────────────────────────────────────────────────
class TemplatePage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self._active_side = "front"   # "front" or "back"
        self._front_config = None
        self._back_config  = None
        self._build_ui()
        self._load_default_elements()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)

        # ── Top bar: title, front/back, zoom, save ───────────────────
        topbar = QFrame()
        topbar.setStyleSheet("background:#1A2340; border-bottom:1px solid #2A3354;")
        topbar.setFixedHeight(42)
        tbl = QHBoxLayout(topbar)
        tbl.setContentsMargins(12, 5, 12, 5)
        tbl.setSpacing(8)

        title = QLabel("Template Designer")
        title.setStyleSheet("font-size:10.5pt; font-weight:bold; color:#FFD700;")

        SIDE_BTN = """
            QPushButton { background:#253056; color:#A0ADCA; border:1px solid #3A4570;
                          border-radius:5px; font-size:9pt; font-weight:bold;
                          min-width:90px; padding:0 12px; }
            QPushButton:checked { background:#FFD700; color:#1A2340; border-color:#FFD700; }
            QPushButton:hover   { background:#304070; color:#FFF; }
        """
        for side, lbl in [("front", "◼  Front Side"), ("back", "◻  Back Side")]:
            btn = QPushButton(lbl)
            btn.setCheckable(True)
            btn.setChecked(side == "front")
            btn.setFixedHeight(30)
            btn.setStyleSheet(SIDE_BTN)
            btn.clicked.connect(lambda c, s=side: self._switch_side(s))
            setattr(self, "_{}_btn".format(side), btn)
            tbl.addWidget(btn)

        tbl.addStretch()

        # Grid toggle
        self.grid_btn = QPushButton("⊞  Grid On")
        self.grid_btn.setCheckable(True); self.grid_btn.setChecked(True)
        self.grid_btn.setFixedHeight(30); self.grid_btn.setMinimumWidth(90)
        self.grid_btn.setStyleSheet("""
            QPushButton { background:#253056; color:#A0ADCA; border:1px solid #3A4570; border-radius:5px; font-size:9pt; }
            QPushButton:checked { background:#10B981; color:#FFF; border-color:#10B981; }
        """)
        self.grid_btn.toggled.connect(lambda v: (
            setattr(self.canvas, "show_grid", v),
            self.grid_btn.setText("⊞  Grid On" if v else "⊞  Grid Off"),
            self.canvas.update()
        ))
        tbl.addWidget(self.grid_btn)

        zoom_lbl = QLabel("Zoom:")
        zoom_lbl.setStyleSheet("color:#A0ADCA; font-size:9pt;")
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(40, 250); self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(100)
        self.zoom_slider.setStyleSheet("QSlider::handle:horizontal { background:#2E5BFF; width:14px; border-radius:7px; }")
        self.zoom_slider.valueChanged.connect(lambda v: setattr(self.canvas, "zoom", v/100) or self.canvas.update())
        tbl.addWidget(zoom_lbl)
        tbl.addWidget(self.zoom_slider)

        tbl.addSpacing(12)

        save_btn = QPushButton("💾  Save & Activate")
        save_btn.setFixedHeight(32)
        save_btn.setMinimumWidth(150)
        save_btn.setStyleSheet("""
            QPushButton { background:#10B981; color:#FFF; border:none; border-radius:6px;
                          font-weight:bold; font-size:9pt; padding:0 16px; }
            QPushButton:hover { background:#059669; }
        """)
        save_btn.clicked.connect(self._save_and_activate)
        tbl.addWidget(save_btn)

        print_tmpl_btn = QPushButton("🖨  Print Template")
        print_tmpl_btn.setFixedHeight(32)
        print_tmpl_btn.setMinimumWidth(140)
        print_tmpl_btn.setToolTip("Save & send this template to the printer — prints same card for all staff (e.g. back side)")
        print_tmpl_btn.setStyleSheet("""
            QPushButton { background:#2E5BFF; color:#FFF; border:none; border-radius:6px;
                          font-weight:bold; font-size:9pt; padding:0 14px; }
            QPushButton:hover { background:#1A47E8; }
        """)
        print_tmpl_btn.clicked.connect(self._print_template_direct)
        tbl.addWidget(print_tmpl_btn)

        layout.addWidget(topbar)

        # ── Body: left tools | canvas | right properties ──────────────
        body = QHBoxLayout()
        body.setContentsMargins(0,0,0,0)
        body.setSpacing(0)

        # ── Left vertical toolbar ─────────────────────────────────────
        VBTN = """
            QPushButton {{
                background: {bg};
                color: #D0D8F0;
                border: 1px solid #2E3A5C;
                border-radius: 6px;
                font-size: 9pt;
                text-align: left;
                padding: 0 10px;
            }}
            QPushButton:checked {{ background:#2E5BFF; color:#FFF; border-color:#2E5BFF; }}
            QPushButton:hover   {{ background:#304070; color:#FFF; }}
        """
        VBTN_TOOL = VBTN.format(bg="#1E2C50")
        VBTN_ADD  = VBTN.format(bg="#16213E")

        left_toolbar = QFrame()
        left_toolbar.setStyleSheet("background:#131C38; border-right:2px solid #0F1628;")
        left_toolbar.setFixedWidth(max(140, int(self.width() * 0.12)))
        ltl = QVBoxLayout(left_toolbar)
        ltl.setContentsMargins(8, 10, 8, 10)
        ltl.setSpacing(3)

        def section_label(txt):
            lbl = QLabel(txt)
            lbl.setStyleSheet("color:#5A6A8A; font-size:7.5pt; font-weight:bold; padding:6px 2px 2px 2px; letter-spacing:1px;")
            return lbl

        def vbtn(label, tip, height=32, style=VBTN_TOOL):
            b = QPushButton(label)
            b.setToolTip(tip)
            b.setFixedHeight(height)
            b.setStyleSheet(style)
            return b

        # — TOOLS section —
        ltl.addWidget(section_label("TOOLS"))
        self.tool_btns = {}
        tools = [
            ("select",  "↖   Select",      "Select & move elements"),
            ("rect",    "▬   Rectangle",   "Draw a rectangle"),
            ("ellipse", "●   Circle",      "Draw a circle or ellipse"),
            ("line",    "╱   Line",        "Draw a straight line"),
            ("text",    "T   Text Box",    "Draw a custom text box"),
            ("draw",    "✏   Freehand",   "Freehand draw"),
            ("rotate",  "↻   Rotate",      "Rotate selected element"),
        ]
        for tool, label, tip in tools:
            btn = vbtn(label, tip, style=VBTN_TOOL)
            btn.setCheckable(True)
            btn.clicked.connect(lambda c, t=tool: self._set_tool(t))
            self.tool_btns[tool] = btn
            ltl.addWidget(btn)
        self.tool_btns["select"].setChecked(True)

        # — ADD ELEMENTS section —
        ltl.addWidget(section_label("ADD ELEMENT"))
        add_items = [
            ("📷   Photo",        self._add_photo_el,   "Add staff photo placeholder"),
            ("👤   Name",         self._add_name_el,    "Add name text (Montserrat 9pt, bound to name)"),
            ("🪪   Staff ID",     self._add_staffid_el, "Add Staff ID text (Montserrat 9pt, bound to staff_id)"),
            ("📱   QR Code",      self._add_qr_el,      "Add QR code placeholder"),
            ("🖼   Image/Logo",   self._add_image_el,   "Import an image or logo"),
            ("🎨   Background",   self._set_bg,         "Set card background colour or image"),
        ]
        for label, slot, tip in add_items:
            btn = vbtn(label, tip, style=VBTN_ADD)
            btn.clicked.connect(slot)
            ltl.addWidget(btn)

        # — ARRANGE section —
        ltl.addWidget(section_label("ARRANGE"))
        for label, slot, tip in [
            ("⬡   Group",        self.canvas_group,    "Group selected elements  (Ctrl+G)"),
            ("⬡   Ungroup",      self.canvas_ungroup,  "Ungroup elements  (Ctrl+U)"),
            ("▲   Bring Up",     self._layer_up,       "Move element up one layer"),
            ("▼   Send Down",    self._layer_down,     "Move element down one layer"),
        ]:
            btn = vbtn(label, tip, style=VBTN_TOOL)
            btn.clicked.connect(slot)
            ltl.addWidget(btn)

        # — DELETE —
        ltl.addSpacing(4)
        del_btn = vbtn("🗑   Delete", "Delete selected element  (Del)", style=VBTN_TOOL)
        del_btn.setStyleSheet(del_btn.styleSheet().replace("#1E2C50","#3D1515").replace("#304070","#5C1A1A"))
        del_btn.clicked.connect(self._delete_el)
        ltl.addWidget(del_btn)

        # — TEMPLATES section —
        ltl.addSpacing(4)
        ltl.addWidget(section_label("TEMPLATES"))
        load_tmpl_btn = vbtn("Load Template", "Load selected template onto the canvas", style=VBTN_TOOL)
        load_tmpl_btn.clicked.connect(self._load_selected_template)
        ltl.addWidget(load_tmpl_btn)
        del_tmpl_btn = vbtn("Delete Template", "Delete selected template from database", style=VBTN_TOOL)
        del_tmpl_btn.setStyleSheet(del_tmpl_btn.styleSheet().replace("#1E2C50","#3D1515").replace("#304070","#5C1A1A"))
        del_tmpl_btn.clicked.connect(self._delete_template)
        ltl.addWidget(del_tmpl_btn)

        ltl.addStretch()

        body.addWidget(left_toolbar)

        # ── Centre split: panels left + canvas ───────────────────────
        centre_split = QSplitter(Qt.Horizontal)

        # Panel: saved templates + staff preview + elements list
        panel = QFrame()
        panel.setStyleSheet("background:#FAFAFA; border-right:1px solid #E5E7EB;")
        panel.setFixedWidth(max(200, int(self.width() * 0.17)))
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(6,10,6,10)
        pl.setSpacing(6)

        tl_lbl = QLabel("Saved Templates")
        tl_lbl.setStyleSheet("font-size:9pt; font-weight:bold; color:#1A1F36;")
        pl.addWidget(tl_lbl)

        self.template_list = QListWidget()
        self.template_list.setStyleSheet("""
            QListWidget { border:1px solid #E5E7EB; border-radius:6px; font-size:8.5pt; background:#FFF; }
            QListWidget::item { padding:6px 8px; color:#1A1F36; }
            QListWidget::item:selected { background:#EEF2FF; color:#1A1F36; }
        """)
        self.template_list.currentItemChanged.connect(self._on_template_selected)
        pl.addWidget(self.template_list, stretch=2)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background:#E5E7EB; max-height:1px;")
        pl.addWidget(sep)

        sl_lbl = QLabel("Preview Staff")
        sl_lbl.setStyleSheet("font-size:9pt; font-weight:bold; color:#1A1F36;")
        pl.addWidget(sl_lbl)

        self.staff_combo = QComboBox()
        self.staff_combo.setStyleSheet("""
            QComboBox { background:#FFF; color:#1A1F36; border:1px solid #D1D5DB; border-radius:5px; padding:4px 8px; }
            QComboBox QAbstractItemView { background:#FFF; color:#1A1F36; selection-background-color:#EEF2FF; }
        """)
        self.staff_combo.currentIndexChanged.connect(self._on_staff_changed)
        pl.addWidget(self.staff_combo)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("background:#E5E7EB; max-height:1px;")
        pl.addWidget(sep2)

        el_lbl = QLabel("Elements")
        el_lbl.setStyleSheet("font-size:9pt; font-weight:bold; color:#1A1F36;")
        pl.addWidget(el_lbl)

        self.elem_list = QListWidget()
        self.elem_list.setStyleSheet("""
            QListWidget { border:1px solid #E5E7EB; border-radius:6px; font-size:8pt; background:#FFF; }
            QListWidget::item { padding:4px 6px; color:#1A1F36; }
            QListWidget::item:selected { background:#EEF2FF; color:#1A1F36; }
        """)
        self.elem_list.currentRowChanged.connect(self._on_elem_list_clicked)
        pl.addWidget(self.elem_list, stretch=1)

        centre_split.addWidget(panel)

        # Canvas
        self.canvas = CardCanvas()
        self.canvas.selection_changed.connect(self._on_selection_changed)
        self.canvas.canvas_changed.connect(self._on_canvas_changed)
        centre_split.addWidget(self.canvas)

        # Right properties panel
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setMinimumWidth(260)
        right_scroll.setMaximumWidth(300)
        right_scroll.setStyleSheet("border:none; background:#F9FAFB;")
        self.props = PropertiesPanel()
        self.props.setMinimumWidth(250)
        self.props.changed.connect(self.canvas.update)
        self.props.changed.connect(self.canvas.canvas_changed.emit)
        self.props._up_btn.clicked.connect(self._layer_up)
        self.props._dn_btn.clicked.connect(self._layer_down)
        right_scroll.setWidget(self.props)
        centre_split.addWidget(right_scroll)

        total = max(1000, self.width())
        centre_split.setSizes([int(total*0.17), int(total*0.55), int(total*0.28)])
        centre_split.setCollapsible(2, False)
        body.addWidget(centre_split)
        layout.addLayout(body, stretch=1)

        # Status bar
        self.status_bar = QLabel("  Front Side  ·  54 × 84.5 mm  ·  Select a tool to begin  ·  Scroll to zoom")
        self.status_bar.setStyleSheet("background:#1A2340; color:#7B88A8; font-size:8pt; padding:4px 12px;")
        self.status_bar.setFixedHeight(22)
        layout.addWidget(self.status_bar)

    # ── canvas proxy methods (needed before canvas exists) ────────────
    def canvas_group(self):
        self.canvas.group_selected()
        self._refresh_elem_list()

    def canvas_ungroup(self):
        self.canvas.ungroup_selected()
        self._refresh_elem_list()

    # ── default layout ────────────────────────────────────────────────
    def _load_default_elements(self):
        """Start with a completely plain canvas — no background colour.
        The physical card IS the background."""
        self.canvas.elements = []
        self.canvas.bg_color  = "#FFFFFF"
        self.canvas.bg_pixmap = None
        self.canvas.update()
        self._refresh_elem_list()

    def _load_default_back(self):
        """Plain back canvas too."""
        self.canvas.elements = []
        self.canvas.bg_color  = "#FFFFFF"
        self.canvas.bg_pixmap = None
        self.canvas.update()
        self._refresh_elem_list()

    # ── side switching ────────────────────────────────────────────────
    def _switch_side(self, side):
        if side == self._active_side:
            return
        # Save current side config
        if self._active_side == "front":
            self._front_config = self.canvas.get_config()
        else:
            self._back_config = self.canvas.get_config()

        self._active_side = side
        self._front_btn.setChecked(side == "front")
        self._back_btn.setChecked(side == "back")

        # Load the other side
        if side == "front":
            if self._front_config:
                self.canvas.load_config(self._front_config)
            else:
                self._load_default_elements()
        else:
            if self._back_config:
                self.canvas.load_config(self._back_config)
            else:
                self._load_default_back()

        self._refresh_elem_list()
        self.status_bar.setText("  {} Side  ·  54 × 84.5 mm  ·  Editing template".format(
            "Front" if side=="front" else "Back"
        ))

    # ── toolbar slots ─────────────────────────────────────────────────
    def _set_tool(self, tool):
        for t, btn in self.tool_btns.items():
            btn.setChecked(t == tool)
        self.canvas.set_tool(tool)
        self.status_bar.setText("  Tool: {}  ·  {} Side".format(
            tool.capitalize(), self._active_side.capitalize()
        ))

    def _add_photo_el(self):
        el = CanvasElement(ELEM_PHOTO, 2, 2, CARD_W_MM-4, 46, label="Photo", key="photo_path")
        self.canvas.add_element(el); self._refresh_elem_list()

    def _add_qr_el(self):
        qr_x = (CARD_W_MM - 15.5) / 2
        el = CanvasElement(ELEM_QR, qr_x, CARD_H_MM-18, 15.5, 15.5, label="QR Code", key="qr")
        self.canvas.add_element(el); self._refresh_elem_list()

    def _add_name_el(self):
        el = CanvasElement(
            ELEM_TEXT, 2, 55, CARD_W_MM-4, 8,
            key="name", label="Full Name",
            text="Full Name",
            font_name="Montserrat", font_size=9,
            bold=False, italic=False, text_color="#1A1A1A"
        )
        self.canvas.add_element(el)
        self._refresh_elem_list()

    def _add_staffid_el(self):
        el = CanvasElement(
            ELEM_TEXT, 2, 65, CARD_W_MM-4, 8,
            key="staff_id", label="Staff ID",
            text="Staff ID",
            font_name="Montserrat", font_size=9,
            bold=False, italic=False, text_color="#1A1A1A"
        )
        self.canvas.add_element(el)
        self._refresh_elem_list()

    def _add_image_el(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.tif)"
        )
        if path:
            el = CanvasElement(ELEM_IMAGE, 5, 5, 20, 20, image_path=path, label="Image")
            self.canvas.add_element(el); self._refresh_elem_list()

    def _set_bg(self):
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QDialogButtonBox
        dlg = QDialog(self)
        dlg.setWindowTitle("Set Background")
        dlg.setFixedWidth(300)
        dlg.setStyleSheet("background:#FFF;")
        vl = QVBoxLayout(dlg)
        vl.setSpacing(8); vl.setContentsMargins(16,16,16,16)

        lbl = QLabel("Choose background type:")
        lbl.setStyleSheet("font-size:9.5pt; color:#1A1F36; font-weight:bold;")
        vl.addWidget(lbl)

        BTN = "QPushButton { background:#F0F4FF; color:#1A1F36; border:1px solid #D1D5DB; border-radius:6px; padding:10px; font-size:9pt; text-align:left; } QPushButton:hover { background:#EEF2FF; }"

        img_btn   = QPushButton("🖼   Image file  (import a photo or graphic)")
        color_btn = QPushButton("🎨   Solid colour  (pick a colour)")
        clear_btn = QPushButton("⬜   Transparent / Plain  (no background)")
        for b in [img_btn, color_btn, clear_btn]:
            b.setStyleSheet(BTN); b.setFixedHeight(44)
            vl.addWidget(b)

        result = {"choice": None}

        def pick_img():
            result["choice"] = "img"; dlg.accept()
        def pick_color():
            result["choice"] = "color"; dlg.accept()
        def pick_clear():
            result["choice"] = "clear"; dlg.accept()

        img_btn.clicked.connect(pick_img)
        color_btn.clicked.connect(pick_color)
        clear_btn.clicked.connect(pick_clear)

        cancel = QPushButton("Cancel")
        cancel.setStyleSheet("QPushButton { background:#F3F4F6; color:#374151; border:1px solid #D1D5DB; border-radius:6px; padding:6px; } QPushButton:hover { background:#E5E7EB; }")
        cancel.clicked.connect(dlg.reject)
        vl.addWidget(cancel)

        dlg.exec_()
        choice = result["choice"]

        if choice == "img":
            path, _ = QFileDialog.getOpenFileName(
                self, "Background Image", "",
                "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.tif)"
            )
            if path:
                pix = QPixmap(path)
                if not pix.isNull():
                    self.canvas.set_background(pix)
                    self.canvas._bg_image_path = path

        elif choice == "color":
            color = QColorDialog.getColor(QColor(self.canvas.bg_color), self)
            if color.isValid():
                self.canvas.set_bg_color(color.name())

        elif choice == "clear":
            self.canvas.bg_pixmap = None
            self.canvas._bg_image_path = ""
            self.canvas.bg_color = "#FFFFFF"
            self.canvas.update()

    def _delete_el(self):
        self.canvas.delete_selected()
        self._refresh_elem_list()

    def _layer_up(self):
        self.canvas.move_up(); self._refresh_elem_list()

    def _layer_down(self):
        self.canvas.move_down(); self._refresh_elem_list()

    # ── element list ──────────────────────────────────────────────────
    def _refresh_elem_list(self):
        self.elem_list.blockSignals(True)
        self.elem_list.clear()
        icons = {
            ELEM_TEXT:"T ", ELEM_PHOTO:"📷", ELEM_QR:"📱",
            ELEM_RECT:"▬ ", ELEM_ELLIPSE:"● ", ELEM_IMAGE:"🖼",
            ELEM_LINE:"╱ ",
        }
        for el in reversed(self.canvas.elements):
            gmark = " [G]" if el.group_id else ""
            lbl = "{}  {}{}".format(icons.get(el.type,"?"), el.label or el.type, gmark)
            item = QListWidgetItem(lbl)
            item.setData(Qt.UserRole, el.id)
            self.elem_list.addItem(item)
        self.elem_list.blockSignals(False)

    def _on_elem_list_clicked(self, row):
        if row < 0: return
        item = self.elem_list.item(row)
        if not item: return
        eid = item.data(Qt.UserRole)
        for el in self.canvas.elements:
            if el.id == eid:
                self.canvas.selected = [el]
                self.canvas.selection_changed.emit(el)
                self.canvas.update()
                break

    # ── selection ─────────────────────────────────────────────────────
    def _on_selection_changed(self, el):
        self.props.load(el)
        if el:
            self.status_bar.setText(
                "  Selected: {}  ·  X:{:.1f}  Y:{:.1f}  W:{:.1f}  H:{:.1f} mm  ·  Rotate: {:.0f}°".format(
                    el.label or el.type, el.x, el.y, el.w, el.h, el.rotation
                ))
        else:
            self.status_bar.setText(
                "  {} Side  ·  54 × 84.5 mm  ·  Click element to select".format(
                    self._active_side.capitalize()
                ))

    def _on_canvas_changed(self):
        self.canvas.update()
        # Sync props if element is selected
        el = self.canvas._primary()
        if el:
            self.props.load(el)

    # ── template list ─────────────────────────────────────────────────
    def _refresh_template_list(self):
        self.template_list.clear()
        for t in self.main.db.get_all_templates():
            side = t.get("side","front")
            icon = "🎨" if side=="front" else "🔲"
            item = QListWidgetItem("{}  {}  [{}]".format(icon, t["name"], side))
            item.setData(Qt.UserRole, t)
            self.template_list.addItem(item)

    def _on_template_selected(self, current, previous):
        pass   # Only load on explicit "Load" click

    def _load_selected_template(self):
        item = self.template_list.currentItem()
        if not item:
            QMessageBox.information(self, "No Selection",
                "Please click a template from the list first, then click Load.")
            return
        tmpl = item.data(Qt.UserRole)
        try:
            # Parse config — may be pre-parsed or raw JSON string
            if isinstance(tmpl.get("config"), dict):
                config = tmpl["config"]
            else:
                config = json.loads(tmpl.get("config_json", "{}"))

            # Switch to the side this template was designed for
            side = config.get("side", tmpl.get("side", "front"))
            if side != self._active_side:
                self._switch_side(side)

            # Load canvas — even if no elements (bg colour/image still loads)
            self.canvas.load_config(config)
            self._refresh_elem_list()

            self.main.set_status("✅  Loaded template: «{}»  ({} side)".format(tmpl["name"], side))
            QMessageBox.information(self, "Template Loaded",
                "✅  «{}» loaded onto the {} canvas.\n\nEdit as needed, then Save & Activate.".format(
                    tmpl["name"], side))
        except Exception as e:
            QMessageBox.warning(self, "Load Error",
                "Could not load template «{}»:\n{}".format(tmpl.get("name",""), str(e)))

    def _delete_template(self):
        item = self.template_list.currentItem()
        if not item:
            QMessageBox.information(self, "No Selection",
                "Please click a template from the list first, then click Delete.")
            return
        tmpl = item.data(Qt.UserRole)
        name = tmpl["name"]

        reply = QMessageBox.question(
            self, "Delete Template",
            "Delete template «{}»?\n\nThis cannot be undone.".format(name),
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        ok, msg = self.main.db.delete_template(name)
        if ok:
            # If this was the active template, clear it
            active = getattr(self.main, "active_template", None)
            if active and active.get("name") == name:
                self.main.set_active_template("", "", {})
                self.canvas.load_config({})
                self._refresh_elem_list()

            self._refresh_template_list()
            self.main.set_status("🗑  Deleted template: «{}»".format(name))
        else:
            QMessageBox.warning(self, "Delete Error", msg)

    def _save_and_activate(self):
        # Ask for name
        default = "Front Template" if self._active_side=="front" else "Back Template"
        item = self.template_list.currentItem()
        if item:
            default = item.data(Qt.UserRole)["name"]

        name, ok = QInputDialog.getText(self, "Save Template", "Template name:", text=default)
        if not ok or not name.strip():
            return
        name = name.strip()

        config = self.canvas.get_config()
        config["side"] = self._active_side

        # Save to DB
        ok2, msg = self.main.db.save_template(name, "", config)
        if not ok2:
            QMessageBox.warning(self, "Error", msg)
            return

        self._refresh_template_list()

        # If front side, set as active template immediately (syncs to preview + print)
        if self._active_side == "front":
            self.main.set_active_template(name, "", config)
            self.main.set_status("✅  Front template '{}' saved & activated — preview and print are now synced.".format(name))
            QMessageBox.information(
                self, "Template Saved",
                "✅  '{}' saved and set as the active template.\n\n"
                "Go to Preview to see your staff cards rendered with this template.\n"
                "Print will use this template automatically.".format(name)
            )
        else:
            # Store back config in settings for use when printing back side
            self.main.db.settings["back_template"] = name
            self.main.db.save_settings()
            self.main.set_status("✅  Back template '{}' saved.".format(name))
            QMessageBox.information(
                self, "Back Template Saved",
                "✅  Back template '{}' saved.\n\n"
                "This will be used for the reverse side of ID cards.".format(name)
            )

    # ── print template directly ───────────────────────────────────────
    def _print_template_direct(self):
        """Save & activate current template, load ALL staff into print queue,
        then navigate straight to the Print page — ideal for back-side cards."""
        # First save & activate silently (no dialog)
        side = self._active_side
        default_name = "Front Template" if side == "front" else "Back Template"
        item = self.template_list.currentItem()
        if item:
            name = item.data(Qt.UserRole)["name"]
        else:
            name = default_name

        config = self.canvas.get_config()
        config["side"] = side

        ok2, msg = self.main.db.save_template(name, "", config)
        if not ok2:
            QMessageBox.warning(self, "Save Error", msg)
            return

        self.main.set_active_template(name, "", config)
        self._refresh_template_list()

        # Switch print page to template-only mode with THIS specific template's config
        self.main.pages[5].set_template_only_mode(config=config, template_name=name)
        self.main.navigate_to(5)
        self.main.set_status("🖨  «{}» ({} side) ready — click Print Now to print.".format(name, side))

    # ── staff preview ─────────────────────────────────────────────────
    def _refresh_staff_list(self):
        self.staff_combo.clear()
        self.staff_combo.addItem("— No preview staff —", None)
        for s in self.main.db.get_all_staff():
            self.staff_combo.addItem("👤  {}".format(s.get("name","")), s)

    def _on_staff_changed(self, idx):
        staff = self.staff_combo.currentData()
        self.canvas.set_staff(staff or {})

    # ── lifecycle ─────────────────────────────────────────────────────
    def on_activate(self):
        self._refresh_template_list()
        self._refresh_staff_list()
        tmpl = self.main.active_template
        if tmpl:
            self.main.set_status("Active template: {}".format(tmpl.get("name","")))