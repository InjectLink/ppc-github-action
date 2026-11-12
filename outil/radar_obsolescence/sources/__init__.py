"""Accès HTTP avec cache local pour les sources publiques."""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    # magasin de certificats du système (Windows, macOS) au lieu de celui d'OpenSSL :
    # évite « CERTIFICATE_VERIFY_FAILED » derrière un antivirus ou un proxy d'entreprise
    import truststore
    truststore.inject_into_ssl()
except Exception:  # bibliothèque facultative : pip install truststore
    pass

USER_AGENT = "radar-obsolescence-PPC/0.4.0 (+https://www.perennite-programmee-circulaire.org/)"


class Cache:
    def __init__(self, dossier: str | Path = ".cache_radar", ttl_jours: float = 7, hors_ligne: bool = False):
        self.dossier = Path(dossier)
        self.ttl = ttl_jours * 86400
        self.hors_ligne = hors_ligne
        self.dossier.mkdir(parents=True, exist_ok=True)

    def _fichier(self, cle: str) -> Path:
        return self.dossier / (hashlib.sha1(cle.encode()).hexdigest() + ".json")

    def lire(self, cle: str):
        f = self._fichier(cle)
        if f.exists() and (self.hors_ligne or time.time() - f.stat().st_mtime < self.ttl):
            return json.loads(f.read_text(encoding="utf-8"))
        return None

    def ecrire(self, cle: str, valeur):
        self._fichier(cle).write_text(json.dumps(valeur), encoding="utf-8")


class ErreurSource(Exception):
    pass


def _proxy_https() -> bool:
    """Vrai si le proxy est lui-même en HTTPS : urllib ne sait pas l'utiliser,
    on passe alors par la bibliothèque requests si elle est installée."""
    p = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or ""
    return p.startswith("https://")


def _via_requests(methode: str, url: str, en_tetes: dict, donnees: bytes | None, timeout: int):
    try:
        import requests
    except ImportError as e:
        raise ErreurSource("proxy HTTPS détecté : installez requests (pip install requests)") from e
    try:
        r = requests.request(methode, url, headers=en_tetes, data=donnees, timeout=timeout)
    except requests.RequestException as e:
        raise ErreurSource(f"réseau indisponible pour {url} : {e}") from e
    return r.status_code, r.content


def _message_reseau(url: str, e: Exception) -> str:
    msg = f"réseau indisponible pour {url} : {e}"
    if "CERTIFICATE_VERIFY_FAILED" in str(e):
        msg += " : certificat non reconnu : installer « pip install truststore » puis relancer"
    return msg


class _SansCache:
    hors_ligne = False

    def lire(self, cle):
        return None

    def ecrire(self, cle, valeur):
        pass


def get_json(url: str, cache: Cache | None, en_tetes: dict | None = None, timeout: int = 20):
    """GET JSON avec cache (cache=None : pas de cache). Retourne None si 404."""
    cache = cache or _SansCache()
    en_cache = cache.lire(url)
    if en_cache is not None:
        return en_cache.get("data")
    if cache.hors_ligne:
        raise ErreurSource(f"hors ligne et absent du cache : {url}")
    tetes = {"User-Agent": USER_AGENT, "Accept": "application/json", **(en_tetes or {})}
    if _proxy_https():
        code, contenu = _via_requests("GET", url, tetes, None, timeout)
        if code == 404:
            cache.ecrire(url, {"data": None})
            return None
        if code >= 400:
            raise ErreurSource(f"HTTP {code} sur {url}")
        data = json.loads(contenu.decode("utf-8"))
        cache.ecrire(url, {"data": data})
        return data
    req = urllib.request.Request(url, headers=tetes)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            cache.ecrire(url, {"data": None})
            return None
        raise ErreurSource(f"HTTP {e.code} sur {url}") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise ErreurSource(_message_reseau(url, e)) from e
    cache.ecrire(url, {"data": data})
    return data


def post_json(url: str, corps: dict | bytes, en_tetes: dict | None = None, timeout: int = 30, formulaire=False):
    if formulaire:
        donnees = corps if isinstance(corps, bytes) else urllib.parse.urlencode(corps).encode()
        type_contenu = "application/x-www-form-urlencoded"
    else:
        donnees = json.dumps(corps).encode()
        type_contenu = "application/json"
    tetes = {"User-Agent": USER_AGENT, "Content-Type": type_contenu, **(en_tetes or {})}
    if _proxy_https():
        code, contenu = _via_requests("POST", url, tetes, donnees, timeout)
        if code >= 400:
            raise ErreurSource(f"HTTP {code} sur {url}")
        return json.loads(contenu.decode("utf-8"))
    req = urllib.request.Request(url, data=donnees, method="POST", headers=tetes)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise ErreurSource(f"HTTP {e.code} sur {url}") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise ErreurSource(_message_reseau(url, e)) from e
