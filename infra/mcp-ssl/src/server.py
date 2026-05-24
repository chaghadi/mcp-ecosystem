"""server.py — mcp-ssl MCP server entry point.

Inspect SSL/TLS certificates for any HTTPS endpoint.
Pure Python — no API credentials needed.
"""

import socket
import ssl
from datetime import datetime, timezone
from typing import Any

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "mcp-ssl",
    instructions="SSL/TLS certificate inspection for mmiri28 solutions. Check expiry, chains, fingerprints, issuer for any HTTPS endpoint.",
)


def _fetch_cert(domain: str, port: int = 443, timeout: int = 10) -> dict[str, Any]:
    """Fetch the SSL certificate from a domain and parse it."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # Allow inspection even of self-signed
    try:
        with socket.create_connection((domain, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                der = ssock.getpeercert(binary_form=True)
                cert = x509.load_der_x509_certificate(der, default_backend())
                return {"ok": True, "cert": cert}
    except socket.gaierror:
        return {"ok": False, "error": f"Could not resolve '{domain}'"}
    except socket.timeout:
        return {"ok": False, "error": f"Connection to {domain}:{port} timed out"}
    except ConnectionRefusedError:
        return {"ok": False, "error": f"Connection refused on {domain}:{port}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _name_to_dict(name: x509.Name) -> dict[str, str]:
    """Convert an x509.Name to a dict like {"CN": "...", "O": "..."}."""
    result = {}
    for attr in name:
        result[attr.oid._name] = attr.value
    return result


@mcp.tool()
def health_check() -> dict:
    """mcp-ssl needs no credentials — always ready."""
    return {"ok": True, "status": "ready",
            "note": "Pure Python SSL inspection. No API keys required."}


@mcp.tool()
def check_ssl(domain: str, port: int = 443) -> dict[str, Any]:
    """
    Inspect the SSL certificate for a domain.

    Returns full certificate details: subject, issuer, validity period,
    SANs, signature algorithm, fingerprint.

    Args:
        domain: Hostname to check (e.g. "mmiri28.com").
        port:   Port number. Default: 443.
    """
    result = _fetch_cert(domain, port)
    if not result["ok"]:
        return result

    cert = result["cert"]
    now = datetime.now(timezone.utc)

    # Get SAN (Subject Alternative Names)
    sans = []
    try:
        ext = cert.extensions.get_extension_for_oid(x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
        sans = [name.value for name in ext.value]
    except x509.ExtensionNotFound:
        pass

    not_after = cert.not_valid_after_utc
    not_before = cert.not_valid_before_utc
    days_left = (not_after - now).days

    return {
        "ok": True,
        "domain": domain, "port": port,
        "subject": _name_to_dict(cert.subject),
        "issuer": _name_to_dict(cert.issuer),
        "valid_from": not_before.isoformat(),
        "valid_until": not_after.isoformat(),
        "days_until_expiry": days_left,
        "expired": days_left < 0,
        "san": sans,
        "serial_number": str(cert.serial_number),
        "signature_algorithm": cert.signature_algorithm_oid._name,
        "fingerprint_sha256": cert.fingerprint(hashes.SHA256()).hex(),
        "version": cert.version.name,
    }


@mcp.tool()
def get_expiration(domain: str, port: int = 443) -> dict[str, Any]:
    """
    Quick check — days until SSL cert expires for a domain.

    Args:
        domain: Hostname to check.
        port:   Port number. Default: 443.
    """
    result = _fetch_cert(domain, port)
    if not result["ok"]:
        return result

    cert = result["cert"]
    now = datetime.now(timezone.utc)
    not_after = cert.not_valid_after_utc
    days = (not_after - now).days

    if days < 0:
        status = "expired"
    elif days < 14:
        status = "critical"
    elif days < 30:
        status = "warning"
    else:
        status = "ok"

    return {
        "ok": True,
        "domain": domain,
        "days_until_expiry": days,
        "expires_at": not_after.isoformat(),
        "status": status,
        "renew_recommended": days < 30,
    }


@mcp.tool()
def check_multiple(domains: list[str]) -> dict[str, Any]:
    """
    Check SSL expiration for multiple domains in one call.
    Useful for monitoring all your domains at once.

    Args:
        domains: List of hostnames.
    """
    results = []
    for d in domains:
        r = get_expiration(d)
        if r["ok"]:
            results.append({"domain": d, "days_until_expiry": r["days_until_expiry"],
                            "status": r["status"]})
        else:
            results.append({"domain": d, "error": r["error"]})

    expiring_soon = [r for r in results if r.get("status") in ("critical", "warning", "expired")]
    return {
        "ok": True, "checked": len(domains),
        "expiring_soon": len(expiring_soon),
        "results": results,
        "alerts": expiring_soon,
    }


@mcp.tool()
def verify_chain(domain: str, port: int = 443) -> dict[str, Any]:
    """
    Verify that the certificate chain is trusted by the system CA store.

    Args:
        domain: Hostname to verify.
        port:   Port number.
    """
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((domain, port), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain):
                pass
        return {"ok": True, "domain": domain, "valid": True,
                "message": "Certificate chain is trusted."}
    except ssl.SSLCertVerificationError as exc:
        return {"ok": True, "domain": domain, "valid": False,
                "error": exc.verify_message, "reason": exc.reason}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
