from __future__ import annotations

import unittest

from fastapi import HTTPException

from app.schemas.share import ShareCreateRequest, ShareResolveRequest
from app.services.share_service import ShareService


class ShareServiceTests(unittest.TestCase):
    def test_round_trip_payload(self) -> None:
        created = ShareService.create_share_payload(
            ShareCreateRequest(
                kind="playground-session",
                label="bubble-sort-run",
                data={"code": "print('hi')", "runtime_ms": 12},
                expires_in_seconds=3600,
            )
        )
        resolved = ShareService.resolve_share_payload(ShareResolveRequest(token=created.token))
        self.assertEqual(resolved.kind, "playground-session")
        self.assertEqual(resolved.label, "bubble-sort-run")
        self.assertEqual(resolved.data["runtime_ms"], 12)

    def test_rejects_tampered_token(self) -> None:
        created = ShareService.create_share_payload(
            ShareCreateRequest(data={"hello": "world"})
        )
        tampered = f"{created.token[:-1]}{'A' if created.token[-1] != 'A' else 'B'}"
        with self.assertRaises(HTTPException):
            ShareService.resolve_share_payload(ShareResolveRequest(token=tampered))


if __name__ == "__main__":
    unittest.main()
