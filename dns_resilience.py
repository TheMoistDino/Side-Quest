"""
dns_resilience.py: Resilient DNS Resolution & Dispatch Protection for uAgents.

Mitigates Windows/ISP UDP port 53 DNS failures and long connection hangs
for Agentverse and ASI:One/Flockx endpoints (e.g. api.flockx.io, agentverse.ai).
"""

import socket
import ssl
import json
import logging
import urllib.request
from typing import Dict, List, Tuple, Any

logger = logging.getLogger("dns_resilience")

# Hardcoded fallback records verified via Cloudflare DoH
STATIC_DNS_CACHE: Dict[str, List[str]] = {
    "api.flockx.io": ["3.33.161.45", "13.248.131.213", "15.197.152.254", "35.71.150.51"],
    "aquatic-argentinosaurus-e9baspnpjnq925423unbjlrp.herokudns.com": ["3.33.161.45", "13.248.131.213", "15.197.152.254", "35.71.150.51"],
    "agentverse.ai": ["104.26.12.52", "104.26.13.52", "172.67.70.26"],
    "v2.agentverse.ai": ["104.26.12.52", "104.26.13.52", "172.67.70.26"],
}

_ORIGINAL_GETADDRINFO = socket.getaddrinfo
_PATCH_APPLIED = False


def doh_lookup(hostname: str) -> List[str]:
    """Fallback DNS lookup over HTTPS (Cloudflare 1.1.1.1 / Google 8.8.8.8)."""
    endpoints = [
        f"https://1.1.1.1/dns-query?name={hostname}&type=A",
        f"https://8.8.8.8/resolve?name={hostname}&type=A",
    ]
    ctx = ssl._create_unverified_context()
    for url in endpoints:
        try:
            req = urllib.request.Request(url, headers={"accept": "application/dns-json"})
            with urllib.request.urlopen(req, context=ctx, timeout=2.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                answers = data.get("Answer", [])
                ips = [a["data"] for a in answers if a.get("type") == 1]
                if ips:
                    return ips
        except Exception:
            continue
    return []


def resilient_getaddrinfo(host, port, *args, **kwargs):
    # Fast path: Check static fallback cache
    if isinstance(host, str) and host in STATIC_DNS_CACHE:
        ips = STATIC_DNS_CACHE[host]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ips[0], port))]

    try:
        return _ORIGINAL_GETADDRINFO(host, port, *args, **kwargs)
    except socket.gaierror as e:
        if isinstance(host, str):
            # Check suffix matches
            for known_host, ips in STATIC_DNS_CACHE.items():
                if host == known_host or host.endswith(f".{known_host}"):
                    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ips[0], port))]

            # DoH fallback query
            ips = doh_lookup(host)
            if ips:
                STATIC_DNS_CACHE[host] = ips
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ips[0], port))]
        raise e


def apply_dns_patches():
    """Applies monkeypatches to socket and uagents communication."""
    global _PATCH_APPLIED
    if _PATCH_APPLIED:
        return
    _PATCH_APPLIED = True

    # 1. Patch socket.getaddrinfo
    socket.getaddrinfo = resilient_getaddrinfo

    # 2. Patch uagents.communication.send_exchange_envelope to enforce tight timeouts
    try:
        import uagents.communication as ucomm
        import aiohttp
        from uagents_core.envelope import Envelope
        from uagents_core.types import DeliveryStatus, MsgStatus
        from pydantic import ValidationError

        orig_send_envelope = ucomm.send_exchange_envelope

        async def resilient_send_exchange_envelope(
            envelope: Envelope, endpoints: list[str], sync: bool = False
        ) -> MsgStatus | Envelope:
            headers = {"content-type": "application/json"}
            if sync:
                headers["x-uagents-connection"] = "sync"
            errors = []
            
            # Enforce 6.0s total, 2.5s connect timeout to prevent 300s hanging dispenser
            client_timeout = aiohttp.ClientTimeout(total=6.0, connect=2.5)

            for endpoint in endpoints:
                try:
                    async with aiohttp.ClientSession(timeout=client_timeout) as session:
                        async with session.post(
                            endpoint,
                            headers=headers,
                            data=envelope.model_dump_json(),
                        ) as resp:
                            success = resp.status == 200
                            if success:
                                if sync:
                                    env = Envelope.model_validate(await resp.json())
                                    if env.signature:
                                        verified = False
                                        try:
                                            verified = env.verify()
                                        except Exception as ex:
                                            errors.append(f"Received response envelope that failed verification: {ex}")
                                        if not verified:
                                            continue
                                    return await ucomm.dispatch_sync_response_envelope(env, endpoint)
                                return MsgStatus(
                                    status=DeliveryStatus.DELIVERED,
                                    detail="Message successfully delivered via HTTP",
                                    destination=envelope.target,
                                    endpoint=endpoint,
                                    session=envelope.session,
                                )
                            body = await resp.text()
                            try:
                                error_json = json.loads(body)
                                detail = error_json.get("detail", body)
                            except json.JSONDecodeError:
                                detail = body
                        errors.append(f"{resp.status}: {detail}")
                except aiohttp.ClientConnectorError as ex:
                    errors.append(f"Failed to connect: {ex}")
                except aiohttp.ServerTimeoutError as ex:
                    errors.append(f"Server timeout: {ex}")
                except TimeoutError as ex:
                    errors.append(f"Request timeout: {ex}")
                except ValidationError as ex:
                    errors.append(f"Invalid sync response: {ex}")
                except Exception as ex:
                    errors.append(f"Failed to send message: {ex}")

            ucomm.LOGGER.warning(
                f"Failed to deliver message to {envelope.target} @ {endpoints}: {errors}"
            )
            return MsgStatus(
                status=DeliveryStatus.FAILED,
                detail="Message delivery failed",
                destination=envelope.target,
                endpoint="",
                session=envelope.session,
            )

        ucomm.send_exchange_envelope = resilient_send_exchange_envelope
        logger.info("Successfully installed resilient uAgents communication patch.")
    except Exception as e:
        logger.warning(f"Could not patch uagents.communication: {e}")
