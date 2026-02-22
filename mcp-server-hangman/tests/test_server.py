"""Test cases for hangman MCP server tools."""

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from mcp_server_hangman.dependencies import get_hangman_service
from mcp_server_hangman.hangman.module import HangmanService
from mcp_server_hangman.hybrid_routers.guess_letter import guess_letter
from mcp_server_hangman.hybrid_routers.guess_letter import router as guess_letter_router
from mcp_server_hangman.hybrid_routers.start_game import router as start_game_router
from mcp_server_hangman.hybrid_routers.start_game import start_game
from mcp_server_hangman.schemas import GuessLetterRequest, StartGameRequest


@pytest.mark.asyncio
async def test_start_and_guess_happy_path():
    service = HangmanService()

    # Start
    request = StartGameRequest(secret_word="Go", max_attempts=3)
    state = await start_game(request=request, service=service)
    assert state.player_id
    assert state.masked_chars == list("__")
    assert state.remaining_attempts == 3

    # Guess correctly and win
    guess_req = GuessLetterRequest(player_id=state.player_id, letter="g")
    state = await guess_letter(request=guess_req, service=service)
    assert "".join(state.masked_chars).lower() == "g_"
    guess_req = GuessLetterRequest(player_id=state.player_id, letter="o")
    state = await guess_letter(request=guess_req, service=service)
    assert state.won is True
    assert "".join(state.masked_chars).lower() == "go"


@pytest.mark.asyncio
async def test_guess_invalid_then_repeat_no_penalty():
    service = HangmanService()

    request = StartGameRequest(secret_word="Hi", max_attempts=2)
    state = await start_game(request=request, service=service)
    pid = state.player_id

    # Invalid guess -> HTTPException
    with pytest.raises(HTTPException):
        guess_req = GuessLetterRequest(player_id=pid, letter="12")
        await guess_letter(request=guess_req, service=service)

    # Incorrect then repeat
    guess_req = GuessLetterRequest(player_id=pid, letter="x")
    state = await guess_letter(request=guess_req, service=service)
    assert state.remaining_attempts == 1
    state = await guess_letter(request=guess_req, service=service)
    assert state.remaining_attempts == 1


@pytest.mark.asyncio
async def test_start_game_rejects_non_letters():
    service = HangmanService()
    with pytest.raises(HTTPException):
        request = StartGameRequest(secret_word="Abc123", max_attempts=6)
        await start_game(request=request, service=service)
    with pytest.raises(HTTPException):
        request = StartGameRequest(secret_word="Ice-Cream!", max_attempts=6)
        await start_game(request=request, service=service)


@pytest.mark.asyncio
async def test_loose_game_sequence():
    service = HangmanService()

    request = StartGameRequest(secret_word="No", max_attempts=2)
    state = await start_game(request=request, service=service)
    pid = state.player_id
    # Wrong twice -> attempts 0, not won; game becomes invalid
    guess_req = GuessLetterRequest(player_id=pid, letter="x")
    state = await guess_letter(request=guess_req, service=service)
    assert state.remaining_attempts == 1 and state.won is False
    guess_req = GuessLetterRequest(player_id=pid, letter="y")
    state = await guess_letter(request=guess_req, service=service)
    assert state.remaining_attempts == 0 and state.won is False
    # Further guesses should now raise HTTPException due to invalidated game
    with pytest.raises(HTTPException):
        guess_req = GuessLetterRequest(player_id=pid, letter="z")
        await guess_letter(request=guess_req, service=service)


@pytest.mark.asyncio
async def test_win_scenario_server():
    service = HangmanService()

    request = StartGameRequest(secret_word="Go", max_attempts=3)
    state = await start_game(request=request, service=service)
    pid = state.player_id
    guess_req = GuessLetterRequest(player_id=pid, letter="g")
    state = await guess_letter(request=guess_req, service=service)
    assert "".join(state.masked_chars).lower() == "g_" and state.won is False
    guess_req = GuessLetterRequest(player_id=pid, letter="o")
    state = await guess_letter(request=guess_req, service=service)
    assert state.won is True
    # After win, guesses should error (game terminated)
    with pytest.raises(HTTPException):
        guess_req = GuessLetterRequest(player_id=pid, letter="x")
        await guess_letter(request=guess_req, service=service)


@pytest.mark.asyncio
async def test_start_game_invalid_secret_raises():
    service = HangmanService()
    with pytest.raises(HTTPException):
        request = StartGameRequest(secret_word="", max_attempts=3)
        await start_game(request=request, service=service)


@pytest.mark.asyncio
async def test_guess_without_game():
    service = HangmanService()
    with pytest.raises(HTTPException):
        guess_req = GuessLetterRequest(player_id="nonexistent", letter="a")
        await guess_letter(request=guess_req, service=service)


@pytest.mark.asyncio
async def test_start_game_endpoint_via_http():
    """HTTP-level test for start_game endpoint."""
    service = HangmanService()
    app = FastAPI()
    app.include_router(start_game_router, prefix="/hybrid")
    app.dependency_overrides[get_hangman_service] = lambda: service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/hybrid/start-game",
            json={"secret_word": "Test", "max_attempts": 5},
        )

    assert response.status_code == 200
    data = response.json()
    assert "player_id" in data
    assert data["masked_chars"] == ["_", "_", "_", "_"]
    assert data["remaining_attempts"] == 5


@pytest.mark.asyncio
async def test_guess_letter_endpoint_via_http():
    """HTTP-level test for guess_letter endpoint."""
    service = HangmanService()
    app = FastAPI()
    app.include_router(start_game_router, prefix="/hybrid")
    app.include_router(guess_letter_router, prefix="/hybrid")
    app.dependency_overrides[get_hangman_service] = lambda: service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Start game first
        start_response = await client.post(
            "/hybrid/start-game",
            json={"secret_word": "Go", "max_attempts": 3},
        )
        assert start_response.status_code == 200
        player_id = start_response.json()["player_id"]

        # Guess a letter
        guess_response = await client.post(
            "/hybrid/guess-letter",
            json={"player_id": player_id, "letter": "g"},
        )

    assert guess_response.status_code == 200
    data = guess_response.json()
    assert "".join(data["masked_chars"]).lower() == "g_"
    assert data["remaining_attempts"] == 3


@pytest.mark.asyncio
async def test_guess_letter_invalid_player_returns_404():
    """HTTP-level validation for invalid player_id."""
    service = HangmanService()
    app = FastAPI()
    app.include_router(guess_letter_router, prefix="/hybrid")
    app.dependency_overrides[get_hangman_service] = lambda: service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/hybrid/guess-letter",
            json={"player_id": "nonexistent", "letter": "a"},
        )

    assert response.status_code == 404
