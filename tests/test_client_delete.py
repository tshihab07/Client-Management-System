from types import SimpleNamespace

import pytest
from bson import ObjectId

from routers.clients import delete_client


@pytest.mark.asyncio
async def test_delete_client_removes_record_and_redirects():
    deleted_query = {}

    class FakeCollection:
        def delete_one(self, query):
            deleted_query["query"] = query["_id"]
            return SimpleNamespace(deleted_count=1)

    client_id = "507f1f77bcf86cd799439011"
    response = await delete_client(client_id, collection=FakeCollection())

    assert response.status_code == 303
    assert response.headers["location"].startswith("/view")
    assert "message=Client%20removed%20successfully" in response.headers["location"]
    assert deleted_query["query"] == ObjectId(client_id)
