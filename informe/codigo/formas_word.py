"""Diagramas hechos con formas de Word (cajas con texto y flechas), en lugar de imágenes.

Cada diagrama es un grupo de formas dentro de un párrafo, como cuando en Word se insertan formas y se agrupan.
Así se pueden mover, recolorear o cambiar el texto en Word. Las medidas van en centímetros, con el origen en la
esquina superior izquierda del dibujo; el texto usa la fuente del documento.
En el texto de las cajas, *cursiva* y **negrita** funcionan como en docx_final.runs()."""
from docx_final import runs

EMU = 360000  # EMU por centímetro


def _e(cm):
    return int(round(cm * EMU))


def _rpr(tam, color, extra=""):
    return f'<w:sz w:val="{int(tam * 2)}"/><w:szCs w:val="{int(tam * 2)}"/><w:color w:val="{color}"/>{extra}'


def parrafo(texto, tam=8, color="2B2B2B", negrita=False, cursiva=False, antes=0, jc="center", linea=None):
    """Un párrafo dentro de una caja. antes: espacio antes, en puntos. Un salto de línea en el texto cambia de
    renglón sin cambiar de párrafo. linea: color de una raya bajo el párrafo, como la que separa un título."""
    extra = ("<w:b/><w:bCs/>" if negrita else "") + ("<w:i/><w:iCs/>" if cursiva else "")
    rpr = _rpr(tam, color, extra)

    def con_formato(t):
        return runs(t).replace("<w:r><w:rPr>", f"<w:r><w:rPr>{rpr}").replace("<w:r><w:t", f"<w:r><w:rPr>{rpr}</w:rPr><w:t")

    r = f"<w:r><w:rPr>{rpr}</w:rPr><w:br/></w:r>".join(con_formato(t) for t in texto.split("\n"))
    borde = (f'<w:pBdr><w:bottom w:val="single" w:sz="4" w:space="2" w:color="{linea}"/></w:pBdr>' if linea else "")
    return (f'<w:p><w:pPr><w:keepNext/>{borde}<w:spacing w:before="{int(antes * 20)}" w:after="0" w:line="240" '
            f'w:lineRule="auto"/><w:ind w:left="0" w:right="0" w:firstLine="0"/><w:jc w:val="{jc}"/>'
            f'<w:rPr>{rpr}</w:rPr></w:pPr>{r}</w:p>')


class Dibujo:
    def __init__(self, ancho, alto, id_dibujo):
        self.ancho, self.alto, self.id = ancho, alto, id_dibujo
        self.formas = []
        self.n = 0

    def _id(self):
        self.n += 1
        return self.id * 100 + self.n

    def caja(self, x, y, w, h, parrafos, relleno, borde=None, ancla="t", margen=0.12, redondeo=True, grosor=0.75):
        """Caja con texto. parrafos: lista de XML de parrafo(). ancla: 't' arriba, 'ctr' al centro."""
        i = self._id()
        ln = (f'<a:ln w="{int(grosor * 12700)}"><a:solidFill><a:srgbClr val="{borde}"/></a:solidFill></a:ln>' if borde
              else "<a:ln><a:noFill/></a:ln>")
        geom = ('<a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val 6000"/></a:avLst></a:prstGeom>'
                if redondeo else '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>')
        m = _e(margen)
        self.formas.append(
            f'<wps:wsp><wps:cNvPr id="{i}" name="Caja {i}"/><wps:cNvSpPr/>'
            f'<wps:spPr><a:xfrm><a:off x="{_e(x)}" y="{_e(y)}"/><a:ext cx="{_e(w)}" cy="{_e(h)}"/></a:xfrm>'
            f'{geom}<a:solidFill><a:srgbClr val="{relleno}"/></a:solidFill>{ln}</wps:spPr>'
            f'<wps:txbx><w:txbxContent>{"".join(parrafos)}</w:txbxContent></wps:txbx>'
            f'<wps:bodyPr rot="0" vert="horz" wrap="square" lIns="{m}" tIns="{m}" rIns="{m}" bIns="{m}" '
            f'anchor="{ancla}" anchorCtr="0"><a:noAutofit/></wps:bodyPr></wps:wsp>')

    def flecha(self, x1, y1, x2, y2, color="77766F", grosor=1.0, punta=True, guion=False):
        """Línea recta de (x1, y1) a (x2, y2), con punta en el extremo final. guion: línea punteada."""
        i = self._id()
        flip = (' flipH="1"' if x2 < x1 else "") + (' flipV="1"' if y2 < y1 else "")
        x, y = min(x1, x2), min(y1, y2)
        w, h = abs(x2 - x1), abs(y2 - y1)
        cola = ('<a:prstDash val="dash"/>' if guion else "") + (
            '<a:tailEnd type="triangle" w="med" len="med"/>' if punta else "")
        self.formas.append(
            f'<wps:wsp><wps:cNvPr id="{i}" name="Flecha {i}"/><wps:cNvCnPr/>'
            f'<wps:spPr><a:xfrm{flip}><a:off x="{_e(x)}" y="{_e(y)}"/><a:ext cx="{_e(w)}" cy="{_e(h)}"/></a:xfrm>'
            f'<a:prstGeom prst="straightConnector1"><a:avLst/></a:prstGeom><a:noFill/>'
            f'<a:ln w="{int(grosor * 12700)}"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill>{cola}</a:ln>'
            f'</wps:spPr><wps:bodyPr/></wps:wsp>')

    def linea(self, puntos, color="2B2B2B", grosor=0.75, guion=False):
        """Varias rectas seguidas, sin punta (para llaves, corchetes y separadores)."""
        for (x1, y1), (x2, y2) in zip(puntos, puntos[1:]):
            self.flecha(x1, y1, x2, y2, color=color, grosor=grosor, punta=False, guion=guion)

    def texto(self, x, y, w, h, parrafos, ancla="ctr"):
        """Texto suelto, sin relleno ni borde."""
        i = self._id()
        self.formas.append(
            f'<wps:wsp><wps:cNvPr id="{i}" name="Texto {i}"/><wps:cNvSpPr txBox="1"/>'
            f'<wps:spPr><a:xfrm><a:off x="{_e(x)}" y="{_e(y)}"/><a:ext cx="{_e(w)}" cy="{_e(h)}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></wps:spPr>'
            f'<wps:txbx><w:txbxContent>{"".join(parrafos)}</w:txbxContent></wps:txbx>'
            f'<wps:bodyPr rot="0" vert="horz" wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" anchor="{ancla}" '
            f'anchorCtr="0"><a:noAutofit/></wps:bodyPr></wps:wsp>')

    def xml(self):
        """El párrafo centrado con el grupo de formas."""
        W, H = _e(self.ancho), _e(self.alto)
        return (
            '<w:p><w:pPr><w:keepNext/><w:spacing w:before="120" w:after="60"/><w:ind w:left="0" w:firstLine="0"/>'
            '<w:jc w:val="center"/></w:pPr><w:r><mc:AlternateContent><mc:Choice Requires="wpg"><w:drawing>'
            f'<wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{W}" cy="{H}"/>'
            '<wp:effectExtent l="0" t="0" r="0" b="0"/>'
            f'<wp:docPr id="{self.id}" name="Diagrama {self.id}"/><wp:cNvGraphicFramePr/>'
            '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<a:graphicData uri="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup">'
            '<wpg:wgp><wpg:cNvGrpSpPr/><wpg:grpSpPr>'
            f'<a:xfrm><a:off x="0" y="0"/><a:ext cx="{W}" cy="{H}"/><a:chOff x="0" y="0"/><a:chExt cx="{W}" cy="{H}"/>'
            '</a:xfrm></wpg:grpSpPr>' + "".join(self.formas) +
            '</wpg:wgp></a:graphicData></a:graphic></wp:inline></w:drawing></mc:Choice></mc:AlternateContent>'
            '</w:r></w:p>')


def etapas(id_dibujo, cajas, color_final, tinte, ancho=15.0, alto=4.0, sep=0.4, tinta="2B2B2B"):
    """Diagrama de etapas en fila: cajas = [(título, periodo, [párrafos])]. La última va en el color del modelo.
    Cada párrafo puede tener saltos de línea; entre párrafos queda un espacio."""
    n = len(cajas)
    w = (ancho - sep * (n - 1)) / n
    d = Dibujo(ancho, alto, id_dibujo)
    for k, (titulo, periodo, lineas) in enumerate(cajas):
        final = k == n - 1
        c = "FFFFFF" if final else tinta
        ps = [parrafo(titulo, 9, c, negrita=True), parrafo(periodo, 8, c, cursiva=True, antes=1)]
        ps += [parrafo(t, 8, c, antes=6 if j == 0 else 4) for j, t in enumerate(lineas)]
        x = k * (w + sep)
        d.caja(x, 0, w, alto, ps, color_final if final else tinte)
        if not final:
            d.flecha(x + w + 0.04, alto / 2, x + w + sep - 0.04, alto / 2, grosor=1.25)
    return d.xml()
