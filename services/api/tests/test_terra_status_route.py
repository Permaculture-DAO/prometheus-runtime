"""RC5 route contract without invoking database lifespan or external I/O."""
import unittest
from app.main import create_app
from app.terra_semantic import status_view

class TerraStatusRouteTests(unittest.TestCase):
    def test_route_contract(self):
        app = create_app()
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
