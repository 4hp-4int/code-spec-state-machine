"""Simple async database tests to validate functionality."""

from datetime import datetime
from pathlib import Path
import shutil
import tempfile

import pytest

from agentic_spec.async_db import SQLiteBackend
from agentic_spec.exceptions import DatabaseError
from agentic_spec.models import SpecificationDB, SpecStatus


@pytest.mark.asyncio
async def test_sqlite_backend_basic_operations():
    """Test basic SQLite backend operations."""
    # Create temporary database
    temp_dir = tempfile.mkdtemp()
    try:
        db_path = Path(temp_dir) / "test.db"
        backend = SQLiteBackend(database_path=db_path)

        # Initialize
        await backend.initialize()

        # Create a sample specification
        spec = SpecificationDB(
            id="test-spec-123",
            title="Test Specification",
            inherits=[],
            created=datetime.now(),
            updated=datetime.now(),
            version="1.0",
            status=SpecStatus.DRAFT,
            parent_spec_id=None,
            child_spec_ids=[],
            context={"project": "test", "domain": "testing"},
            requirements={"functional": ["test"], "non_functional": ["fast"]},
            review_notes=["looks good"],
            context_parameters=None,
        )

        # Test CRUD operations
        spec_id = await backend.create_specification(spec)
        assert spec_id == spec.id

        retrieved_spec = await backend.get_specification(spec_id)
        assert retrieved_spec is not None
        assert retrieved_spec.title == "Test Specification"

        # Test list
        specs = await backend.list_specifications()
        assert len(specs) == 1

        # Clean up
        await backend.close()

    finally:
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_sqlite_backend_transaction():
    """Test transaction functionality."""
    temp_dir = tempfile.mkdtemp()
    try:
        db_path = Path(temp_dir) / "test.db"
        backend = SQLiteBackend(database_path=db_path)
        await backend.initialize()

        spec = SpecificationDB(
            id="transaction-test",
            title="Transaction Test",
            inherits=[],
            created=datetime.now(),
            updated=datetime.now(),
            version="1.0",
            status=SpecStatus.DRAFT,
            context={"project": "test"},
            requirements={"functional": ["test"]},
        )

        # Test successful transaction
        async with backend.transaction():
            await backend.create_specification(spec)

        # Verify spec was saved
        result = await backend.get_specification("transaction-test")
        assert result is not None

        await backend.close()

    finally:
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_database_not_initialized():
    """Test operations fail when database not initialized."""
    backend = SQLiteBackend("test.db")

    spec = SpecificationDB(
        id="test",
        title="test",
        inherits=[],
        created=datetime.now(),
        updated=datetime.now(),
        version="1.0",
        status=SpecStatus.DRAFT,
        context={},
        requirements={},
    )

    with pytest.raises(DatabaseError, match="Database not initialized"):
        await backend.create_specification(spec)
