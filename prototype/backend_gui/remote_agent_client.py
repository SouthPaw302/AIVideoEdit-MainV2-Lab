#!/usr/bin/env python3
"""Dependency-free client for the optional AIVideoEdit remote Tool API adapter."""
from __future__ import annotations

import json
import os
import urllib.request
import uuid


class RemoteClient:
    def __init__(self, base_url:str, token:str|None=None, timeout:float=60.0):
        self.base_url=base_url.rstrip("/")
        self.token=token or os.environ.get("AIVE_REMOTE_TOKEN") or ""
        self.timeout=timeout

    def _request(self,path:str,payload:dict|None=None):
        headers={
            "Accept":"application/json",
            "Authorization":f"Bearer {self.token}",
            "X-Request-ID":str(uuid.uuid4()),
        }
        data=None
        method="GET"
        if payload is not None:
            data=json.dumps(payload).encode("utf-8")
            headers["Content-Type"]="application/json"
            method="POST"
        req=urllib.request.Request(
            self.base_url+path,data=data,headers=headers,method=method
        )
        with urllib.request.urlopen(req,timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def health(self):
        return self._request("/api/remote/health")

    def capabilities(self):
        return self._request("/api/remote/capabilities")

    def call(self,name:str,arguments:dict|None=None):
        return self._request(
            "/api/remote/call",
            {"name":name,"arguments":arguments or {}},
        )
