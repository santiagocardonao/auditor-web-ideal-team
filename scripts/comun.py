"""Utilidades compartidas: peticiones HTTP sin dependencias externas y parser HTML."""

import gzip
import http.client
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from html.parser import HTMLParser

# Algunas plataformas (Shopify, Cloudflare) devuelven 403/429 a user agents de bots.
# Por defecto usamos uno de navegador; se puede cambiar con la variable AUDITOR_UA.
USER_AGENT = os.environ.get("AUDITOR_UA", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
TIMEOUT = 20


class _SinRedireccion(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_opener = urllib.request.build_opener(_SinRedireccion)


def _decodificar(cuerpo, encoding):
    if encoding == "gzip":
        return gzip.decompress(cuerpo)
    if encoding == "deflate":
        try:
            return zlib.decompress(cuerpo)
        except zlib.error:
            return zlib.decompress(cuerpo, -zlib.MAX_WBITS)
    return cuerpo


def pedir(url, metodo="GET", leer_cuerpo=True, max_bytes=3_000_000, reintentos=2):
    """Una sola petición, sin seguir redirecciones. Si recibe 429, espera y reintenta.

    Devuelve dict con status, headers (minúsculas), cuerpo (str), ttfb_ms, bytes y error.
    """
    r = _pedir(url, metodo, leer_cuerpo, max_bytes)
    while r["status"] == 429 and reintentos > 0:
        try:
            espera = min(int(r["headers"].get("retry-after", "10")), 60)
        except ValueError:
            espera = 10
        time.sleep(espera)
        reintentos -= 1
        r = _pedir(url, metodo, leer_cuerpo, max_bytes)
    return r


def _pedir(url, metodo, leer_cuerpo, max_bytes):
    req = urllib.request.Request(url, method=metodo, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "es,en;q=0.8",
    })
    inicio = time.time()
    try:
        resp = _opener.open(req, timeout=TIMEOUT)
    except urllib.error.HTTPError as e:
        resp = e
    except (urllib.error.URLError, ssl.SSLError, http.client.HTTPException, OSError, ValueError) as e:
        return {"url": url, "status": None, "headers": {}, "cuerpo": "", "ttfb_ms": None,
                "bytes": 0, "error": str(getattr(e, "reason", e))}
    ttfb = round((time.time() - inicio) * 1000)
    headers = {k.lower(): v for k, v in resp.headers.items()}
    cuerpo = b""
    if leer_cuerpo and metodo != "HEAD":
        try:
            cuerpo = resp.read(max_bytes)
        except Exception:
            cuerpo = b""
        cuerpo = _decodificar(cuerpo, headers.get("content-encoding", ""))
    status = getattr(resp, "status", None) or getattr(resp, "code", None)
    charset = "utf-8"
    m = re.search(r"charset=([\w-]+)", headers.get("content-type", ""))
    if m:
        charset = m.group(1)
    try:
        texto = cuerpo.decode(charset, errors="replace")
    except LookupError:
        texto = cuerpo.decode("utf-8", errors="replace")
    return {"url": url, "status": status, "headers": headers, "cuerpo": texto,
            "ttfb_ms": ttfb, "bytes": len(cuerpo), "error": None}


def seguir(url, max_saltos=10, **kw):
    """Sigue redirecciones manualmente. Devuelve (respuesta_final, cadena)."""
    cadena = []
    actual = url
    for _ in range(max_saltos):
        r = pedir(actual, **kw)
        cadena.append({"url": actual, "status": r["status"]})
        if r["status"] in (301, 302, 303, 307, 308) and r["headers"].get("location"):
            actual = urllib.parse.urljoin(actual, r["headers"]["location"])
            continue
        return r, cadena
    return r, cadena


def normalizar(url):
    """Quita fragmento; deja query. Minúsculas en esquema y host."""
    p = urllib.parse.urlsplit(url)
    ruta = p.path or "/"
    return urllib.parse.urlunsplit((p.scheme.lower(), p.netloc.lower(), ruta, p.query, ""))


def mismo_sitio(url, host_base):
    host = urllib.parse.urlsplit(url).netloc.lower()
    quitar = lambda h: h[4:] if h.startswith("www.") else h
    return quitar(host) == quitar(host_base)


class ParserPagina(HTMLParser):
    """Extrae lo que necesitan los agentes de una página HTML."""

    def __init__(self, url_base):
        super().__init__(convert_charrefs=True)
        self.base = url_base
        self.title = None
        self._en_title = False
        self._en_svg = 0
        self.metas = {}
        self.lang = None
        self.canonical = None
        self.hreflang = []
        self.encabezados = []  # (nivel, texto)
        self._encabezado = None
        self.enlaces = []  # dicts href, texto, rel, oculto
        self._enlace = None
        self.imagenes = []
        self.scripts = []
        self.estilos = []
        self.iframes = []
        self.jsonld = []
        self._en_jsonld = False
        self._jsonld_buf = []
        self.formularios = []
        self._form = None
        self._ignorar = 0  # dentro de script/style/noscript
        self._texto = []
        self.scripts_inline = []
        self._en_script = False
        self._script_buf = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "html" and a.get("lang"):
            self.lang = a["lang"]
        elif tag == "svg":
            self._en_svg += 1
        elif tag == "title" and not self._en_svg and self.title is None:
            # Solo el <title> del documento, no los de íconos SVG.
            self._en_title = True
        elif tag == "meta":
            clave = (a.get("name") or a.get("property") or "").lower()
            if clave:
                self.metas[clave] = a.get("content", "")
        elif tag == "link":
            rel = a.get("rel", "").lower()
            href = urllib.parse.urljoin(self.base, a.get("href", ""))
            if "canonical" in rel:
                self.canonical = href
            elif "alternate" in rel and a.get("hreflang"):
                self.hreflang.append({"hreflang": a["hreflang"], "href": href})
            elif "stylesheet" in rel:
                self.estilos.append(href)
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._encabezado = [int(tag[1]), []]
        elif tag == "a" and a.get("href"):
            estilo = a.get("style", "").replace(" ", "").lower()
            self._enlace = {
                "href": urllib.parse.urljoin(self.base, a["href"]),
                "href_crudo": a["href"],
                "rel": a.get("rel", ""),
                "oculto": "display:none" in estilo or "visibility:hidden" in estilo,
                "texto": [],
            }
        elif tag == "img":
            src = a.get("src") or a.get("data-src") or ""
            self.imagenes.append({
                "src": urllib.parse.urljoin(self.base, src) if src else "",
                "alt": a.get("alt"),
                "width": a.get("width"), "height": a.get("height"),
                "loading": a.get("loading"),
            })
        elif tag == "script":
            if a.get("type", "").lower() == "application/ld+json":
                self._en_jsonld = True
                self._jsonld_buf = []
            elif a.get("src"):
                self.scripts.append({
                    "src": urllib.parse.urljoin(self.base, a["src"]),
                    "async": "async" in a, "defer": "defer" in a,
                    "type": a.get("type", ""),
                })
            else:
                self._en_script = True
                self._script_buf = []
            self._ignorar += 1
        elif tag in ("style", "noscript"):
            self._ignorar += 1
        elif tag == "iframe":
            self.iframes.append(urllib.parse.urljoin(self.base, a.get("src", "")))
        elif tag == "form":
            self._form = {"action": urllib.parse.urljoin(self.base, a.get("action", "")) if a.get("action") else "",
                          "method": a.get("method", "get").lower(), "campos": []}
        elif tag in ("input", "textarea", "select") and self._form is not None:
            tipo = a.get("type", tag).lower()
            if tipo not in ("hidden", "submit", "button"):
                self._form["campos"].append({"tipo": tipo, "nombre": a.get("name", ""),
                                             "requerido": "required" in a})

    def handle_endtag(self, tag):
        if tag == "svg":
            self._en_svg = max(0, self._en_svg - 1)
        elif tag == "title":
            self._en_title = False
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6") and self._encabezado:
            self.encabezados.append((self._encabezado[0], " ".join("".join(self._encabezado[1]).split())))
            self._encabezado = None
        elif tag == "a" and self._enlace:
            self._enlace["texto"] = " ".join("".join(self._enlace["texto"]).split())[:120]
            self.enlaces.append(self._enlace)
            self._enlace = None
        elif tag == "script":
            if self._en_jsonld:
                self.jsonld.append("".join(self._jsonld_buf))
                self._en_jsonld = False
            if self._en_script:
                self.scripts_inline.append("".join(self._script_buf)[:20000])
                self._en_script = False
            self._ignorar = max(0, self._ignorar - 1)
        elif tag in ("style", "noscript"):
            self._ignorar = max(0, self._ignorar - 1)
        elif tag == "form" and self._form is not None:
            self.formularios.append(self._form)
            self._form = None

    def handle_data(self, data):
        if self._en_jsonld:
            self._jsonld_buf.append(data)
            return
        if self._en_script:
            self._script_buf.append(data)
            return
        if self._en_title:
            self.title = (self.title or "") + data
        if self._encabezado:
            self._encabezado[1].append(data)
        if self._enlace:
            self._enlace["texto"].append(data)
        if not self._ignorar:
            self._texto.append(data)

    def texto_visible(self):
        return " ".join(" ".join(self._texto).split())


def guardar_json(datos, ruta):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
