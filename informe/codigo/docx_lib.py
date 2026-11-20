"""Generador mínimo de .docx con OOXML a mano: párrafos, títulos, listas, tablas,
imágenes, ecuaciones (OMML), tabla de contenido y pie con número de página."""
import zipfile
from xml.sax.saxutils import escape

from PIL import Image

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
NS = ('xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
      'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture" ' + W)

FUENTE = "Calibri"
ANCHO_TEXTO = 9360  # dxa: carta con márgenes de 1,25"? se ajusta abajo


def esc(t):
    return escape(t, {'"': "&quot;"})


# ---------- texto en línea ----------
def run(t, b=False, i=False, sz=None, color=None, sup=False, font=None):
    rpr = ""
    if font:
        rpr += f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}"/>'
    if b:
        rpr += "<w:b/>"
    if i:
        rpr += "<w:i/>"
    if color:
        rpr += f'<w:color w:val="{color}"/>'
    if sz:
        rpr += f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>'
    if sup:
        rpr += '<w:vertAlign w:val="superscript"/>'
    rpr = f"<w:rPr>{rpr}</w:rPr>" if rpr else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{esc(t)}</w:t></w:r>'


def _arg(s, i):
    if s[i] == "{":
        j, nivel = i + 1, 1
        while nivel:
            nivel += {"{": 1, "}": -1}.get(s[j], 0); j += 1
        return s[i + 1:j - 1], j
    return s[i], i + 1


def mini(s):
    """Subíndices y superíndices tipo LaTeX: x_i, e_{t,H}, B^7."""
    out, buf, i = [], "", 0
    while i < len(s):
        c = s[i]
        if c in "_^" and buf:
            base = buf[-1]; buf = buf[:-1]
            if buf:
                out.append(r(buf)); buf = ""
            a1, i = _arg(s, i + 1)
            if i < len(s) and s[i] in "_^" and s[i] != c:
                a2, i = _arg(s, i + 1)
                lo, hi = (a1, a2) if c == "_" else (a2, a1)
                out.append(subsup(r(base), mini(lo), mini(hi)))
            else:
                out.append((sub if c == "_" else sup)(r(base), mini(a1)))
            continue
        buf += c; i += 1
    if buf:
        out.append(r(buf))
    return "".join(out)


def rich(texto, **kw):
    """Convierte *cursiva*, **negrilla** y $matemática$ en runs."""
    if "$" in texto:
        partes = texto.split("$")
        return "".join(rich(t, **kw) if k % 2 == 0 else f"<m:oMath>{mini(t)}</m:oMath>"
                       for k, t in enumerate(partes) if t)
    out, i, b, it = [], 0, False, False
    buf = ""
    while i < len(texto):
        if texto.startswith("**", i):
            if buf:
                out.append(run(buf, b=b, i=it, **kw)); buf = ""
            b = not b; i += 2; continue
        if texto[i] == "*" :
            if buf:
                out.append(run(buf, b=b, i=it, **kw)); buf = ""
            it = not it; i += 1; continue
        buf += texto[i]; i += 1
    if buf:
        out.append(run(buf, b=b, i=it, **kw))
    return "".join(out)


def p(texto="", estilo=None, align=None, runs=None, keep=False, espacio=None, sangria=None):
    ppr = ""
    if estilo:
        ppr += f'<w:pStyle w:val="{estilo}"/>'
    if keep:
        ppr += "<w:keepNext/>"
    if espacio:
        ppr += f'<w:spacing w:before="{espacio[0]}" w:after="{espacio[1]}"/>'
    if sangria:
        ppr += f'<w:ind w:left="{sangria}"/>'
    if align:
        ppr += f'<w:jc w:val="{align}"/>'
    ppr = f"<w:pPr>{ppr}</w:pPr>" if ppr else ""
    return f"<w:p>{ppr}{runs if runs is not None else rich(texto)}</w:p>"


def h1(t): return p(t, "Heading1")
def h2(t): return p(t, "Heading2")
def h3(t): return p(t, "Heading3")


def salto():
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


# ---------- listas ----------
class Listas:
    def __init__(self):
        self.nums = []  # (numId, abstractId)

    def nueva(self, ordenada):
        nid = len(self.nums) + 1
        self.nums.append((nid, 1 if ordenada else 0))
        return nid

    def xml(self):
        ab = []
        for aid, fmt, txt in ((0, "bullet", "•"), (1, "decimal", "%1.")):
            lvl = (f'<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="{fmt}"/>'
                   f'<w:lvlText w:val="{txt}"/><w:lvlJc w:val="left"/>'
                   f'<w:pPr><w:ind w:left="567" w:hanging="283"/></w:pPr>'
                   + ('<w:rPr><w:rFonts w:ascii="Symbol" w:hAnsi="Symbol" w:hint="default"/></w:rPr>'
                      .replace("Symbol", "Calibri") if fmt == "bullet" else "")
                   + "</w:lvl>")
            ab.append(f'<w:abstractNum w:abstractNumId="{aid}"><w:multiLevelType w:val="singleLevel"/>{lvl}</w:abstractNum>')
        nums = "".join(
            f'<w:num w:numId="{n}"><w:abstractNumId w:val="{a}"/>'
            + (f'<w:lvlOverride w:ilvl="0"><w:startOverride w:val="1"/></w:lvlOverride>' if a == 1 else "")
            + "</w:num>" for n, a in self.nums)
        return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:numbering {W}>{"".join(ab)}{nums}</w:numbering>'


LISTAS = Listas()


def lista(items, ordenada=False):
    nid = LISTAS.nueva(ordenada)
    out = []
    for it in items:
        out.append(f'<w:p><w:pPr><w:pStyle w:val="ListParagraph"/><w:numPr><w:ilvl w:val="0"/>'
                   f'<w:numId w:val="{nid}"/></w:numPr><w:spacing w:after="60"/></w:pPr>{rich(it)}</w:p>')
    return "".join(out)


# ---------- tablas ----------
def tabla(filas, anchos=None, encabezado=True, tam=19, alinear_num=True, ancho_total=9360):
    n = len(filas[0])
    if anchos is None:
        anchos = [ancho_total // n] * n
    else:
        s = sum(anchos)
        anchos = [round(a * ancho_total / s) for a in anchos]
    grid = "".join(f'<w:gridCol w:w="{a}"/>' for a in anchos)
    borde = ('<w:tblBorders><w:top w:val="single" w:sz="8" w:color="5A5852"/>'
             '<w:bottom w:val="single" w:sz="8" w:color="5A5852"/>'
             '<w:insideH w:val="single" w:sz="4" w:color="D9D8D2"/></w:tblBorders>')
    out = [f'<w:tbl><w:tblPr><w:tblW w:w="{sum(anchos)}" w:type="dxa"/><w:jc w:val="center"/>{borde}'
           f'<w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="40" w:type="dxa"/><w:left w:w="80" w:type="dxa"/>'
           f'<w:bottom w:w="40" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar></w:tblPr>'
           f'<w:tblGrid>{grid}</w:tblGrid>']
    for k, fila in enumerate(filas):
        cab = encabezado and k == 0
        trpr = '<w:trPr><w:cantSplit/>' + ('<w:tblHeader/>' if cab else '') + '</w:trPr>'
        celdas = []
        for j, c in enumerate(fila):
            c = str(c)
            sh = '<w:shd w:val="clear" w:color="auto" w:fill="EDECE7"/>' if cab else ""
            num = alinear_num and j > 0 and not cab and _es_num(c)
            jc = '<w:jc w:val="right"/>' if num else '<w:jc w:val="left"/>'
            celdas.append(
                f'<w:tc><w:tcPr><w:tcW w:w="{anchos[j]}" w:type="dxa"/>{sh}<w:vAlign w:val="center"/></w:tcPr>'
                f'<w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="252" w:lineRule="auto"/>{jc}</w:pPr>'
                f'{rich(c, sz=tam) if not cab else run(c, b=True, sz=tam)}</w:p></w:tc>')
        out.append(f"<w:tr>{trpr}{''.join(celdas)}</w:tr>")
    out.append("</w:tbl>")
    return "".join(out) + p("", espacio=(0, 60))


def _es_num(c):
    c = c.replace("%", "").replace(",", "").replace(".", "").replace("−", "").replace("-", "").replace("<", "").replace(" ", "").replace("≤", "")
    return c.isdigit()


# ---------- imágenes ----------
class Imagenes:
    def __init__(self):
        self.lista = []

    def agregar(self, ruta):
        rid = f"rIdImg{len(self.lista) + 1}"
        self.lista.append((rid, ruta))
        return rid


IMGS = Imagenes()
CONT = {"fig": 0, "tab": 0, "ec": 0}


def figura(ruta, pie, ancho_cm=16.0):
    rid = IMGS.agregar(ruta)
    w, h = Image.open(ruta).size
    cx = int(ancho_cm * 360000)
    cy = int(cx * h / w)
    n = len(IMGS.lista)
    CONT["fig"] += 1
    dib = (f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
           f'<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{n}" name="Figura {n}"/>'
           f'<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
           f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
           f'<pic:pic><pic:nvPicPr><pic:cNvPr id="{n}" name="img{n}.png"/><pic:cNvPicPr/></pic:nvPicPr>'
           f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
           f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
           f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic>'
           f'</wp:inline></w:drawing></w:r>')
    return (p(runs=dib, align="center", keep=True, espacio=(120, 40))
            + p(runs=run(f"Figura {CONT['fig']}. ", b=True) + rich(pie), estilo="Caption"))


def titulo_tabla(t):
    CONT["tab"] += 1
    return p(runs=run(f"Tabla {CONT['tab']}. ", b=True) + rich(t), estilo="Caption", keep=True)


# ---------- ecuaciones (OMML) ----------
def r(t, normal=False):
    st = '<m:rPr><m:sty m:val="p"/></m:rPr>' if normal else ""
    return f'<m:r>{st}<m:t xml:space="preserve">{esc(t)}</m:t></m:r>'


def tx(t):
    return r(t, normal=True)


def e(*partes):
    return "".join(partes)


def sub(base, s):
    return f"<m:sSub><m:e>{base}</m:e><m:sub>{s}</m:sub></m:sSub>"


def sup(base, s):
    return f"<m:sSup><m:e>{base}</m:e><m:sup>{s}</m:sup></m:sSup>"


def subsup(base, s, u):
    return f"<m:sSubSup><m:e>{base}</m:e><m:sub>{s}</m:sub><m:sup>{u}</m:sup></m:sSubSup>"


def frac(n, d):
    return f"<m:f><m:num>{n}</m:num><m:den>{d}</m:den></m:f>"


def par(x, a="(", b=")"):
    return f'<m:d><m:dPr><m:begChr m:val="{esc(a)}"/><m:endChr m:val="{esc(b)}"/></m:dPr><m:e>{x}</m:e></m:d>'


def suma(abajo, arriba, cuerpo, chr_="∑"):
    oc = ('<m:subHide m:val="1"/>' if not abajo else '') + ('<m:supHide m:val="1"/>' if not arriba else '')
    return (f'<m:nary><m:naryPr><m:chr m:val="{chr_}"/><m:limLoc m:val="undOvr"/>{oc}</m:naryPr>'
            f"<m:sub>{abajo}</m:sub><m:sup>{arriba}</m:sup><m:e>{cuerpo}</m:e></m:nary>")


def raiz(x):
    return f'<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e>{x}</m:e></m:rad>'


def barra(x):
    return f'<m:bar><m:barPr><m:pos m:val="top"/></m:barPr><m:e>{x}</m:e></m:bar>'


def gorro(x):
    return f'<m:acc><m:accPr><m:chr m:val="̂"/></m:accPr><m:e>{x}</m:e></m:acc>'


def tilde(x):
    return f'<m:acc><m:accPr><m:chr m:val="̃"/></m:accPr><m:e>{x}</m:e></m:acc>'


def ec(contenido, numerar=True):
    """Ecuación centrada con número a la derecha (tabla invisible de 3 columnas)."""
    if not numerar:
        return f'<w:p><w:pPr><w:jc w:val="center"/></w:pPr><m:oMathPara><m:oMath>{contenido}</m:oMath></m:oMathPara></w:p>'
    CONT["ec"] += 1
    k = CONT["ec"]
    anchos = (800, 7760, 800)
    nb = '<w:tblBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/><w:insideH w:val="nil"/><w:insideV w:val="nil"/></w:tblBorders>'
    celda = lambda w_, inner: f'<w:tc><w:tcPr><w:tcW w:w="{w_}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>{inner}</w:tc>'
    return (f'<w:tbl><w:tblPr><w:tblW w:w="9360" w:type="dxa"/><w:jc w:val="center"/>{nb}<w:tblLayout w:type="fixed"/></w:tblPr>'
            f'<w:tblGrid>' + "".join(f'<w:gridCol w:w="{a}"/>' for a in anchos) + '</w:tblGrid><w:tr><w:trPr><w:cantSplit/></w:trPr>'
            + celda(anchos[0], '<w:p/>')
            + celda(anchos[1], f'<w:p><w:pPr><w:spacing w:before="60" w:after="60"/><w:jc w:val="center"/></w:pPr><m:oMath>{contenido}</m:oMath></w:p>')
            + celda(anchos[2], f'<w:p><w:pPr><w:spacing w:before="60" w:after="60"/><w:jc w:val="right"/></w:pPr>{run(f"({k})")}</w:p>')
            + '</w:tr></w:tbl>')


def mat_inline(contenido):
    return f"<m:oMath>{contenido}</m:oMath>"


# ---------- tabla de contenido ----------
def toc():
    return ('<w:p><w:pPr><w:pStyle w:val="TOCHeading"/></w:pPr>' + run("Contenido") + '</w:p>'
            '<w:p><w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r>'
            '<w:r><w:instrText xml:space="preserve"> TOC \\o "1-2" \\h \\z \\u </w:instrText></w:r>'
            '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
            + run("Clic derecho y «Actualizar campo» para ver la tabla de contenido.", i=True, color="77766F")
            + '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>')


# ---------- partes fijas ----------
def estilos():
    def est(sid, nombre, ppr="", rpr="", basado="Normal", sig="Normal", tipo="paragraph", extra=""):
        return (f'<w:style w:type="{tipo}" w:styleId="{sid}"><w:name w:val="{nombre}"/>'
                + (f'<w:basedOn w:val="{basado}"/>' if basado else "")
                + (f'<w:next w:val="{sig}"/>' if sig else "") + extra
                + f'<w:qFormat/><w:pPr>{ppr}</w:pPr><w:rPr>{rpr}</w:rPr></w:style>')
    f = f'<w:rFonts w:ascii="{FUENTE}" w:hAnsi="{FUENTE}" w:cs="{FUENTE}"/>'
    s = [
        f'<w:docDefaults><w:rPrDefault><w:rPr>{f}<w:sz w:val="22"/><w:szCs w:val="22"/><w:lang w:val="es-CO"/></w:rPr></w:rPrDefault>'
        '<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>',
        est("Normal", "Normal", '<w:jc w:val="both"/>', basado=None, sig=None),
        est("Title", "Title", '<w:spacing w:before="0" w:after="200"/><w:jc w:val="left"/>',
            f'<w:b/><w:color w:val="1F2A44"/><w:sz w:val="48"/><w:szCs w:val="48"/>'),
        est("Subtitle", "Subtitle", '<w:spacing w:after="120"/><w:jc w:val="left"/>', '<w:color w:val="5A5852"/><w:sz w:val="28"/>'),
        est("Heading1", "heading 1", '<w:keepNext/><w:keepLines/><w:pageBreakBefore/><w:spacing w:before="0" w:after="200"/><w:jc w:val="left"/><w:outlineLvl w:val="0"/>',
            '<w:b/><w:color w:val="1F2A44"/><w:sz w:val="34"/><w:szCs w:val="34"/>'),
        est("Heading2", "heading 2", '<w:keepNext/><w:keepLines/><w:spacing w:before="280" w:after="100"/><w:jc w:val="left"/><w:outlineLvl w:val="1"/>',
            '<w:b/><w:color w:val="2A5599"/><w:sz w:val="27"/><w:szCs w:val="27"/>'),
        est("Heading3", "heading 3", '<w:keepNext/><w:keepLines/><w:spacing w:before="200" w:after="80"/><w:jc w:val="left"/><w:outlineLvl w:val="2"/>',
            '<w:b/><w:color w:val="3A3A3A"/><w:sz w:val="23"/><w:szCs w:val="23"/>'),
        est("Caption", "caption", '<w:spacing w:before="40" w:after="200"/><w:jc w:val="left"/>', '<w:color w:val="4A4A46"/><w:sz w:val="19"/><w:szCs w:val="19"/>'),
        est("ListParagraph", "List Paragraph", '<w:ind w:left="567"/><w:jc w:val="left"/>'),
        est("TOCHeading", "TOC Heading", '<w:spacing w:before="0" w:after="200"/>', '<w:b/><w:color w:val="1F2A44"/><w:sz w:val="34"/>'),
        est("TOC1", "toc 1", '<w:spacing w:before="80" w:after="40"/><w:jc w:val="left"/>', '<w:b/>'),
        est("TOC2", "toc 2", '<w:spacing w:after="20"/><w:ind w:left="300"/><w:jc w:val="left"/>'),
        est("Nota", "Nota", '<w:pBdr><w:left w:val="single" w:sz="18" w:space="8" w:color="2A5599"/></w:pBdr><w:shd w:val="clear" w:color="auto" w:fill="F1F5FB"/><w:ind w:left="200" w:right="200"/><w:jc w:val="left"/>', '<w:sz w:val="21"/>'),
        est("Codigo", "Codigo", '<w:spacing w:after="0" w:line="240" w:lineRule="auto"/><w:jc w:val="left"/><w:shd w:val="clear" w:color="auto" w:fill="F4F4F1"/>',
            '<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/><w:sz w:val="18"/>'),
        est("Footer", "footer", '<w:jc w:val="center"/>', '<w:color w:val="77766F"/><w:sz w:val="18"/>'),
    ]
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles {W}>{"".join(s)}</w:styles>'


def guardar(ruta, cuerpo):
    sect = ('<w:sectPr><w:footerReference w:type="default" r:id="rIdFooter"/>'
            '<w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1418" w:right="1440" w:bottom="1418" w:left="1440" '
            'w:header="708" w:footer="567" w:gutter="0"/><w:titlePg/></w:sectPr>')
    doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {NS}><w:body>'
           f"{cuerpo}{sect}</w:body></w:document>")
    footer = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr {NS}><w:p><w:pPr><w:pStyle w:val="Footer"/></w:pPr>'
              '<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
              '<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>1</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>')
    rels = ['<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>',
            '<Relationship Id="rIdNum" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>',
            '<Relationship Id="rIdSettings" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>',
            '<Relationship Id="rIdFooter" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>']
    for k, (rid, ruta_img) in enumerate(IMGS.lista):
        rels.append(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/img{k + 1}.png"/>')
    settings = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings {W} '
                'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">'
                '<w:updateFields w:val="true"/><w:defaultTabStop w:val="708"/>'
                '<m:mathPr><m:mathFont m:val="Cambria Math"/><m:dispDef/></m:mathPr>'
                '<w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat></w:settings>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
          '<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>'
          '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
          '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
          '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>')
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            '<dc:title>Avance de tesis: pronóstico horario del precio de bolsa a una semana</dc:title><dc:language>es-CO</dc:language></cp:coreProperties>')
    with zipfile.ZipFile(ruta, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                   '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/></Relationships>')
        z.writestr("docProps/core.xml", core)
        z.writestr("word/document.xml", doc)
        z.writestr("word/styles.xml", estilos())
        z.writestr("word/numbering.xml", LISTAS.xml())
        z.writestr("word/settings.xml", settings)
        z.writestr("word/footer1.xml", footer)
        z.writestr("word/_rels/document.xml.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + "".join(rels) + "</Relationships>")
        for k, (rid, ruta_img) in enumerate(IMGS.lista):
            z.write(ruta_img, f"word/media/img{k + 1}.png")
