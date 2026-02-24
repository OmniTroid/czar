from tests.mock import MockClient


async def test_handshake(test_server):
    """Connect, perform the full handshake, and verify key state."""
    async with MockClient(test_server._test_host, test_server._test_port) as client:
        info = await client.handshake()

        assert info["player_id"] is not None
        assert len(info["char_list"]) > 0
        assert "noencryption" in info["features"]


async def test_select_character(test_server):
    """After handshake, select a character and receive PV."""
    async with MockClient(test_server._test_host, test_server._test_port) as client:
        await client.handshake()
        cmd, args = await client.select_character(0)

        assert cmd == "PV"
        assert client.char_id == 0


async def test_send_ic_message(test_server):
    """Select a character then send an IC message and receive the broadcast."""
    async with MockClient(test_server._test_host, test_server._test_port) as client:
        await client.handshake()
        await client.select_character(0)

        await client.send_ic_message("Hello from test!")
        cmd, args = await client.recv_until("MS")

        # The broadcast MS packet should contain our message text at index 4
        assert args[4] == "Hello from test!"
