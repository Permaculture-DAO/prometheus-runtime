"""RC7 route contract and in-process HTTP test; no network or production DB."""
import asyncio
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import httpx
from app.main import create_app
from app.settings import Settings
from app.terra_semantic import status_view

class TerraStatusRouteTests(unittest.TestCase):
    def isolated_app(self, directory):
        root = Path(directory)
        return create_app(replace(Settings(), database_url="sqlite:///" + str(root / "test.db"),
                                  evidence_storage_path=root / "evidence",
                                  write_api_key="", production_admitted=False,
                                  document_integrity_required=False))
    def test_route_contract(self):
        with TemporaryDirectory() as directory:
            app = self.isolated_app(directory)
            routes = [r for r in app.routes if getattr(r, "path", None) == "/v1/terra/status"]
            self.assertEqual(len(routes), 1)
            self.assertEqual(routes[0].methods, {"GET"})
            self.assertEqual(routes[0].endpoint(), status_view())
            data = routes[0].endpoint()
            self.assertEqual(data["state"], "HOLD")
            for k in ("real_ingestion_enabled", "real_gis_enabled", "evidence_spine_write",
                      "holochain_commit", "production_admitted", "authoritative"):
                self.assertIs(data[k], False)
            self.assertEqual(data["statement"], "evaluation, not certification")
    def test_http_read_only(self):
        async def check():
            with TemporaryDirectory() as directory:
                app = self.isolated_app(directory)
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                             base_url="http://testserver") as client:
                    response = await client.get("/v1/terra/status")
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json(), status_view())
                    for method in ("POST", "PUT", "PATCH", "DELETE"):
                        denied = await client.request(method, "/v1/terra/status", json={})
                        self.assertEqual(denied.status_code, 405)
                    self.assertEqual((await client.get("/v1/terra/nonexistent")).status_code, 404)
                self.assertFalse((Path(directory) / "test.db").exists())
        asyncio.run(check())
