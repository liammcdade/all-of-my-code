#!/usr/bin/env python3
"""
CV Studio — a dashboard that builds CVs in 25 different styles and exports PDFs.

Install dependency:
    pip install reportlab

Run:
    python cv_studio.py
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from dataclasses import dataclass, field

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import simpleSplit


# =============================================================================
#  DATA MODEL
# =============================================================================

@dataclass
class CVData:
    name: str = ""
    title: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    website: str = ""
    summary: str = ""
    skills: list = field(default_factory=list)
    languages: list = field(default_factory=list)
    certifications: list = field(default_factory=list)
    experience: list = field(default_factory=list)   # {role, company, dates, description}
    education: list = field(default_factory=list)    # {degree, level, school, year, details}


# =============================================================================
#  FONTS + 25 STYLE DEFINITIONS
# =============================================================================

FONT_SETS = {
    "sans":  {"regular": "Helvetica", "bold": "Helvetica-Bold",
              "italic": "Helvetica-Oblique", "bolditalic": "Helvetica-BoldOblique"},
    "serif": {"regular": "Times-Roman", "bold": "Times-Bold",
              "italic": "Times-Italic", "bolditalic": "Times-BoldItalic"},
}


def S(name, layout, font, accent, heading="rule", sidebar=None,
      sidebar_text="#FFFFFF", sidebar_muted="#C9D3E0",
      text="#222222", muted="#5A6675"):
    return dict(name=name, layout=layout, font=font, accent=accent,
                heading=heading,
                sidebar=sidebar or accent,
                sidebar_text=sidebar_text, sidebar_muted=sidebar_muted,
                text=text, muted=muted)


STYLES = [
    S("Classic Navy",      "classic",      "sans",  "#1F3A5F", "rule"),
    S("Classic Burgundy",  "classic",      "serif", "#7B1E28", "rule"),
    S("Classic Forest",    "classic",      "serif", "#1E4620", "rule"),
    S("Classic Cyan",      "classic",      "sans",  "#00707F", "rule"),

    S("Minimal Black",     "minimal",      "sans",  "#111111", "plain"),
    S("Minimal Stone",     "minimal",      "serif", "#4E4E4E", "plain"),
    S("Minimal Gold",      "minimal",      "serif", "#8A6D1F", "plain"),

    S("Azure Sidebar",     "sidebar_left", "sans",  "#1565C0", "rule", "#1565C0"),
    S("Charcoal Sidebar",  "sidebar_left", "sans",  "#2E3440", "rule", "#2E3440"),
    S("Emerald Sidebar",   "sidebar_left", "serif", "#0B6E4F", "rule", "#0B6E4F"),
    S("Graphite Sidebar",  "sidebar_left", "serif", "#212121", "rule", "#212121"),

    S("Plum Sidebar",      "sidebar_right","sans",  "#5E2B6B", "rule", "#5E2B6B"),
    S("Slate Sidebar",     "sidebar_right","sans",  "#37474F", "rule", "#37474F"),
    S("Crimson Sidebar",   "sidebar_right","serif", "#A31E2A", "rule", "#A31E2A"),

    S("Ocean Header",      "header_band",  "sans",  "#0277BD", "leftbar"),
    S("Amber Header",      "header_band",  "sans",  "#D35400", "leftbar"),
    S("Teal Header",       "header_band",  "serif", "#00695C", "leftbar"),
    S("Indigo Header",     "header_band",  "sans",  "#283593", "leftbar"),
    S("Midnight Header",   "header_band",  "serif", "#1A237E", "leftbar"),

    S("Timeline Blue",     "timeline",     "sans",  "#1565C0", "leftbar"),
    S("Timeline Olive",    "timeline",     "serif", "#5B7F2A", "leftbar"),
    S("Timeline Rose",     "timeline",     "sans",  "#AD1457", "leftbar"),

    S("Blocks Indigo",     "blocks",       "sans",  "#303F9F", "bar"),
    S("Blocks Coral",      "blocks",       "sans",  "#C0392B", "bar"),
    S("Blocks Sage",       "blocks",       "serif", "#4E7A5A", "bar"),
]

assert len(STYLES) == 25


# =============================================================================
#  PDF DRAWING HELPERS
# =============================================================================

class Flow:
    """A vertical writing cursor inside a rectangular column."""

    def __init__(self, cv, x, w, top, bottom, newpage=None, accent="#000000"):
        self.cv = cv
        self.c = cv.c
        self.x = x
        self.w = w
        self.top = top
        self.bottom = bottom
        self.y = top
        self.newpage = newpage
        self.accent = accent

    def need(self, h):
        if self.y - h < self.bottom and self.newpage:
            self.newpage(self)


def f_text(flow, text, font, size, color, leading=None, align="left",
           indent=0, gap=0):
    """Draw a wrapped paragraph (supports \n). Returns the new y."""
    if not text:
        return flow.y
    lead = leading or size * 1.38
    x = flow.x + indent
    w = flow.w - indent
    c = flow.c
    for para in str(text).split("\n"):
        lines = simpleSplit(para, font, size, w) or [""]
        for ln in lines:
            flow.need(lead)
            c.setFont(font, size)
            c.setFillColor(HexColor(color))
            if align == "center":
                c.drawCentredString(x + w / 2, flow.y, ln)
            elif align == "right":
                c.drawRightString(x + w, flow.y, ln)
            else:
                c.drawString(x, flow.y, ln)
            flow.y -= lead
    flow.y -= gap
    return flow.y


def f_bullets(flow, items, color, size=9.5, leading=None, bullet="•"):
    lead = leading or size * 1.4
    c = flow.c
    font = flow.cv.f["regular"]
    for it in items:
        it = str(it).strip()
        if not it:
            continue
        lines = simpleSplit(it, font, size, flow.w - 13) or [""]
        first = True
        for ln in lines:
            flow.need(lead)
            if first:
                c.setFont(font, size)
                c.setFillColor(HexColor(flow.accent))
                c.drawString(flow.x, flow.y, bullet)
                first = False
            c.setFont(font, size)
            c.setFillColor(HexColor(color))
            c.drawString(flow.x + 13, flow.y, ln)
            flow.y -= lead
        flow.y -= 1.5


def f_heading(flow, title, kind="rule", size=10.5, gap_before=16, gap_after=8):
    cv, c = flow.cv, flow.c
    bold = cv.f["bold"]
    accent = flow.accent
    flow.y -= gap_before
    flow.need(size + 18)
    t = title.upper()

    if kind == "bar":
        c.setFillColor(HexColor(accent))
        c.rect(flow.x, flow.y - 5, flow.w, 18, stroke=0, fill=1)
        c.setFillColor(HexColor("#FFFFFF"))
        c.setFont(bold, size)
        c.drawString(flow.x + 8, flow.y, t)
        flow.y -= 23
    elif kind == "leftbar":
        c.setFillColor(HexColor(accent))
        c.rect(flow.x, flow.y - 4, 3.2, 14, stroke=0, fill=1)
        c.setFillColor(HexColor(accent))
        c.setFont(bold, size)
        c.drawString(flow.x + 11, flow.y, t)
        flow.y -= gap_after + 9
    elif kind == "rule":
        c.setFillColor(HexColor(accent))
        c.setFont(bold, size)
        c.drawString(flow.x, flow.y, t)
        flow.y -= 5
        c.setStrokeColor(HexColor(accent))
        c.setLineWidth(0.9)
        c.line(flow.x, flow.y, flow.x + flow.w, flow.y)
        flow.y -= gap_after + 5
    else:  # plain
        c.setFillColor(HexColor(accent))
        c.setFont(bold, size)
        c.drawString(flow.x, flow.y, t)
        flow.y -= gap_after + 7


def contact_parts(d):
    return [p for p in (d.email, d.phone, d.location, d.website) if p]


def job_description(job):
    raw = job.get("description", "")
    out = []
    for line in str(raw).split("\n"):
        line = line.strip().lstrip("-•* ").strip()
        if line:
            out.append(line)
    return out


# =============================================================================
#  PDF BUILDER
# =============================================================================

class CVPdf:
    def __init__(self, path, data: CVData, style: dict):
        self.c = canvas.Canvas(path, pagesize=A4)
        self.W, self.H = A4
        self.c.setTitle("CV - %s" % (data.name or "Untitled"))
        self.c.setAuthor(data.name or "")
        self.data = data
        self.st = style
        self.f = FONT_SETS[style["font"]]

    # -- public ------------------------------------------------------------
    def build(self):
        layout = self.st["layout"]
        if layout == "classic":
            self._classic()
        elif layout == "minimal":
            self._minimal()
        elif layout == "blocks":
            self._blocks()
        elif layout == "timeline":
            self._timeline()
        elif layout == "sidebar_left":
            self._sidebar("left")
        elif layout == "sidebar_right":
            self._sidebar("right")
        elif layout == "header_band":
            self._header_band()
        else:
            self._classic()
        self.c.save()

    # -- shared blocks -----------------------------------------------------
    def _exp_block(self, flow, size=9.6, bold_dates=True, show_company=True):
        st = self.st
        for job in self.data.experience:
            role = job.get("role", "").strip()
            comp = job.get("company", "").strip()
            dates = job.get("dates", "").strip()
            if not (role or comp):
                continue
            flow.y -= 4
            flow.need(34)
            c = self.c
            c.setFillColor(HexColor(st["text"]))
            c.setFont(self.f["bold"], size + 1.2)
            c.drawString(flow.x, flow.y, role or comp)
            if dates:
                c.setFont(self.f["regular"], size - 0.4)
                c.setFillColor(HexColor(st["muted"]))
                c.drawRightString(flow.x + flow.w, flow.y, dates)
            flow.y -= size * 1.45
            if show_company and role and comp:
                c.setFont(self.f["italic"], size - 0.2)
                c.setFillColor(HexColor(st["accent"]))
                c.drawString(flow.x, flow.y, comp)
                flow.y -= size * 1.4
            desc = job_description(job)
            if desc:
                f_bullets(flow, desc, st["text"], size=size - 0.4)
            flow.y -= 6

    def _edu_block(self, flow, size=9.6):
        st = self.st
        for ed in self.data.education:
            deg = ed.get("Subject", "").strip()
            lvl = ed.get("level", "").strip()
            sch = ed.get("school", "").strip()
            yr = ed.get("year", "").strip()
            det = ed.get("details", "").strip()
            if not (deg or sch):
                continue
            flow.y -= 4
            flow.need(30)
            c = self.c
            c.setFillColor(HexColor(st["text"]))
            c.setFont(self.f["bold"], size + 0.8)
            label = deg
            if lvl:
                label = "%s (%s)" % (deg, lvl) if deg else lvl
            c.drawString(flow.x, flow.y, label or sch)
            if yr:
                c.setFont(self.f["regular"], size - 0.4)
                c.setFillColor(HexColor(st["muted"]))
                c.drawRightString(flow.x + flow.w, flow.y, yr)
            flow.y -= size * 1.45
            if deg and sch:
                c.setFont(self.f["italic"], size - 0.2)
                c.setFillColor(HexColor(st["accent"]))
                c.drawString(flow.x, flow.y, sch)
                flow.y -= size * 1.4
            if det:
                f_text(flow, det, self.f["regular"], size - 0.4, st["muted"],
                       leading=(size - 0.4) * 1.35)
            flow.y -= 6

    def _plain_list(self, flow, items, size=9.6, columns=1):
        st = self.st
        if columns > 1:
            half = (len(items) + 1) // 2
            col_w = (flow.w - 14) / 2
            start_y = flow.y
            for i, chunk in enumerate((items[:half], items[half:])):
                f = Flow(self, flow.x + i * (col_w + 14), col_w,
                         start_y, flow.bottom, flow.newpage, st["accent"])
                f_bullets(f, chunk, st["text"], size=size - 0.4)
                flow.y = min(flow.y, f.y)
        else:
            f_bullets(flow, items, st["text"], size=size - 0.4)

    # =====================================================================
    #  LAYOUT: CLASSIC  (centered header + ruled sections)
    # =====================================================================
    def _classic(self):
        st, c, d = self.st, self.c, self.data
        W, H = self.W, self.H
        m = 56

        y = H - 62
        c.setFillColor(HexColor(st["accent"]))
        c.setFont(self.f["bold"], 25)
        c.drawCentredString(W / 2, y, (d.name or "Your Name").upper())
        y -= 20
        if d.title:
            c.setFillColor(HexColor(st["muted"]))
            c.setFont(self.f["regular"], 12)
            c.drawCentredString(W / 2, y, d.title)
            y -= 16
        parts = contact_parts(d)
        if parts:
            c.setFillColor(HexColor("#6B7280"))
            c.setFont(self.f["regular"], 8.8)
            c.drawCentredString(W / 2, y, "   •   ".join(parts))
            y -= 13
        y -= 6
        c.setStrokeColor(HexColor(st["accent"]))
        c.setLineWidth(1.6)
        c.line(m, y, W - m, y)
        y -= 20

        def newpage(flow):
            c.showPage()
            flow.y = H - 60

        flow = Flow(self, m, W - 2 * m, y, 50, newpage, st["accent"])

        if d.summary:
            f_heading(flow, "Profile", st["heading"], gap_before=0)
            f_text(flow, d.summary, self.f["regular"], 9.7, st["text"])
        if d.experience:
            f_heading(flow, "Experience", st["heading"])
            self._exp_block(flow)
        if d.education:
            f_heading(flow, "Education", st["heading"])
            self._edu_block(flow)
        if d.skills:
            f_heading(flow, "Skills", st["heading"])
            self._plain_list(flow, d.skills, columns=2)
        if d.languages:
            f_heading(flow, "Languages", st["heading"])
            f_text(flow, "   •   ".join(d.languages), self.f["regular"],
                   9.6, st["text"])
        if d.certifications:
            f_heading(flow, "Certifications", st["heading"])
            f_bullets(flow, d.certifications, st["text"], size=9.3)

    # =====================================================================
    #  LAYOUT: MINIMAL  (airy, left aligned, thin rules)
    # =====================================================================
    def _minimal(self):
        st, c, d = self.st, self.c, self.data
        W, H = self.W, self.H
        m = 62

        y = H - 72
        c.setFillColor(HexColor(st["text"]))
        c.setFont(self.f["bold"], 22)
        c.drawString(m, y, d.name or "Your Name")
        y -= 18
        if d.title:
            c.setFillColor(HexColor(st["muted"]))
            c.setFont(self.f["regular"], 10.5)
            c.drawString(m, y, d.title)
            y -= 14
        parts = contact_parts(d)
        if parts:
            c.setFillColor(HexColor("#8A8F98"))
            c.setFont(self.f["regular"], 8.6)
            c.drawString(m, y, "  /  ".join(parts))
            y -= 10
        y -= 8
        c.setStrokeColor(HexColor("#DADDE2"))
        c.setLineWidth(0.7)
        c.line(m, y, W - m, y)
        y -= 18

        def newpage(flow):
            c.showPage()
            flow.y = H - 60

        flow = Flow(self, m, W - 2 * m, y, 52, newpage, st["accent"])

        if d.summary:
            f_heading(flow, "About", "plain", gap_before=0, gap_after=4)
            f_text(flow, d.summary, self.f["regular"], 9.8, st["text"])
        if d.experience:
            f_heading(flow, "Experience", "plain", gap_after=4)
            self._exp_block(flow)
        if d.education:
            f_heading(flow, "Education", "plain", gap_after=4)
            self._edu_block(flow)
        if d.skills:
            f_heading(flow, "Skills", "plain", gap_after=4)
            f_text(flow, "   ·   ".join(d.skills), self.f["regular"],
                   9.6, st["text"])
        if d.languages:
            f_heading(flow, "Languages", "plain", gap_after=4)
            f_text(flow, "   ·   ".join(d.languages), self.f["regular"],
                   9.6, st["text"])
        if d.certifications:
            f_heading(flow, "Certifications", "plain", gap_after=4)
            f_bullets(flow, d.certifications, st["text"], size=9.3,
                      bullet="–")

    # =====================================================================
    #  LAYOUT: BLOCKS  (filled section bars)
    # =====================================================================
    def _blocks(self):
        st, c, d = self.st, self.c, self.data
        W, H = self.W, self.H
        m = 50

        c.setFillColor(HexColor(st["accent"]))
        c.rect(0, H - 96, W, 96, stroke=0, fill=1)
        c.setFillColor(HexColor("#FFFFFF"))
        c.setFont(self.f["bold"], 24)
        c.drawString(m, H - 52, d.name or "Your Name")
        if d.title:
            c.setFont(self.f["regular"], 11)
            c.setFillColor(HexColor("#EAF0FF"))
            c.drawString(m, H - 70, d.title)
        parts = contact_parts(d)
        if parts:
            c.setFont(self.f["regular"], 8.6)
            c.setFillColor(HexColor("#EAF0FF"))
            c.drawRightString(W - m, H - 40, parts[0])
            if len(parts) > 1:
                c.drawRightString(W - m, H - 54, "  |  ".join(parts[1:]))

        def newpage(flow):
            c.showPage()
            c.setFillColor(HexColor(st["accent"]))
            c.rect(0, H - 14, W, 14, stroke=0, fill=1)
            flow.y = H - 50

        flow = Flow(self, m, W - 2 * m, H - 126, 50, newpage, st["accent"])

        if d.summary:
            f_heading(flow, "Profile", "bar", gap_before=0)
            f_text(flow, d.summary, self.f["regular"], 9.7, st["text"])
        if d.experience:
            f_heading(flow, "Experience", "bar")
            self._exp_block(flow)
        if d.education:
            f_heading(flow, "Education", "bar")
            self._edu_block(flow)
        if d.skills:
            f_heading(flow, "Skills", "bar")
            self._plain_list(flow, d.skills, columns=2)
        if d.languages:
            f_heading(flow, "Languages", "bar")
            f_text(flow, "   •   ".join(d.languages), self.f["regular"],
                   9.6, st["text"])
        if d.certifications:
            f_heading(flow, "Certifications", "bar")
            f_bullets(flow, d.certifications, st["text"], size=9.3)

    # =====================================================================
    #  LAYOUT: TIMELINE  (vertical rail with dots)
    # =====================================================================
    def _timeline(self):
        st, c, d = self.st, self.c, self.data
        W, H = self.W, self.H
        m = 58
        rail_x = m + 6

        y = H - 64
        c.setFillColor(HexColor(st["accent"]))
        c.setFont(self.f["bold"], 24)
        c.drawString(m, y, d.name or "Your Name")
        y -= 19
        if d.title:
            c.setFillColor(HexColor(st["muted"]))
            c.setFont(self.f["regular"], 11.5)
            c.drawString(m, y, d.title)
            y -= 15
        parts = contact_parts(d)
        if parts:
            c.setFillColor(HexColor("#6B7280"))
            c.setFont(self.f["regular"], 8.6)
            c.drawString(m, y, "   •   ".join(parts))
            y -= 12
        y -= 8
        c.setStrokeColor(HexColor(st["accent"]))
        c.setLineWidth(0.8)
        c.line(m, y, W - m, y)
        y -= 18

        def newpage(flow):
            c.showPage()
            flow.y = H - 60

        flow = Flow(self, m + 22, W - 2 * m - 22, y, 52, newpage, st["accent"])
        rail_left = m + 6

        if d.summary:
            f_heading(flow, "Profile", st["heading"], gap_before=0)
            f_text(flow, d.summary, self.f["regular"], 9.7, st["text"])

        if d.experience:
            f_heading(flow, "Experience", st["heading"])
            for job in d.experience:
                role = job.get("role", "").strip()
                comp = job.get("company", "").strip()
                dates = job.get("dates", "").strip()
                if not (role or comp):
                    continue
                page_before = c.getPageNumber()
                top_y = flow.y - 2
                flow.y -= 2
                flow.need(30)
                c.setFillColor(HexColor(st["text"]))
                c.setFont(self.f["bold"], 10.8)
                c.drawString(flow.x, flow.y, role or comp)
                if dates:
                    c.setFont(self.f["regular"], 9)
                    c.setFillColor(HexColor(st["muted"]))
                    c.drawRightString(flow.x + flow.w, flow.y, dates)
                flow.y -= 13
                if role and comp:
                    c.setFont(self.f["italic"], 9.4)
                    c.setFillColor(HexColor(st["accent"]))
                    c.drawString(flow.x, flow.y, comp)
                    flow.y -= 13
                desc = job_description(job)
                if desc:
                    f_bullets(flow, desc, st["text"], size=9.2)
                flow.y -= 8
                if c.getPageNumber() == page_before:
                    c.setStrokeColor(HexColor(st["accent"]))
                    c.setLineWidth(1.2)
                    c.line(rail_left, top_y + 3, rail_left, flow.y + 12)
                    c.setFillColor(HexColor(st["accent"]))
                    c.circle(rail_left, top_y + 3, 3.4, stroke=0, fill=1)

        if d.education:
            f_heading(flow, "Education", st["heading"])
            self._edu_block(flow)
        if d.skills:
            f_heading(flow, "Skills", st["heading"])
            self._plain_list(flow, d.skills, columns=2)
        if d.languages:
            f_heading(flow, "Languages", st["heading"])
            f_text(flow, "   •   ".join(d.languages), self.f["regular"],
                   9.6, st["text"])
        if d.certifications:
            f_heading(flow, "Certifications", st["heading"])
            f_bullets(flow, d.certifications, st["text"], size=9.3)

    # =====================================================================
    #  LAYOUT: SIDEBAR (left or right)
    # =====================================================================
    def _sidebar(self, side="left"):
        st, c, d = self.st, self.c, self.data
        W, H = self.W, self.H
        SBW = 198

        # page-1 sidebar panel
        c.setFillColor(HexColor(st["sidebar"]))
        if side == "left":
            c.rect(0, 0, SBW, H, stroke=0, fill=1)
            sx = 24
        else:
            c.rect(W - SBW, 0, SBW, H, stroke=0, fill=1)
            sx = W - SBW + 24
        sw = SBW - 48

        sf = Flow(self, sx, sw, H - 62, 34, None, st["sidebar_text"])

        # --- name / title
        c.setFillColor(HexColor(st["sidebar_text"]))
        c.setFont(self.f["bold"], 20)
        for ln in simpleSplit(d.name or "Your Name", self.f["bold"], 20, sw):
            c.drawString(sx, sf.y, ln)
            sf.y -= 23
        if d.title:
            c.setFillColor(HexColor(st["sidebar_muted"]))
            c.setFont(self.f["regular"], 10)
            for ln in simpleSplit(d.title, self.f["regular"], 10, sw):
                c.drawString(sx, sf.y, ln)
                sf.y -= 13
        sf.y -= 10
        c.setStrokeColor(HexColor(st["sidebar_muted"]))
        c.setLineWidth(0.6)
        c.line(sx, sf.y, sx + sw, sf.y)
        sf.y -= 16

        def sb_head(text):
            c.setFillColor(HexColor(st["sidebar_text"]))
            c.setFont(self.f["bold"], 9.2)
            c.drawString(sx, sf.y, text.upper())
            sf.y -= 5
            c.setStrokeColor(HexColor(st["sidebar_muted"]))
            c.setLineWidth(0.5)
            c.line(sx, sf.y, sx + sw, sf.y)
            sf.y -= 13

        def sb_lines(text, size=8.8, color=None):
            c.setFont(self.f["regular"], size)
            c.setFillColor(HexColor(color or st["sidebar_text"]))
            for para in str(text).split("\n"):
                for ln in simpleSplit(para, self.f["regular"], size, sw) or [""]:
                    c.drawString(sx, sf.y, ln)
                    sf.y -= size * 1.42

        # --- contact
        parts = contact_parts(d)
        if parts:
            sb_head("Contact")
            for p in parts:
                sb_lines(p)
            sf.y -= 6

        # --- skills
        if d.skills:
            sb_head("Skills")
            for s in d.skills:
                sb_lines("• " + str(s))
            sf.y -= 6

        # --- languages
        if d.languages:
            sb_head("Languages")
            for s in d.languages:
                sb_lines("• " + str(s))
            sf.y -= 6

        # --- certifications
        if d.certifications:
            sb_head("Certifications")
            for s in d.certifications:
                sb_lines("• " + str(s))

        # --- main column
        def newpage(flow):
            c.showPage()
            c.setFillColor(HexColor(st["accent"]))
            c.rect(0, H - 12, W, 12, stroke=0, fill=1)
            flow.y = H - 48

        if side == "left":
            mx = SBW + 28
            mw = W - SBW - 60
        else:
            mx = 40
            mw = W - SBW - 60

        flow = Flow(self, mx, mw, H - 62, 50, newpage, st["accent"])

        if d.summary:
            f_heading(flow, "Profile", st["heading"], gap_before=0)
            f_text(flow, d.summary, self.f["regular"], 9.7, st["text"])
        if d.experience:
            f_heading(flow, "Experience", st["heading"])
            self._exp_block(flow)
        if d.education:
            f_heading(flow, "Education", st["heading"])
            self._edu_block(flow)

    # =====================================================================
    #  LAYOUT: HEADER BAND (full-width band + 2 column body)
    # =====================================================================
    def _header_band(self):
        st, c, d = self.st, self.c, self.data
        W, H = self.W, self.H
        band_h = 112

        c.setFillColor(HexColor(st["accent"]))
        c.rect(0, H - band_h, W, band_h, stroke=0, fill=1)

        c.setFillColor(HexColor("#FFFFFF"))
        c.setFont(self.f["bold"], 25)
        c.drawString(46, H - 52, d.name or "Your Name")
        if d.title:
            c.setFont(self.f["regular"], 11.5)
            c.setFillColor(HexColor("#E9EFFF"))
            c.drawString(46, H - 71, d.title)
        parts = contact_parts(d)
        if parts:
            c.setFont(self.f["regular"], 8.7)
            c.setFillColor(HexColor("#E9EFFF"))
            yy = H - 40
            for p in parts[:4]:
                c.drawRightString(W - 46, yy, p)
                yy -= 13

        body_top = H - band_h - 28
        left_x = 46
        left_w = (W - 92) * 0.62 - 12
        right_x = left_x + left_w + 26
        right_w = W - 92 - left_w - 26

        def newpage(flow):
            c.showPage()
            c.setFillColor(HexColor(st["accent"]))
            c.rect(0, H - 14, W, 14, stroke=0, fill=1)
            flow.y = H - 50

        left = Flow(self, left_x, left_w, body_top, 50, newpage, st["accent"])
        right = Flow(self, right_x, right_w, body_top, 50, None, st["accent"])

        # --- right column (short static lists)
        if d.skills:
            f_heading(right, "Skills", st["heading"], gap_before=0)
            f_bullets(right, d.skills, st["text"], size=9.2)
        if d.languages:
            f_heading(right, "Languages", st["heading"])
            f_bullets(right, d.languages, st["text"], size=9.2)
        if d.certifications:
            f_heading(right, "Certifications", st["heading"])
            f_bullets(right, d.certifications, st["text"], size=9.2)

        # --- left column (long, paginated)
        if d.summary:
            f_heading(left, "Profile", st["heading"], gap_before=0)
            f_text(left, d.summary, self.f["regular"], 9.7, st["text"])
        if d.experience:
            f_heading(left, "Experience", st["heading"])
            self._exp_block(left)
        if d.education:
            f_heading(left, "Education", st["heading"])
            self._edu_block(left)


# =============================================================================
#  PREVIEW RENDERER  (Tkinter schematic of the selected style)
# =============================================================================

def draw_preview(cnv, st, data, W, H):
    cnv.delete("all")
    if W < 60 or H < 60:
        return

    margin = 12
    ph = H - 2 * margin
    pw = ph * 595.0 / 842.0
    if pw > W - 2 * margin:
        pw = W - 2 * margin
        ph = pw * 842.0 / 595.0
    ox = (W - pw) / 2
    oy = (H - ph) / 2
    s = pw / 595.0

    def R(x, y, w, h, fill, outline=""):
        cnv.create_rectangle(ox + x * s, oy + y * s,
                             ox + (x + w) * s, oy + (y + h) * s,
                             fill=fill, outline=outline)

    def T(x, y, txt, size, color, bold=False, anchor="nw"):
        px = max(5, int(size * s))
        fam = "Times" if st["font"] == "serif" else "Helvetica"
        cnv.create_text(ox + x * s, oy + y * s, text=txt, fill=color,
                        anchor=anchor,
                        font=(fam, -px, "bold" if bold else "normal"))

    def lines(x, y, w, n, color="#C9CFD8", gap=11, h=3.2, widths=None):
        for i in range(n):
            ww = w if not widths else widths[i % len(widths)]
            R(x, y + i * gap, ww, h, color)

    # page shadow + paper
    cnv.create_rectangle(ox + 4, oy + 4, ox + pw + 4, oy + ph + 4,
                         fill="#D3D9E2", outline="")
    R(0, 0, 595, 842, "#FFFFFF", "#C3CAD6")

    name = data.name or "Your Name"
    title = data.title or "Professional Title"
    accent = st["accent"]
    muted = st["muted"]
    layout = st["layout"]

    if layout in ("sidebar_left", "sidebar_right"):
        SBW = 198
        if layout == "sidebar_left":
            R(0, 0, SBW, 842, st["sidebar"])
            sx = 22
            mx = SBW + 26
        else:
            R(595 - SBW, 0, SBW, 842, st["sidebar"])
            sx = 595 - SBW + 22
            mx = 38
        mw = 595 - SBW - 58
        T(sx, 42, name, 19, st["sidebar_text"], bold=True)
        T(sx, 68, title, 9, st["sidebar_muted"])
        R(sx, 88, SBW - 44, 0.8, st["sidebar_muted"])
        for i, lab in enumerate(["CONTACT", "SKILLS", "LANGUAGES"]):
            yy = 108 + i * 88
            T(sx, yy, lab, 7.5, st["sidebar_text"], bold=True)
            R(sx, yy + 12, SBW - 44, 0.6, st["sidebar_muted"])
            lines(sx, yy + 22, SBW - 44, 4 if lab != "SKILLS" else 5,
                  st["sidebar_muted"], gap=10,
                  widths=[SBW - 44, SBW - 70, SBW - 55, SBW - 80])
        # main
        for i, lab in enumerate(["PROFILE", "EXPERIENCE", "EDUCATION"]):
            yy = 40 + i * 168
            T(mx, yy, lab, 8.5, accent, bold=True)
            R(mx, yy + 14, mw, 0.9, accent)
            if lab == "EXPERIENCE":
                lines(mx, yy + 28, mw, 8, "#C9CFD8", gap=12,
                      widths=[mw, mw - 60, mw * 0.8, mw - 30,
                              mw * 0.9, mw - 70, mw * 0.7, mw * 0.5])
            else:
                lines(mx, yy + 28, mw, 5, "#C9CFD8", gap=12,
                      widths=[mw, mw - 40, mw * 0.85, mw - 90, mw * 0.6])

    elif layout == "header_band":
        R(0, 0, 595, 112, accent)
        T(44, 32, name, 23, "#FFFFFF", bold=True)
        T(44, 62, title, 9.5, "#E9EFFF")
        for i in range(3):
            T(551, 30 + i * 15, ["email@mail.com", "+00 000 000", "City"],
              7.5, "#E9EFFF", anchor="ne")
        # right column
        for i, lab in enumerate(["SKILLS", "LANGUAGES", "CERTS"]):
            yy = 142 + i * 150
            R(378, yy, 3, 11, accent)
            T(388, yy - 1, lab, 7.5, accent, bold=True)
            lines(378, yy + 18, 175, 5, "#C9CFD8", gap=11,
                  widths=[175, 150, 165, 120, 140])
        # left column
        for i, lab in enumerate(["PROFILE", "EXPERIENCE", "EDUCATION"]):
            yy = 142 + i * 200
            R(44, yy, 3, 11, accent)
            T(54, yy - 1, lab, 7.5, accent, bold=True)
            if lab == "EXPERIENCE":
                lines(44, yy + 20, 310, 9, "#C9CFD8", gap=11,
                      widths=[310, 250, 290, 200, 300, 260, 180, 240, 150])
            else:
                lines(44, yy + 20, 310, 5, "#C9CFD8", gap=11,
                      widths=[310, 260, 300, 230, 170])

    elif layout == "blocks":
        R(0, 0, 595, 96, accent)
        T(46, 26, name, 22, "#FFFFFF", bold=True)
        T(46, 58, title, 9.5, "#EAF0FF")
        T(549, 30, "email@mail.com", 7.5, "#EAF0FF", anchor="ne")
        for i, lab in enumerate(["PROFILE", "EXPERIENCE", "EDUCATION",
                                 "SKILLS"]):
            yy = 126 + i * 165
            R(46, yy, 503, 17, accent)
            T(54, yy + 4, lab, 7.5, "#FFFFFF", bold=True)
            if lab == "EXPERIENCE":
                lines(46, yy + 28, 503, 8, "#C9CFD8", gap=12,
                      widths=[503, 430, 470, 360, 500, 400, 300, 260])
            elif lab == "SKILLS":
                lines(46, yy + 28, 240, 5, "#C9CFD8", gap=11,
                      widths=[240, 200, 230, 170, 210])
                lines(309, yy + 28, 240, 5, "#C9CFD8", gap=11,
                      widths=[240, 200, 230, 170, 210])
            else:
                lines(46, yy + 28, 503, 5, "#C9CFD8", gap=12,
                      widths=[503, 440, 480, 380, 300])

    elif layout == "timeline":
        T(56, 34, name, 22, accent, bold=True)
        T(56, 62, title, 9.5, muted)
        R(56, 84, 483, 0.9, accent)
        rail = 62
        for i, lab in enumerate(["PROFILE", "EXPERIENCE"]):
            yy = 110 + i * 190
            R(56, yy, 3, 11, accent)
            T(66, yy - 1, lab, 7.5, accent, bold=True)
            if lab == "EXPERIENCE":
                for k in range(3):
                    ey = yy + 28 + k * 58
                    cnv.create_oval(ox + (rail - 3.2) * s, oy + (ey - 3.2) * s,
                                    ox + (rail + 3.2) * s, oy + (ey + 3.2) * s,
                                    fill=accent, outline="")
                    if k < 2:
                        R(rail - 0.6, ey + 4, 1.2, 50, accent)
                    lines(80, ey, 440, 3, "#C9CFD8", gap=11,
                          widths=[300, 440, 380])
            else:
                lines(80, yy + 24, 440, 5, "#C9CFD8", gap=12,
                      widths=[440, 380, 420, 300, 240])

    else:  # classic / minimal
        centered = layout == "classic"
        if centered:
            T(297, 40, name.upper(), 21, accent, bold=True, anchor="n")
            T(297, 70, title, 9.5, muted, anchor="n")
            T(297, 88, "email  •  phone  •  city", 7.5, "#6B7280", anchor="n")
            R(56, 106, 483, 1.3, accent)
        else:
            T(60, 40, name, 20, "#111111" if st["font"] == "sans" else muted,
              bold=True)
            T(60, 68, title, 9.5, muted)
            T(60, 86, "email  /  phone  /  city", 7.5, "#8A8F98")
            R(60, 104, 475, 0.7, "#DADDE2")

        for i, lab in enumerate(["PROFILE", "EXPERIENCE", "EDUCATION",
                                 "SKILLS"]):
            yy = 132 + i * 168
            if st["heading"] == "rule":
                T(60, yy, lab, 7.5, accent, bold=True)
                R(60, yy + 13, 475, 0.9, accent)
            else:
                T(60, yy, lab, 7.5, accent, bold=True)
            if lab == "EXPERIENCE":
                lines(60, yy + 26, 475, 9, "#C9CFD8", gap=12,
                      widths=[475, 400, 450, 330, 470, 380, 280, 240, 160])
            elif lab == "SKILLS":
                lines(60, yy + 26, 225, 5, "#C9CFD8", gap=11,
                      widths=[225, 190, 215, 160, 200])
                lines(310, yy + 26, 225, 5, "#C9CFD8", gap=11,
                      widths=[225, 190, 215, 160, 200])
            else:
                lines(60, yy + 26, 475, 5, "#C9CFD8", gap=12,
                      widths=[475, 410, 450, 350, 260])


# =============================================================================
#  GUI
# =============================================================================

BG        = "#EEF2F7"
PANEL     = "#FFFFFF"
ACCENT    = "#2563EB"
ACCENT_DK = "#1D4ED8"
TEXT      = "#1F2937"
MUTED     = "#6B7280"
BORDER    = "#D7DEE8"


class ScrollFrame(ttk.Frame):
    """A vertically scrollable container."""

    def __init__(self, parent, bg=PANEL):
        super().__init__(parent, style="Panel.TFrame")
        self.canvas = tk.Canvas(self, highlightthickness=0, bg=bg, bd=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical",
                                 command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0, 0), window=self.inner,
                                              anchor="nw")
        self.inner.bind("<Configure>", self._on_inner)
        self.canvas.bind("<Configure>", self._on_canvas)
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)

    def _on_inner(self, _e=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas(self, e):
        self.canvas.itemconfigure(self._win, width=e.width)

    def _bind_wheel(self, _e=None):
        self.canvas.bind_all("<MouseWheel>", self._wheel)
        self.canvas.bind_all("<Button-4>", self._wheel)
        self.canvas.bind_all("<Button-5>", self._wheel)

    def _unbind_wheel(self, _e=None):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _wheel(self, e):
        if e.num == 4:
            delta = -1
        elif e.num == 5:
            delta = 1
        else:
            delta = -1 if e.delta > 0 else 1
        self.canvas.yview_scroll(delta, "units")


class Card(tk.Frame):
    """A white rounded-ish panel."""

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=PANEL, highlightbackground=BORDER,
                         highlightthickness=1, bd=0, **kw)


def field_label(parent, text):
    return tk.Label(parent, text=text.upper(), bg=PANEL, fg=MUTED,
                    font=("Segoe UI", 7, "bold"), anchor="w")


def entry(parent, textvariable=None):
    e = tk.Entry(parent, textvariable=textvariable, bg="#F7F9FC", fg=TEXT,
                 relief="flat", highlightthickness=1,
                 highlightbackground=BORDER, highlightcolor=ACCENT,
                 insertbackground=TEXT, font=("Segoe UI", 10))
    return e


def text_area(parent, height=4):
    t = tk.Text(parent, height=height, bg="#F7F9FC", fg=TEXT, relief="flat",
                highlightthickness=1, highlightbackground=BORDER,
                highlightcolor=ACCENT, insertbackground=TEXT, wrap="word",
                font=("Segoe UI", 10), padx=6, pady=4)
    return t


# ---------------------------------------------------------------- entry rows

class ExperienceRow(Card):
    def __init__(self, parent, on_remove):
        super().__init__(parent)
        self.on_remove = on_remove
        pad = tk.Frame(self, bg=PANEL)
        pad.pack(fill="x", padx=8, pady=8)

        top = tk.Frame(pad, bg=PANEL)
        top.pack(fill="x")
        self.v_role = tk.StringVar()
        self.v_company = tk.StringVar()
        self.v_dates = tk.StringVar()

        c1 = tk.Frame(top, bg=PANEL); c1.pack(side="left", fill="x", expand=True)
        field_label(c1, "Role / Title").pack(fill="x")
        entry(c1, self.v_role).pack(fill="x", pady=(2, 0))

        c2 = tk.Frame(top, bg=PANEL); c2.pack(side="left", fill="x",
                                              expand=True, padx=(6, 0))
        field_label(c2, "Company").pack(fill="x")
        entry(c2, self.v_company).pack(fill="x", pady=(2, 0))

        c3 = tk.Frame(top, bg=PANEL); c3.pack(side="left", fill="x",
                                              expand=True, padx=(6, 0))
        field_label(c3, "Dates").pack(fill="x")
        entry(c3, self.v_dates).pack(fill="x", pady=(2, 0))

        field_label(pad, "Achievements (one per line)").pack(fill="x",
                                                             pady=(8, 2))
        self.txt = text_area(pad, 3)
        self.txt.pack(fill="x")

        btns = tk.Frame(pad, bg=PANEL)
        btns.pack(fill="x", pady=(6, 0))
        tk.Button(btns, text="Remove", command=self._remove, relief="flat",
                  bg="#FDECEC", fg="#B91C1C", activebackground="#FBD5D5",
                  font=("Segoe UI", 8), cursor="hand2", bd=0,
                  padx=10, pady=2).pack(side="right")

    def _remove(self):
        self.on_remove(self)

    def get(self):
        return {
            "role": self.v_role.get().strip(),
            "company": self.v_company.get().strip(),
            "dates": self.v_dates.get().strip(),
            "description": self.txt.get("1.0", "end").strip(),
        }

    def is_empty(self):
        g = self.get()
        return not (g["role"] or g["company"] or g["description"])


class EducationRow(Card):
    LEVELS = [
        ("", "—"),
        ("PhD", "PhD / Doctorate"),
        ("Masters", "Masters"),
        ("Bachelors", "Bachelors"),
        ("Associates", "Associates"),
        ("A Levels", "A Levels"),
        ("GCSE", "GCSE"),
        ("Diploma", "Diploma"),
        ("Certificate", "Certificate"),
        ("High School", "High School"),
    ]

    def __init__(self, parent, on_remove):
        super().__init__(parent)
        self.on_remove = on_remove
        pad = tk.Frame(self, bg=PANEL)
        pad.pack(fill="x", padx=8, pady=8)

        self.v_degree = tk.StringVar()
        self.v_school = tk.StringVar()
        self.v_year = tk.StringVar()
        self.v_details = tk.StringVar()
        self.v_level = tk.StringVar()

        top = tk.Frame(pad, bg=PANEL); top.pack(fill="x")
        c1 = tk.Frame(top, bg=PANEL); c1.pack(side="left", fill="x", expand=True)
        field_label(c1, "Degree").pack(fill="x")
        entry(c1, self.v_degree).pack(fill="x", pady=(2, 0))

        c2 = tk.Frame(top, bg=PANEL); c2.pack(side="left", fill="x",
                                               expand=True, padx=(6, 0))
        field_label(c2, "Level").pack(fill="x")
        self.combo_level = ttk.Combobox(c2, textvariable=self.v_level,
                                        values=[l for _, l in self.LEVELS],
                                        state="readonly", font=("Segoe UI", 10))
        self.combo_level.pack(fill="x", pady=(2, 0))

        c3 = tk.Frame(top, bg=PANEL); c3.pack(side="left", fill="x",
                                               expand=True, padx=(6, 0))
        field_label(c3, "School").pack(fill="x")
        entry(c3, self.v_school).pack(fill="x", pady=(2, 0))

        c4 = tk.Frame(top, bg=PANEL); c4.pack(side="left", fill="x",
                                               expand=True, padx=(6, 0))
        field_label(c4, "Year").pack(fill="x")
        entry(c4, self.v_year).pack(fill="x", pady=(2, 0))

        field_label(pad, "Details").pack(fill="x", pady=(8, 2))
        entry(pad, self.v_details).pack(fill="x")

        btns = tk.Frame(pad, bg=PANEL)
        btns.pack(fill="x", pady=(6, 0))
        tk.Button(btns, text="Remove", command=lambda: self.on_remove(self),
                  relief="flat", bg="#FDECEC", fg="#B91C1C",
                  activebackground="#FBD5D5", font=("Segoe UI", 8),
                  cursor="hand2", bd=0, padx=10, pady=2).pack(side="right")

    def get(self):
        return {
            "degree": self.v_degree.get().strip(),
            "level": self.v_level.get().strip(),
            "school": self.v_school.get().strip(),
            "year": self.v_year.get().strip(),
            "details": self.v_details.get().strip(),
        }

    def is_empty(self):
        g = self.get()
        return not (g["degree"] or g["school"] or g["details"])


class StyleTile(tk.Frame):
    def __init__(self, parent, style, index, on_select):
        super().__init__(parent, bg=PANEL, cursor="hand2",
                         highlightthickness=2, highlightbackground=PANEL)
        self.style = style
        self.index = index
        self.on_select = on_select
        self.selected = False

        swatch = tk.Canvas(self, width=52, height=34, bg=PANEL,
                           highlightthickness=0)
        swatch.pack(side="left", padx=(6, 8), pady=6)
        self._draw_swatch(swatch, style)

        right = tk.Frame(self, bg=PANEL)
        right.pack(side="left", fill="both", expand=True, pady=6)
        self.lbl = tk.Label(right, text="%02d  %s" % (index + 1, style["name"]),
                            bg=PANEL, fg=TEXT, font=("Segoe UI", 9),
                            anchor="w")
        self.lbl.pack(fill="x")
        self.sub = tk.Label(right, text=style["layout"].replace("_", " "),
                            bg=PANEL, fg=MUTED, font=("Segoe UI", 7),
                            anchor="w")
        self.sub.pack(fill="x")

        for w in (self, swatch, right, self.lbl, self.sub):
            w.bind("<Button-1>", lambda e: self.on_select(self.index))

    @staticmethod
    def _draw_swatch(cnv, style):
        cnv.create_rectangle(1, 1, 51, 33, outline=BORDER, fill="#FFFFFF")
        lay = style["layout"]
        ac = style["accent"]
        sb = style["sidebar"]
        if lay == "sidebar_left":
            cnv.create_rectangle(1, 1, 16, 33, fill=sb, outline="")
            cnv.create_rectangle(20, 6, 47, 8, fill=ac, outline="")
            for i in range(3):
                cnv.create_rectangle(20, 13 + i * 6, 47, 14 + i * 6,
                                     fill="#C9CFD8", outline="")
        elif lay == "sidebar_right":
            cnv.create_rectangle(37, 1, 51, 33, fill=sb, outline="")
            cnv.create_rectangle(5, 6, 32, 8, fill=ac, outline="")
            for i in range(3):
                cnv.create_rectangle(5, 13 + i * 6, 32, 14 + i * 6,
                                     fill="#C9CFD8", outline="")
        elif lay == "header_band":
            cnv.create_rectangle(1, 1, 51, 11, fill=ac, outline="")
            for i in range(3):
                cnv.create_rectangle(5, 16 + i * 6, 27, 17 + i * 6,
                                     fill="#C9CFD8", outline="")
                cnv.create_rectangle(31, 16 + i * 6, 47, 17 + i * 6,
                                     fill="#C9CFD8", outline="")
        elif lay == "blocks":
            cnv.create_rectangle(1, 1, 51, 9, fill=ac, outline="")
            for i in range(3):
                cnv.create_rectangle(5, 14 + i * 7, 47, 18 + i * 7,
                                     fill=ac, outline="")
        elif lay == "timeline":
            cnv.create_rectangle(9, 6, 10, 30, fill=ac, outline="")
            for i in range(4):
                cnv.create_oval(7, 6 + i * 7, 12, 11 + i * 7,
                                fill=ac, outline="")
                cnv.create_rectangle(16, 7 + i * 7, 47, 9 + i * 7,
                                     fill="#C9CFD8", outline="")
        elif lay == "minimal":
            cnv.create_rectangle(5, 6, 34, 9, fill="#333333", outline="")
            for i in range(4):
                cnv.create_rectangle(5, 14 + i * 5, 47, 15 + i * 5,
                                     fill="#DADDE2", outline="")
        else:  # classic
            cnv.create_rectangle(15, 6, 37, 8, fill=ac, outline="")
            cnv.create_rectangle(5, 12, 47, 13, fill=ac, outline="")
            for i in range(3):
                cnv.create_rectangle(5, 17 + i * 5, 47, 18 + i * 5,
                                     fill="#C9CFD8", outline="")

    def set_selected(self, flag):
        self.selected = flag
        self.configure(highlightbackground=ACCENT if flag else PANEL,
                       bg="#EEF4FF" if flag else PANEL)
        for w in self.winfo_children():
            try:
                w.configure(bg="#EEF4FF" if flag else PANEL)
            except tk.TclError:
                pass
            for c in w.winfo_children():
                try:
                    c.configure(bg="#EEF4FF" if flag else PANEL)
                except tk.TclError:
                    pass


# ---------------------------------------------------------------- main app

class CVStudio(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CV Studio — 25 Templates, PDF Export")
        self.geometry("1480x920")
        self.minsize(1200, 760)
        self.configure(bg=BG)

        self._setup_style()

        self.exp_rows = []
        self.edu_rows = []
        self.tiles = []
        self.selected = 0

        self._build_header()
        self._build_body()
        self._build_footer()

        self._add_experience()
        self._add_education()
        self._select_style(0)

    # ------------------------------------------------------------ styling
    def _setup_style(self):
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("Panel.TFrame", background=PANEL)
        st.configure("Bg.TFrame", background=BG)
        st.configure("Vertical.TScrollbar", background="#D7DEE8",
                     troughcolor=PANEL, bordercolor=PANEL, arrowcolor=MUTED)
        st.configure("TCombobox", fieldbackground="#F7F9FC")

    # ------------------------------------------------------------ header
    def _build_header(self):
        bar = tk.Frame(self, bg="#0F172A", height=64)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        tk.Label(bar, text="CV STUDIO", bg="#0F172A", fg="#FFFFFF",
                 font=("Segoe UI", 16, "bold")).pack(side="left", padx=22)
        tk.Label(bar, text="25 templates · live preview · PDF export",
                 bg="#0F172A", fg="#8FA3BF",
                 font=("Segoe UI", 9)).pack(side="left")

        tk.Button(bar, text="Export all 25 styles…", command=self.export_all,
                  relief="flat", bg="#1E293B", fg="#E2E8F0",
                  activebackground="#334155", activeforeground="#FFFFFF",
                  font=("Segoe UI", 9), cursor="hand2", bd=0,
                  padx=14, pady=6).pack(side="right", padx=(0, 16), pady=14)

        tk.Button(bar, text="Generate PDF", command=self.export_current,
                  relief="flat", bg=ACCENT, fg="#FFFFFF",
                  activebackground=ACCENT_DK, activeforeground="#FFFFFF",
                  font=("Segoe UI", 10, "bold"), cursor="hand2", bd=0,
                  padx=18, pady=6).pack(side="right", padx=(0, 10), pady=14)

    # ------------------------------------------------------------ body
    def _build_body(self):
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=14, pady=12)
        body.columnconfigure(0, weight=0, minsize=430)
        body.columnconfigure(1, weight=0, minsize=300)
        body.columnconfigure(2, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_form(body)
        self._build_gallery(body)
        self._build_preview(body)

    # -------- left: form
    def _build_form(self, parent):
        wrap = tk.Frame(parent, bg=BG)
        wrap.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        wrap.rowconfigure(1, weight=1)
        wrap.columnconfigure(0, weight=1)

        head = tk.Frame(wrap, bg=BG)
        head.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tk.Label(head, text="Your details", bg=BG, fg=TEXT,
                 font=("Segoe UI", 12, "bold")).pack(side="left")
        tk.Button(head, text="Load sample", command=self.load_sample,
                  relief="flat", bg=BG, fg=ACCENT, font=("Segoe UI", 9),
                  cursor="hand2", bd=0).pack(side="right")

        sf = ScrollFrame(wrap, bg=PANEL)
        sf.grid(row=1, column=0, sticky="nsew")
        root = sf.inner
        root.configure(padx=14, pady=14)

        # variables
        self.v_name = tk.StringVar()
        self.v_title = tk.StringVar()
        self.v_email = tk.StringVar()
        self.v_phone = tk.StringVar()
        self.v_location = tk.StringVar()
        self.v_website = tk.StringVar()
        self.v_skills = tk.StringVar()
        self.v_languages = tk.StringVar()
        self.v_certs = tk.StringVar()

        self.v_name.trace_add("write", lambda *a: self._refresh_preview())

        # --- personal
        self._section(root, "Personal")
        self._field(root, "Full name", self.v_name)
        self._field(root, "Professional title", self.v_title)
        row = tk.Frame(root, bg=PANEL); row.pack(fill="x")
        half = tk.Frame(row, bg=PANEL); half.pack(side="left", fill="x",
                                                  expand=True)
        field_label(half, "Email").pack(fill="x")
        entry(half, self.v_email).pack(fill="x", pady=(2, 8))
        half2 = tk.Frame(row, bg=PANEL); half2.pack(side="left", fill="x",
                                                     expand=True, padx=(8, 0))
        field_label(half2, "Phone").pack(fill="x")
        entry(half2, self.v_phone).pack(fill="x", pady=(2, 8))

        row = tk.Frame(root, bg=PANEL); row.pack(fill="x")
        half = tk.Frame(row, bg=PANEL); half.pack(side="left", fill="x",
                                                  expand=True)
        field_label(half, "Location").pack(fill="x")
        entry(half, self.v_location).pack(fill="x", pady=(2, 8))
        half2 = tk.Frame(row, bg=PANEL); half2.pack(side="left", fill="x",
                                                     expand=True, padx=(8, 0))
        field_label(half2, "Website").pack(fill="x")
        entry(half2, self.v_website).pack(fill="x", pady=(2, 8))

        # --- summary
        self._section(root, "Profile summary")
        field_label(root, "A few lines about you").pack(fill="x")
        self.txt_summary = text_area(root, 4)
        self.txt_summary.pack(fill="x", pady=(2, 6))

        # --- experience
        self._section(root, "Experience")
        self.exp_container = tk.Frame(root, bg=PANEL)
        self.exp_container.pack(fill="x")
        self._add_button(root, "＋ Add experience", self._add_experience)

        # --- education
        self._section(root, "Education")
        self.edu_container = tk.Frame(root, bg=PANEL)
        self.edu_container.pack(fill="x")
        self._add_button(root, "＋ Add education", self._add_education)

        # --- skills
        self._section(root, "Skills & extras")
        self._field(root, "Skills (comma separated)", self.v_skills)
        self._field(root, "Languages (comma separated)", self.v_languages)
        self._field(root, "Certifications (comma separated)", self.v_certs)

        tk.Frame(root, bg=PANEL, height=20).pack(fill="x")

    def _section(self, parent, title):
        f = tk.Frame(parent, bg=PANEL)
        f.pack(fill="x", pady=(12, 6))
        tk.Label(f, text=title, bg=PANEL, fg=ACCENT,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Frame(f, bg=BORDER, height=1).pack(side="left", fill="x",
                                              expand=True, padx=(8, 0))

    def _field(self, parent, label, var):
        f = tk.Frame(parent, bg=PANEL)
        f.pack(fill="x", pady=(0, 6))
        field_label(f, label).pack(fill="x")
        entry(f, var).pack(fill="x", pady=(2, 0))

    def _add_button(self, parent, text, cmd):
        tk.Button(parent, text=text, command=cmd, relief="flat",
                  bg="#EDF3FF", fg=ACCENT, activebackground="#DCE7FF",
                  font=("Segoe UI", 9), cursor="hand2", bd=0,
                  pady=4).pack(fill="x", pady=(4, 0))

    def _add_experience(self):
        row = ExperienceRow(self.exp_container, self._remove_experience)
        row.pack(fill="x", pady=(0, 8))
        self.exp_rows.append(row)

    def _remove_experience(self, row):
        if row in self.exp_rows:
            self.exp_rows.remove(row)
        row.destroy()

    def _add_education(self):
        row = EducationRow(self.edu_container, self._remove_education)
        row.pack(fill="x", pady=(0, 8))
        self.edu_rows.append(row)

    def _remove_education(self, row):
        if row in self.edu_rows:
            self.edu_rows.remove(row)
        row.destroy()

    # -------- middle: gallery
    def _build_gallery(self, parent):
        wrap = tk.Frame(parent, bg=BG)
        wrap.grid(row=0, column=1, sticky="nsew", padx=(0, 12))
        wrap.rowconfigure(1, weight=1)
        wrap.columnconfigure(0, weight=1)

        head = tk.Frame(wrap, bg=BG)
        head.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tk.Label(head, text="25 styles", bg=BG, fg=TEXT,
                 font=("Segoe UI", 12, "bold")).pack(side="left")

        sf = ScrollFrame(wrap, bg=PANEL)
        sf.grid(row=1, column=0, sticky="nsew")
        holder = sf.inner
        holder.configure(padx=6, pady=6)

        for i, style in enumerate(STYLES):
            tile = StyleTile(holder, style, i, self._select_style)
            tile.pack(fill="x", pady=2)
            self.tiles.append(tile)

    # -------- right: preview
    def _build_preview(self, parent):
        wrap = tk.Frame(parent, bg=BG)
        wrap.grid(row=0, column=2, sticky="nsew")
        wrap.rowconfigure(1, weight=1)
        wrap.columnconfigure(0, weight=1)

        head = tk.Frame(wrap, bg=BG)
        head.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.lbl_style = tk.Label(head, text="", bg=BG, fg=TEXT,
                                  font=("Segoe UI", 12, "bold"))
        self.lbl_style.pack(side="left")

        card = Card(wrap)
        card.grid(row=1, column=0, sticky="nsew")
        self.preview = tk.Canvas(card, bg="#F4F6FA", highlightthickness=0)
        self.preview.pack(fill="both", expand=True, padx=10, pady=10)
        self.preview.bind("<Configure>",
                          lambda e: self._refresh_preview())

    # ------------------------------------------------------------ footer
    def _build_footer(self):
        bar = tk.Frame(self, bg=BG, height=30)
        bar.pack(fill="x", side="bottom")
        self.status = tk.Label(bar, text="Ready.", bg=BG, fg=MUTED,
                               font=("Segoe UI", 8), anchor="w")
        self.status.pack(side="left", padx=16)

    def _set_status(self, msg):
        self.status.configure(text=msg)

    # ------------------------------------------------------------ actions
    def _select_style(self, index):
        self.selected = index
        for i, t in enumerate(self.tiles):
            t.set_selected(i == index)
        self.lbl_style.configure(
            text="%02d · %s" % (index + 1, STYLES[index]["name"]))
        self._refresh_preview()

    def _refresh_preview(self):
        w = self.preview.winfo_width()
        h = self.preview.winfo_height()
        if w < 20 or h < 20:
            return
        draw_preview(self.preview, STYLES[self.selected], self.collect(),
                     w, h)

    # ------------------------------------------------------------ collect
    def collect(self) -> CVData:
        d = CVData()
        d.name = self.v_name.get().strip()
        d.title = self.v_title.get().strip()
        d.email = self.v_email.get().strip()
        d.phone = self.v_phone.get().strip()
        d.location = self.v_location.get().strip()
        d.website = self.v_website.get().strip()
        d.summary = self.txt_summary.get("1.0", "end").strip()
        d.skills = [s.strip() for s in self.v_skills.get().split(",")
                    if s.strip()]
        d.languages = [s.strip() for s in self.v_languages.get().split(",")
                       if s.strip()]
        d.certifications = [s.strip() for s in self.v_certs.get().split(",")
                            if s.strip()]
        d.experience = [r.get() for r in self.exp_rows if not r.is_empty()]
        d.education = [r.get() for r in self.edu_rows if not r.is_empty()]
        return d

    # ------------------------------------------------------------ export
    def _safe_filename(self, data, style):
        base = data.name.strip().replace(" ", "_") or "CV"
        for ch in '\\/:*?"<>|':
            base = base.replace(ch, "")
        return "%s_%s.pdf" % (base, style["name"].replace(" ", ""))

    def export_current(self):
        data = self.collect()
        if not data.name:
            messagebox.showwarning("Missing name",
                                   "Please enter at least a name before "
                                   "exporting.")
            return
        style = STYLES[self.selected]
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=self._safe_filename(data, style),
            filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        try:
            CVPdf(path, data, style).build()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Export failed", str(exc))
            return
        self._set_status("Saved: %s" % path)
        messagebox.showinfo("Done", "PDF saved to:\n%s" % path)

    def export_all(self):
        data = self.collect()
        if not data.name:
            messagebox.showwarning("Missing name",
                                   "Please enter at least a name before "
                                   "exporting.")
            return
        folder = filedialog.askdirectory(title="Choose output folder")
        if not folder:
            return
        ok, fail = 0, 0
        for style in STYLES:
            fname = self._safe_filename(data, style)
            try:
                CVPdf(os.path.join(folder, fname), data, style).build()
                ok += 1
            except Exception:  # noqa: BLE001
                fail += 1
        self._set_status("Exported %d PDFs to %s" % (ok, folder))
        messagebox.showinfo("Batch export",
                            "%d PDFs written to:\n%s\n%d failures."
                            % (ok, folder, fail))

    # ------------------------------------------------------------ sample
    def load_sample(self):
        self.v_name.set("Alex Morgan")
        self.v_title.set("Senior Product Designer")
        self.v_email.set("alex.morgan@email.com")
        self.v_phone.set("+44 7700 900123")
        self.v_location.set("London, UK")
        self.v_website.set("alexmorgan.design")

        self.txt_summary.delete("1.0", "end")
        self.txt_summary.insert("1.0",
            "Product designer with 8+ years of experience building "
            "accessible, data-informed interfaces for fintech and health "
            "platforms. Comfortable leading discovery, design systems and "
            "cross-functional delivery.")

        for r in list(self.exp_rows):
            self._remove_experience(r)
        for r in list(self.edu_rows):
            self._remove_education(r)

        samples = [
            ("Senior Product Designer", "Northwind Bank",
             "2021 — Present",
             "Led redesign of the mobile onboarding flow, lifting completion "
             "by 27%.\nBuilt and maintained a 120-component design system "
             "used by 6 squads.\nMentored 4 junior designers and ran weekly "
             "critique sessions."),
            ("Product Designer", "Helio Health", "2018 — 2021",
             "Shipped a patient-facing appointment booking product from 0 to 1.\n"
             "Ran 60+ usability sessions and translated findings into a "
             "prioritised roadmap.\nPartnered with engineering to cut average "
             "page load time by 41%."),
            ("UI Designer", "Bright Studio", "2016 — 2018",
             "Designed marketing sites and dashboards for 12 client accounts.\n"
             "Introduced a shared Figma library that halved design handoff time."),
        ]
        for role, comp, dates, desc in samples:
            self._add_experience()
            row = self.exp_rows[-1]
            row.v_role.set(role)
            row.v_company.set(comp)
            row.v_dates.set(dates)
            row.txt.delete("1.0", "end")
            row.txt.insert("1.0", desc)

        edu = [
            ("MA Interaction Design", "Masters", "Royal College of Art", "2016",
             "Distinction — thesis on accessible data visualisation"),
            ("BSc Computer Science", "Bachelors", "University of Manchester",
             "2014", "First Class Honours"),
        ]
        for deg, lvl, sch, yr, det in edu:
            self._add_education()
            row = self.edu_rows[-1]
            row.v_degree.set(deg)
            row.v_level.set(lvl)
            row.v_school.set(sch)
            row.v_year.set(yr)
            row.v_details.set(det)

        self.v_skills.set("Design Systems, Figma, Prototyping, User Research, "
                          "Accessibility, HTML/CSS, Data Visualisation, "
                          "Workshop Facilitation")
        self.v_languages.set("English (native), Spanish (fluent), "
                             "French (basic)")
        self.v_certs.set("Nielsen Norman Group UX Certification, "
                         "IAAP CPACC Accessibility Core Competencies")

        self._refresh_preview()
        self._set_status("Sample data loaded — try a style on the right.")


# =============================================================================
#  MAIN
# =============================================================================

def main():
    try:
        app = CVStudio()
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            "Could not start the GUI: %s\n"
            "Make sure Tkinter is installed and reportlab is available "
            "(pip install reportlab)." % exc
        )
    app.mainloop()


if __name__ == "__main__":
    main()