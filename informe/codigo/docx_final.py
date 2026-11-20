"""Funciones para escribir en informe/Imforme final.docx sin abrir Word.

El .docx es la fuente: Andrés también lo edita en Word. Cada script de sección lee el
archivo, cambia solo su parte (comprobando que esté vacía) y lo vuelve a guardar.
En el texto, *cursiva* y **negrita** se convierten en el formato de Word."""
import re
import shutil
import unicodedata
import zipfile
from pathlib import Path

from PIL import Image

INFORME = Path(__file__).resolve().parents[1] / "Imforme final.docx"


class Docx:
    def __init__(self, ruta):
        with zipfile.ZipFile(ruta) as z:
            self.archivos = {n: z.read(n) for n in z.namelist()}
        self.doc = self.archivos["word/document.xml"].decode("utf8")

    # ---------------------------------------------------------- lectura
    def parrafos(self):
        """Lista de (inicio, fin, xml) de cada párrafo del cuerpo."""
        return [(m.start(), m.end(), m.group(0))
                # Word guarda los párrafos vacíos como <w:p .../>, que hay que reconocer primero
                for m in re.finditer(r"<w:p(?:\s[^>]*)?/>|<w:p(?:\s[^>]*)?>.*?</w:p>", self.doc, re.S)]

    @staticmethod
    def texto(xml):
        t = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml))
        return t.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")

    def bloques(self):
        """Lista de (inicio, fin) de cada párrafo o tabla de primer nivel del cuerpo. A diferencia de parrafos(),
        no se confunde con los párrafos que van dentro de las tablas o de los cuadros de texto de un diagrama."""
        ini = self.doc.find("<w:body>") + len("<w:body>")
        fin = self.doc.rfind("<w:sectPr")
        etiqueta = re.compile(r"<w:(p|tbl|sdt)(?=[ >/])[^>]*?(/?)>|</w:(p|tbl|sdt)>")
        pila, out, inicio = [], [], 0
        for m in etiqueta.finditer(self.doc, ini, fin):
            if m.group(1):
                if m.group(2):                  # párrafo vacío, <w:p/>
                    if not pila:
                        out.append((m.start(), m.end()))
                    continue
                if not pila:
                    inicio = m.start()
                pila.append(m.group(1))
            else:
                assert pila and pila[-1] == m.group(3), f"etiquetas mal cerradas en {m.start()}"
                pila.pop()
                if not pila:
                    out.append((inicio, m.end()))
        return out

    def media_de(self, nombre_dibujo):
        """Nombre del archivo de word/media que muestra la imagen llamada nombre_dibujo (docPr name).
        Word renombra las imágenes al guardar, así que se buscan por el nombre del dibujo."""
        rels = self.archivos["word/_rels/document.xml.rels"].decode("utf8")
        dibujos = [m.group(0) for m in re.finditer(r"<w:drawing>.*?</w:drawing>", self.doc, re.S)
                   if f'name="{nombre_dibujo}"' in m.group(0)]
        assert len(dibujos) == 1, f"hay {len(dibujos)} dibujos llamados {nombre_dibujo!r}"
        rid = re.search(r'r:embed="([^"]+)"', dibujos[0]).group(1)
        return re.search(r'Id="%s"[^>]*Target="media/([^"]+)"' % rid, rels).group(1)

    def buscar_titulo(self, titulo):
        for i, (a, b, p) in enumerate(self.parrafos()):
            if "Ttulo" in p and self.texto(p) == titulo:
                return i
        raise ValueError(f"no está el título {titulo!r}")

    # ---------------------------------------------------------- escritura
    def reemplazar_vacio_tras(self, titulo, xml_nuevo):
        """Cambia el párrafo vacío que sigue al título por xml_nuevo. Falla si ya tiene texto."""
        ps = self.parrafos()
        i = self.buscar_titulo(titulo)
        a, b, p = ps[i + 1]
        assert not self.texto(p).strip() and "Ttulo" not in p and "w:drawing" not in p, \
            f"la sección {titulo!r} ya tiene contenido"
        self.doc = self.doc[:a] + xml_nuevo + self.doc[b:]

    def reemplazar_parrafo_con_imagen(self, nombre_imagen, xml_nuevo):
        """Cambia el párrafo que tiene la imagen llamada nombre_imagen (docPr name) por xml_nuevo,
        y borra la imagen vieja del paquete si ya nadie la usa."""
        ps = [x for x in self.parrafos() if f'name="{nombre_imagen}"' in x[2] and "w:drawing" in x[2]]
        assert len(ps) == 1, f"hay {len(ps)} imágenes llamadas {nombre_imagen!r}"
        a, b, p = ps[0]
        assert not self.texto(p).strip(), "el párrafo de la imagen también tiene texto"
        rids = re.findall(r'r:embed="([^"]+)"', p)
        self.doc = self.doc[:a] + xml_nuevo + self.doc[b:]
        rels = self.archivos["word/_rels/document.xml.rels"].decode("utf8")
        for rid in rids:
            if f'"{rid}"' in self.doc:
                continue
            m = re.search(r'<Relationship [^>]*Id="%s"[^>]*/>' % rid, rels)
            destino = re.search(r'Target="([^"]+)"', m.group(0)).group(1)
            rels = rels.replace(m.group(0), "")
            if destino not in rels:
                self.archivos.pop("word/" + destino, None)
        self.archivos["word/_rels/document.xml.rels"] = rels.encode("utf8")

    def cambiar_imagen(self, nombre_media, ruta_png):
        """Cambia la imagen word/media/nombre_media por ruta_png y ajusta el alto a su proporción,
        conservando el ancho con que está en el documento."""
        rels = self.archivos["word/_rels/document.xml.rels"].decode("utf8")
        rid = re.search(r'Id="([^"]+)"[^>]*Target="media/%s"' % re.escape(nombre_media), rels).group(1)
        self.archivos["word/media/" + nombre_media] = Path(ruta_png).read_bytes()
        w, h = Image.open(ruta_png).size
        dibujos = [m.group(0) for m in re.finditer(r"<w:drawing>.*?</w:drawing>", self.doc, re.S)
                   if f'r:embed="{rid}"' in m.group(0)]
        assert len(dibujos) == 1, f"{nombre_media} aparece {len(dibujos)} veces"
        cx = int(re.search(r'<wp:extent cx="(\d+)"', dibujos[0]).group(1))
        nuevo = re.sub(r'(<wp:extent cx="\d+" cy=")\d+', rf"\g<1>{round(cx * h / w)}", dibujos[0])
        nuevo = re.sub(r'(<a:ext cx="\d+" cy=")\d+', rf"\g<1>{round(cx * h / w)}", nuevo)
        self.doc = self.doc.replace(dibujos[0], nuevo)

    def reemplazar_parrafo(self, inicio, texto_nuevo):
        """Cambia todo el texto del único párrafo que empieza con `inicio`, conservando su formato de párrafo."""
        ps = [x for x in self.parrafos() if self.texto(x[2]).startswith(inicio)]
        assert len(ps) == 1, f"hay {len(ps)} párrafos que empiezan con {inicio!r}"
        a, b, p = ps[0]
        ppr = re.search(r"<w:pPr>.*?</w:pPr>", p, re.S)
        apertura = re.match(r"<w:p(?:\s[^>]*)?>", p).group(0)
        self.doc = self.doc[:a] + apertura + (ppr.group(0) if ppr else "") + runs(texto_nuevo) + "</w:p>" + self.doc[b:]

    def cambiar_texto(self, viejo, nuevo):
        """Cambia un texto que debe estar una sola vez y dentro de un mismo run."""
        n = self.doc.count(esc(viejo))
        assert n == 1, f"{viejo!r} aparece {n} veces"
        self.doc = self.doc.replace(esc(viejo), esc(nuevo))

    def agregar_imagen(self, ruta_png, rid):
        nombre = Path(ruta_png).name
        self.archivos[f"word/media/{nombre}"] = Path(ruta_png).read_bytes()
        rels = self.archivos["word/_rels/document.xml.rels"].decode("utf8")
        if f'Id="{rid}"' not in rels:
            rels = rels.replace("</Relationships>",
                f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                f'relationships/image" Target="media/{nombre}"/></Relationships>')
        self.archivos["word/_rels/document.xml.rels"] = rels.encode("utf8")
        tipos = self.archivos["[Content_Types].xml"].decode("utf8")
        if 'Extension="png"' not in tipos:
            tipos = tipos.replace("<Default ", '<Default Extension="png" ContentType="image/png"/><Default ', 1)
        self.archivos["[Content_Types].xml"] = tipos.encode("utf8")

    def referencias(self, nuevas):
        """Agrega referencias (texto APA con *cursiva*) a la sección Referencias, en orden alfabético."""
        ps = self.parrafos()
        i = self.buscar_titulo("Referencias")
        j = self.buscar_titulo("Anexos")
        actuales = [p for _, _, p in ps[i + 1:j] if self.texto(p).strip()]
        por_texto = {self.texto(p): p for p in actuales}
        for ref in nuevas:
            x = par_referencia(ref)
            por_texto.setdefault(self.texto(x), x)
        sin_tildes = lambda s: "".join(c for c in unicodedata.normalize("NFKD", s.lower())
                                       if not unicodedata.combining(c))
        ordenadas = [por_texto[k] for k in sorted(por_texto, key=sin_tildes)]
        a = ps[i + 1][0]
        b = ps[j][0]
        self.doc = self.doc[:a] + "".join(ordenadas) + self.doc[b:]

    def insertar_tras(self, inicio, xml_nuevo):
        """Pone xml_nuevo justo después del único párrafo que empieza con `inicio`."""
        ps = [x for x in self.parrafos() if self.texto(x[2]).startswith(inicio)]
        assert len(ps) == 1, f"hay {len(ps)} párrafos que empiezan con {inicio!r}"
        b = ps[0][1]
        self.doc = self.doc[:b] + xml_nuevo + self.doc[b:]

    def borrar_parrafo(self, inicio):
        ps = [x for x in self.parrafos() if self.texto(x[2]).startswith(inicio)]
        assert len(ps) == 1, f"hay {len(ps)} párrafos que empiezan con {inicio!r}"
        a, b, _ = ps[0]
        self.doc = self.doc[:a] + self.doc[b:]

    def titulo_como(self, titulo_modelo, texto):
        """Un título nuevo con el mismo formato que `titulo_modelo`."""
        p = self.parrafos()[self.buscar_titulo(titulo_modelo)][2]
        ppr = re.search(r"<w:pPr>.*?</w:pPr>", p, re.S).group(0)
        return f"<w:p>{ppr}{runs(texto)}</w:p>"

    def renumerar(self):
        """Pone en orden el número que Word muestra en cada leyenda (campo SEQ Figura o SEQ Tabla).
        Word lo recalcula al actualizar campos; esto deja el archivo bien aunque no se actualicen."""
        for tipo in ("Figura", "Tabla"):
            n = 0
            pos = 0
            while True:
                i = self.doc.find(f"SEQ {tipo} ", pos)
                if i < 0:
                    break
                n += 1
                m = re.compile(r"(<w:t[^>]*>)(\d+)(</w:t>)").search(self.doc, i)
                self.doc = self.doc[:m.start(2)] + str(n) + self.doc[m.end(2):]
                pos = m.end()

    def guardar(self, ruta):
        self.archivos["word/document.xml"] = self.doc.encode("utf8")
        ruta = Path(ruta)
        tmp = ruta.with_suffix(".tmp")
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            for n, b in self.archivos.items():
                z.writestr(n, b)
        shutil.move(tmp, ruta)


# -------------------------------------------------------------- piezas de XML
def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


_WT = re.compile(r"(<w:t(?:\s[^>]*)?>)([^<]*)(</w:t>)")


def reemplazar_en_bloque(x, viejo, nuevo):
    """Cambia `viejo` por `nuevo` en el XML de un bloque, aunque Word lo haya repartido en varios <w:t> al guardar.
    El texto nuevo queda en el primer <w:t> que toca, con su formato, y de los demás se borra lo que cubría.
    `viejo` debe estar una sola vez en el bloque."""
    ms = list(_WT.finditer(x))
    plano = "".join(m.group(2) for m in ms)
    v, n = esc(viejo), esc(nuevo)
    assert plano.count(v) == 1, f"{viejo!r} aparece {plano.count(v)} veces en el bloque"
    p = plano.index(v)
    q = p + len(v)
    partes, ultimo, base, puesto = [], 0, 0, False
    for m in ms:
        a, b = base, base + len(m.group(2))
        base = b
        if b <= p or a >= q:
            continue
        c = m.group(2)
        c = c[:max(p - a, 0)] + ("" if puesto else n) + c[min(q - a, len(c)):]
        puesto = True
        apertura = m.group(1)
        if (c[:1] == " " or c[-1:] == " ") and "xml:space" not in apertura:
            apertura = apertura[:-1] + ' xml:space="preserve">'
        partes.append(x[ultimo:m.start()] + apertura + c + m.group(3))
        ultimo = m.end()
    return "".join(partes) + x[ultimo:]


def runs(t):
    """Texto con *cursiva*, **negrita**, _{subíndice} y ^{superíndice} a runs de Word.
    Los subíndices y superíndices salen en cursiva, como las variables a las que acompañan."""
    out = []
    for trozo in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*|_\{[^}]+\}|\^\{[^}]+\})", t):
        if not trozo:
            continue
        rpr = ""
        if trozo.startswith("**"):
            trozo, rpr = trozo[2:-2], "<w:rPr><w:b/><w:bCs/></w:rPr>"
        elif trozo.startswith("*"):
            trozo, rpr = trozo[1:-1], "<w:rPr><w:i/><w:iCs/></w:rPr>"
        elif trozo.startswith("_{") or trozo.startswith("^{"):
            pos = "subscript" if trozo[0] == "_" else "superscript"
            trozo, rpr = trozo[2:-1], f'<w:rPr><w:i/><w:iCs/><w:vertAlign w:val="{pos}"/></w:rPr>'
        out.append(f'<w:r>{rpr}<w:t xml:space="preserve">{esc(trozo)}</w:t></w:r>')
    return "".join(out)


def par(t, estilo=None, ppr=""):
    ps = f'<w:pStyle w:val="{estilo}"/>' if estilo else ""
    return f"<w:p><w:pPr>{ps}{ppr}</w:pPr>{runs(t)}</w:p>"


def par_referencia(t):
    return ('<w:p><w:pPr><w:spacing w:after="120"/><w:ind w:left="720" w:hanging="720"/><w:jc w:val="left"/></w:pPr>'
            f"{runs(t)}</w:p>")


def leyenda(tipo, texto, ppr=""):
    """Leyenda numerada de Word: 'Figura N.' o 'Tabla N.' con campo SEQ, para las listas de figuras y tablas."""
    b = "<w:rPr><w:b/><w:bCs/></w:rPr>"
    return (f'<w:p><w:pPr><w:pStyle w:val="Descripcin"/>{ppr}</w:pPr>'
            f'<w:r>{b}<w:t xml:space="preserve">{tipo} </w:t></w:r>'
            f'<w:r>{b}<w:fldChar w:fldCharType="begin"/></w:r>'
            f'<w:r>{b}<w:instrText xml:space="preserve"> SEQ {tipo} \\* ARABIC </w:instrText></w:r>'
            f'<w:r>{b}<w:fldChar w:fldCharType="separate"/></w:r>'
            '<w:r><w:rPr><w:b/><w:bCs/><w:noProof/></w:rPr><w:t>1</w:t></w:r>'
            f'<w:r>{b}<w:fldChar w:fldCharType="end"/></w:r>'
            f'<w:r>{b}<w:t xml:space="preserve">. </w:t></w:r>'
            f"{runs(texto)}</w:p>")


def tabla(filas, anchos_cm, encabezado=True, tam=20, junta=True):
    """Tabla sencilla al estilo APA: líneas arriba, abajo y bajo el encabezado, sin líneas verticales.
    filas: lista de listas de texto (admiten *cursiva*); tam en medios puntos.
    junta: cada fila queda pegada a la siguiente, para que Word no parta la tabla entre páginas."""
    anchos = [int(a * 567) for a in anchos_cm]
    linea = '<w:{0} w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
    tbl = ('<w:tbl><w:tblPr>'
           f'<w:tblW w:w="{sum(anchos)}" w:type="dxa"/><w:jc w:val="center"/>'
           f'<w:tblBorders>{linea.format("top")}{linea.format("bottom")}</w:tblBorders>'
           '<w:tblLayout w:type="fixed"/>'
           '<w:tblCellMar><w:left w:w="80" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar>'
           '</w:tblPr><w:tblGrid>' + "".join(f'<w:gridCol w:w="{a}"/>' for a in anchos) + "</w:tblGrid>")
    for i, fila in enumerate(filas):
        cabeza = encabezado and i == 0
        pegada = "<w:keepNext/>" if junta and i < len(filas) - 1 else ""
        tbl += "<w:tr>" + ("<w:trPr><w:cantSplit/><w:tblHeader/></w:trPr>" if cabeza
                           else "<w:trPr><w:cantSplit/></w:trPr>")
        for a, celda in zip(anchos, fila):
            borde = f"<w:tcBorders>{linea.format('bottom')}</w:tcBorders>" if cabeza else ""
            rpr = f'<w:b/><w:bCs/><w:sz w:val="{tam}"/>' if cabeza else f'<w:sz w:val="{tam}"/>'
            texto = runs(celda).replace("<w:r><w:rPr>", f"<w:r><w:rPr>{rpr}").replace(
                "<w:r><w:t", f"<w:r><w:rPr>{rpr}</w:rPr><w:t")
            tbl += (f'<w:tc><w:tcPr><w:tcW w:w="{a}" w:type="dxa"/>{borde}</w:tcPr>'
                    f'<w:p><w:pPr>{pegada}<w:spacing w:before="40" w:after="40" w:line="240" w:lineRule="auto"/>'
                    f'<w:ind w:left="0" w:firstLine="0"/><w:jc w:val="left"/></w:pPr>{texto}</w:p></w:tc>')
        tbl += "</w:tr>"
    return tbl + "</w:tbl>"


# -------------------------------------------------------------- ecuaciones (OMML, editables en Word)
_FUENTE_M = '<w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/></w:rPr>'


def m(t):
    """Texto matemático (las letras salen en cursiva)."""
    return f'<m:r>{_FUENTE_M}<m:t xml:space="preserve">{esc(t)}</m:t></m:r>'


def mr(t):
    """Texto matemático recto, para nombres como RMSE o tanh."""
    return f'<m:r><m:rPr><m:sty m:val="p"/></m:rPr>{_FUENTE_M}<m:t xml:space="preserve">{esc(t)}</m:t></m:r>'


def sub(base, s):
    return f"<m:sSub><m:e>{base}</m:e><m:sub>{s}</m:sub></m:sSub>"


def sup(base, s):
    return f"<m:sSup><m:e>{base}</m:e><m:sup>{s}</m:sup></m:sSup>"


def subsup(base, s, p):
    return f"<m:sSubSup><m:e>{base}</m:e><m:sub>{s}</m:sub><m:sup>{p}</m:sup></m:sSubSup>"


def frac(n, d):
    return f"<m:f><m:num>{n}</m:num><m:den>{d}</m:den></m:f>"


def raiz(x):
    return f'<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e>{x}</m:e></m:rad>'


def paren(x, a="(", b=")"):
    return f'<m:d><m:dPr><m:begChr m:val="{a}"/><m:endChr m:val="{b}"/></m:dPr><m:e>{x}</m:e></m:d>'


def suma(abajo, arriba, x):
    arr = f"<m:sup>{arriba}</m:sup>" if arriba else "<m:sup/>"
    oculto = "" if arriba else '<m:supHide m:val="1"/>'
    return (f'<m:nary><m:naryPr><m:chr m:val="∑"/><m:limLoc m:val="undOvr"/>{oculto}</m:naryPr>'
            f"<m:sub>{abajo}</m:sub>{arr}<m:e>{x}</m:e></m:nary>")


def acento(x, chr_="̂"):
    """Gorro por defecto; '̃' para la tilde."""
    return f'<m:acc><m:accPr><m:chr m:val="{chr_}"/></m:accPr><m:e>{x}</m:e></m:acc>'


def barra(x):
    return f'<m:bar><m:barPr><m:pos m:val="top"/></m:barPr><m:e>{x}</m:e></m:bar>'


def funcion(nombre, x):
    return f"<m:func><m:fName>{mr(nombre)}</m:fName><m:e>{x}</m:e></m:func>"


def ecuacion(omml, numero, ancho_texto=8838):
    """Ecuación centrada y en tamaño completo, con el número a la derecha.
    Va en una tabla sin bordes de tres columnas (vacía, ecuación, número): así la ecuación queda sola en
    su párrafo, que es lo que Word necesita para mostrarla en tamaño completo."""
    lado = 900
    celda = ('<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
             '<w:p><w:pPr><w:spacing w:before="60" w:after="60"/><w:ind w:left="0" w:firstLine="0"/>'
             '<w:jc w:val="{jc}"/></w:pPr>{x}</w:p></w:tc>')
    return ('<w:tbl><w:tblPr>'
            f'<w:tblW w:w="{ancho_texto}" w:type="dxa"/><w:jc w:val="center"/><w:tblLayout w:type="fixed"/>'
            '<w:tblCellMar><w:left w:w="0" w:type="dxa"/><w:right w:w="0" w:type="dxa"/></w:tblCellMar>'
            '<w:tblLook w:val="0000" w:firstRow="0" w:lastRow="0" w:firstColumn="0" w:lastColumn="0" '
            'w:noHBand="1" w:noVBand="1"/></w:tblPr>'
            f'<w:tblGrid><w:gridCol w:w="{lado}"/><w:gridCol w:w="{ancho_texto - 2 * lado}"/>'
            f'<w:gridCol w:w="{lado}"/></w:tblGrid><w:tr>'
            + celda.format(w=lado, jc="left", x="")
            + celda.format(w=ancho_texto - 2 * lado, jc="center",
                           x=f'<m:oMathPara><m:oMath>{omml}</m:oMath></m:oMathPara>')
            + celda.format(w=lado, jc="right", x=f"<w:r><w:t>({numero})</w:t></w:r>")
            + "</w:tr></w:tbl>")


def figura(ruta_png, rid, id_dibujo, ancho_cm, leyenda):
    """Imagen centrada y su leyenda numerada (Figura N, con campo SEQ para la lista de figuras)."""
    w, h = Image.open(ruta_png).size
    cx = int(ancho_cm * 360000)
    cy = int(cx * h / w)
    img = (
        '<w:p><w:pPr><w:keepNext/><w:spacing w:before="120" w:after="0"/><w:jc w:val="center"/></w:pPr>'
        '<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
        f'<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{id_dibujo}" name="Figura {id_dibujo}"/>'
        '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<pic:nvPicPr><pic:cNvPr id="{id_dibujo}" name="{Path(ruta_png).name}"/><pic:cNvPicPr/></pic:nvPicPr>'
        f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
        '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')
    cap = ('<w:p><w:pPr><w:pStyle w:val="Descripcin"/></w:pPr>'
           '<w:r><w:rPr><w:b/><w:bCs/></w:rPr><w:t xml:space="preserve">Figura </w:t></w:r>'
           '<w:r><w:rPr><w:b/><w:bCs/></w:rPr><w:fldChar w:fldCharType="begin"/></w:r>'
           '<w:r><w:rPr><w:b/><w:bCs/></w:rPr><w:instrText xml:space="preserve"> SEQ Figura \\* ARABIC </w:instrText></w:r>'
           '<w:r><w:rPr><w:b/><w:bCs/></w:rPr><w:fldChar w:fldCharType="separate"/></w:r>'
           '<w:r><w:rPr><w:b/><w:bCs/><w:noProof/></w:rPr><w:t>1</w:t></w:r>'
           '<w:r><w:rPr><w:b/><w:bCs/></w:rPr><w:fldChar w:fldCharType="end"/></w:r>'
           '<w:r><w:rPr><w:b/><w:bCs/></w:rPr><w:t xml:space="preserve">. </w:t></w:r>'
           f"{runs(leyenda)}</w:p>")
    return img + cap
