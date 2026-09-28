import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session


@pytest.fixture
def mock_db_session():
    """Fixture que simula uma sessão de banco de dados do SQLAlchemy."""
    session = MagicMock(spec=Session)
    return session
